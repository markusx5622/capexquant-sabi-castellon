"""Tests for the CapexQuant SABI financial-feature module."""

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal

from src.clean_data import clean_sabi_data
from src.financial_features import (
    EBITDA_LATEST,
    EBITDA_PREVIOUS,
    EMPLOYEES_LATEST,
    FINANCIAL_FEATURE_COLUMNS,
    REQUIRED_FINANCIAL_COLUMNS,
    REVENUE_LATEST,
    REVENUE_PREVIOUS,
    add_financial_features,
    calculate_ebitda_margin,
    calculate_ebitda_per_employee,
    calculate_revenue_growth,
    calculate_revenue_per_employee,
    safe_divide,
    validate_financial_schema,
)
from src.load_data import load_sabi_data


EXPECTED_ROWS = 6_711
EXPECTED_INPUT_COLUMNS = 16
EXPECTED_OUTPUT_COLUMNS = 28

EXPECTED_REVENUE_GROWTH_OBSERVATIONS = 6_436
EXPECTED_EBITDA_MARGIN_OBSERVATIONS = 6_637

EXPECTED_NEGATIVE_EBITDA_RECORDS = 1_637
EXPECTED_REVENUE_DECLINE_RECORDS = 2_936
EXPECTED_EXTREME_EBITDA_MARGIN_RECORDS = 148
EXPECTED_INCOMPLETE_FINANCIAL_RECORDS = 275

ORIGINAL_FINANCIAL_COLUMNS = [
    EMPLOYEES_LATEST,
    REVENUE_LATEST,
    REVENUE_PREVIOUS,
    EBITDA_LATEST,
    EBITDA_PREVIOUS,
]


@pytest.fixture(scope="module")
def cleaned_dataframe() -> pd.DataFrame:
    """Load and clean the private SABI extraction once."""

    raw_dataframe = load_sabi_data()

    return clean_sabi_data(raw_dataframe)


@pytest.fixture(scope="module")
def financial_dataframe(
    cleaned_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Create the financial features once for integration tests."""

    return add_financial_features(cleaned_dataframe)


@pytest.fixture()
def synthetic_financial_dataframe() -> pd.DataFrame:
    """
    Create a small deterministic dataset for unit tests.

    The fixture includes:
    - a normal growing company;
    - a zero previous-revenue denominator;
    - a zero latest-revenue denominator;
    - missing financial information;
    - negative revenue and EBITDA.
    """

    return pd.DataFrame(
        {
            REVENUE_LATEST: [
                120.0,
                50.0,
                0.0,
                np.nan,
                -10.0,
            ],
            REVENUE_PREVIOUS: [
                100.0,
                0.0,
                50.0,
                80.0,
                10.0,
            ],
            EBITDA_LATEST: [
                24.0,
                -5.0,
                10.0,
                5.0,
                -2.0,
            ],
            EBITDA_PREVIOUS: [
                20.0,
                -10.0,
                5.0,
                np.nan,
                -1.0,
            ],
            EMPLOYEES_LATEST: [
                10,
                5,
                2,
                4,
                1,
            ],
        },
        index=[
            "normal_growth",
            "zero_previous_revenue",
            "zero_latest_revenue",
            "missing_latest_revenue",
            "negative_revenue",
        ],
    )


def test_required_financial_columns_are_unique() -> None:
    """The required-column definition must not contain duplicates."""

    assert len(REQUIRED_FINANCIAL_COLUMNS) == len(
        set(REQUIRED_FINANCIAL_COLUMNS)
    )


def test_financial_feature_columns_are_unique() -> None:
    """The financial-feature definition must not contain duplicates."""

    assert len(FINANCIAL_FEATURE_COLUMNS) == len(
        set(FINANCIAL_FEATURE_COLUMNS)
    )


def test_validate_financial_schema_accepts_valid_data(
    synthetic_financial_dataframe: pd.DataFrame,
) -> None:
    """A DataFrame containing all required fields must pass validation."""

    validate_financial_schema(
        synthetic_financial_dataframe
    )


def test_validate_financial_schema_rejects_missing_column(
    synthetic_financial_dataframe: pd.DataFrame,
) -> None:
    """A missing financial field must raise an explicit error."""

    invalid_dataframe = (
        synthetic_financial_dataframe.drop(
            columns=[EBITDA_LATEST]
        )
    )

    with pytest.raises(
        ValueError,
        match="Missing columns required for financial features",
    ):
        validate_financial_schema(invalid_dataframe)


def test_safe_divide_calculates_valid_ratios() -> None:
    """Valid numerators and denominators must be divided correctly."""

    numerator = pd.Series(
        [10.0, 20.0, -15.0],
        index=["a", "b", "c"],
    )

    denominator = pd.Series(
        [2.0, 4.0, 3.0],
        index=["a", "b", "c"],
    )

    actual_result = safe_divide(
        numerator,
        denominator,
    )

    expected_result = pd.Series(
        [5.0, 5.0, -5.0],
        index=["a", "b", "c"],
        dtype="float64",
    )

    assert_series_equal(
        actual_result,
        expected_result,
    )


def test_safe_divide_handles_zero_and_missing_denominators() -> None:
    """Zero and missing denominators must generate NaN, not infinity."""

    numerator = pd.Series(
        [10.0, 20.0, 30.0, np.nan],
    )

    denominator = pd.Series(
        [2.0, 0.0, np.nan, 5.0],
    )

    result = safe_divide(
        numerator,
        denominator,
    )

    assert result.iloc[0] == pytest.approx(5.0)
    assert pd.isna(result.iloc[1])
    assert pd.isna(result.iloc[2])
    assert pd.isna(result.iloc[3])

    assert not np.isinf(
        result.dropna().to_numpy()
    ).any()


def test_revenue_growth_unit_calculation(
    synthetic_financial_dataframe: pd.DataFrame,
) -> None:
    """Revenue growth must follow latest / previous - 1."""

    result = calculate_revenue_growth(
        synthetic_financial_dataframe
    )

    assert result.loc[
        "normal_growth"
    ] == pytest.approx(0.20)

    assert pd.isna(
        result.loc["zero_previous_revenue"]
    )

    assert result.loc[
        "zero_latest_revenue"
    ] == pytest.approx(-1.0)

    assert pd.isna(
        result.loc["missing_latest_revenue"]
    )

    assert result.loc[
        "negative_revenue"
    ] == pytest.approx(-2.0)


def test_ebitda_margin_unit_calculation(
    synthetic_financial_dataframe: pd.DataFrame,
) -> None:
    """EBITDA margin must follow EBITDA / latest revenue."""

    result = calculate_ebitda_margin(
        synthetic_financial_dataframe
    )

    assert result.loc[
        "normal_growth"
    ] == pytest.approx(0.20)

    assert result.loc[
        "zero_previous_revenue"
    ] == pytest.approx(-0.10)

    assert pd.isna(
        result.loc["zero_latest_revenue"]
    )

    assert pd.isna(
        result.loc["missing_latest_revenue"]
    )

    assert result.loc[
        "negative_revenue"
    ] == pytest.approx(0.20)


def test_revenue_per_employee_unit_calculation(
    synthetic_financial_dataframe: pd.DataFrame,
) -> None:
    """Revenue per employee must preserve thousand-euro units."""

    result = calculate_revenue_per_employee(
        synthetic_financial_dataframe
    )

    assert result.loc[
        "normal_growth"
    ] == pytest.approx(12.0)

    assert result.loc[
        "zero_previous_revenue"
    ] == pytest.approx(10.0)

    assert result.loc[
        "zero_latest_revenue"
    ] == pytest.approx(0.0)

    assert pd.isna(
        result.loc["missing_latest_revenue"]
    )

    assert result.loc[
        "negative_revenue"
    ] == pytest.approx(-10.0)


def test_ebitda_per_employee_unit_calculation(
    synthetic_financial_dataframe: pd.DataFrame,
) -> None:
    """EBITDA per employee must preserve thousand-euro units."""

    result = calculate_ebitda_per_employee(
        synthetic_financial_dataframe
    )

    assert result.loc[
        "normal_growth"
    ] == pytest.approx(2.4)

    assert result.loc[
        "zero_previous_revenue"
    ] == pytest.approx(-1.0)

    assert result.loc[
        "zero_latest_revenue"
    ] == pytest.approx(5.0)

    assert result.loc[
        "missing_latest_revenue"
    ] == pytest.approx(1.25)

    assert result.loc[
        "negative_revenue"
    ] == pytest.approx(-2.0)


def test_absolute_financial_changes(
    synthetic_financial_dataframe: pd.DataFrame,
) -> None:
    """Absolute revenue and EBITDA changes must use current minus previous."""

    result = add_financial_features(
        synthetic_financial_dataframe
    )

    assert result.loc[
        "normal_growth",
        "revenue_change_k_eur",
    ] == pytest.approx(20.0)

    assert result.loc[
        "normal_growth",
        "ebitda_change_k_eur",
    ] == pytest.approx(4.0)

    assert result.loc[
        "zero_latest_revenue",
        "revenue_change_k_eur",
    ] == pytest.approx(-50.0)

    assert pd.isna(
        result.loc[
            "missing_latest_revenue",
            "revenue_change_k_eur",
        ]
    )

    assert pd.isna(
        result.loc[
            "missing_latest_revenue",
            "ebitda_change_k_eur",
        ]
    )


def test_synthetic_quality_flags(
    synthetic_financial_dataframe: pd.DataFrame,
) -> None:
    """Quality and performance flags must classify synthetic cases."""

    result = add_financial_features(
        synthetic_financial_dataframe
    )

    assert bool(
        result.loc[
            "negative_revenue",
            "has_negative_latest_revenue",
        ]
    )

    assert bool(
        result.loc[
            "zero_latest_revenue",
            "has_zero_latest_revenue",
        ]
    )

    assert bool(
        result.loc[
            "zero_previous_revenue",
            "has_negative_latest_ebitda",
        ]
    )

    assert bool(
        result.loc[
            "negative_revenue",
            "has_negative_latest_ebitda",
        ]
    )

    assert bool(
        result.loc[
            "zero_latest_revenue",
            "has_revenue_decline",
        ]
    )

    assert bool(
        result.loc[
            "negative_revenue",
            "has_revenue_decline",
        ]
    )

    assert bool(
        result.loc[
            "missing_latest_revenue",
            "has_incomplete_financial_data",
        ]
    )


def test_extreme_ebitda_margin_flag() -> None:
    """Absolute EBITDA margins above 100% must be flagged."""

    dataframe = pd.DataFrame(
        {
            REVENUE_LATEST: [
                100.0,
                100.0,
                100.0,
                -100.0,
            ],
            REVENUE_PREVIOUS: [
                100.0,
                100.0,
                100.0,
                100.0,
            ],
            EBITDA_LATEST: [
                50.0,
                100.0,
                150.0,
                150.0,
            ],
            EBITDA_PREVIOUS: [
                40.0,
                90.0,
                120.0,
                120.0,
            ],
            EMPLOYEES_LATEST: [
                10,
                10,
                10,
                10,
            ],
        }
    )

    result = add_financial_features(dataframe)

    expected_flag = pd.Series(
        [False, False, True, True],
        name="has_extreme_ebitda_margin",
    )

    assert_series_equal(
        result["has_extreme_ebitda_margin"],
        expected_flag,
    )


def test_empty_dataframe_raises_error() -> None:
    """An empty DataFrame must be rejected before calculation."""

    with pytest.raises(
        ValueError,
        match=(
            "Cannot create financial features "
            "from an empty DataFrame"
        ),
    ):
        add_financial_features(pd.DataFrame())


def test_row_count_is_preserved(
    cleaned_dataframe: pd.DataFrame,
    financial_dataframe: pd.DataFrame,
) -> None:
    """Financial feature engineering must not alter the row count."""

    assert len(cleaned_dataframe) == EXPECTED_ROWS
    assert len(financial_dataframe) == EXPECTED_ROWS


def test_expected_column_count(
    cleaned_dataframe: pd.DataFrame,
    financial_dataframe: pd.DataFrame,
) -> None:
    """Exactly twelve financial fields must be added."""

    assert (
        cleaned_dataframe.shape[1]
        == EXPECTED_INPUT_COLUMNS
    )

    assert (
        financial_dataframe.shape[1]
        == EXPECTED_OUTPUT_COLUMNS
    )

    added_columns = [
        column
        for column in financial_dataframe.columns
        if column not in cleaned_dataframe.columns
    ]

    assert added_columns == FINANCIAL_FEATURE_COLUMNS


def test_input_dataframe_is_not_mutated(
    cleaned_dataframe: pd.DataFrame,
) -> None:
    """The financial-feature function must not mutate its input."""

    original_dataframe = cleaned_dataframe.copy(
        deep=True
    )

    add_financial_features(cleaned_dataframe)

    assert_frame_equal(
        cleaned_dataframe,
        original_dataframe,
    )


def test_original_columns_are_preserved(
    cleaned_dataframe: pd.DataFrame,
    financial_dataframe: pd.DataFrame,
) -> None:
    """Every original cleaned column must remain unchanged."""

    for column in cleaned_dataframe.columns:
        assert_series_equal(
            cleaned_dataframe[column],
            financial_dataframe[column],
            check_names=True,
            check_dtype=True,
        )


def test_original_financial_values_are_preserved(
    cleaned_dataframe: pd.DataFrame,
    financial_dataframe: pd.DataFrame,
) -> None:
    """Original SABI financial observations must remain unchanged."""

    for column in ORIGINAL_FINANCIAL_COLUMNS:
        assert_series_equal(
            cleaned_dataframe[column],
            financial_dataframe[column],
            check_names=True,
            check_dtype=True,
        )


def test_feature_columns_contain_no_infinity(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Derived financial metrics must never contain positive or negative infinity."""

    numeric_feature_columns = [
        "revenue_growth",
        "revenue_change_k_eur",
        "ebitda_margin",
        "ebitda_change_k_eur",
        "revenue_per_employee_k_eur",
        "ebitda_per_employee_k_eur",
    ]

    feature_values = financial_dataframe[
        numeric_feature_columns
    ].to_numpy(
        dtype="float64",
        na_value=np.nan,
    )

    assert not np.isinf(feature_values).any()


def test_revenue_growth_observation_count(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Revenue-growth availability must match the audited extraction."""

    actual_count = int(
        financial_dataframe[
            "revenue_growth"
        ].notna().sum()
    )

    assert (
        actual_count
        == EXPECTED_REVENUE_GROWTH_OBSERVATIONS
    )


def test_ebitda_margin_observation_count(
    financial_dataframe: pd.DataFrame,
) -> None:
    """EBITDA-margin availability must match the audited extraction."""

    actual_count = int(
        financial_dataframe[
            "ebitda_margin"
        ].notna().sum()
    )

    assert (
        actual_count
        == EXPECTED_EBITDA_MARGIN_OBSERVATIONS
    )


def test_negative_latest_ebitda_count(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Negative latest EBITDA must match the audited extraction."""

    actual_count = int(
        financial_dataframe[
            "has_negative_latest_ebitda"
        ].sum()
    )

    assert (
        actual_count
        == EXPECTED_NEGATIVE_EBITDA_RECORDS
    )


def test_revenue_decline_count(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Revenue-decline records must match the audited extraction."""

    actual_count = int(
        financial_dataframe[
            "has_revenue_decline"
        ].sum()
    )

    assert (
        actual_count
        == EXPECTED_REVENUE_DECLINE_RECORDS
    )


def test_extreme_ebitda_margin_count(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Extreme EBITDA margins must match the audited extraction."""

    actual_count = int(
        financial_dataframe[
            "has_extreme_ebitda_margin"
        ].sum()
    )

    assert (
        actual_count
        == EXPECTED_EXTREME_EBITDA_MARGIN_RECORDS
    )


def test_incomplete_financial_data_count(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Incomplete financial records must match the audited extraction."""

    actual_count = int(
        financial_dataframe[
            "has_incomplete_financial_data"
        ].sum()
    )

    assert (
        actual_count
        == EXPECTED_INCOMPLETE_FINANCIAL_RECORDS
    )


def test_revenue_decline_flag_matches_growth(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Revenue-decline flags must agree with negative revenue growth."""

    expected_flag = financial_dataframe[
        "revenue_growth"
    ].lt(0)

    assert_series_equal(
        financial_dataframe["has_revenue_decline"],
        expected_flag,
        check_names=False,
    )


def test_negative_ebitda_flag_matches_source(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Negative-EBITDA flags must agree with the source EBITDA field."""

    expected_flag = financial_dataframe[
        EBITDA_LATEST
    ].lt(0)

    assert_series_equal(
        financial_dataframe[
            "has_negative_latest_ebitda"
        ],
        expected_flag,
        check_names=False,
    )


def test_extreme_margin_flag_matches_metric(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Extreme-margin flags must agree with the calculated margin."""

    expected_flag = financial_dataframe[
        "ebitda_margin"
    ].abs().gt(1)

    assert_series_equal(
        financial_dataframe[
            "has_extreme_ebitda_margin"
        ],
        expected_flag,
        check_names=False,
    )


def test_incomplete_flag_matches_source_fields(
    financial_dataframe: pd.DataFrame,
) -> None:
    """The incomplete-data flag must match missing source observations."""

    expected_flag = financial_dataframe[
        [
            REVENUE_LATEST,
            REVENUE_PREVIOUS,
            EBITDA_LATEST,
            EBITDA_PREVIOUS,
        ]
    ].isna().any(axis=1)

    assert_series_equal(
        financial_dataframe[
            "has_incomplete_financial_data"
        ],
        expected_flag,
        check_names=False,
    )