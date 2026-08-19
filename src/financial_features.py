"""Financial feature engineering for CapexQuant SABI Castellón."""

import numpy as np
import pandas as pd

from src.clean_data import clean_sabi_data


REVENUE_LATEST = "operating_revenue_latest_k_eur"
REVENUE_PREVIOUS = "operating_revenue_previous_k_eur"
EBITDA_LATEST = "ebitda_latest_k_eur"
EBITDA_PREVIOUS = "ebitda_previous_k_eur"
EMPLOYEES_LATEST = "employees_latest"

REQUIRED_FINANCIAL_COLUMNS = [
    REVENUE_LATEST,
    REVENUE_PREVIOUS,
    EBITDA_LATEST,
    EBITDA_PREVIOUS,
    EMPLOYEES_LATEST,
]

FINANCIAL_FEATURE_COLUMNS = [
    "revenue_growth",
    "revenue_change_k_eur",
    "ebitda_margin",
    "ebitda_change_k_eur",
    "revenue_per_employee_k_eur",
    "ebitda_per_employee_k_eur",
    "has_negative_latest_revenue",
    "has_zero_latest_revenue",
    "has_negative_latest_ebitda",
    "has_revenue_decline",
    "has_extreme_ebitda_margin",
    "has_incomplete_financial_data",
]


def validate_financial_schema(
    dataframe: pd.DataFrame,
) -> None:
    """Validate the columns required for financial calculations."""

    missing_columns = [
        column
        for column in REQUIRED_FINANCIAL_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns required for financial features: "
            f"{missing_columns}"
        )


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """
    Divide two numeric Series without producing infinite values.

    A missing numerator, missing denominator or zero denominator
    produces NaN.
    """

    valid_denominator = denominator.notna() & denominator.ne(0)
    valid_numerator = numerator.notna()
    valid_rows = valid_denominator & valid_numerator

    result = pd.Series(
        np.nan,
        index=numerator.index,
        dtype="float64",
    )

    result.loc[valid_rows] = (
        numerator.loc[valid_rows]
        / denominator.loc[valid_rows]
    )

    return result


def calculate_revenue_growth(
    dataframe: pd.DataFrame,
) -> pd.Series:
    """
    Calculate year-over-year operating-revenue growth.

    Formula
    -------
    latest revenue / previous revenue - 1

    Missing or zero previous revenue produces NaN.
    """

    revenue_ratio = safe_divide(
        dataframe[REVENUE_LATEST],
        dataframe[REVENUE_PREVIOUS],
    )

    return revenue_ratio - 1


def calculate_ebitda_margin(
    dataframe: pd.DataFrame,
) -> pd.Series:
    """
    Calculate the latest EBITDA margin.

    Formula
    -------
    latest EBITDA / latest operating revenue

    Missing or zero revenue produces NaN.
    """

    return safe_divide(
        dataframe[EBITDA_LATEST],
        dataframe[REVENUE_LATEST],
    )


def calculate_revenue_per_employee(
    dataframe: pd.DataFrame,
) -> pd.Series:
    """
    Calculate latest operating revenue per employee.

    The result remains expressed in thousands of euros per employee.
    """

    return safe_divide(
        dataframe[REVENUE_LATEST],
        dataframe[EMPLOYEES_LATEST],
    )


def calculate_ebitda_per_employee(
    dataframe: pd.DataFrame,
) -> pd.Series:
    """
    Calculate latest EBITDA per employee.

    The result remains expressed in thousands of euros per employee.
    """

    return safe_divide(
        dataframe[EBITDA_LATEST],
        dataframe[EMPLOYEES_LATEST],
    )


def add_financial_features(
    dataframe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Add financial metrics and quality-control flags.

    The function does not remove records, winsorize observations,
    impute missing values or overwrite the original financial fields.

    Parameters
    ----------
    dataframe:
        Optional cleaned SABI DataFrame. If omitted, the complete
        ingestion and cleaning pipeline is executed.

    Returns
    -------
    pandas.DataFrame
        Input records with financial metrics and quality flags added.
    """

    if dataframe is None:
        dataframe = clean_sabi_data()

    if dataframe.empty:
        raise ValueError(
            "Cannot create financial features from an empty DataFrame."
        )

    validate_financial_schema(dataframe)

    featured_dataframe = dataframe.copy()

    featured_dataframe["revenue_growth"] = (
        calculate_revenue_growth(featured_dataframe)
    )

    featured_dataframe["revenue_change_k_eur"] = (
        featured_dataframe[REVENUE_LATEST]
        - featured_dataframe[REVENUE_PREVIOUS]
    )

    featured_dataframe["ebitda_margin"] = (
        calculate_ebitda_margin(featured_dataframe)
    )

    featured_dataframe["ebitda_change_k_eur"] = (
        featured_dataframe[EBITDA_LATEST]
        - featured_dataframe[EBITDA_PREVIOUS]
    )

    featured_dataframe[
        "revenue_per_employee_k_eur"
    ] = calculate_revenue_per_employee(
        featured_dataframe
    )

    featured_dataframe[
        "ebitda_per_employee_k_eur"
    ] = calculate_ebitda_per_employee(
        featured_dataframe
    )

    featured_dataframe[
        "has_negative_latest_revenue"
    ] = featured_dataframe[
        REVENUE_LATEST
    ].lt(0)

    featured_dataframe[
        "has_zero_latest_revenue"
    ] = featured_dataframe[
        REVENUE_LATEST
    ].eq(0)

    featured_dataframe[
        "has_negative_latest_ebitda"
    ] = featured_dataframe[
        EBITDA_LATEST
    ].lt(0)

    featured_dataframe[
        "has_revenue_decline"
    ] = featured_dataframe[
        "revenue_growth"
    ].lt(0)

    featured_dataframe[
        "has_extreme_ebitda_margin"
    ] = (
        featured_dataframe[
            "ebitda_margin"
        ].abs().gt(1)
    )

    featured_dataframe[
        "has_incomplete_financial_data"
    ] = featured_dataframe[
        [
            REVENUE_LATEST,
            REVENUE_PREVIOUS,
            EBITDA_LATEST,
            EBITDA_PREVIOUS,
        ]
    ].isna().any(axis=1)

    return featured_dataframe


if __name__ == "__main__":
    financial_dataframe = add_financial_features()

    print("Financial features created successfully.")
    print(f"Rows: {len(financial_dataframe):,}")
    print(f"Columns: {len(financial_dataframe.columns)}")

    print("\nFinancial-feature columns:")
    print(FINANCIAL_FEATURE_COLUMNS)

    print("\nRevenue-growth observations available:")
    print(
        financial_dataframe[
            "revenue_growth"
        ].notna().sum()
    )

    print("\nEBITDA-margin observations available:")
    print(
        financial_dataframe[
            "ebitda_margin"
        ].notna().sum()
    )

    print("\nCompanies with negative latest EBITDA:")
    print(
        financial_dataframe[
            "has_negative_latest_ebitda"
        ].sum()
    )

    print("\nCompanies with declining revenue:")
    print(
        financial_dataframe[
            "has_revenue_decline"
        ].sum()
    )

    print("\nCompanies with absolute EBITDA margin above 100%:")
    print(
        financial_dataframe[
            "has_extreme_ebitda_margin"
        ].sum()
    )

    print("\nCompanies with incomplete financial data:")
    print(
        financial_dataframe[
            "has_incomplete_financial_data"
        ].sum()
    )