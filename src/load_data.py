"""Data-ingestion utilities for the CapexQuant SABI Castellón project."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "SABI Castellon Excel.xlsx"
)

RESULTS_SHEET = "Resultados"

EXPECTED_ORIGINAL_COLUMNS = [
    "Unnamed: 0",
    "Nombre",
    "Dirección web",
    "Localidad",
    "Ultimo número empleados",
    "Ingresos de explotación\nmil EUR\nÚlt. año disp.",
    "Ingresos de explotación\nmil EUR\nAño - 1",
    "EBITDA\nmil EUR\nÚlt. año disp.",
    "EBITDA\nmil EUR\nAño - 1",
    "Nombre accionista",
]

STANDARD_COLUMN_NAMES = {
    "Unnamed: 0": "record_order",
    "Nombre": "company_name",
    "Dirección web": "website",
    "Localidad": "municipality",
    "Ultimo número empleados": "employees_latest",
    "Ingresos de explotación\nmil EUR\nÚlt. año disp.": (
        "operating_revenue_latest_k_eur"
    ),
    "Ingresos de explotación\nmil EUR\nAño - 1": (
        "operating_revenue_previous_k_eur"
    ),
    "EBITDA\nmil EUR\nÚlt. año disp.": "ebitda_latest_k_eur",
    "EBITDA\nmil EUR\nAño - 1": "ebitda_previous_k_eur",
    "Nombre accionista": "shareholder_name",
}

NUMERIC_COLUMNS = [
    "employees_latest",
    "operating_revenue_latest_k_eur",
    "operating_revenue_previous_k_eur",
    "ebitda_latest_k_eur",
    "ebitda_previous_k_eur",
]


def validate_source_file(file_path: Path) -> None:
    """Validate that the private source workbook exists."""

    if not file_path.exists():
        raise FileNotFoundError(
            "SABI workbook not found. Expected file at: "
            f"{file_path}"
        )

    if file_path.suffix.lower() != ".xlsx":
        raise ValueError(
            f"Expected an .xlsx workbook, received: {file_path.suffix}"
        )


def validate_schema(dataframe: pd.DataFrame) -> None:
    """Validate that the source sheet contains the expected columns."""

    actual_columns = dataframe.columns.tolist()

    missing_columns = [
        column
        for column in EXPECTED_ORIGINAL_COLUMNS
        if column not in actual_columns
    ]

    unexpected_columns = [
        column
        for column in actual_columns
        if column not in EXPECTED_ORIGINAL_COLUMNS
    ]

    if missing_columns or unexpected_columns:
        raise ValueError(
            "Unexpected SABI schema.\n"
            f"Missing columns: {missing_columns}\n"
            f"Unexpected columns: {unexpected_columns}"
        )


def convert_numeric_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Convert financial and employment fields to numeric values."""

    cleaned_dataframe = dataframe.copy()

    for column in NUMERIC_COLUMNS:
        cleaned_dataframe[column] = pd.to_numeric(
            cleaned_dataframe[column],
            errors="coerce",
        )

    return cleaned_dataframe


def load_sabi_data(
    file_path: Path | str = DEFAULT_DATA_PATH,
) -> pd.DataFrame:
    """
    Load and minimally standardize the SABI results sheet.

    The function performs only ingestion-level transformations:

    1. validates the source file;
    2. reads the Results sheet;
    3. validates the original schema;
    4. renames columns;
    5. converts numeric fields;
    6. validates that the dataset is not empty.

    The function does not modify the source workbook.
    """

    normalized_path = Path(file_path)

    validate_source_file(normalized_path)

    dataframe = pd.read_excel(
        normalized_path,
        sheet_name=RESULTS_SHEET,
        engine="openpyxl",
        na_values=["n.d.", "n.d", "N.D.", "N/D"],
        keep_default_na=True,
    )

    validate_schema(dataframe)

    dataframe = dataframe.rename(
        columns=STANDARD_COLUMN_NAMES
    )

    dataframe = convert_numeric_columns(dataframe)

    if dataframe.empty:
        raise ValueError("The SABI Results sheet contains no records.")

    return dataframe


if __name__ == "__main__":
    sabi_dataframe = load_sabi_data()

    print("SABI data loaded successfully.")
    print(f"Rows: {len(sabi_dataframe):,}")
    print(f"Columns: {len(sabi_dataframe.columns)}")
    print("\nData types:")
    print(sabi_dataframe.dtypes)
    print("\nFirst five rows:")
    print(sabi_dataframe.head())