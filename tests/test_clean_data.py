"""Automated tests for the CapexQuant SABI cleaning module."""

import pandas as pd
import pytest
from pandas.testing import assert_series_equal

from src.clean_data import (
    NO_SHAREHOLDER_INFORMATION,
    clean_sabi_data,
    clean_shareholder_information,
    create_company_match_key,
    extract_legal_status,
    normalize_company_name,
    normalize_whitespace,
)
from src.load_data import load_sabi_data


EXPECTED_ROWS = 6_711
EXPECTED_INPUT_COLUMNS = 10
EXPECTED_OUTPUT_COLUMNS = 16

EXPECTED_LEGAL_STATUS_COUNTS = {
    "no_adverse_marker": 5_544,
    "extinct": 882,
    "in_liquidation": 284,
    "in_dissolution": 1,
}

EXPECTED_ADVERSE_STATUS_RECORDS = 1_167
EXPECTED_POTENTIAL_DUPLICATE_RECORDS = 18
EXPECTED_MISSING_SHAREHOLDER_RECORDS = 3_360

ORIGINAL_FINANCIAL_COLUMNS = [
    "employees_latest",
    "operating_revenue_latest_k_eur",
    "operating_revenue_previous_k_eur",
    "ebitda_latest_k_eur",
    "ebitda_previous_k_eur",
]

EXPECTED_ADDED_COLUMNS = [
    "company_name_normalized",
    "legal_status",
    "has_adverse_legal_status",
    "company_match_key",
    "potential_duplicate",
    "potential_duplicate_count",
]


@pytest.fixture(scope="module")
def raw_dataframe() -> pd.DataFrame:
    """Load the standardized private SABI dataset once."""

    return load_sabi_data()


@pytest.fixture(scope="module")
def cleaned_dataframe(
    raw_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Clean the standardized SABI dataset once."""

    return clean_sabi_data(raw_dataframe)


def test_normalize_whitespace() -> None:
    """Whitespace must be stripped and collapsed deterministically."""

    value = "  COMPANY   NAME\n  SOCIEDAD  "

    assert normalize_whitespace(value) == (
        "COMPANY NAME SOCIEDAD"
    )


def test_normalize_whitespace_preserves_missing_value() -> None:
    """Missing text values must remain missing."""

    assert pd.isna(normalize_whitespace(pd.NA))


def test_normalize_company_name() -> None:
    """Company names must be uppercase and free of accents and punctuation."""

    company_name = "  Cerámica Álvarez, S.L.  "

    assert normalize_company_name(company_name) == (
        "CERAMICA ALVAREZ S L"
    )


@pytest.mark.parametrize(
    ("company_name", "expected_status"),
    [
        (
            "EMPRESA EJEMPLO SL (EXTINGUIDA)",
            "extinct",
        ),
        (
            "EMPRESA EJEMPLO SA (EXTINGUIDO)",
            "extinct",
        ),
        (
            "EMPRESA EJEMPLO SL (EN LIQUIDACIÓN)",
            "in_liquidation",
        ),
        (
            "EMPRESA EJEMPLO SL (EN LIQUIDACION)",
            "in_liquidation",
        ),
        (
            "EMPRESA EJEMPLO SL (EN DISOLUCIÓN)",
            "in_dissolution",
        ),
        (
            "EMPRESA EJEMPLO SL",
            "no_adverse_marker",
        ),
    ],
)
def test_extract_legal_status(
    company_name: str,
    expected_status: str,
) -> None:
    """Explicit company-name markers must produce the expected status."""

    assert extract_legal_status(company_name) == expected_status


def test_missing_company_name_has_unknown_status() -> None:
    """A missing company name must produce an unknown legal status."""

    assert extract_legal_status(pd.NA) == "unknown"


def test_no_shareholder_message_becomes_missing() -> None:
    """SABI's absence message must be converted into missing data."""

    result = clean_shareholder_information(
        NO_SHAREHOLDER_INFORMATION
    )

    assert pd.isna(result)


def test_actual_shareholder_information_is_preserved() -> None:
    """Real shareholder information must remain available."""

    shareholder = "  COMPANY HOLDING SL  "

    assert clean_shareholder_information(
        shareholder
    ) == "COMPANY HOLDING SL"


def test_match_key_removes_adverse_status() -> None:
    """The duplicate-matching key must remove legal-status markers."""

    active_key = create_company_match_key(
        "COMPACGLASS SL"
    )

    extinct_key = create_company_match_key(
        "COMPACGLASS SL (EXTINGUIDA)"
    )

    assert active_key == extinct_key
    assert active_key == "COMPACGLASS SL"


def test_cleaning_preserves_row_count(
    raw_dataframe: pd.DataFrame,
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """Cleaning must not add or remove company records."""

    assert len(raw_dataframe) == EXPECTED_ROWS
    assert len(cleaned_dataframe) == EXPECTED_ROWS


def test_cleaning_adds_expected_columns(
    raw_dataframe: pd.DataFrame,
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """Cleaning must add exactly the expected analytical fields."""

    assert raw_dataframe.shape[1] == EXPECTED_INPUT_COLUMNS
    assert cleaned_dataframe.shape[1] == EXPECTED_OUTPUT_COLUMNS

    added_columns = [
        column
        for column in cleaned_dataframe.columns
        if column not in raw_dataframe.columns
    ]

    assert added_columns == EXPECTED_ADDED_COLUMNS


def test_cleaning_does_not_modify_input_dataframe(
    raw_dataframe: pd.DataFrame,
) -> None:
    """The function must not mutate its input DataFrame."""

    original_dataframe = raw_dataframe.copy(deep=True)

    clean_sabi_data(raw_dataframe)

    pd.testing.assert_frame_equal(
        raw_dataframe,
        original_dataframe,
    )


def test_financial_columns_remain_unchanged(
    raw_dataframe: pd.DataFrame,
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """Cleaning must preserve all original financial observations."""

    for column in ORIGINAL_FINANCIAL_COLUMNS:
        assert_series_equal(
            raw_dataframe[column],
            cleaned_dataframe[column],
            check_names=True,
            check_dtype=True,
        )


def test_legal_status_distribution(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """The legal-status classification must match the source extraction."""

    actual_counts = (
        cleaned_dataframe["legal_status"]
        .value_counts()
        .to_dict()
    )

    assert actual_counts == EXPECTED_LEGAL_STATUS_COUNTS


def test_adverse_status_count(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """The adverse-status flag must match the classified records."""

    actual_count = int(
        cleaned_dataframe[
            "has_adverse_legal_status"
        ].sum()
    )

    assert actual_count == EXPECTED_ADVERSE_STATUS_RECORDS


def test_adverse_status_flag_is_consistent(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """The boolean flag must agree with the legal-status classification."""

    expected_flag = cleaned_dataframe[
        "legal_status"
    ].isin(
        [
            "extinct",
            "in_liquidation",
            "in_dissolution",
        ]
    )

    assert_series_equal(
        cleaned_dataframe["has_adverse_legal_status"],
        expected_flag,
        check_names=False,
    )


def test_potential_duplicate_count(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """The duplicate-matching logic must reproduce the audited result."""

    actual_count = int(
        cleaned_dataframe[
            "potential_duplicate"
        ].sum()
    )

    assert actual_count == EXPECTED_POTENTIAL_DUPLICATE_RECORDS


def test_duplicate_flags_have_multiple_records(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """Every flagged match key must contain at least two records."""

    flagged_records = cleaned_dataframe.loc[
        cleaned_dataframe["potential_duplicate"]
    ]

    assert not flagged_records.empty

    assert (
        flagged_records["potential_duplicate_count"] >= 2
    ).all()


def test_non_duplicate_records_have_count_one(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """Unflagged match keys must contain exactly one record."""

    non_duplicate_records = cleaned_dataframe.loc[
        ~cleaned_dataframe["potential_duplicate"]
    ]

    assert (
        non_duplicate_records[
            "potential_duplicate_count"
        ] == 1
    ).all()


def test_missing_shareholder_count(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """The cleaned shareholder field must reproduce the audited absence count."""

    actual_missing = int(
        cleaned_dataframe[
            "shareholder_name"
        ].isna().sum()
    )

    assert actual_missing == EXPECTED_MISSING_SHAREHOLDER_RECORDS


def test_no_shareholder_message_was_removed(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """The original SABI absence message must not remain as a name."""

    remaining_messages = (
        cleaned_dataframe["shareholder_name"]
        .dropna()
        .eq(NO_SHAREHOLDER_INFORMATION)
        .sum()
    )

    assert remaining_messages == 0


def test_normalized_names_are_complete(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """Every company must receive a normalized name and matching key."""

    assert cleaned_dataframe[
        "company_name_normalized"
    ].notna().all()

    assert cleaned_dataframe[
        "company_match_key"
    ].notna().all()


def test_cleaning_empty_dataframe_raises_error() -> None:
    """An empty DataFrame must be rejected explicitly."""

    empty_dataframe = pd.DataFrame()

    with pytest.raises(
        ValueError,
        match="Cannot clean an empty SABI DataFrame",
    ):
        clean_sabi_data(empty_dataframe)