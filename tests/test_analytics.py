"""Tests for the CapexQuant SABI analytics module."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.analytics import (
    calculate_coverage,
    calculate_revenue_concentration,
    calculate_revenue_percentiles,
    create_company_ranking,
    create_municipality_summary,
    create_overview_summary,
    create_scope_comparison,
    filter_analytical_scope,
    validate_analytics_schema,
)
from src.financial_features import (
    EBITDA_LATEST,
    EMPLOYEES_LATEST,
    REVENUE_LATEST,
)
from src.quality_control import add_quality_controls


EXPECTED_ROWS = 6_711

EXPECTED_SCOPE_COUNTS = {
    "all": 6_711,
    "eligible": 6_278,
    "no_adverse_eligible": 5_250,
    "no_adverse_marker": 5_544,
}

EXPECTED_REVENUE_TOTAL_K_EUR = 42_731_101.586895
EXPECTED_EBITDA_TOTAL_K_EUR = 2_633_077
EXPECTED_EMPLOYEE_COUNT = 164_781

EXPECTED_CONCENTRATION = {
    1: 0.168239,
    2: 0.231412,
    5: 0.270276,
    10: 0.307652,
    20: 0.358249,
    50: 0.465195,
    100: 0.563467,
}

EXPECTED_REVENUE_PERCENTILES = {
    0.25: 413.959910,
    0.50: 862.842670,
    0.75: 2_287.070730,
    0.90: 7_375.732500,
    0.95: 17_701.411180,
    0.99: 91_365.107441,
}


@pytest.fixture(scope="module")
def analytical_dataframe() -> pd.DataFrame:
    """Create the complete validated analytical dataset once."""

    return add_quality_controls()


def test_validate_analytics_schema_accepts_valid_data(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """The complete analytical dataset must pass schema validation."""

    validate_analytics_schema(analytical_dataframe)


def test_validate_analytics_schema_rejects_missing_column(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """A missing required analytical field must raise an error."""

    invalid_dataframe = analytical_dataframe.drop(
        columns=["revenue_growth"]
    )

    with pytest.raises(
        ValueError,
        match="Missing columns required for analytics",
    ):
        validate_analytics_schema(invalid_dataframe)


def test_invalid_scope_is_rejected(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """An undocumented analytical scope must be rejected."""

    with pytest.raises(
        ValueError,
        match="Invalid analytical scope",
    ):
        filter_analytical_scope(
            analytical_dataframe,
            scope="invalid_scope",
        )


@pytest.mark.parametrize(
    ("scope", "expected_count"),
    EXPECTED_SCOPE_COUNTS.items(),
)
def test_scope_record_counts(
    analytical_dataframe: pd.DataFrame,
    scope: str,
    expected_count: int,
) -> None:
    """Analytical scopes must reproduce audited record counts."""

    scoped_dataframe = filter_analytical_scope(
        analytical_dataframe,
        scope,
    )

    assert len(scoped_dataframe) == expected_count


def test_scope_filter_does_not_mutate_input(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Scope filtering must not modify the original dataset."""

    original_dataframe = analytical_dataframe.copy(deep=True)

    filter_analytical_scope(
        analytical_dataframe,
        scope="no_adverse_eligible",
    )

    assert_frame_equal(
        analytical_dataframe,
        original_dataframe,
    )


def test_no_adverse_scope_contains_no_adverse_records(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """The no-adverse scope must exclude explicit adverse markers."""

    scoped_dataframe = filter_analytical_scope(
        analytical_dataframe,
        scope="no_adverse_marker",
    )

    assert not scoped_dataframe[
        "has_adverse_legal_status"
    ].any()


def test_eligible_scope_contains_only_eligible_records(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """The eligible scope must contain only standard eligible records."""

    scoped_dataframe = filter_analytical_scope(
        analytical_dataframe,
        scope="eligible",
    )

    assert scoped_dataframe[
        "analytical_eligibility"
    ].eq("eligible").all()


def test_overview_all_scope(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """The complete overview must reproduce audited totals."""

    summary = create_overview_summary(
        analytical_dataframe,
        scope="all",
    ).iloc[0]

    assert summary["company_count"] == EXPECTED_ROWS
    assert summary["employee_count"] == EXPECTED_EMPLOYEE_COUNT

    assert summary[
        "revenue_total_k_eur"
    ] == pytest.approx(
        EXPECTED_REVENUE_TOTAL_K_EUR,
        abs=0.01,
    )

    assert summary[
        "ebitda_total_k_eur"
    ] == pytest.approx(
        EXPECTED_EBITDA_TOTAL_K_EUR,
        abs=1,
    )

    assert summary[
        "median_revenue_k_eur"
    ] == pytest.approx(
        862.842670,
    )

    assert summary[
        "median_revenue_growth"
    ] == pytest.approx(
        0.022669,
        abs=0.000001,
    )

    assert summary[
        "median_ebitda_margin"
    ] == pytest.approx(
        0.044824,
        abs=0.000001,
    )


def test_scope_comparison_contains_all_scopes(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """The comparison table must contain each documented scope once."""

    comparison = create_scope_comparison(
        analytical_dataframe
    )

    assert set(comparison["scope"]) == set(
        EXPECTED_SCOPE_COUNTS
    )

    assert comparison["scope"].is_unique
    assert len(comparison) == 4


def test_scope_comparison_counts(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Scope comparison counts must match the audited filters."""

    comparison = (
        create_scope_comparison(
            analytical_dataframe
        )
        .set_index("scope")
    )

    for scope, expected_count in EXPECTED_SCOPE_COUNTS.items():
        assert (
            comparison.loc[
                scope,
                "company_count",
            ]
            == expected_count
        )


@pytest.mark.parametrize(
    ("top_n", "expected_share"),
    EXPECTED_CONCENTRATION.items(),
)
def test_revenue_concentration_regression(
    analytical_dataframe: pd.DataFrame,
    top_n: int,
    expected_share: float,
) -> None:
    """Top-N revenue shares must match audited results."""

    concentration = calculate_revenue_concentration(
        analytical_dataframe,
        top_levels=[top_n],
        scope="all",
    )

    actual_share = concentration.iloc[0][
        "concentration_rate"
    ]

    assert actual_share == pytest.approx(
        expected_share,
        abs=0.000001,
    )


def test_revenue_concentration_is_monotonic(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Accumulated revenue concentration must never decrease."""

    concentration = calculate_revenue_concentration(
        analytical_dataframe,
        scope="all",
    )

    assert concentration[
        "concentration_rate"
    ].is_monotonic_increasing


def test_invalid_concentration_level_is_rejected(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Top-N concentration levels must be positive integers."""

    with pytest.raises(ValueError):
        calculate_revenue_concentration(
            analytical_dataframe,
            top_levels=[0],
        )


@pytest.mark.parametrize(
    ("percentile", "expected_revenue"),
    EXPECTED_REVENUE_PERCENTILES.items(),
)
def test_revenue_percentile_regression(
    analytical_dataframe: pd.DataFrame,
    percentile: float,
    expected_revenue: float,
) -> None:
    """Revenue percentiles must match the audited extraction."""

    percentiles = calculate_revenue_percentiles(
        analytical_dataframe,
        percentiles=[percentile],
        scope="all",
    )

    actual_revenue = percentiles.iloc[0][
        "revenue_k_eur"
    ]

    assert actual_revenue == pytest.approx(
        expected_revenue,
        abs=0.000001,
    )


def test_invalid_percentile_is_rejected(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Percentiles outside zero and one must be rejected."""

    with pytest.raises(
        ValueError,
        match="Percentiles must remain between zero and one",
    ):
        calculate_revenue_percentiles(
            analytical_dataframe,
            percentiles=[1.1],
        )


def test_company_ranking_order(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Revenue ranking must be sorted from highest to lowest."""

    ranking = create_company_ranking(
        analytical_dataframe,
        metric=REVENUE_LATEST,
        top_n=10,
        scope="all",
    )

    assert len(ranking) == 10

    assert ranking[
        REVENUE_LATEST
    ].is_monotonic_decreasing

    assert ranking["rank"].tolist() == list(
        range(1, 11)
    )


def test_highest_revenue_value(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """The highest-revenue observation must match the audited value."""

    ranking = create_company_ranking(
        analytical_dataframe,
        metric=REVENUE_LATEST,
        top_n=1,
        scope="all",
    )

    assert ranking.iloc[0][
        REVENUE_LATEST
    ] == pytest.approx(
        7_189_039,
        abs=1,
    )


def test_invalid_ranking_metric_is_rejected(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """A missing ranking metric must raise an explicit error."""

    with pytest.raises(
        ValueError,
        match="Ranking metric not found",
    ):
        create_company_ranking(
            analytical_dataframe,
            metric="nonexistent_metric",
        )


def test_non_numeric_ranking_metric_is_rejected(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """A textual ranking field must be rejected."""

    with pytest.raises(
        ValueError,
        match="Ranking metric must be numeric",
    ):
        create_company_ranking(
            analytical_dataframe,
            metric="company_name",
        )


def test_municipality_summary_preserves_company_count(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Municipality aggregation must account for every company."""

    summary = create_municipality_summary(
        analytical_dataframe,
        scope="all",
    )

    assert summary["company_count"].sum() == EXPECTED_ROWS


def test_largest_raw_municipality_category(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """The leading raw municipality category must match the audit."""

    summary = create_municipality_summary(
        analytical_dataframe,
        scope="all",
    )

    first_row = summary.iloc[0]

    assert first_row[
        "municipality"
    ] == "CASTELLO DE LA PLANA"

    assert first_row[
        "company_count"
    ] == 1_707

    assert first_row[
        "employee_count"
    ] == 36_195


def test_coverage_regression(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Variable coverage must reproduce audited availability."""

    coverage = calculate_coverage(
        analytical_dataframe,
        [
            EMPLOYEES_LATEST,
            REVENUE_LATEST,
            EBITDA_LATEST,
            "revenue_growth",
            "ebitda_margin",
        ],
    ).set_index("variable")

    assert coverage.loc[
        EMPLOYEES_LATEST,
        "available_records",
    ] == 6_711

    assert coverage.loc[
        REVENUE_LATEST,
        "available_records",
    ] == 6_637

    assert coverage.loc[
        EBITDA_LATEST,
        "available_records",
    ] == 6_687

    assert coverage.loc[
        "revenue_growth",
        "available_records",
    ] == 6_436

    assert coverage.loc[
        "ebitda_margin",
        "available_records",
    ] == 6_637


def test_coverage_rates_are_valid(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Coverage rates must remain between zero and one."""

    coverage = calculate_coverage(
        analytical_dataframe,
        [REVENUE_LATEST, EBITDA_LATEST],
    )

    assert coverage[
        "coverage_rate"
    ].between(
        0,
        1,
        inclusive="both",
    ).all()