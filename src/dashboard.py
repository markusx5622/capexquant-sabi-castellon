"""Streamlit interactive dashboard for CapexQuant SABI Castellón.

Provides a multi-view financial analytics dashboard built strictly on top of
the reproducible public synthetic dataset.
"""

from __future__ import annotations

import json
from typing import Any, Final

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.analytics import VALID_ANALYTICAL_SCOPES, filter_analytical_scope
from src.pipeline import (
    ANALYTICAL_TABLE_NAMES,
    DEFAULT_RANKING_SIZE,
    PipelineResult,
    run_pipeline,
)
from src.visualization import (
    create_company_ranking_figure,
    create_coverage_figure,
    create_municipality_summary_figure,
    create_revenue_concentration_figure,
    create_revenue_percentiles_figure,
)

VIEW_NAMES: Final[list[str]] = [
    "Overview & Scope Comparison",
    "Variable Coverage",
    "Data Quality & Business Risk",
    "Revenue Concentration",
    "Revenue Percentiles",
    "Company Rankings",
    "Municipality Analysis",
    "Company Explorer",
]


@st.cache_data(show_spinner=False)
def load_dashboard_data(
    ranking_size: int = DEFAULT_RANKING_SIZE,
) -> PipelineResult:
    """Execute the CapexQuant pipeline using exclusively the public synthetic source."""
    return run_pipeline(
        source="synthetic",
        ranking_size=ranking_size,
    )


def compute_kpi_metrics(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    """Compute high-level executive financial and data-quality KPI metrics."""
    if dataframe.empty:
        return {
            "total_companies": 0,
            "total_revenue_k_eur": 0.0,
            "median_revenue_k_eur": 0.0,
            "total_ebitda_k_eur": 0.0,
            "median_ebitda_margin": 0.0,
            "total_employees": 0,
            "data_quality_issue_rate": 0.0,
            "business_risk_signal_rate": 0.0,
            "eligible_companies": 0,
        }

    total_companies = len(dataframe)
    total_rev = dataframe["operating_revenue_latest_k_eur"].sum()
    med_rev = dataframe["operating_revenue_latest_k_eur"].median()
    total_ebitda = dataframe["ebitda_latest_k_eur"].sum()
    med_margin = dataframe["ebitda_margin"].median()
    total_emp = int(dataframe["employees_latest"].sum())
    
    dq_issues = int(dataframe["has_data_quality_issue"].sum()) if "has_data_quality_issue" in dataframe.columns else 0
    risk_signals = int(dataframe["has_business_risk_signal"].sum()) if "has_business_risk_signal" in dataframe.columns else 0
    eligible_count = int((dataframe["analytical_eligibility"] == "eligible").sum()) if "analytical_eligibility" in dataframe.columns else 0

    return {
        "total_companies": total_companies,
        "total_revenue_k_eur": float(total_rev) if pd.notna(total_rev) else 0.0,
        "median_revenue_k_eur": float(med_rev) if pd.notna(med_rev) else 0.0,
        "total_ebitda_k_eur": float(total_ebitda) if pd.notna(total_ebitda) else 0.0,
        "median_ebitda_margin": float(med_margin) if pd.notna(med_margin) else 0.0,
        "total_employees": total_emp,
        "data_quality_issue_rate": (dq_issues / total_companies) if total_companies > 0 else 0.0,
        "business_risk_signal_rate": (risk_signals / total_companies) if total_companies > 0 else 0.0,
        "eligible_companies": eligible_count,
    }


def filter_company_dataframe(
    dataframe: pd.DataFrame,
    scope: str = "all",
    selected_municipalities: list[str] | None = None,
    min_revenue: float | None = None,
    max_revenue: float | None = None,
    min_employees: int | None = None,
    max_employees: int | None = None,
    quality_statuses: list[str] | None = None,
    risk_filter: str = "All",
) -> pd.DataFrame:
    """Filter company dataset by scope, municipality, size ranges, and quality/risk status."""
    filtered_df = filter_analytical_scope(dataframe, scope=scope)

    if selected_municipalities:
        filtered_df = filtered_df[
            filtered_df["municipality"].isin(selected_municipalities)
        ]

    if min_revenue is not None:
        filtered_df = filtered_df[
            filtered_df["operating_revenue_latest_k_eur"].isna()
            | (filtered_df["operating_revenue_latest_k_eur"] >= min_revenue)
        ]

    if max_revenue is not None:
        filtered_df = filtered_df[
            filtered_df["operating_revenue_latest_k_eur"].isna()
            | (filtered_df["operating_revenue_latest_k_eur"] <= max_revenue)
        ]

    if min_employees is not None:
        filtered_df = filtered_df[
            filtered_df["employees_latest"].isna()
            | (filtered_df["employees_latest"] >= min_employees)
        ]

    if max_employees is not None:
        filtered_df = filtered_df[
            filtered_df["employees_latest"].isna()
            | (filtered_df["employees_latest"] <= max_employees)
        ]

    if quality_statuses:
        filtered_df = filtered_df[
            filtered_df["data_quality_status"].isin(quality_statuses)
        ]

    if risk_filter == "Risk Signals Only":
        filtered_df = filtered_df[filtered_df["has_business_risk_signal"] == True]  # noqa: E712
    elif risk_filter == "No Risk Signals":
        filtered_df = filtered_df[filtered_df["has_business_risk_signal"] == False]  # noqa: E712

    return filtered_df


def render_kpi_cards(kpi_metrics: dict[str, Any]) -> None:
    """Render executive metric cards in a responsive multi-column layout."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Companies",
            value=f"{kpi_metrics['total_companies']:,}",
            help="Total company records in the current scope",
        )
        st.metric(
            label="Total Employment",
            value=f"{kpi_metrics['total_employees']:,}",
            help="Aggregated workforce across companies",
        )

    with col2:
        st.metric(
            label="Aggregated Revenue",
            value=f"€{kpi_metrics['total_revenue_k_eur']:,.1f}k",
            help="Total latest operating revenue in thousands of EUR",
        )
        st.metric(
            label="Median Revenue",
            value=f"€{kpi_metrics['median_revenue_k_eur']:,.1f}k",
            help="Median operating revenue per company",
        )

    with col3:
        st.metric(
            label="Aggregated EBITDA",
            value=f"€{kpi_metrics['total_ebitda_k_eur']:,.1f}k",
            help="Total latest EBITDA in thousands of EUR",
        )
        st.metric(
            label="Median EBITDA Margin",
            value=f"{kpi_metrics['median_ebitda_margin']:.1%}",
            help="Median ratio of EBITDA to Operating Revenue",
        )

    with col4:
        st.metric(
            label="DQ Issue Rate",
            value=f"{kpi_metrics['data_quality_issue_rate']:.1%}",
            help="Proportion of records with active data quality issues",
        )
        st.metric(
            label="Business Risk Rate",
            value=f"{kpi_metrics['business_risk_signal_rate']:.1%}",
            help="Proportion of records with active business risk signals",
        )


def render_download_buttons(
    dataframe: pd.DataFrame,
    filename_prefix: str,
    key_suffix: str = "",
) -> None:
    """Provide standard CSV and JSON download buttons for any dataframe."""
    col1, col2 = st.columns(2)
    with col1:
        csv_data = dataframe.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"{filename_prefix}.csv",
            mime="text/csv",
            key=f"dl_csv_{filename_prefix}_{key_suffix}",
            use_container_width=True,
        )
    with col2:
        json_data = dataframe.to_json(orient="records", indent=2).encode("utf-8")
        st.download_button(
            label="📥 Download JSON",
            data=json_data,
            file_name=f"{filename_prefix}.json",
            mime="application/json",
            key=f"dl_json_{filename_prefix}_{key_suffix}",
            use_container_width=True,
        )


def render_scope_comparison_view(pipeline_result: PipelineResult) -> None:
    """Render Scope Comparison view."""
    st.subheader("1. Analytical Scope Comparison")
    st.markdown(
        "Comparative evaluation across documented analytical scopes. "
        "Filters are explicit and records are not silently deleted."
    )

    scope_table = pipeline_result.get_table("scope_comparison")
    st.dataframe(
        scope_table.style.format(
            {
                "company_count": "{:,}",
                "employee_count": "{:,}",
                "revenue_available_count": "{:,}",
                "ebitda_available_count": "{:,}",
                "revenue_total_k_eur": "€{:,.1f}k",
                "ebitda_total_k_eur": "€{:,.1f}k",
                "median_employees": "{:,.1f}",
                "median_revenue_k_eur": "€{:,.1f}k",
                "median_ebitda_k_eur": "€{:,.1f}k",
                "median_revenue_growth": "{:.2%}",
                "median_ebitda_margin": "{:.2%}",
                "negative_ebitda_count": "{:,}",
                "revenue_decline_count": "{:,}",
            }
        ),
        use_container_width=True,
    )
    render_download_buttons(scope_table, "scope_comparison")


def render_coverage_view(pipeline_result: PipelineResult) -> None:
    """Render Variable Coverage view."""
    st.subheader("2. Variable Coverage & Data Completeness")
    st.markdown(
        "Observation availability and missing rates across core financial fields. "
        "Missing values are preserved rather than converted to artificial zeros."
    )

    coverage_table = pipeline_result.get_table("coverage")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(
            coverage_table.style.format(
                {
                    "available_records": "{:,}",
                    "missing_records": "{:,}",
                    "coverage_rate": "{:.1%}",
                }
            ),
            use_container_width=True,
        )
        render_download_buttons(coverage_table, "coverage")

    with col2:
        fig = create_coverage_figure(coverage_table)
        st.pyplot(fig)
        plt.close(fig)


def render_quality_view(pipeline_result: PipelineResult) -> None:
    """Render Data Quality and Business Risk summary view."""
    st.subheader("3. Data Quality & Business Risk Screening")
    st.markdown(
        "Strict separation between **data-quality issues** (incomplete data, zero denominators, "
        "extreme margins) and **business-risk signals** (negative EBITDA, revenue decline, adverse legal markers)."
    )

    quality_table = pipeline_result.get_table("quality_summary")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("#### Quality & Risk Indicators")
        st.dataframe(
            quality_table.style.format(
                {
                    "record_count": "{:,}",
                    "record_percentage": "{:.2%}",
                }
            ),
            use_container_width=True,
        )
        render_download_buttons(quality_table, "quality_summary")

    with col2:
        st.markdown("#### Status Breakdown")
        quality_df = pipeline_result.quality_dataframe
        status_counts = quality_df["data_quality_status"].value_counts().reset_index()
        status_counts.columns = ["Data Quality Status", "Company Count"]
        
        eligibility_counts = quality_df["analytical_eligibility"].value_counts().reset_index()
        eligibility_counts.columns = ["Analytical Eligibility", "Company Count"]
        
        st.dataframe(status_counts, use_container_width=True)
        st.dataframe(eligibility_counts, use_container_width=True)


def render_concentration_view(pipeline_result: PipelineResult) -> None:
    """Render Revenue Concentration view."""
    st.subheader("4. Cumulative Revenue Concentration")
    st.markdown(
        "Top-N cumulative revenue distribution showing economic concentration without disclosing confidential entities."
    )

    concentration_table = pipeline_result.get_table("revenue_concentration")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(
            concentration_table.style.format(
                {
                    "top_n": "{:,}",
                    "companies_included": "{:,}",
                    "revenue_k_eur": "€{:,.1f}k",
                    "concentration_rate": "{:.2%}",
                }
            ),
            use_container_width=True,
        )
        render_download_buttons(concentration_table, "revenue_concentration")

    with col2:
        fig = create_revenue_concentration_figure(concentration_table)
        st.pyplot(fig)
        plt.close(fig)


def render_percentiles_view(pipeline_result: PipelineResult) -> None:
    """Render Revenue Percentiles view."""
    st.subheader("5. Revenue Distribution Percentiles")
    st.markdown(
        "Operating revenue quantiles (P25 to P99) capturing distribution skewness and scale disparities."
    )

    percentiles_table = pipeline_result.get_table("revenue_percentiles")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(
            percentiles_table.style.format(
                {
                    "percentile": lambda p: f"P{int(p*100)}",
                    "revenue_k_eur": "€{:,.1f}k",
                }
            ),
            use_container_width=True,
        )
        render_download_buttons(percentiles_table, "revenue_percentiles")

    with col2:
        fig = create_revenue_percentiles_figure(percentiles_table)
        st.pyplot(fig)
        plt.close(fig)


def render_rankings_view(pipeline_result: PipelineResult) -> None:
    """Render Company Rankings view."""
    st.subheader("6. Company Revenue Rankings")
    st.markdown(
        "Ranked leaderboards by operating revenue. All entities in the public demonstration "
        "are explicitly prefixed with `SYNTHETIC`."
    )

    ranking_table = pipeline_result.get_table("company_ranking")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(
            ranking_table.style.format(
                {
                    "rank": "#{:,}",
                    "employees_latest": "{:,}",
                    "operating_revenue_latest_k_eur": "€{:,.1f}k",
                    "ebitda_latest_k_eur": "€{:,.1f}k",
                    "revenue_growth": "{:.2%}",
                    "ebitda_margin": "{:.2%}",
                }
            ),
            use_container_width=True,
        )
        render_download_buttons(ranking_table, "company_ranking")

    with col2:
        fig = create_company_ranking_figure(ranking_table, top_n=min(15, len(ranking_table)))
        st.pyplot(fig)
        plt.close(fig)


def render_municipality_view(pipeline_result: PipelineResult) -> None:
    """Render Municipality Analysis view."""
    st.subheader("7. Municipality Aggregations")
    st.markdown(
        "Geographic distribution of companies, employment, aggregate revenues, EBITDA and adverse legal statuses."
    )

    muni_table = pipeline_result.get_table("municipality_summary")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(
            muni_table.style.format(
                {
                    "company_count": "{:,}",
                    "employee_count": "{:,}",
                    "revenue_total_k_eur": "€{:,.1f}k",
                    "ebitda_total_k_eur": "€{:,.1f}k",
                    "median_revenue_k_eur": "€{:,.1f}k",
                    "median_ebitda_margin": "{:.2%}",
                    "adverse_status_count": "{:,}",
                    "negative_ebitda_count": "{:,}",
                    "adverse_status_rate": "{:.1%}",
                    "negative_ebitda_rate": "{:.1%}",
                }
            ),
            use_container_width=True,
        )
        render_download_buttons(muni_table, "municipality_summary")

    with col2:
        fig = create_municipality_summary_figure(muni_table, top_n=min(10, len(muni_table)))
        st.pyplot(fig)
        plt.close(fig)


def render_company_explorer_view(quality_dataframe: pd.DataFrame) -> None:
    """Render Interactive Company-Level Explorer."""
    st.subheader("8. Interactive Company-Level Explorer")
    st.markdown(
        "Search, filter and inspect full 36-column company-level analytical observations "
        "derived from the synthetic public dataset."
    )

    st.write(f"Showing **{len(quality_dataframe):,}** company records matching active filters.")
    
    display_cols = [
        "record_order",
        "company_name",
        "municipality",
        "employees_latest",
        "operating_revenue_latest_k_eur",
        "ebitda_latest_k_eur",
        "revenue_growth",
        "ebitda_margin",
        "data_quality_status",
        "analytical_eligibility",
        "has_business_risk_signal",
        "data_quality_reasons",
        "business_risk_reasons",
    ]
    
    available_display_cols = [c for c in display_cols if c in quality_dataframe.columns]
    
    st.dataframe(
        quality_dataframe[available_display_cols].style.format(
            {
                "employees_latest": lambda x: f"{x:,.0f}" if pd.notna(x) else "-",
                "operating_revenue_latest_k_eur": lambda x: f"€{x:,.1f}k" if pd.notna(x) else "-",
                "ebitda_latest_k_eur": lambda x: f"€{x:,.1f}k" if pd.notna(x) else "-",
                "revenue_growth": lambda x: f"{x:.2%}" if pd.notna(x) else "-",
                "ebitda_margin": lambda x: f"{x:.2%}" if pd.notna(x) else "-",
            }
        ),
        use_container_width=True,
    )
    render_download_buttons(quality_dataframe, "companies_quality_controlled")


def render_dashboard() -> None:
    """Main rendering entry point for the Streamlit dashboard."""
    st.set_page_config(
        page_title="CapexQuant SABI Castellón Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("📊 CapexQuant SABI Castellón")
    st.caption(
        "Reproducible Corporate Financial Analytics, Data Quality & Business Risk Screening "
        "• Public Synthetic Dataset"
    )

    # Sidebar setup
    with st.sidebar:
        st.header("⚙️ Configuration & Filters")
        st.info(
            "🔒 **Data Policy:** Running in 100% public synthetic mode. "
            "Private SABI microdata is never loaded or exposed."
        )

        selected_view = st.selectbox(
            "Select Analytical View",
            options=VIEW_NAMES,
            index=0,
        )

        st.divider()
        st.subheader("Global Filters")

        scope_option = st.selectbox(
            "Analytical Scope",
            options=sorted(VALID_ANALYTICAL_SCOPES),
            index=0,
            help="Filter by strict analytical scope definition",
        )

        ranking_size = st.slider(
            "Leaderboard Ranking Size",
            min_value=5,
            max_value=50,
            value=DEFAULT_RANKING_SIZE,
            step=5,
        )

    # Load baseline pipeline results
    pipeline_result = load_dashboard_data(ranking_size=ranking_size)
    full_quality_df = pipeline_result.quality_dataframe

    # Additional sidebar filters based on available dataset values
    municipalities_available = sorted(full_quality_df["municipality"].dropna().unique().tolist())
    
    with st.sidebar:
        selected_munis = st.multiselect(
            "Municipalities",
            options=municipalities_available,
            default=[],
            help="Leave empty to include all municipalities",
        )

        dq_status_options = ["clean", "review", "high_priority_review"]
        selected_dq_statuses = st.multiselect(
            "Data Quality Status",
            options=dq_status_options,
            default=[],
            help="Leave empty for all data quality statuses",
        )

        risk_filter = st.radio(
            "Business Risk Signal",
            options=["All", "Risk Signals Only", "No Risk Signals"],
            index=0,
        )

    # Filtered company dataset
    filtered_df = filter_company_dataframe(
        dataframe=full_quality_df,
        scope=scope_option,
        selected_municipalities=selected_munis if selected_munis else None,
        quality_statuses=selected_dq_statuses if selected_dq_statuses else None,
        risk_filter=risk_filter,
    )

    # Top KPI summary for the filtered population
    kpis = compute_kpi_metrics(filtered_df)
    render_kpi_cards(kpis)
    st.divider()

    # Route view
    if selected_view == "Overview & Scope Comparison":
        render_scope_comparison_view(pipeline_result)
    elif selected_view == "Variable Coverage":
        render_coverage_view(pipeline_result)
    elif selected_view == "Data Quality & Business Risk":
        render_quality_view(pipeline_result)
    elif selected_view == "Revenue Concentration":
        render_concentration_view(pipeline_result)
    elif selected_view == "Revenue Percentiles":
        render_percentiles_view(pipeline_result)
    elif selected_view == "Company Rankings":
        render_rankings_view(pipeline_result)
    elif selected_view == "Municipality Analysis":
        render_municipality_view(pipeline_result)
    elif selected_view == "Company Explorer":
        render_company_explorer_view(filtered_df)

    st.divider()
    st.caption(
        "CapexQuant SABI Castellón • MIT License • "
        "Public demonstrations use deterministic synthetic simulation (Seed 20260820)."
    )


if __name__ == "__main__":
    render_dashboard()
