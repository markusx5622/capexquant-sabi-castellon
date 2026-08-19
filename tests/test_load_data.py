"""Automated tests for the CapexQuant SABI data-ingestion module."""

from pathlib import Path

import pandas as pd
import pytest

from src.load_data import (
    DEFAULT_DATA_PATH,
    NUMERIC_COLUMNS,
    STANDARD_COLUMN_NAMES,
    load_sabi_data,
    validate_source_file,
)


EXPECTED_STANDARD_COLUMNS = list(STANDARD_COLUMN_NAMES.values())

EXPECTED_ROWS = 6_711
EXPECTED_COLUMNS = 10


@pytest.fixture(scope="module")
def sabi_dataframe() -> pd.DataFrame:
    """
    Load the private SABI dataset once for the integration tests.

    The module scope prevents the Excel workbook from being loaded
    repeatedly for every individual test.
    """
    return load_sabi_data()


def test_source_workbook_exists() -> None:
    """The private SABI workbook must exist locally."""

    assert DEFAULT_DATA_PATH.exists()
    assert DEFAULT_DATA_PATH.is_file()
    assert DEFAULT_DATA_PATH.suffix.lower() == ".xlsx"


def test_missing_source_file_raises_error(
    tmp_path: Path,
) -> None:
    """A nonexistent workbook must raise FileNotFoundError."""

    missing_file = tmp_path / "missing.xlsx"

    with pytest.raises(FileNotFoundError):
        validate_source_file(missing_file)


def test_invalid_extension_raises_error(
    tmp_path: Path,
) -> None:
    """A source file with an invalid extension must raise ValueError."""

    invalid_file = tmp_path / "invalid.csv"

    invalid_file.write_text(
        "company,revenue",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        validate_source_file(invalid_file)


def test_dataset_dimensions(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """The original SABI extraction must contain the expected dimensions."""

    assert sabi_dataframe.shape == (
        EXPECTED_ROWS,
        EXPECTED_COLUMNS,
    )


def test_standardized_columns(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """The loader must return the expected standardized column names."""

    assert (
        sabi_dataframe.columns.tolist()
        == EXPECTED_STANDARD_COLUMNS
    )


def test_numeric_columns_are_numeric(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """Employment and financial fields must use numeric data types."""

    for column in NUMERIC_COLUMNS:
        assert pd.api.types.is_numeric_dtype(
            sabi_dataframe[column]
        ), f"{column} is not numeric"


def test_dataset_is_not_empty(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """The loaded dataset must contain company records."""

    assert not sabi_dataframe.empty


def test_company_names_are_complete(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """Every record must contain a company name."""

    assert sabi_dataframe["company_name"].notna().all()


def test_company_names_are_non_empty(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """Company names must not contain empty strings."""

    company_names = sabi_dataframe[
        "company_name"
    ].astype(str).str.strip()

    assert company_names.ne("").all()


def test_missing_financial_values_exist(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """
    Missing SABI financial values must have been converted to NaN.

    The source dataset contains unavailable financial observations,
    so at least one missing value should exist after ingestion.
    """

    financial_columns = [
        "operating_revenue_latest_k_eur",
        "operating_revenue_previous_k_eur",
        "ebitda_latest_k_eur",
        "ebitda_previous_k_eur",
    ]

    total_missing = (
        sabi_dataframe[financial_columns]
        .isna()
        .sum()
        .sum()
    )

    assert total_missing > 0


def test_employee_values_are_positive(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """
    Employee counts must respect the original SABI search criterion.

    The extraction strategy requires at least five employees.
    """

    assert (
        sabi_dataframe["employees_latest"] >= 5
    ).all()


def test_record_order_is_unique(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """The source record-order field must contain unique values."""

    assert sabi_dataframe["record_order"].is_unique


def test_record_order_has_no_missing_values(
    sabi_dataframe: pd.DataFrame,
) -> None:
    """Every source observation must contain a record-order value."""

    assert sabi_dataframe["record_order"].notna().all()