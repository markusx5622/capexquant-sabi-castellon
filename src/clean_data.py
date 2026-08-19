"""Data-cleaning utilities for the CapexQuant SABI Castellón project."""

import re
import unicodedata

import pandas as pd

from src.load_data import load_sabi_data


NO_SHAREHOLDER_INFORMATION = (
    "There is no shareholders information for this company"
)

LEGAL_STATUS_PATTERNS = {
    "extinct": r"\bEXTINGUID[AO]S?\b",
    "in_liquidation": r"\bEN\s+LIQUIDACI[ÓO]N\b",
    "in_dissolution": r"\bEN\s+DISOLUCI[ÓO]N\b",
}


def normalize_whitespace(value: object) -> object:
    """
    Normalize whitespace in a text value.

    Leading and trailing spaces are removed and consecutive
    whitespace characters are replaced with a single space.
    Missing values are preserved.
    """
    if pd.isna(value):
        return value

    return re.sub(r"\s+", " ", str(value)).strip()


def remove_accents(value: str) -> str:
    """Return a text value without Unicode accents."""

    normalized = unicodedata.normalize("NFKD", value)

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def normalize_company_name(company_name: object) -> object:
    """
    Create a standardized company name for matching purposes.

    The normalized value:
    - removes leading and trailing whitespace;
    - collapses repeated whitespace;
    - converts text to uppercase;
    - removes accents;
    - removes punctuation;
    - preserves the legal company wording.

    This field is intended for matching and duplicate detection.
    The original company name remains unchanged.
    """
    if pd.isna(company_name):
        return company_name

    normalized_name = normalize_whitespace(company_name)
    normalized_name = remove_accents(str(normalized_name))
    normalized_name = normalized_name.upper()

    normalized_name = re.sub(
        r"[^A-Z0-9\s]",
        " ",
        normalized_name,
    )

    normalized_name = re.sub(
        r"\s+",
        " ",
        normalized_name,
    ).strip()

    return normalized_name


def extract_legal_status(company_name: object) -> str:
    """
    Infer the legal-status marker contained in the company name.

    The classification is based only on explicit text contained
    in the SABI company-name field. Therefore, 'no_adverse_marker'
    does not guarantee that a company is legally active.
    """
    if pd.isna(company_name):
        return "unknown"

    normalized_name = remove_accents(
        str(normalize_whitespace(company_name))
    ).upper()

    if re.search(
        LEGAL_STATUS_PATTERNS["in_liquidation"],
        normalized_name,
    ):
        return "in_liquidation"

    if re.search(
        LEGAL_STATUS_PATTERNS["in_dissolution"],
        normalized_name,
    ):
        return "in_dissolution"

    if re.search(
        LEGAL_STATUS_PATTERNS["extinct"],
        normalized_name,
    ):
        return "extinct"

    return "no_adverse_marker"


def clean_shareholder_information(value: object) -> object:
    """
    Convert SABI's no-shareholder-information message to missing data.

    Actual shareholder names are preserved unchanged except for
    whitespace normalization.
    """
    if pd.isna(value):
        return pd.NA

    cleaned_value = normalize_whitespace(value)

    if cleaned_value == NO_SHAREHOLDER_INFORMATION:
        return pd.NA

    return cleaned_value


def create_company_match_key(
    company_name: object,
) -> object:
    """
    Create a matching key for potential duplicate detection.

    Explicit adverse legal-status markers are removed from the
    normalized company name. The function does not automatically
    classify matching keys as true duplicates.
    """
    if pd.isna(company_name):
        return company_name

    match_key = normalize_company_name(company_name)

    status_expressions = [
        r"\bEXTINGUID[AO]S?\b",
        r"\bEN\s+LIQUIDACION\b",
        r"\bEN\s+DISOLUCION\b",
    ]

    for expression in status_expressions:
        match_key = re.sub(
            expression,
            " ",
            str(match_key),
        )

    match_key = re.sub(
        r"\s+",
        " ",
        match_key,
    ).strip()

    return match_key


def add_duplicate_flags(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add potential-duplicate indicators based on the company match key.

    A duplicate flag is an analytical warning only. It does not prove
    that two records represent the same legal entity.
    """
    cleaned_dataframe = dataframe.copy()

    duplicate_mask = cleaned_dataframe[
        "company_match_key"
    ].duplicated(
        keep=False
    )

    cleaned_dataframe[
        "potential_duplicate"
    ] = duplicate_mask

    duplicate_counts = (
        cleaned_dataframe
        .groupby(
            "company_match_key",
            dropna=False,
        )["company_match_key"]
        .transform("size")
    )

    cleaned_dataframe[
        "potential_duplicate_count"
    ] = duplicate_counts.astype("Int64")

    return cleaned_dataframe


def clean_sabi_data(
    dataframe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Apply deterministic cleaning to standardized SABI data.

    The function preserves the original financial variables and adds
    analytical fields required for later quality-control work.

    Parameters
    ----------
    dataframe:
        Optional standardized DataFrame. If omitted, the private SABI
        source workbook is loaded through load_sabi_data().

    Returns
    -------
    pandas.DataFrame
        Cleaned dataset with additional normalized fields and flags.
    """
    if dataframe is None:
        dataframe = load_sabi_data()

    if dataframe.empty:
        raise ValueError(
            "Cannot clean an empty SABI DataFrame."
        )

    cleaned_dataframe = dataframe.copy()

    text_columns = [
        "company_name",
        "website",
        "municipality",
    ]

    for column in text_columns:
        cleaned_dataframe[column] = (
            cleaned_dataframe[column]
            .apply(normalize_whitespace)
        )

    cleaned_dataframe[
        "shareholder_name"
    ] = cleaned_dataframe[
        "shareholder_name"
    ].apply(
        clean_shareholder_information
    )

    cleaned_dataframe[
        "company_name_normalized"
    ] = cleaned_dataframe[
        "company_name"
    ].apply(
        normalize_company_name
    )

    cleaned_dataframe[
        "legal_status"
    ] = cleaned_dataframe[
        "company_name"
    ].apply(
        extract_legal_status
    )

    cleaned_dataframe[
        "has_adverse_legal_status"
    ] = cleaned_dataframe[
        "legal_status"
    ].isin(
        [
            "extinct",
            "in_liquidation",
            "in_dissolution",
        ]
    )

    cleaned_dataframe[
        "company_match_key"
    ] = cleaned_dataframe[
        "company_name"
    ].apply(
        create_company_match_key
    )

    cleaned_dataframe = add_duplicate_flags(
        cleaned_dataframe
    )

    return cleaned_dataframe


if __name__ == "__main__":
    cleaned_sabi_dataframe = clean_sabi_data()

    print("SABI data cleaned successfully.")
    print(
        f"Rows: {len(cleaned_sabi_dataframe):,}"
    )
    print(
        f"Columns: {len(cleaned_sabi_dataframe.columns)}"
    )

    print("\nLegal-status distribution:")
    print(
        cleaned_sabi_dataframe[
            "legal_status"
        ].value_counts(
            dropna=False
        )
    )

    print("\nPotential duplicate records:")
    print(
        cleaned_sabi_dataframe[
            "potential_duplicate"
        ].sum()
    )

    print("\nShareholder information missing:")
    print(
        cleaned_sabi_dataframe[
            "shareholder_name"
        ].isna().sum()
    )