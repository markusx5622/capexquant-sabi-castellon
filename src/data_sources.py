"""Unified data-source access for CapexQuant SABI Castellón."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

from src.generate_synthetic_data import (
    DEFAULT_OUTPUT_PATH as DEFAULT_SYNTHETIC_PATH,
    STANDARD_COLUMNS,
    export_synthetic_dataset,
)
from src.load_data import (
    DEFAULT_DATA_PATH as DEFAULT_SABI_PATH,
    load_sabi_data,
)


SUPPORTED_SOURCES: Final[frozenset[str]] = frozenset(
    {
        "synthetic",
        "sabi",
    }
)

NUMERIC_STANDARD_COLUMNS: Final[tuple[str, ...]] = (
    "record_order",
    "employees_latest",
    "operating_revenue_latest_k_eur",
    "operating_revenue_previous_k_eur",
    "ebitda_latest_k_eur",
    "ebitda_previous_k_eur",
)

TEXT_STANDARD_COLUMNS: Final[tuple[str, ...]] = (
    "company_name",
    "website",
    "municipality",
    "shareholder_name",
)


def normalize_source_name(
    source: str,
) -> str:
    """Normalize and validate a supported source name."""

    if not isinstance(source, str):
        raise TypeError(
            "source must be a string."
        )

    normalized_source = source.strip().lower()

    if normalized_source not in SUPPORTED_SOURCES:
        supported_sources = ", ".join(
            sorted(SUPPORTED_SOURCES)
        )

        raise ValueError(
            f"Unsupported data source: {source!r}. "
            f"Expected one of: {supported_sources}."
        )

    return normalized_source


def validate_standardized_schema(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate the standardized CapexQuant source schema.

    The validation is strict: missing, unexpected or reordered
    columns are rejected.
    """

    actual_columns = dataframe.columns.tolist()

    missing_columns = [
        column
        for column in STANDARD_COLUMNS
        if column not in actual_columns
    ]

    unexpected_columns = [
        column
        for column in actual_columns
        if column not in STANDARD_COLUMNS
    ]

    if missing_columns or unexpected_columns:
        raise ValueError(
            "Invalid standardized source schema. "
            f"Missing columns: {missing_columns}. "
            f"Unexpected columns: {unexpected_columns}."
        )

    if actual_columns != STANDARD_COLUMNS:
        raise ValueError(
            "Standardized source columns are not in the "
            "expected order."
        )


def validate_standardized_data(
    dataframe: pd.DataFrame,
) -> None:
    """Validate structural and semantic source requirements."""

    validate_standardized_schema(dataframe)

    if dataframe.empty:
        raise ValueError(
            "The standardized source dataset is empty."
        )

    if dataframe["record_order"].isna().any():
        raise ValueError(
            "record_order contains missing values."
        )

    if not dataframe["record_order"].is_unique:
        raise ValueError(
            "record_order must contain unique values."
        )

    if dataframe["company_name"].isna().any():
        raise ValueError(
            "company_name contains missing values."
        )

    empty_company_names = (
        dataframe["company_name"]
        .astype(str)
        .str.strip()
        .eq("")
    )

    if empty_company_names.any():
        raise ValueError(
            "company_name contains empty values."
        )

    for column in NUMERIC_STANDARD_COLUMNS:
        if not pd.api.types.is_numeric_dtype(
            dataframe[column]
        ):
            raise TypeError(
                f"Standardized column is not numeric: {column}"
            )


def standardize_source_dtypes(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize source data types without imputing missing values.

    Financial missing values remain NaN. Textual missing values
    remain missing and are not replaced by empty strings.
    """

    standardized_dataframe = dataframe.copy()

    for column in NUMERIC_STANDARD_COLUMNS:
        standardized_dataframe[column] = pd.to_numeric(
            standardized_dataframe[column],
            errors="coerce",
        )

    standardized_dataframe[
        "record_order"
    ] = standardized_dataframe[
        "record_order"
    ].astype("Int64")

    standardized_dataframe[
        "employees_latest"
    ] = standardized_dataframe[
        "employees_latest"
    ].astype("Int64")

    for column in TEXT_STANDARD_COLUMNS:
        standardized_dataframe[column] = (
            standardized_dataframe[column]
            .astype("string")
        )

    return standardized_dataframe


def load_synthetic_data(
    file_path: Path | str = DEFAULT_SYNTHETIC_PATH,
    generate_if_missing: bool = True,
) -> pd.DataFrame:
    """
    Load the public synthetic CSV using the standardized schema.

    If the default file does not exist, it may be generated
    deterministically.
    """

    normalized_path = Path(file_path)

    if not normalized_path.exists():
        if not generate_if_missing:
            raise FileNotFoundError(
                "Synthetic dataset not found at: "
                f"{normalized_path}"
            )

        export_synthetic_dataset(
            output_path=normalized_path,
        )

    if normalized_path.suffix.lower() != ".csv":
        raise ValueError(
            "Synthetic source must be a CSV file."
        )

    dataframe = pd.read_csv(
        normalized_path,
        encoding="utf-8",
        keep_default_na=True,
    )

    dataframe = standardize_source_dtypes(
        dataframe
    )

    validate_standardized_data(
        dataframe
    )

    return dataframe


def load_data_source(
    source: str = "synthetic",
    file_path: Path | str | None = None,
    generate_if_missing: bool = True,
) -> pd.DataFrame:
    """
    Load a supported CapexQuant source with a common schema.

    Parameters
    ----------
    source:
        Either ``synthetic`` or ``sabi``.

    file_path:
        Optional custom source path. When omitted, the default
        path for the selected source is used.

    generate_if_missing:
        Applies only to the synthetic source. When True, a missing
        synthetic CSV is generated deterministically.

    Returns
    -------
    pandas.DataFrame
        A validated DataFrame using the standardized ten-column
        CapexQuant source schema.
    """

    normalized_source = normalize_source_name(
        source
    )

    if normalized_source == "synthetic":
        selected_path = (
            DEFAULT_SYNTHETIC_PATH
            if file_path is None
            else Path(file_path)
        )

        dataframe = load_synthetic_data(
            file_path=selected_path,
            generate_if_missing=generate_if_missing,
        )

    else:
        selected_path = (
            DEFAULT_SABI_PATH
            if file_path is None
            else Path(file_path)
        )

        dataframe = load_sabi_data(
            file_path=selected_path
        )

        dataframe = standardize_source_dtypes(
            dataframe
        )

        validate_standardized_data(
            dataframe
        )

    return dataframe


if __name__ == "__main__":
    source_dataframe = load_data_source(
        source="synthetic"
    )

    print("Data source loaded successfully.")
    print("Source: synthetic")
    print(f"Rows: {len(source_dataframe):,}")
    print(
        f"Columns: {len(source_dataframe.columns)}"
    )
    print(
        "Schema valid: "
        f"{source_dataframe.columns.tolist() == STANDARD_COLUMNS}"
    )
    print("\nData types:")
    print(source_dataframe.dtypes.to_string())