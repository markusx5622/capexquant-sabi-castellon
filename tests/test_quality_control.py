"""Tests for the CapexQuant SABI quality-control module."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal

from src.financial_features import add_financial_features
from src.quality_control import (
    BUSINESS_RISK_FLAGS,
    BUSINESS_RISK_REASON_LABELS,
    DATA_QUALITY_FLAGS,
    DATA_QUALITY_REASON_LABELS,
    QUALITY_CONTROL_COLUMNS,
    REQUIRED_QUALITY_COLUMNS,
    add_quality_controls,
    classify_analytical_eligibility,
    classify_data_quality_status,
    combine_flag_reasons,
    create_quality_summary,
    validate_boolean_flags,
    validate_quality_schema,
)


EXPECTED_ROWS = 6_711
EXPECTED_INPUT_COLUMNS = 28
EXPECTED_OUTPUT_COLUMNS = 36

EXPECTED_DATA_QUALITY_STATUS_COUNTS = {
    "clean": 6_278,
    "review": 425,
    "high_priority_review": 8,
}

EXPECTED_ANALYTICAL_ELIGIBILITY_COUNTS = {
    "eligible": 6_278,
    "not_eligible": 415,
    "eligible_with_review": 18,
}

EXPECTED_BUSINESS_RISK_COUNT_DISTRIBUTION = {
    0: 2_815,
    1: 2_463,
    2: 1_022,
    3: 411,
}

EXPECTED_FLAG_COUNTS = {
    "has_incomplete_financial_data": 275,
    "has_negative_latest_revenue": 0,
    "has_zero_latest_revenue": 0,
    "has_extreme_ebitda_margin": 148,
    "potential_duplicate": 18,
    "has_adverse_legal_status": 1_167,
    "has_negative_latest_ebitda": 1_637,
    "has_revenue_decline": 2_936,
    "has_data_quality_issue": 433,
    "has_business_risk_signal": 3_896,
}


@pytest.fixture(scope="module")
def financial_dataframe() -> pd.DataFrame:
    """Create the complete financial-feature dataset once."""

    return add_financial_features()


@pytest.fixture(scope="module")
def quality_dataframe(
    financial_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Apply quality controls once for integration tests."""

    return add_quality_controls(financial_dataframe)


@pytest.fixture()
def synthetic_quality_dataframe() -> pd.DataFrame:
    """Create deterministic quality-control cases."""

    return pd.DataFrame(
        {
            "has_incomplete_financial_data": [
                False,
                True,
                False,
                False,
                True,
            ],
            "has_negative_latest_revenue": [
                False,
                False,
                True,
                False,
                False,
            ],
            "has_zero_latest_revenue": [
                False,
                False,
                False,
                True,
                False,
            ],
            "has_extreme_ebitda_margin": [
                False,
                False,
                False,
                False,
                True,
            ],
            "potential_duplicate": [
                False,
                False,
                False,
                False,
                True,
            ],
            "has_adverse_legal_status": [
                False,
                False,
                True,
                False,
                True,
            ],
            "has_negative_latest_ebitda": [
                False,
                True,
                False,
                False,
                True,
            ],
            "has_revenue_decline": [
                False,
                False,
                True,
                True,
                True,
            ],
        },
        index=[
            "clean_company",
            "incomplete_company",
            "negative_revenue_company",
            "zero_revenue_company",
            "multiple_issues_company",
        ],
    )


def test_quality_column_definitions_are_unique() -> None:
    """Quality-control column collections must not contain duplicates."""

    assert len(DATA_QUALITY_FLAGS) == len(
        set(DATA_QUALITY_FLAGS)
    )

    assert len(BUSINESS_RISK_FLAGS) == len(
        set(BUSINESS_RISK_FLAGS)
    )

    assert len(REQUIRED_QUALITY_COLUMNS) == len(
        set(REQUIRED_QUALITY_COLUMNS)
    )

    assert len(QUALITY_CONTROL_COLUMNS) == len(
        set(QUALITY_CONTROL_COLUMNS)
    )


def test_quality_and_risk_flags_do_not_overlap() -> None:
    """Data-quality flags and business-risk flags must be distinct."""

    overlap = set(DATA_QUALITY_FLAGS).intersection(
        BUSINESS_RISK_FLAGS
    )

    assert overlap == set()


def test_validate_quality_schema_accepts_valid_data(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """A complete quality schema must pass validation."""

    validate_quality_schema(
        synthetic_quality_dataframe
    )


def test_validate_quality_schema_rejects_missing_column(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """A missing required flag must produce an explicit error."""

    invalid_dataframe = synthetic_quality_dataframe.drop(
        columns=["has_revenue_decline"]
    )

    with pytest.raises(
        ValueError,
        match="Missing columns required for quality control",
    ):
        validate_quality_schema(invalid_dataframe)


def test_boolean_flag_validation_accepts_valid_flags(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """Boolean quality and risk fields must pass validation."""

    validate_boolean_flags(
        synthetic_quality_dataframe,
        REQUIRED_QUALITY_COLUMNS,
    )


def test_boolean_flag_validation_rejects_missing_value(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """A missing boolean classification must be rejected."""

    invalid_dataframe = synthetic_quality_dataframe.copy()

    invalid_dataframe[
        "has_revenue_decline"
    ] = invalid_dataframe[
        "has_revenue_decline"
    ].astype("boolean")

    invalid_dataframe.loc[
        "clean_company",
        "has_revenue_decline",
    ] = pd.NA

    with pytest.raises(
        ValueError,
        match="Quality-control flags must contain only",
    ):
        validate_boolean_flags(
            invalid_dataframe,
            REQUIRED_QUALITY_COLUMNS,
        )


def test_boolean_flag_validation_rejects_invalid_value(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """A non-boolean flag value must be rejected."""

    invalid_dataframe = synthetic_quality_dataframe.copy()

    invalid_dataframe[
        "has_revenue_decline"
    ] = invalid_dataframe[
        "has_revenue_decline"
    ].astype(object)

    invalid_dataframe.loc[
        "clean_company",
        "has_revenue_decline",
    ] = "unknown"

    with pytest.raises(
        ValueError,
        match="Quality-control flags must contain only",
    ):
        validate_boolean_flags(
            invalid_dataframe,
            REQUIRED_QUALITY_COLUMNS,
        )


def test_classify_data_quality_status() -> None:
    """Issue counts must produce the expected quality categories."""

    issue_count = pd.Series(
        [0, 1, 2, 3],
        index=["a", "b", "c", "d"],
        dtype="Int64",
    )

    actual = classify_data_quality_status(
        issue_count
    )

    expected = pd.Series(
        [
            "clean",
            "review",
            "high_priority_review",
            "high_priority_review",
        ],
        index=["a", "b", "c", "d"],
        dtype="string",
    )

    assert_series_equal(actual, expected)


def test_classify_analytical_eligibility(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """Blocking and nonblocking issues must be classified correctly."""

    actual = classify_analytical_eligibility(
        synthetic_quality_dataframe
    )

    expected = pd.Series(
        [
            "eligible",
            "not_eligible",
            "eligible_with_review",
            "not_eligible",
            "not_eligible",
        ],
        index=synthetic_quality_dataframe.index,
        dtype="string",
    )

    assert_series_equal(actual, expected)


def test_blocking_issue_overrides_nonblocking_review() -> None:
    """A blocking issue must override eligible-with-review status."""

    dataframe = pd.DataFrame(
        {
            "has_incomplete_financial_data": [True],
            "has_zero_latest_revenue": [False],
            "has_extreme_ebitda_margin": [False],
            "has_negative_latest_revenue": [False],
            "potential_duplicate": [True],
        }
    )

    result = classify_analytical_eligibility(
        dataframe
    )

    assert result.iloc[0] == "not_eligible"


def test_combine_data_quality_reasons(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """Active quality flags must produce traceable reason strings."""

    actual = combine_flag_reasons(
        synthetic_quality_dataframe,
        DATA_QUALITY_REASON_LABELS,
    )

    assert actual.loc["clean_company"] == ""

    assert (
        actual.loc["incomplete_company"]
        == "incomplete_financial_data"
    )

    assert (
        actual.loc["negative_revenue_company"]
        == "negative_latest_revenue"
    )

    assert (
        actual.loc["zero_revenue_company"]
        == "zero_latest_revenue"
    )

    assert actual.loc[
        "multiple_issues_company"
    ] == (
        "incomplete_financial_data"
        "|extreme_ebitda_margin"
        "|potential_duplicate"
    )


def test_combine_business_risk_reasons(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """Active business-risk flags must produce traceable reasons."""

    actual = combine_flag_reasons(
        synthetic_quality_dataframe,
        BUSINESS_RISK_REASON_LABELS,
    )

    assert actual.loc["clean_company"] == ""

    assert actual.loc[
        "incomplete_company"
    ] == "negative_latest_ebitda"

    assert actual.loc[
        "negative_revenue_company"
    ] == (
        "adverse_legal_status"
        "|revenue_decline"
    )

    assert actual.loc[
        "multiple_issues_company"
    ] == (
        "adverse_legal_status"
        "|negative_latest_ebitda"
        "|revenue_decline"
    )


def test_synthetic_issue_counts(
    synthetic_quality_dataframe: pd.DataFrame,
) -> None:
    """Issue-count fields must equal the number of active flags."""

    result = add_quality_controls(
        synthetic_quality_dataframe
    )

    assert (
        result.loc[
            "clean_company",
            "data_quality_issue_count",
        ]
        == 0
    )

    assert (
        result.loc[
            "incomplete_company",
            "data_quality_issue_count",
        ]
        == 1
    )

    assert (
        result.loc[
            "multiple_issues_company",
            "data_quality_issue_count",
        ]
        == 3
    )

    assert (
        result.loc[
            "multiple_issues_company",
            "business_risk_signal_count",
        ]
        == 3
    )


def test_empty_dataframe_is_rejected() -> None:
    """An empty DataFrame must be rejected explicitly."""

    with pytest.raises(
        ValueError,
        match=(
            "Cannot perform quality control "
            "on an empty DataFrame"
        ),
    ):
        add_quality_controls(pd.DataFrame())


def test_quality_summary_rejects_empty_dataframe() -> None:
    """An empty quality summary input must be rejected."""

    with pytest.raises(
        ValueError,
        match="Cannot summarize quality for an empty DataFrame",
    ):
        create_quality_summary(pd.DataFrame())


def test_quality_summary_rejects_missing_columns() -> None:
    """A quality summary requires all expected indicator fields."""

    with pytest.raises(
        ValueError,
        match="Missing columns required for quality summary",
    ):
        create_quality_summary(
            pd.DataFrame(
                {
                    "has_data_quality_issue": [
                        True,
                    ]
                }
            )
        )


def test_row_count_is_preserved(
    financial_dataframe: pd.DataFrame,
    quality_dataframe: pd.DataFrame,
) -> None:
    """Quality control must not add or remove records."""

    assert len(financial_dataframe) == EXPECTED_ROWS
    assert len(quality_dataframe) == EXPECTED_ROWS


def test_expected_column_count(
    financial_dataframe: pd.DataFrame,
    quality_dataframe: pd.DataFrame,
) -> None:
    """Exactly eight quality-control columns must be added."""

    assert (
        financial_dataframe.shape[1]
        == EXPECTED_INPUT_COLUMNS
    )

    assert (
        quality_dataframe.shape[1]
        == EXPECTED_OUTPUT_COLUMNS
    )

    added_columns = [
        column
        for column in quality_dataframe.columns
        if column not in financial_dataframe.columns
    ]

    assert added_columns == QUALITY_CONTROL_COLUMNS


def test_input_dataframe_is_not_mutated(
    financial_dataframe: pd.DataFrame,
) -> None:
    """Quality control must not mutate its input DataFrame."""

    original_dataframe = financial_dataframe.copy(
        deep=True
    )

    add_quality_controls(financial_dataframe)

    assert_frame_equal(
        financial_dataframe,
        original_dataframe,
    )


def test_original_columns_are_preserved(
    financial_dataframe: pd.DataFrame,
    quality_dataframe: pd.DataFrame,
) -> None:
    """All preexisting financial columns must remain unchanged."""

    for column in financial_dataframe.columns:
        assert_series_equal(
            financial_dataframe[column],
            quality_dataframe[column],
            check_names=True,
            check_dtype=True,
        )


def test_data_quality_status_distribution(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Quality-status counts must match the audited extraction."""

    actual = (
        quality_dataframe["data_quality_status"]
        .value_counts()
        .to_dict()
    )

    assert actual == EXPECTED_DATA_QUALITY_STATUS_COUNTS


def test_analytical_eligibility_distribution(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Eligibility counts must match the audited extraction."""

    actual = (
        quality_dataframe["analytical_eligibility"]
        .value_counts()
        .to_dict()
    )

    assert actual == (
        EXPECTED_ANALYTICAL_ELIGIBILITY_COUNTS
    )


def test_business_risk_count_distribution(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Risk-signal counts must match the audited extraction."""

    actual = (
        quality_dataframe[
            "business_risk_signal_count"
        ]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    assert actual == (
        EXPECTED_BUSINESS_RISK_COUNT_DISTRIBUTION
    )


@pytest.mark.parametrize(
    ("flag", "expected_count"),
    EXPECTED_FLAG_COUNTS.items(),
)
def test_audited_flag_counts(
    quality_dataframe: pd.DataFrame,
    flag: str,
    expected_count: int,
) -> None:
    """Each quality and risk flag must match its audited count."""

    actual_count = int(
        quality_dataframe[flag].sum()
    )

    assert actual_count == expected_count


def test_data_quality_issue_count_matches_flags(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Quality issue counts must equal active data-quality flags."""

    expected = quality_dataframe[
        DATA_QUALITY_FLAGS
    ].sum(
        axis=1
    ).astype("Int64")

    assert_series_equal(
        quality_dataframe[
            "data_quality_issue_count"
        ],
        expected,
        check_names=False,
    )


def test_business_risk_count_matches_flags(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Risk-signal counts must equal active business-risk flags."""

    expected = quality_dataframe[
        BUSINESS_RISK_FLAGS
    ].sum(
        axis=1
    ).astype("Int64")

    assert_series_equal(
        quality_dataframe[
            "business_risk_signal_count"
        ],
        expected,
        check_names=False,
    )


def test_quality_boolean_matches_issue_count(
    quality_dataframe: pd.DataFrame,
) -> None:
    """The quality-issue boolean must agree with issue count."""

    expected = quality_dataframe[
        "data_quality_issue_count"
    ].gt(0)

    assert_series_equal(
        quality_dataframe[
            "has_data_quality_issue"
        ],
        expected,
        check_names=False,
    )


def test_business_risk_boolean_matches_count(
    quality_dataframe: pd.DataFrame,
) -> None:
    """The risk boolean must agree with risk-signal count."""

    expected = quality_dataframe[
        "business_risk_signal_count"
    ].gt(0)

    assert_series_equal(
        quality_dataframe[
            "has_business_risk_signal"
        ],
        expected,
        check_names=False,
    )


def test_clean_records_have_no_quality_reasons(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Records without quality issues must have an empty reason field."""

    clean_records = quality_dataframe.loc[
        ~quality_dataframe[
            "has_data_quality_issue"
        ]
    ]

    assert clean_records[
        "data_quality_reasons"
    ].eq("").all()


def test_records_without_risk_have_no_risk_reasons(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Records without business risk must have an empty reason field."""

    no_risk_records = quality_dataframe.loc[
        ~quality_dataframe[
            "has_business_risk_signal"
        ]
    ]

    assert no_risk_records[
        "business_risk_reasons"
    ].eq("").all()


def test_quality_summary_counts(
    quality_dataframe: pd.DataFrame,
) -> None:
    """The generated summary must reproduce audited flag counts."""

    summary = create_quality_summary(
        quality_dataframe
    )

    actual_counts = dict(
        zip(
            summary["indicator"],
            summary["record_count"],
            strict=True,
        )
    )

    assert actual_counts == EXPECTED_FLAG_COUNTS


def test_quality_summary_percentages_are_valid(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Summary percentages must remain between zero and one."""

    summary = create_quality_summary(
        quality_dataframe
    )

    assert summary[
        "record_percentage"
    ].between(
        0,
        1,
        inclusive="both",
    ).all()


def test_quality_summary_formula(
    quality_dataframe: pd.DataFrame,
) -> None:
    """Every summary percentage must equal count divided by 6,711."""

    summary = create_quality_summary(
        quality_dataframe
    )

    expected_percentage = (
        summary["record_count"]
        / EXPECTED_ROWS
    )

    assert_series_equal(
        summary["record_percentage"],
        expected_percentage,
        check_names=False,
    )