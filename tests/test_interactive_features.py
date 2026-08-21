"""Tests for CapexQuant interactive visualization and stress testing modules."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.dashboard import load_dashboard_data
from src.interactive_charts import (
    create_health_gauge_chart,
    create_interactive_concentration_chart,
    create_interactive_coverage_chart,
    create_interactive_percentiles_chart,
    create_interactive_quadrant_scatter,
    create_interactive_rankings_chart,
    create_interactive_treemap,
    create_radar_benchmark_chart,
    create_stress_test_comparison_chart,
)
from src.stress_testing import (
    apply_macroeconomic_stress,
    calculate_stress_impact_summary,
    compute_company_health_score,
    generate_executive_briefing,
)


@pytest.fixture
def synthetic_pipeline_result():
    """Load the synthetic pipeline execution result."""
    return load_dashboard_data()


def test_apply_macroeconomic_stress_negative_shock(synthetic_pipeline_result) -> None:
    """Verify that a negative revenue shock and cost inflation reduces EBITDA."""
    df = synthetic_pipeline_result.quality_dataframe
    stressed_df = apply_macroeconomic_stress(
        dataframe=df,
        revenue_shock_pct=-10.0,
        cost_inflation_pct=5.0,
    )

    assert len(stressed_df) == len(df)
    assert "stressed_revenue_k_eur" in stressed_df.columns
    assert "stressed_ebitda_k_eur" in stressed_df.columns
    assert "is_newly_distressed" in stressed_df.columns

    # Stressed total EBITDA should be strictly lower than baseline
    base_ebitda = df["ebitda_latest_k_eur"].sum()
    stressed_ebitda = stressed_df["stressed_ebitda_k_eur"].sum()
    assert stressed_ebitda < base_ebitda


def test_apply_macroeconomic_stress_zero_shock(synthetic_pipeline_result) -> None:
    """Verify that 0% shock preserves baseline values."""
    df = synthetic_pipeline_result.quality_dataframe
    stressed_df = apply_macroeconomic_stress(
        dataframe=df,
        revenue_shock_pct=0.0,
        cost_inflation_pct=0.0,
    )

    pd.testing.assert_series_equal(
        df["operating_revenue_latest_k_eur"],
        stressed_df["stressed_revenue_k_eur"],
        check_names=False,
    )


def test_calculate_stress_impact_summary(synthetic_pipeline_result) -> None:
    """Verify calculation of stress impact metrics."""
    df = synthetic_pipeline_result.quality_dataframe
    stressed_df = apply_macroeconomic_stress(
        dataframe=df,
        revenue_shock_pct=-15.0,
        cost_inflation_pct=8.0,
    )

    summary = calculate_stress_impact_summary(df, stressed_df)

    assert summary["base_total_revenue_k_eur"] > 0
    assert summary["stressed_total_revenue_k_eur"] < summary["base_total_revenue_k_eur"]
    assert summary["revenue_delta_k_eur"] < 0
    assert summary["ebitda_delta_k_eur"] < 0
    assert summary["stressed_negative_ebitda_count"] >= summary["base_negative_ebitda_count"]
    assert 0.0 <= summary["resilience_rate"] <= 1.0


def test_calculate_stress_impact_summary_empty() -> None:
    """Verify calculation on empty DataFrames."""
    empty_df = pd.DataFrame(
        columns=[
            "operating_revenue_latest_k_eur",
            "ebitda_latest_k_eur",
            "employees_latest",
        ]
    )
    summary = calculate_stress_impact_summary(empty_df, empty_df)
    assert summary["base_total_revenue_k_eur"] == 0.0
    assert summary["resilience_rate"] == 1.0


def test_compute_company_health_score_clean_record() -> None:
    """Verify score calculation on a pristine record."""
    clean_row = pd.Series(
        {
            "company_name": "TEST CLEAN SL",
            "has_incomplete_financial_data": False,
            "has_negative_latest_revenue": False,
            "has_zero_latest_revenue": False,
            "has_extreme_ebitda_margin": False,
            "potential_duplicate": False,
            "has_adverse_legal_status": False,
            "has_negative_latest_ebitda": False,
            "has_revenue_decline": False,
            "ebitda_latest_k_eur": 500.0,
            "revenue_growth": 0.12,
            "ebitda_margin": 0.18,
        }
    )

    health = compute_company_health_score(clean_row)
    assert health["health_score"] >= 90
    assert health["grade"] == "AAA"
    assert len(health["deductions"]) == 0
    assert len(health["positives"]) > 0


def test_compute_company_health_score_distressed_record() -> None:
    """Verify score calculation on a distressed record."""
    distressed_row = pd.Series(
        {
            "company_name": "TEST DISTRESSED SL",
            "has_incomplete_financial_data": True,
            "has_negative_latest_revenue": False,
            "has_zero_latest_revenue": False,
            "has_extreme_ebitda_margin": True,
            "potential_duplicate": False,
            "has_adverse_legal_status": True,
            "has_negative_latest_ebitda": True,
            "has_revenue_decline": True,
            "ebitda_latest_k_eur": -200.0,
            "revenue_growth": -0.40,
            "ebitda_margin": -0.35,
        }
    )

    health = compute_company_health_score(distressed_row)
    assert health["health_score"] < 40
    assert "CCC" in health["grade"] or health["grade"] == "B"
    assert len(health["deductions"]) >= 4


def test_generate_executive_briefing(synthetic_pipeline_result) -> None:
    """Verify generation of automated executive briefing text."""
    df = synthetic_pipeline_result.quality_dataframe
    kpis = {
        "total_companies": 120,
        "total_revenue_k_eur": 150000.0,
        "median_revenue_k_eur": 12000.0,
        "total_ebitda_k_eur": 18000.0,
        "median_ebitda_margin": 0.12,
        "total_employees": 8500,
        "data_quality_issue_rate": 0.033,
        "business_risk_signal_rate": 0.15,
        "eligible_companies": 116,
    }

    briefing = generate_executive_briefing(df, kpis)
    assert isinstance(briefing, str)
    assert "Executive Intelligence Briefing" in briefing
    assert "120" in briefing
    assert "Takeaways" in briefing


def test_interactive_charts_return_figures(synthetic_pipeline_result) -> None:
    """Verify that all Plotly chart builders return valid Figure instances."""
    res = synthetic_pipeline_result

    fig_conc = create_interactive_concentration_chart(res.get_table("revenue_concentration"))
    assert isinstance(fig_conc, go.Figure)

    fig_quad = create_interactive_quadrant_scatter(res.quality_dataframe)
    assert isinstance(fig_quad, go.Figure)

    fig_tree = create_interactive_treemap(res.quality_dataframe)
    assert isinstance(fig_tree, go.Figure)

    fig_pct = create_interactive_percentiles_chart(res.get_table("revenue_percentiles"))
    assert isinstance(fig_pct, go.Figure)

    fig_rank = create_interactive_rankings_chart(res.get_table("company_ranking"))
    assert isinstance(fig_rank, go.Figure)

    fig_cov = create_interactive_coverage_chart(res.get_table("coverage"))
    assert isinstance(fig_cov, go.Figure)

    sample_row = res.quality_dataframe.iloc[0]
    fig_radar = create_radar_benchmark_chart(sample_row, res.quality_dataframe)
    assert isinstance(fig_radar, go.Figure)

    fig_gauge = create_health_gauge_chart(score=85, grade="AA", grade_color="#34D399")
    assert isinstance(fig_gauge, go.Figure)

    stressed_df = apply_macroeconomic_stress(res.quality_dataframe, revenue_shock_pct=-10.0)
    fig_comp = create_stress_test_comparison_chart(res.quality_dataframe, stressed_df)
    assert isinstance(fig_comp, go.Figure)
