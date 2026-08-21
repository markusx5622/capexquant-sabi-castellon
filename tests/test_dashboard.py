"""Tests for the CapexQuant Streamlit dashboard module."""

import pandas as pd
import pytest

from src.dashboard import (
    VIEW_NAMES,
    compute_kpi_metrics,
    filter_company_dataframe,
    load_dashboard_data,
)
from src.pipeline import PipelineResult


def test_view_names_are_defined() -> None:
    """Verify that all standard view names are defined and non-empty."""
    assert len(VIEW_NAMES) == 11
    assert "Overview & Scope Comparison" in VIEW_NAMES
    assert "Variable Coverage" in VIEW_NAMES
    assert "Data Quality & Business Risk" in VIEW_NAMES
    assert "Revenue Concentration" in VIEW_NAMES
    assert "Revenue Percentiles" in VIEW_NAMES
    assert "Company Rankings" in VIEW_NAMES
    assert "Municipality Analysis & Treemap" in VIEW_NAMES
    assert "4D Quantitative Positioning" in VIEW_NAMES
    assert "🧪 Stress Testing & Scenario Lab" in VIEW_NAMES
    assert "🏢 Company Factsheet & Deep-Dive" in VIEW_NAMES
    assert "Company Explorer" in VIEW_NAMES


def test_load_dashboard_data_returns_synthetic_result() -> None:
    """Verify that load_dashboard_data runs the synthetic pipeline correctly."""
    result = load_dashboard_data()

    assert isinstance(result, PipelineResult)
    assert result.source_name == "synthetic"
    assert result.row_count == 120
    assert result.final_column_count == 36
    assert len(result.analytical_tables) == 7
    assert result.source_dataframe["company_name"].str.startswith("SYNTHETIC ").all()


def test_load_dashboard_data_custom_ranking() -> None:
    """Verify that custom ranking sizes are propagated to the pipeline."""
    result = load_dashboard_data(ranking_size=10)
    ranking_table = result.get_table("company_ranking")
    assert len(ranking_table) == 10


def test_compute_kpi_metrics_full_dataset() -> None:
    """Verify KPI metrics calculation on the full synthetic dataset."""
    result = load_dashboard_data()
    kpis = compute_kpi_metrics(result.quality_dataframe)

    assert kpis["total_companies"] == 120
    assert kpis["total_revenue_k_eur"] > 0
    assert kpis["median_revenue_k_eur"] > 0
    assert kpis["total_employees"] > 0
    assert 0.0 <= kpis["data_quality_issue_rate"] <= 1.0
    assert 0.0 <= kpis["business_risk_signal_rate"] <= 1.0
    assert kpis["eligible_companies"] > 0


def test_compute_kpi_metrics_empty_dataset() -> None:
    """Verify KPI metrics calculation on an empty DataFrame."""
    empty_df = pd.DataFrame(
        columns=[
            "operating_revenue_latest_k_eur",
            "ebitda_latest_k_eur",
            "ebitda_margin",
            "employees_latest",
            "has_data_quality_issue",
            "has_business_risk_signal",
            "analytical_eligibility",
        ]
    )
    kpis = compute_kpi_metrics(empty_df)

    assert kpis["total_companies"] == 0
    assert kpis["total_revenue_k_eur"] == 0.0
    assert kpis["median_revenue_k_eur"] == 0.0
    assert kpis["total_ebitda_k_eur"] == 0.0
    assert kpis["median_ebitda_margin"] == 0.0
    assert kpis["total_employees"] == 0
    assert kpis["data_quality_issue_rate"] == 0.0
    assert kpis["business_risk_signal_rate"] == 0.0
    assert kpis["eligible_companies"] == 0


def test_filter_company_dataframe_by_scope() -> None:
    """Verify filtering by analytical scope."""
    result = load_dashboard_data()
    df = result.quality_dataframe

    all_filtered = filter_company_dataframe(df, scope="all")
    assert len(all_filtered) == len(df)

    no_adverse = filter_company_dataframe(df, scope="no_adverse_marker")
    assert (no_adverse["has_adverse_legal_status"] == False).all()  # noqa: E712
    assert len(no_adverse) <= len(df)

    eligible = filter_company_dataframe(df, scope="eligible")
    assert (eligible["analytical_eligibility"] == "eligible").all()
    assert len(eligible) <= len(df)


def test_filter_company_dataframe_by_municipality() -> None:
    """Verify filtering by specific municipality."""
    result = load_dashboard_data()
    df = result.quality_dataframe

    munis = ["CASTELLO DE LA PLANA", "VILA-REAL"]
    filtered = filter_company_dataframe(df, selected_municipalities=munis)

    assert set(filtered["municipality"].unique()).issubset(set(munis))
    assert len(filtered) > 0


def test_filter_company_dataframe_by_revenue_range() -> None:
    """Verify filtering by min and max revenue."""
    result = load_dashboard_data()
    df = result.quality_dataframe

    filtered = filter_company_dataframe(
        df,
        min_revenue=1000.0,
        max_revenue=50000.0,
    )

    non_na_rev = filtered["operating_revenue_latest_k_eur"].dropna()
    assert (non_na_rev >= 1000.0).all()
    assert (non_na_rev <= 50000.0).all()


def test_filter_company_dataframe_by_employees_range() -> None:
    """Verify filtering by min and max employees."""
    result = load_dashboard_data()
    df = result.quality_dataframe

    filtered = filter_company_dataframe(
        df,
        min_employees=20,
        max_employees=200,
    )

    non_na_emp = filtered["employees_latest"].dropna()
    assert (non_na_emp >= 20).all()
    assert (non_na_emp <= 200).all()


def test_filter_company_dataframe_by_quality_status() -> None:
    """Verify filtering by data quality status."""
    result = load_dashboard_data()
    df = result.quality_dataframe

    filtered = filter_company_dataframe(
        df,
        quality_statuses=["clean"],
    )

    assert (filtered["data_quality_status"] == "clean").all()


def test_filter_company_dataframe_by_business_risk() -> None:
    """Verify filtering by business risk signal."""
    result = load_dashboard_data()
    df = result.quality_dataframe

    risk_only = filter_company_dataframe(
        df,
        risk_filter="Risk Signals Only",
    )
    assert (risk_only["has_business_risk_signal"] == True).all()  # noqa: E712

    no_risk = filter_company_dataframe(
        df,
        risk_filter="No Risk Signals",
    )
    assert (no_risk["has_business_risk_signal"] == False).all()  # noqa: E712
