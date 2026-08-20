"""Tests for the CapexQuant synthetic public dataset generator."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.analytics import (
    calculate_revenue_concentration,
    create_overview_summary,
    create_scope_comparison,
)
from src.clean_data import clean_sabi_data
from src.financial_features import (
    FINANCIAL_FEATURE_COLUMNS,
    add_financial_features,
)
from src.generate_synthetic_data import (
    COMPANY_COUNT,
    DEFAULT_METADATA_PATH,
    DEFAULT_OUTPUT_PATH,
    RANDOM_SEED,
    STANDARD_COLUMNS,
    build_company_names,
    calculate_file_sha256,
    export_synthetic_dataset,
    generate_synthetic_companies,
)
from src.quality_control import (
    QUALITY_CONTROL_COLUMNS,
    add_quality_controls,
    create_quality_summary,
)


EXPECTED_ROWS = 120
EXPECTED_SOURCE_COLUMNS = 10
EXPECTED_CLEAN_COLUMNS = 16
EXPECTED_FINANCIAL_COLUMNS = 28
EXPECTED_QUALITY_COLUMNS = 36

EXPECTED_LEGAL_STATUS_COUNTS = {
    "no_adverse_marker": 112,
    "extinct": 4,
    "in_liquidation": 3,
    "in_dissolution": 1,
}

NUMERIC_SOURCE_COLUMNS = [
    "record_order",
    "employees_latest",
    "operating_revenue_latest_k_eur",
    "operating_revenue_previous_k_eur",
    "ebitda_latest_k_eur",
    "ebitda_previous_k_eur",
]

FINANCIAL_VALUE_COLUMNS = [
    "operating_revenue_latest_k_eur",
    "operating_revenue_previous_k_eur",
    "ebitda_latest_k_eur",
    "ebitda_previous_k_eur",
]

FORBIDDEN_REAL_COMPANY_TERMS = [
    "BP ENERGIA",
    "BP OIL",
    "PAMESA",
    "PORCELANOSA",
    "UBE CORPORATION",
    "ARGENTA CERAMICA",
    "MARTINAVARRO",
    "COMPACGLASS",
]


@pytest.fixture(scope="module")
def synthetic_dataframe() -> pd.DataFrame:
    """Generate the standard synthetic dataset once."""

    return generate_synthetic_companies()


@pytest.fixture(scope="module")
def synthetic_pipeline_dataframes(
    synthetic_dataframe: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Run the synthetic dataset through the public pipeline."""

    cleaned_dataframe = clean_sabi_data(
        synthetic_dataframe
    )

    financial_dataframe = add_financial_features(
        cleaned_dataframe
    )

    quality_dataframe = add_quality_controls(
        financial_dataframe
    )

    return {
        "source": synthetic_dataframe,
        "clean": cleaned_dataframe,
        "financial": financial_dataframe,
        "quality": quality_dataframe,
    }


def test_default_generation_dimensions(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """The default generator must create 120 rows and 10 columns."""

    assert synthetic_dataframe.shape == (
        EXPECTED_ROWS,
        EXPECTED_SOURCE_COLUMNS,
    )


def test_exact_standardized_schema(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """The synthetic source must reproduce the standardized schema."""

    assert (
        synthetic_dataframe.columns.tolist()
        == STANDARD_COLUMNS
    )

    assert len(STANDARD_COLUMNS) == (
        EXPECTED_SOURCE_COLUMNS
    )

    assert len(STANDARD_COLUMNS) == len(
        set(STANDARD_COLUMNS)
    )


def test_default_constants_are_stable() -> None:
    """Public generation defaults must remain explicit and stable."""

    assert COMPANY_COUNT == EXPECTED_ROWS
    assert RANDOM_SEED == 20260820


def test_same_seed_produces_identical_data() -> None:
    """The same random seed must reproduce the same DataFrame."""

    first_dataframe = generate_synthetic_companies(
        company_count=EXPECTED_ROWS,
        random_seed=RANDOM_SEED,
    )

    second_dataframe = generate_synthetic_companies(
        company_count=EXPECTED_ROWS,
        random_seed=RANDOM_SEED,
    )

    assert_frame_equal(
        first_dataframe,
        second_dataframe,
        check_dtype=True,
        check_exact=True,
    )


def test_different_seed_changes_financial_data() -> None:
    """A different seed must change at least part of the simulation."""

    first_dataframe = generate_synthetic_companies(
        company_count=EXPECTED_ROWS,
        random_seed=RANDOM_SEED,
    )

    second_dataframe = generate_synthetic_companies(
        company_count=EXPECTED_ROWS,
        random_seed=RANDOM_SEED + 1,
    )

    assert not first_dataframe[
        FINANCIAL_VALUE_COLUMNS
    ].equals(
        second_dataframe[
            FINANCIAL_VALUE_COLUMNS
        ]
    )


@pytest.mark.parametrize(
    "invalid_company_count",
    [
        0,
        -1,
        1.5,
        True,
        "120",
    ],
)
def test_invalid_company_count_is_rejected(
    invalid_company_count: object,
) -> None:
    """The company count must be a strictly positive integer."""

    with pytest.raises(
        ValueError,
        match="company_count must be a positive integer",
    ):
        generate_synthetic_companies(
            company_count=invalid_company_count,
        )


@pytest.mark.parametrize(
    "invalid_random_seed",
    [
        1.5,
        True,
        "20260820",
        None,
    ],
)
def test_invalid_random_seed_is_rejected(
    invalid_random_seed: object,
) -> None:
    """The random seed must be an integer."""

    with pytest.raises(
        ValueError,
        match="random_seed must be an integer",
    ):
        generate_synthetic_companies(
            random_seed=invalid_random_seed,
        )


def test_company_names_are_unique(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Every synthetic company name must be unique."""

    assert synthetic_dataframe[
        "company_name"
    ].is_unique


def test_company_names_are_never_missing(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Every synthetic observation must have a company name."""

    assert synthetic_dataframe[
        "company_name"
    ].notna().all()


def test_all_company_names_are_explicitly_synthetic(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Every company name must clearly identify fictional data."""

    company_names = synthetic_dataframe[
        "company_name"
    ].str.upper()

    assert company_names.str.startswith(
        "SYNTHETIC "
    ).all()


def test_generated_names_are_deterministic() -> None:
    """The company-name builder must generate deterministic names."""

    first_names = build_company_names(20)
    second_names = build_company_names(20)

    assert first_names == second_names
    assert len(first_names) == 20
    assert len(set(first_names)) == 20


def test_known_real_company_names_are_absent(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Known companies from the private analysis must not appear."""

    combined_names = " ".join(
        synthetic_dataframe[
            "company_name"
        ].astype(str)
    ).upper()

    for forbidden_term in FORBIDDEN_REAL_COMPANY_TERMS:
        assert forbidden_term not in combined_names


def test_websites_use_reserved_example_domain(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Every available website must use the reserved .example domain."""

    available_websites = synthetic_dataframe[
        "website"
    ].dropna()

    assert not available_websites.empty

    assert available_websites.str.startswith(
        "https://"
    ).all()

    assert available_websites.str.endswith(
        ".example"
    ).all()


def test_websites_are_unique_when_available(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Available fictional websites must be unique."""

    available_websites = synthetic_dataframe[
        "website"
    ].dropna()

    assert available_websites.is_unique


def test_shareholders_are_synthetic_when_available(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Every available shareholder name must be fictional."""

    available_shareholders = synthetic_dataframe[
        "shareholder_name"
    ].dropna()

    assert not available_shareholders.empty

    assert available_shareholders.str.startswith(
        "SYNTHETIC HOLDING "
    ).all()


def test_numeric_source_columns_use_numeric_dtypes(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Employment, order and financial fields must be numeric."""

    for column in NUMERIC_SOURCE_COLUMNS:
        assert pd.api.types.is_numeric_dtype(
            synthetic_dataframe[column]
        ), f"{column} is not numeric"


def test_record_order_is_sequential(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """The synthetic record-order field must be sequential."""

    expected_order = list(
        range(1, EXPECTED_ROWS + 1)
    )

    assert synthetic_dataframe[
        "record_order"
    ].tolist() == expected_order


def test_employee_filter_is_respected(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """Every synthetic company must have at least five employees."""

    assert (
        synthetic_dataframe[
            "employees_latest"
        ] >= 5
    ).all()


def test_financial_data_contains_missing_values(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """The synthetic dataset must contain controlled missing values."""

    missing_count = int(
        synthetic_dataframe[
            FINANCIAL_VALUE_COLUMNS
        ].isna().sum().sum()
    )

    assert missing_count > 0


def test_revenue_contains_growth_and_decline_cases(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """The simulation must contain both revenue growth and decline."""

    comparable_records = synthetic_dataframe.dropna(
        subset=[
            "operating_revenue_latest_k_eur",
            "operating_revenue_previous_k_eur",
        ]
    )

    revenue_change = (
        comparable_records[
            "operating_revenue_latest_k_eur"
        ]
        - comparable_records[
            "operating_revenue_previous_k_eur"
        ]
    )

    assert revenue_change.gt(0).any()
    assert revenue_change.lt(0).any()


def test_ebitda_contains_positive_and_negative_cases(
    synthetic_dataframe: pd.DataFrame,
) -> None:
    """The simulation must include profitable and loss-making cases."""

    latest_ebitda = synthetic_dataframe[
        "ebitda_latest_k_eur"
    ].dropna()

    assert latest_ebitda.gt(0).any()
    assert latest_ebitda.lt(0).any()


def test_legal_status_distribution(
    synthetic_pipeline_dataframes: dict[
        str,
        pd.DataFrame,
    ],
) -> None:
    """Synthetic legal markers must produce the expected statuses."""

    cleaned_dataframe = (
        synthetic_pipeline_dataframes["clean"]
    )

    actual_counts = (
        cleaned_dataframe["legal_status"]
        .value_counts()
        .to_dict()
    )

    assert actual_counts == (
        EXPECTED_LEGAL_STATUS_COUNTS
    )


def test_every_expected_adverse_status_exists(
    synthetic_pipeline_dataframes: dict[
        str,
        pd.DataFrame,
    ],
) -> None:
    """All supported adverse legal-status categories must be present."""

    cleaned_dataframe = (
        synthetic_pipeline_dataframes["clean"]
    )

    observed_statuses = set(
        cleaned_dataframe["legal_status"]
    )

    assert {
        "extinct",
        "in_liquidation",
        "in_dissolution",
    }.issubset(observed_statuses)



    

def test_pipeline_preserves_row_count(
    synthetic_pipeline_dataframes: dict[str, pd.DataFrame],
) -> None:
    """Every public pipeline layer must preserve all records."""

    assert len(
        synthetic_pipeline_dataframes["source"]
    ) == EXPECTED_ROWS

    assert len(
        synthetic_pipeline_dataframes["clean"]
    ) == EXPECTED_ROWS

    assert len(
        synthetic_pipeline_dataframes["financial"]
    ) == EXPECTED_ROWS

    assert len(
        synthetic_pipeline_dataframes["quality"]
    ) == EXPECTED_ROWS


def test_pipeline_column_progression(
    synthetic_pipeline_dataframes: dict[str, pd.DataFrame],
) -> None:
    """The dataset must traverse the expected pipeline schemas."""

    assert synthetic_pipeline_dataframes[
        "source"
    ].shape[1] == EXPECTED_SOURCE_COLUMNS

    assert synthetic_pipeline_dataframes[
        "clean"
    ].shape[1] == EXPECTED_CLEAN_COLUMNS

    assert synthetic_pipeline_dataframes[
        "financial"
    ].shape[1] == EXPECTED_FINANCIAL_COLUMNS

    assert synthetic_pipeline_dataframes[
        "quality"
    ].shape[1] == EXPECTED_QUALITY_COLUMNS


def test_metadata_dimensions(
    tmp_path: Path,
) -> None:
    """Metadata must describe the exported dataset dimensions."""

    output_path = tmp_path / "companies_synthetic.csv"
    metadata_path = tmp_path / "metadata.json"

    dataframe, metadata = export_synthetic_dataset(
        output_path=output_path,
        metadata_path=metadata_path,
    )

    assert metadata["company_count"] == len(dataframe)
    assert metadata["column_count"] == len(dataframe.columns)
    assert metadata["random_seed"] == RANDOM_SEED


def test_default_public_paths_use_sample_directory() -> None:
    """Public artifacts must use the data/sample directory."""

    assert DEFAULT_OUTPUT_PATH.parent.name == "sample"
    assert DEFAULT_METADATA_PATH.parent.name == "sample"
    assert DEFAULT_OUTPUT_PATH.name == "companies_synthetic.csv"
    assert (
        DEFAULT_METADATA_PATH.name
        == "companies_synthetic_metadata.json"
    )