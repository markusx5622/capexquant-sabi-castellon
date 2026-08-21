"""Interactive Plotly visualization components for CapexQuant SABI Castellón."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Design tokens
CHART_THEME = "plotly_white"
PRIMARY_COLOR = "#1E88E5"
SECONDARY_COLOR = "#0D9488"  # Teal
ACCENT_COLOR = "#F59E0B"     # Amber
DANGER_COLOR = "#EF4444"     # Red
SUCCESS_COLOR = "#10B981"    # Emerald
GRID_COLOR = "#E2E8F0"
FONT_FAMILY = "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def apply_standard_layout(
    fig: go.Figure,
    title: str = "",
    height: int = 450,
    show_legend: bool = True,
) -> go.Figure:
    """Apply consistent high-end fintech typography and styling to a Plotly figure."""
    fig.update_layout(
        template=CHART_THEME,
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(family=FONT_FAMILY, size=16, color="#0F172A"),
            x=0.0,
            xanchor="left",
        ),
        font=dict(family=FONT_FAMILY, size=12, color="#334155"),
        margin=dict(l=40, r=30, t=50 if title else 20, b=40),
        height=height,
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11),
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zerolinecolor=GRID_COLOR,
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            zerolinecolor=GRID_COLOR,
            tickfont=dict(size=11),
        ),
        hoverlabel=dict(
            bgcolor="#0F172A",
            font_size=12,
            font_family=FONT_FAMILY,
            font_color="#F8FAFC",
        ),
    )
    return fig


def create_interactive_concentration_chart(
    concentration_df: pd.DataFrame,
) -> go.Figure:
    """Create an interactive Lorenz-style cumulative revenue concentration curve."""
    fig = go.Figure()

    # Cumulative concentration area & line
    fig.add_trace(
        go.Scatter(
            x=concentration_df["top_n"],
            y=concentration_df["concentration_rate"] * 100,
            mode="lines+markers",
            name="Cumulative Revenue Share",
            line=dict(color=PRIMARY_COLOR, width=3, shape="spline"),
            marker=dict(size=8, color=PRIMARY_COLOR, symbol="diamond"),
            hovertemplate=(
                "<b>Top %{x} Entities</b><br>"
                "Cumulative Share: <b>%{y:.2f}%</b><br>"
                "<extra></extra>"
            ),
            fill="tozeroy",
            fillcolor="rgba(30, 136, 229, 0.08)",
        )
    )

    # Equal distribution reference if applicable
    max_n = concentration_df["top_n"].max()
    fig.add_trace(
        go.Scatter(
            x=[1, max_n],
            y=[(1 / max_n) * 100, 100],
            mode="lines",
            name="Equal Distribution Baseline",
            line=dict(color="#94A3B8", width=1.5, dash="dash"),
            hovertemplate="Equal Baseline<extra></extra>",
        )
    )

    fig.update_xaxes(title="<b>Top-N Ranked Companies</b>", type="linear")
    fig.update_yaxes(title="<b>Cumulative Revenue (%)</b>", range=[0, 105])

    return apply_standard_layout(fig, title="Cumulative Revenue Concentration (Lorenz Curve)", height=420)


def create_interactive_quadrant_scatter(
    dataframe: pd.DataFrame,
) -> go.Figure:
    """Create 4D Quantitative Financial Scatter (Revenue vs EBITDA Margin vs Employees vs Risk)."""
    valid_df = dataframe.dropna(
        subset=["operating_revenue_latest_k_eur", "ebitda_margin"]
    ).copy()

    if valid_df.empty:
        fig = go.Figure()
        return apply_standard_layout(fig, title="No Valid Observations for Quadrant Scatter")

    # Clip extreme margins for display aesthetics while noting in hover
    valid_df["display_margin"] = valid_df["ebitda_margin"].clip(lower=-0.5, upper=0.5) * 100
    valid_df["size_scaled"] = valid_df["employees_latest"].fillna(10).clip(lower=5, upper=500)

    # Color classification
    def assign_category(row: pd.Series) -> str:
        if bool(row.get("has_business_risk_signal", False)):
            return "Business Risk Signal"
        if bool(row.get("has_data_quality_issue", False)):
            return "Data Quality Review"
        return "Prime Eligible"

    valid_df["cohort"] = valid_df.apply(assign_category, axis=1)

    color_map = {
        "Prime Eligible": SUCCESS_COLOR,
        "Data Quality Review": ACCENT_COLOR,
        "Business Risk Signal": DANGER_COLOR,
    }

    fig = px.scatter(
        valid_df,
        x="operating_revenue_latest_k_eur",
        y="display_margin",
        size="size_scaled",
        color="cohort",
        color_discrete_map=color_map,
        hover_name="company_name",
        hover_data={
            "municipality": True,
            "operating_revenue_latest_k_eur": ":,.1f",
            "ebitda_latest_k_eur": ":,.1f",
            "ebitda_margin": ":.1%",
            "employees_latest": True,
            "display_margin": False,
            "size_scaled": False,
            "cohort": False,
        },
        labels={
            "operating_revenue_latest_k_eur": "Operating Revenue (€k)",
            "display_margin": "EBITDA Margin (%)",
            "cohort": "Status",
        },
    )

    # Add zero margin horizontal line
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#CBD5E1",
        annotation_text="Breakeven (0% Margin)",
        annotation_position="bottom right",
        annotation_font=dict(size=10, color="#64748B"),
    )

    fig.update_xaxes(title="<b>Operating Revenue (€ in thousands)</b>", type="log")
    fig.update_yaxes(title="<b>EBITDA Margin (%)</b>")

    return apply_standard_layout(fig, title="4D Financial Positioning (Revenue vs Margin vs Employment)", height=480)


def create_interactive_treemap(
    dataframe: pd.DataFrame,
) -> go.Figure:
    """Create a hierarchical Treemap (Municipality ➔ Company) colored by EBITDA Margin."""
    valid_df = dataframe.dropna(
        subset=["municipality", "company_name", "operating_revenue_latest_k_eur"]
    ).copy()

    if valid_df.empty:
        fig = go.Figure()
        return apply_standard_layout(fig, title="No Valid Observations for Treemap")

    valid_df["positive_rev"] = valid_df["operating_revenue_latest_k_eur"].clip(lower=1.0)
    valid_df["ebitda_margin_pct"] = (valid_df["ebitda_margin"].fillna(0.0) * 100).clip(lower=-20.0, upper=40.0)

    fig = px.treemap(
        valid_df,
        path=["municipality", "company_name"],
        values="positive_rev",
        color="ebitda_margin_pct",
        color_continuous_scale=["#EF4444", "#F59E0B", "#10B981", "#059669"],
        color_continuous_midpoint=10.0,
        hover_data={
            "positive_rev": False,
            "operating_revenue_latest_k_eur": ":,.1f",
            "ebitda_latest_k_eur": ":,.1f",
            "employees_latest": True,
            "ebitda_margin_pct": ":.1f",
        },
        labels={
            "operating_revenue_latest_k_eur": "Revenue (€k)",
            "ebitda_margin_pct": "EBITDA Margin (%)",
        },
    )

    fig.update_layout(
        template=CHART_THEME,
        font=dict(family=FONT_FAMILY),
        margin=dict(l=10, r=10, t=30, b=10),
        height=500,
    )
    return fig


def create_interactive_percentiles_chart(
    percentiles_df: pd.DataFrame,
) -> go.Figure:
    """Create interactive step bar chart for revenue percentiles."""
    fig = go.Figure()

    labels = [f"P{int(p*100)}" for p in percentiles_df["percentile"]]
    values = percentiles_df["revenue_k_eur"]

    fig.add_trace(
        go.Bar(
            x=labels,
            y=values,
            marker=dict(
                color=values,
                colorscale="Blues",
                showscale=False,
                line=dict(color=PRIMARY_COLOR, width=1.5),
            ),
            hovertemplate="<b>%{x}</b>: €%{y:,.1f}k<extra></extra>",
            text=[f"€{v:,.0f}k" for v in values],
            textposition="outside",
        )
    )

    fig.update_xaxes(title="<b>Revenue Distribution Percentiles</b>")
    fig.update_yaxes(title="<b>Operating Revenue (€ in thousands)</b>")

    return apply_standard_layout(fig, title="Operating Revenue Quantiles (P25 to P99)", height=420)


def create_interactive_rankings_chart(
    ranking_df: pd.DataFrame,
    top_n: int = 15,
) -> go.Figure:
    """Create an interactive horizontal leaderboard bar chart."""
    display_df = ranking_df.head(top_n).iloc[::-1]  # Invert for top-down display

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=display_df["company_name"],
            x=display_df["operating_revenue_latest_k_eur"],
            orientation="h",
            marker=dict(
                color=PRIMARY_COLOR,
                line=dict(color="#1D4ED8", width=1),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Revenue: <b>€%{x:,.1f}k</b><br>"
                "<extra></extra>"
            ),
            text=[f" €{v:,.0f}k" for v in display_df["operating_revenue_latest_k_eur"]],
            textposition="auto",
        )
    )

    fig.update_xaxes(title="<b>Latest Operating Revenue (€ in thousands)</b>")
    fig.update_yaxes(title="")

    return apply_standard_layout(fig, title=f"Top {top_n} Companies by Operating Revenue", height=max(380, top_n * 26))


def create_interactive_coverage_chart(
    coverage_df: pd.DataFrame,
) -> go.Figure:
    """Create an interactive horizontal stacked coverage bar chart."""
    fig = go.Figure()

    sorted_df = coverage_df.sort_values("coverage_rate", ascending=True)

    fig.add_trace(
        go.Bar(
            y=sorted_df["variable"],
            x=sorted_df["available_records"],
            name="Available Data",
            orientation="h",
            marker=dict(color=SUCCESS_COLOR),
            hovertemplate="Available: <b>%{x}</b> records<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=sorted_df["variable"],
            x=sorted_df["missing_records"],
            name="Missing Data",
            orientation="h",
            marker=dict(color="#CBD5E1"),
            hovertemplate="Missing: <b>%{x}</b> records<extra></extra>",
        )
    )

    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="<b>Record Count</b>")
    fig.update_yaxes(title="")

    return apply_standard_layout(fig, title="Field Observation Coverage & Completeness", height=380)


def create_radar_benchmark_chart(
    company_row: pd.Series,
    all_companies_df: pd.DataFrame,
) -> go.Figure:
    """Create a 5D Spider/Radar benchmark comparing a company against municipal & provincial percentiles."""
    categories = [
        "Revenue Scale",
        "EBITDA Margin",
        "Labor Productivity",
        "Workforce Size",
        "Revenue Growth",
    ]

    # Calculate percentile ranks within global sample (0 to 100)
    rev_pct = float((all_companies_df["operating_revenue_latest_k_eur"] <= company_row.get("operating_revenue_latest_k_eur", 0)).mean() * 100)
    margin_pct = float((all_companies_df["ebitda_margin"].dropna() <= company_row.get("ebitda_margin", 0)).mean() * 100)
    prod_pct = float((all_companies_df["revenue_per_employee_k_eur"].dropna() <= company_row.get("revenue_per_employee_k_eur", 0)).mean() * 100)
    emp_pct = float((all_companies_df["employees_latest"].dropna() <= company_row.get("employees_latest", 0)).mean() * 100)
    growth_pct = float((all_companies_df["revenue_growth"].dropna() <= company_row.get("revenue_growth", 0)).mean() * 100)

    company_values = [rev_pct, margin_pct, prod_pct, emp_pct, growth_pct]
    median_values = [50, 50, 50, 50, 50]  # Provincial median benchmark

    fig = go.Figure()

    # Provincial median benchmark trace
    fig.add_trace(
        go.Scatterpolar(
            r=median_values + [median_values[0]],
            theta=categories + [categories[0]],
            name="Provincial Median (P50)",
            line=dict(color="#94A3B8", dash="dash", width=1.5),
            fill="toself",
            fillcolor="rgba(148, 163, 184, 0.1)",
        )
    )

    # Company trace
    fig.add_trace(
        go.Scatterpolar(
            r=company_values + [company_values[0]],
            theta=categories + [categories[0]],
            name=str(company_row.get("company_name", "Selected Company")),
            line=dict(color=PRIMARY_COLOR, width=2.5),
            fill="toself",
            fillcolor="rgba(30, 136, 229, 0.25)",
            marker=dict(size=6, color=PRIMARY_COLOR),
        )
    )

    fig.update_layout(
        template=CHART_THEME,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10, color="#64748B"),
                gridcolor=GRID_COLOR,
            ),
            angularaxis=dict(
                tickfont=dict(size=11, family=FONT_FAMILY, color="#0F172A"),
                gridcolor=GRID_COLOR,
            ),
        ),
        margin=dict(l=40, r=40, t=30, b=30),
        height=380,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
    )
    return fig


def create_health_gauge_chart(
    score: int,
    grade: str,
    grade_color: str,
) -> go.Figure:
    """Create a high-end radial speedometer gauge for company financial health."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=score,
            domain=dict(x=[0, 1], y=[0, 1]),
            title=dict(
                text=f"<b>Health Rating: {grade}</b>",
                font=dict(family=FONT_FAMILY, size=16, color="#0F172A"),
            ),
            gauge=dict(
                axis=dict(range=[0, 100], tickwidth=1, tickcolor="#94A3B8"),
                bar=dict(color=grade_color, width=10),
                bgcolor="#F1F5F9",
                borderwidth=1,
                bordercolor="#CBD5E1",
                steps=[
                    dict(range=[0, 40], color="rgba(239, 68, 68, 0.15)"),
                    dict(range=[40, 70], color="rgba(245, 158, 11, 0.15)"),
                    dict(range=[70, 100], color="rgba(16, 185, 129, 0.15)"),
                ],
                threshold=dict(
                    line=dict(color="#0F172A", width=3),
                    thickness=0.8,
                    value=score,
                ),
            ),
        )
    )

    fig.update_layout(
        margin=dict(l=25, r=25, t=50, b=20),
        height=260,
        font=dict(family=FONT_FAMILY),
    )
    return fig


def create_stress_test_comparison_chart(
    base_df: pd.DataFrame,
    stressed_df: pd.DataFrame,
) -> go.Figure:
    """Create a grouped comparative bar chart showing baseline vs stressed figures."""
    categories = ["Aggregate Revenue (€k)", "Aggregate EBITDA (€k)"]

    base_rev = float(base_df["operating_revenue_latest_k_eur"].sum() or 0.0)
    base_ebitda = float(base_df["ebitda_latest_k_eur"].sum() or 0.0)

    stressed_rev = float(stressed_df["stressed_revenue_k_eur"].sum() or 0.0)
    stressed_ebitda = float(stressed_df["stressed_ebitda_k_eur"].sum() or 0.0)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Baseline Scenario",
            x=categories,
            y=[base_rev, base_ebitda],
            marker=dict(color=PRIMARY_COLOR),
            hovertemplate="Baseline: <b>€%{y:,.1f}k</b><extra></extra>",
            text=[f"€{base_rev:,.0f}k", f"€{base_ebitda:,.0f}k"],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Stressed Scenario",
            x=categories,
            y=[stressed_rev, stressed_ebitda],
            marker=dict(color=DANGER_COLOR if stressed_ebitda < base_ebitda else SUCCESS_COLOR),
            hovertemplate="Stressed: <b>€%{y:,.1f}k</b><extra></extra>",
            text=[f"€{stressed_rev:,.0f}k", f"€{stressed_ebitda:,.0f}k"],
            textposition="auto",
        )
    )

    fig.update_layout(barmode="group")
    fig.update_yaxes(title="<b>Thousands of EUR (€k)</b>")

    return apply_standard_layout(fig, title="Macroeconomic Impact: Baseline vs. Shock Scenario", height=400)
