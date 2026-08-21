"""Streamlit interactive quantitative terminal for CapexQuant SABI Castellón.

Provides a Tier-1 multi-view financial analytics dashboard built strictly on top of
the reproducible public synthetic dataset with Plotly interactive charts and stress-testing.
"""

from __future__ import annotations

import json
from typing import Any, Final

import pandas as pd
import streamlit as st

from src.analytics import VALID_ANALYTICAL_SCOPES, filter_analytical_scope
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
from src.pipeline import (
    DEFAULT_RANKING_SIZE,
    PipelineResult,
    run_pipeline,
)
from src.stress_testing import (
    apply_macroeconomic_stress,
    calculate_stress_impact_summary,
    compute_company_health_score,
    generate_executive_briefing,
)

VIEW_NAMES: Final[list[str]] = [
    "Overview & Scope Comparison",
    "Variable Coverage",
    "Data Quality & Business Risk",
    "Revenue Concentration",
    "Revenue Percentiles",
    "Company Rankings",
    "Municipality Analysis & Treemap",
    "4D Quantitative Positioning",
    "🧪 Stress Testing & Scenario Lab",
    "🏢 Company Factsheet & Deep-Dive",
    "Company Explorer",
]


def inject_custom_theme_css() -> None:
    """Inject institutional financial terminal CSS styling with glassmorphism and modern cards."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        /* Metric Card Container Styling */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 14px 18px;
            box-shadow: 0 2px 4px rgba(15, 23, 42, 0.04);
            transition: all 0.2s ease-in-out;
        }
        
        div[data-testid="stMetric"]:hover {
            border-color: #3B82F6;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
            transform: translateY(-1px);
        }
        
        div[data-testid="stMetricLabel"] {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748B !important;
        }
        
        div[data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 1.45rem !important;
            font-weight: 700 !important;
            color: #0F172A !important;
        }
        
        /* Badge Pill Utilities */
        .pill-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .pill-emerald { background-color: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; }
        .pill-amber { background-color: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }
        .pill-rose { background-color: #FFE4E6; color: #BE123C; border: 1px solid #FECDD3; }
        .pill-blue { background-color: #DBEAFE; color: #1D4ED8; border: 1px solid #BFDBFE; }
        
        /* Glassmorphic Highlights Box */
        .glass-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.95));
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }
        
        /* Styled Buttons */
        div.stDownloadButton > button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            border: 1px solid #CBD5E1 !important;
            transition: all 0.2s ease !important;
        }
        div.stDownloadButton > button:hover {
            border-color: #1E88E5 !important;
            color: #1E88E5 !important;
            background-color: #EFF6FF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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

    dq_issues = (
        int(dataframe["has_data_quality_issue"].sum())
        if "has_data_quality_issue" in dataframe.columns
        else 0
    )
    risk_signals = (
        int(dataframe["has_business_risk_signal"].sum())
        if "has_business_risk_signal" in dataframe.columns
        else 0
    )
    eligible_count = (
        int((dataframe["analytical_eligibility"] == "eligible").sum())
        if "analytical_eligibility" in dataframe.columns
        else 0
    )

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


def render_scope_comparison_view(
    pipeline_result: PipelineResult,
    filtered_df: pd.DataFrame,
    kpis: dict[str, Any],
) -> None:
    """Render Scope Comparison view with optional automated Executive Briefing."""
    st.subheader("1. Analytical Scope Comparison & Executive Intelligence")
    
    with st.expander("⚡ **Generate Automated Executive Intelligence Briefing**", expanded=True):
        briefing_md = generate_executive_briefing(filtered_df, kpis)
        st.markdown(briefing_md)

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
    """Render Variable Coverage view with interactive completion chart."""
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
        fig = create_interactive_coverage_chart(coverage_table)
        st.plotly_chart(fig, use_container_width=True)


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
        st.markdown("#### Cohort Health Classification Breakdown")
        quality_df = pipeline_result.quality_dataframe
        status_counts = quality_df["data_quality_status"].value_counts().reset_index()
        status_counts.columns = ["Data Quality Status", "Company Count"]

        eligibility_counts = (
            quality_df["analytical_eligibility"].value_counts().reset_index()
        )
        eligibility_counts.columns = ["Analytical Eligibility", "Company Count"]

        st.dataframe(status_counts, use_container_width=True)
        st.dataframe(eligibility_counts, use_container_width=True)


def render_concentration_view(pipeline_result: PipelineResult) -> None:
    """Render Revenue Concentration view with interactive Lorenz Curve."""
    st.subheader("4. Cumulative Revenue Concentration (Lorenz Curve)")
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
        fig = create_interactive_concentration_chart(concentration_table)
        st.plotly_chart(fig, use_container_width=True)


def render_percentiles_view(pipeline_result: PipelineResult) -> None:
    """Render Revenue Percentiles view with interactive quantile chart."""
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
        fig = create_interactive_percentiles_chart(percentiles_table)
        st.plotly_chart(fig, use_container_width=True)


def render_rankings_view(pipeline_result: PipelineResult) -> None:
    """Render Company Rankings view with interactive horizontal leaderboard."""
    st.subheader("6. Company Revenue Rankings & Leaderboard")
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
        fig = create_interactive_rankings_chart(ranking_table, top_n=min(15, len(ranking_table)))
        st.plotly_chart(fig, use_container_width=True)


def render_municipality_view(
    pipeline_result: PipelineResult,
    filtered_df: pd.DataFrame,
) -> None:
    """Render Municipality Analysis view with interactive Treemap."""
    st.subheader("7. Municipality Aggregations & Geographic Treemap")
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
        st.markdown("#### Geographic Treemap (Size = Revenue, Color = EBITDA Margin)")
        fig = create_interactive_treemap(filtered_df)
        st.plotly_chart(fig, use_container_width=True)


def render_quadrant_positioning_view(filtered_df: pd.DataFrame) -> None:
    """Render 4D Quantitative Financial Scatter view."""
    st.subheader("8. 4D Quantitative Positioning (Scale vs Margin vs Employment vs Risk)")
    st.markdown(
        "Multivariate positioning map showing scale on the horizontal axis (log scale), operating profitability "
        "on the vertical axis, bubble size proportional to headcount, and color representing health/risk status."
    )

    fig = create_interactive_quadrant_scatter(filtered_df)
    st.plotly_chart(fig, use_container_width=True)


def render_stress_testing_view(filtered_df: pd.DataFrame) -> None:
    """Render What-If Stress Testing & Macro Scenario Lab."""
    st.subheader("9. 🧪 What-If Stress Testing & Macroeconomic Scenario Lab")
    st.markdown(
        "Simulate corporate distress propagation and credit impairment in real time under "
        "macroeconomic shocks (revenue contraction and cost inflation)."
    )

    st.markdown("#### ⚙️ Define Macroeconomic Shock Parameters")
    ctrl_col1, ctrl_col2 = st.columns(2)

    with ctrl_col1:
        rev_shock = st.slider(
            "Revenue Contraction Shock (%)",
            min_value=-40.0,
            max_value=20.0,
            value=-15.0,
            step=1.0,
            help="Simulated percentage decline in operating revenue",
        )
    with ctrl_col2:
        cost_inflation = st.slider(
            "Operating Cost Inflation (%)",
            min_value=0.0,
            max_value=25.0,
            value=8.0,
            step=0.5,
            help="Simulated percentage increase in non-EBITDA operating costs",
        )

    stressed_df = apply_macroeconomic_stress(
        dataframe=filtered_df,
        revenue_shock_pct=rev_shock,
        cost_inflation_pct=cost_inflation,
    )

    impact = calculate_stress_impact_summary(filtered_df, stressed_df)

    st.markdown("#### 📊 Post-Shock Impact Scorecard")
    imp_col1, imp_col2, imp_col3, imp_col4 = st.columns(4)

    with imp_col1:
        st.metric(
            label="Stressed Revenue",
            value=f"€{impact['stressed_total_revenue_k_eur']:,.1f}k",
            delta=f"{impact['revenue_delta_k_eur']:,.1f}k",
        )
    with imp_col2:
        st.metric(
            label="Stressed EBITDA",
            value=f"€{impact['stressed_total_ebitda_k_eur']:,.1f}k",
            delta=f"{impact['ebitda_delta_k_eur']:,.1f}k",
        )
    with imp_col3:
        st.metric(
            label="Newly Distressed Companies",
            value=f"{impact['newly_distressed_count']:,}",
            help="Companies that were previously profitable but turned EBITDA negative",
        )
    with imp_col4:
        st.metric(
            label="Vulnerable Workforce",
            value=f"{impact['jobs_in_distressed_entities']:,}",
            help="Total employees working in distressed / loss-making entities",
        )

    fig = create_stress_test_comparison_chart(filtered_df, stressed_df)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 View Distressed Companies under Stressed Scenario"):
        newly_distressed_df = stressed_df[stressed_df["is_newly_distressed"]].copy()
        if newly_distressed_df.empty:
            st.info("No companies transitioned into distress under the configured scenario.")
        else:
            st.dataframe(
                newly_distressed_df[
                    [
                        "company_name",
                        "municipality",
                        "employees_latest",
                        "operating_revenue_latest_k_eur",
                        "stressed_revenue_k_eur",
                        "ebitda_latest_k_eur",
                        "stressed_ebitda_k_eur",
                        "stressed_ebitda_margin",
                    ]
                ].style.format(
                    {
                        "employees_latest": "{:,}",
                        "operating_revenue_latest_k_eur": "€{:,.1f}k",
                        "stressed_revenue_k_eur": "€{:,.1f}k",
                        "ebitda_latest_k_eur": "€{:,.1f}k",
                        "stressed_ebitda_k_eur": "€{:,.1f}k",
                        "stressed_ebitda_margin": "{:.2%}",
                    }
                ),
                use_container_width=True,
            )


def render_company_factsheet_view(
    quality_dataframe: pd.DataFrame,
    full_quality_df: pd.DataFrame,
) -> None:
    """Render individual Company Factsheet & Deep-Dive Dossier."""
    st.subheader("10. 🏢 Company Factsheet & Deep-Dive Dossier")
    st.markdown(
        "Select any company to inspect its institutional factsheet, financial health gauge, "
        "and 5D Radar benchmark against provincial medians."
    )

    company_names = sorted(quality_dataframe["company_name"].dropna().unique().tolist())

    if not company_names:
        st.warning("No companies match the current filter criteria.")
        return

    selected_company = st.selectbox(
        "Select Company for Deep-Dive Analysis",
        options=company_names,
        index=0,
    )

    company_row = quality_dataframe[
        quality_dataframe["company_name"] == selected_company
    ].iloc[0]

    health_info = compute_company_health_score(company_row)

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.markdown(f"### **{selected_company}**")
        st.markdown(
            f"📍 **Municipality:** {company_row.get('municipality', 'N/A')} | "
            f"👥 **Employees:** {company_row.get('employees_latest', 0):,}"
        )
        st.markdown(f"**Assessment:** {health_info['assessment']}")

        fig_gauge = create_health_gauge_chart(
            score=health_info["health_score"],
            grade=health_info["grade"],
            grade_color=health_info["grade_color"],
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        st.markdown("#### Score Deductions & Strengths")
        if health_info["positives"]:
            for pos in health_info["positives"]:
                st.markdown(f"✅ <span class='pill-badge pill-emerald'>{pos}</span>", unsafe_allow_html=True)
        if health_info["deductions"]:
            for ded in health_info["deductions"]:
                st.markdown(f"⚠️ <span class='pill-badge pill-rose'>{ded['factor']} ({ded['points']} pts)</span>", unsafe_allow_html=True)

    with col2:
        st.markdown("#### 5D Benchmark vs Provincial Median (P50)")
        fig_radar = create_radar_benchmark_chart(company_row, full_quality_df)
        st.plotly_chart(fig_radar, use_container_width=True)


def render_company_explorer_view(quality_dataframe: pd.DataFrame) -> None:
    """Render Interactive Company-Level Explorer."""
    st.subheader("11. Interactive Company-Level Explorer")
    st.markdown(
        "Search, filter and inspect full 36-column company-level analytical observations "
        "derived from the synthetic public dataset."
    )

    st.write(
        f"Showing **{len(quality_dataframe):,}** company records matching active filters."
    )

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

    available_display_cols = [
        c for c in display_cols if c in quality_dataframe.columns
    ]

    st.dataframe(
        quality_dataframe[available_display_cols].style.format(
            {
                "employees_latest": lambda x: f"{x:,.0f}" if pd.notna(x) else "-",
                "operating_revenue_latest_k_eur": lambda x: f"€{x:,.1f}k"
                if pd.notna(x)
                else "-",
                "ebitda_latest_k_eur": lambda x: f"€{x:,.1f}k"
                if pd.notna(x)
                else "-",
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
        page_title="CapexQuant SABI Castellón Terminal",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_custom_theme_css()

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
    municipalities_available = sorted(
        full_quality_df["municipality"].dropna().unique().tolist()
    )

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
        render_scope_comparison_view(pipeline_result, filtered_df, kpis)
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
    elif selected_view == "Municipality Analysis & Treemap":
        render_municipality_view(pipeline_result, filtered_df)
    elif selected_view == "4D Quantitative Positioning":
        render_quadrant_positioning_view(filtered_df)
    elif selected_view == "🧪 Stress Testing & Scenario Lab":
        render_stress_testing_view(filtered_df)
    elif selected_view == "🏢 Company Factsheet & Deep-Dive":
        render_company_factsheet_view(filtered_df, full_quality_df)
    elif selected_view == "Company Explorer":
        render_company_explorer_view(filtered_df)

    st.divider()
    st.caption(
        "CapexQuant SABI Castellón • MIT License • "
        "Public demonstrations use deterministic synthetic simulation (Seed 20260820)."
    )


if __name__ == "__main__":
    render_dashboard()
