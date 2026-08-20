"""Tests for the unified CapexQuant data-source layer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.data_sources import (
    NUMERIC_STANDARD_COLUMNS,
    SUPPORTED_SOURCES,
    load_data_source,
    load_synthetic_data,
    normalize_source_name,
    standardize_source_dtypes,
    validate_standardized_data,
    validate_standardized_schema,
)
from src.generate_synthetic_data import (
    RANDOM_SEED,
    STANDARD_COLUMNS,
    export_synthetic_dataset,
    generate_synthetic_companies,
)
from src.load_data import DEFAULT_DATA_PATH


EXPECTED_SYNTHETIC_ROWS = 120
EXPECTED_SABI_ROWS = 6_711
EXPECTED_COLUMNS = 10


@pytest.fixture(scope="module")
def synthetic_dataframe() -> pd.DataFrame:
    """Load the committed public synthetic source once."""

    return load_data_source(
        source="synthetic"
    )


def test_supported_sources_are_explicit() -> None:
    """The public API must expose exactly two source types."""

    assert SUPPORTED_SOURCES == frozenset(
        {
            "synthetic",
            "sabi",
        }
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("synthetic", "synthetic"),
        ("SYNTHETIC", "synthetic"),
        (" synthetic ", "synthetic"),
        ("sabi", "sabi"),
        ("SABI", "sabi"),
        (" sabi ", "sabi"),
    ],
)
def test_source_name_normalization(
    source: str,
    expected: str,
) -> None:
    """Source names must be normalized deterministically."""

    assert normalize_source_name(source) == expected


@pytest.mark.parametrize(
    "invalid_source",
    [
        "",
        "excel",
        "private",
        "csv",
        "unknown",
    ],
)
def test_unsupported_source_is_rejected(
    invalid_source: str,
) -> None:
    """Unsupported source names must raise an explicit error."""

    with pytest.raises(
        ValueError,
        match="Unsupported data source",
    ):
        normalize_source_name(invalid_source)


@pytest.mark.parametrize(
    "invalid_source",
    [
        None,
        1,
        True,
        ["synthetic"],
    ],
)
def test_non_string_source_is_rejected(
    invalid_source: object,
) -> None:
    """A source selector must be supplied as text."""

    with pytest.raises(
        TypeError,
        match="source must be a string",
    ):
        normalize_source_name(invalid_source)


def test_synthetic_source_dimensions(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """The default synthetic source must contain 120 rows."""

    assert synthetic_dataframe.shape == (
        EXPECTED_SYNTHETIC_ROWS,
        EXPECTED_COLUMNS,
    )


def test_synthetic_source_schema(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """The synthetic source must expose the standard schema."""

    assert synthetic_dataframe.columns.tolist() == (
        STANDARD_COLUMNS
    )


def test_synthetic_source_numeric_types(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """All defined numeric fields must use numeric dtypes."""

    for column in NUMERIC_STANDARD_COLUMNS:
        assert pd.api.types.is_numeric_dtype(
            synthetic_dataframe[column]
        )


def test_synthetic_source_order_is_unique(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Synthetic record identifiers must be unique."""

    assert synthetic_dataframe[
        "record_order"
    ].is_unique

    assert synthetic_dataframe[
        "record_order"
    ].notna().all()


def test_synthetic_company_names_are_complete(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Synthetic company names must be complete."""

    assert synthetic_dataframe[
        "company_name"
    ].notna().all()

    assert synthetic_dataframe[
        "company_name"
    ].str.strip().ne("").all()


def test_schema_validation_accepts_valid_data(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """A valid standardized dataset must pass validation."""

    validate_standardized_schema(
        synthetic_dataframe
    )

    validate_standardized_data(
        synthetic_dataframe
    )


def test_schema_validation_rejects_missing_column(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """A missing standardized field must be rejected."""

    invalid_dataframe = synthetic_dataframe.drop(
        columns=["shareholder_name"]
    )

    with pytest.raises(
        ValueError,
        match="Invalid standardized source schema",
    ):
        validate_standardized_schema(
            invalid_dataframe
        )


def test_schema_validation_rejects_extra_column(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """An unexpected source field must be rejected."""

    invalid_dataframe = (
        synthetic_dataframe.copy()
    )

    invalid_dataframe[
        "unexpected_column"
    ] = "invalid"

    with pytest.raises(
        ValueError,
        match="Invalid standardized source schema",
    ):
        validate_standardized_schema(
            invalid_dataframe
        )


def test_schema_validation_rejects_wrong_order(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Reordered standardized columns must be rejected."""

    reordered_columns = (
        STANDARD_COLUMNS.copy()
    )

    reordered_columns[0], reordered_columns[1] = (
        reordered_columns[1],
        reordered_columns[0],
    )

    invalid_dataframe = synthetic_dataframe[
        reordered_columns
    ]

    with pytest.raises(
        ValueError,
        match="not in the expected order",
    ):
        validate_standardized_schema(
            invalid_dataframe
        )


def test_empty_standardized_data_is_rejected() -> None:
    """An empty standardized source must be rejected."""

    empty_dataframe = pd.DataFrame(
        columns=STANDARD_COLUMNS
    )

    empty_dataframe = standardize_source_dtypes(
        empty_dataframe
    )

    with pytest.raises(
        ValueError,
        match="source dataset is empty",
    ):
        validate_standardized_data(
            empty_dataframe
        )


def test_duplicate_record_order_is_rejected(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Duplicate source identifiers must be rejected."""

    invalid_dataframe = (
        synthetic_dataframe.copy()
    )

    invalid_dataframe.loc[
        invalid_dataframe.index[1],
        "record_order",
    ] = invalid_dataframe.loc[
        invalid_dataframe.index[0],
        "record_order",
    ]

    with pytest.raises(
        ValueError,
        match="record_order must contain unique values",
    ):
        validate_standardized_data(
            invalid_dataframe
        )


def test_missing_company_name_is_rejected(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Missing company names must be rejected."""

    invalid_dataframe = (
        synthetic_dataframe.copy()
    )

    invalid_dataframe.loc[
        invalid_dataframe.index[0],
        "company_name",
    ] = pd.NA

    with pytest.raises(
        ValueError,
        match="company_name contains missing values",
    ):
        validate_standardized_data(
            invalid_dataframe
        )


def test_empty_company_name_is_rejected(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Whitespace-only company names must be rejected."""

    invalid_dataframe = (
        synthetic_dataframe.copy()
    )

    invalid_dataframe.loc[
        invalid_dataframe.index[0],
        "company_name",
    ] = "   "

    with pytest.raises(
        ValueError,
        match="company_name contains empty values",
    ):
        validate_standardized_data(
            invalid_dataframe
        )


def test_dtype_standardization_does_not_mutate_input() -> None:
    """Dtype normalization must not mutate the supplied DataFrame."""

    dataframe = generate_synthetic_companies(
        company_count=20,
        random_seed=RANDOM_SEED,
    )

    original_dataframe = dataframe.copy(
        deep=True
    )

    standardize_source_dtypes(dataframe)

    assert_frame_equal(
        dataframe,
        original_dataframe,
        check_dtype=True,
    )


def test_dtype_standardization_converts_numeric_text() -> None:
    """Numeric text fields must be converted to numeric dtypes."""

    dataframe = generate_synthetic_companies(
        company_count=10,
        random_seed=RANDOM_SEED,
    )

    dataframe[
        "employees_latest"
    ] = dataframe[
        "employees_latest"
    ].astype(str)

    standardized_dataframe = (
        standardize_source_dtypes(
            dataframe
        )
    )

    assert pd.api.types.is_numeric_dtype(
        standardized_dataframe[
            "employees_latest"
        ]
    )


def test_missing_synthetic_file_is_rejected(
    tmp_path: Path,
) -> None:
    """A missing synthetic file must fail when generation is disabled."""

    missing_path = (
        tmp_path
        / "missing_synthetic.csv"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Synthetic dataset not found",
    ):
        load_synthetic_data(
            file_path=missing_path,
            generate_if_missing=False,
        )


def test_missing_synthetic_file_can_be_generated(
    tmp_path: Path,
) -> None:
    """A missing public source may be generated deterministically."""

    output_path = (
        tmp_path
        / "generated_synthetic.csv"
    )

    dataframe = load_synthetic_data(
        file_path=output_path,
        generate_if_missing=True,
    )

    assert output_path.exists()

    assert dataframe.shape == (
        EXPECTED_SYNTHETIC_ROWS,
        EXPECTED_COLUMNS,
    )


def test_invalid_synthetic_extension_is_rejected(
    tmp_path: Path,
) -> None:
    """The synthetic source loader must require a CSV file."""

    invalid_path = (
        tmp_path
        / "synthetic.xlsx"
    )

    invalid_path.write_text(
        "invalid",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Synthetic source must be a CSV file",
    ):
        load_synthetic_data(
            file_path=invalid_path,
        )


def test_custom_synthetic_source_path(
    tmp_path: Path,
) -> None:
    """The unified loader must accept a custom synthetic path."""

    output_path = (
        tmp_path
        / "custom_synthetic.csv"
    )

    metadata_path = (
        tmp_path
        / "custom_metadata.json"
    )

    expected_dataframe, _ = (
        export_synthetic_dataset(
            output_path=output_path,
            metadata_path=metadata_path,
            company_count=25,
            random_seed=12345,
        )
    )

    actual_dataframe = load_data_source(
        source="synthetic",
        file_path=output_path,
    )

    assert len(actual_dataframe) == 25

    assert (
        actual_dataframe.columns.tolist()
        == STANDARD_COLUMNS
    )

    assert (
        actual_dataframe["company_name"].tolist()
        == expected_dataframe[
            "company_name"
        ].tolist()
    )


def test_sabi_source_when_private_file_exists() -> None:
    """
    The private SABI source must expose the same schema.

    The test is skipped automatically in public environments where
    the licensed workbook is intentionally unavailable.
    """

    if not DEFAULT_DATA_PATH.exists():
        pytest.skip(
            "Private SABI workbook is not available."
        )

    dataframe = load_data_source(
        source="sabi"
    )

    assert dataframe.shape == (
        EXPECTED_SABI_ROWS,
        EXPECTED_COLUMNS,
    )

    assert dataframe.columns.tolist() == (
        STANDARD_COLUMNS
    )


def test_source_schema_equivalence(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """
    Public and private sources must expose equivalent schemas.

    The private comparison is skipped when the SABI workbook is not
    available.
    """

    if not DEFAULT_DATA_PATH.exists():
        pytest.skip(
            "Private SABI workbook is not available."
        )

    sabi_dataframe = load_data_source(
        source="sabi"
    )

    assert synthetic_dataframe.columns.tolist() == (
        sabi_dataframe.columns.tolist()
    )


def test_sabi_loader_does_not_generate_files(
    tmp_path: Path,
) -> None:
    """A missing SABI workbook must never be generated automatically."""

    missing_sabi_path = (
        tmp_path
        / "missing_sabi.xlsx"
    )

    with pytest.raises(
        FileNotFoundError,
    ):
        load_data_source(
            source="sabi",
            file_path=missing_sabi_path,
            generate_if_missing=True,
        )

    assert not missing_sabi_path.exists()