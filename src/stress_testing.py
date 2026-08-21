"""Quantitative stress-testing and executive intelligence engine for CapexQuant SABI Castellón."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.financial_features import (
    EBITDA_LATEST,
    EMPLOYEES_LATEST,
    REVENUE_LATEST,
    safe_divide,
)


def apply_macroeconomic_stress(
    dataframe: pd.DataFrame,
    revenue_shock_pct: float = 0.0,
    cost_inflation_pct: float = 0.0,
) -> pd.DataFrame:
    """
    Simulate macroeconomic shocks on corporate revenue and operating expenses.

    Parameters
    ----------
    dataframe : pd.DataFrame
        Quality-controlled company dataset.
    revenue_shock_pct : float, default 0.0
        Percentage change in operating revenue (e.g. -15.0 for a 15% contraction).
    cost_inflation_pct : float, default 0.0
        Percentage inflation in implied operating costs (e.g. +8.0 for 8% inflation).

    Returns
    -------
    pd.DataFrame
        DataFrame with baseline and stressed financial figures.
    """
    stressed_df = dataframe.copy()

    rev_multiplier = 1.0 + (revenue_shock_pct / 100.0)
    cost_multiplier = 1.0 + (cost_inflation_pct / 100.0)

    # Calculate baseline implied operating costs: OpEx = Revenue - EBITDA
    baseline_revenue = stressed_df[REVENUE_LATEST]
    baseline_ebitda = stressed_df[EBITDA_LATEST]
    baseline_opex = (baseline_revenue - baseline_ebitda).clip(lower=0.0)

    # Apply shock multipliers
    stressed_revenue = baseline_revenue * rev_multiplier
    stressed_opex = baseline_opex * cost_multiplier
    stressed_ebitda = stressed_revenue - stressed_opex
    stressed_margin = safe_divide(stressed_ebitda, stressed_revenue)

    stressed_df["stressed_revenue_k_eur"] = stressed_revenue
    stressed_df["stressed_opex_k_eur"] = stressed_opex
    stressed_df["stressed_ebitda_k_eur"] = stressed_ebitda
    stressed_df["stressed_ebitda_margin"] = stressed_margin
    stressed_df["stressed_has_negative_ebitda"] = stressed_ebitda.lt(0)

    # Track transition states: was profitable, now in loss
    baseline_profitable = baseline_ebitda.ge(0)
    stressed_df["is_newly_distressed"] = baseline_profitable & stressed_ebitda.lt(0)

    return stressed_df


def calculate_stress_impact_summary(
    base_df: pd.DataFrame,
    stressed_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Compute aggregate stress test impact metrics comparing baseline to stressed scenario.
    """
    if base_df.empty:
        return {
            "base_total_revenue_k_eur": 0.0,
            "stressed_total_revenue_k_eur": 0.0,
            "revenue_delta_k_eur": 0.0,
            "base_total_ebitda_k_eur": 0.0,
            "stressed_total_ebitda_k_eur": 0.0,
            "ebitda_delta_k_eur": 0.0,
            "ebitda_contraction_pct": 0.0,
            "base_negative_ebitda_count": 0,
            "stressed_negative_ebitda_count": 0,
            "newly_distressed_count": 0,
            "jobs_in_distressed_entities": 0,
            "resilience_rate": 1.0,
        }

    base_rev = float(base_df[REVENUE_LATEST].sum(min_count=1) or 0.0)
    stressed_rev = float(stressed_df["stressed_revenue_k_eur"].sum(min_count=1) or 0.0)
    rev_delta = stressed_rev - base_rev

    base_ebitda = float(base_df[EBITDA_LATEST].sum(min_count=1) or 0.0)
    stressed_ebitda = float(stressed_df["stressed_ebitda_k_eur"].sum(min_count=1) or 0.0)
    ebitda_delta = stressed_ebitda - base_ebitda
    ebitda_contraction_pct = (
        (ebitda_delta / abs(base_ebitda)) if base_ebitda != 0.0 else 0.0
    )

    base_neg_ebitda = int(base_df[EBITDA_LATEST].lt(0).sum())
    stressed_neg_ebitda = int(stressed_df["stressed_has_negative_ebitda"].sum())
    newly_distressed = int(stressed_df["is_newly_distressed"].sum())

    distressed_mask = stressed_df["stressed_has_negative_ebitda"]
    jobs_at_risk = int(
        stressed_df.loc[distressed_mask, EMPLOYEES_LATEST].sum(min_count=1) or 0
    )

    total_valid = len(stressed_df[REVENUE_LATEST].dropna())
    resilience_rate = (
        ((total_valid - stressed_neg_ebitda) / total_valid)
        if total_valid > 0
        else 0.0
    )

    return {
        "base_total_revenue_k_eur": base_rev,
        "stressed_total_revenue_k_eur": stressed_rev,
        "revenue_delta_k_eur": rev_delta,
        "base_total_ebitda_k_eur": base_ebitda,
        "stressed_total_ebitda_k_eur": stressed_ebitda,
        "ebitda_delta_k_eur": ebitda_delta,
        "ebitda_contraction_pct": ebitda_contraction_pct,
        "base_negative_ebitda_count": base_neg_ebitda,
        "stressed_negative_ebitda_count": stressed_neg_ebitda,
        "newly_distressed_count": newly_distressed,
        "jobs_in_distressed_entities": jobs_at_risk,
        "resilience_rate": max(0.0, min(1.0, resilience_rate)),
    }


def compute_company_health_score(company_row: pd.Series) -> dict[str, Any]:
    """
    Compute a deterministic 0-100 composite Financial & Data Quality Score for a company.

    Returns score, rating grade, and explainable deduction details.
    """
    score = 100
    deductions: list[dict[str, Any]] = []
    positives: list[str] = []

    # 1. Data Integrity checks
    if bool(company_row.get("has_incomplete_financial_data", False)):
        score -= 25
        deductions.append({"factor": "Incomplete Financial Reporting", "points": -25})
    else:
        positives.append("Complete Financial Reporting")

    if bool(company_row.get("has_negative_latest_revenue", False)):
        score -= 30
        deductions.append({"factor": "Negative Operating Revenue Reported", "points": -30})

    if bool(company_row.get("has_zero_latest_revenue", False)):
        score -= 25
        deductions.append({"factor": "Zero Operating Revenue", "points": -25})

    if bool(company_row.get("has_extreme_ebitda_margin", False)):
        score -= 20
        deductions.append({"factor": "Extreme / Distorted EBITDA Margin (>100%)", "points": -20})

    if bool(company_row.get("potential_duplicate", False)):
        score -= 10
        deductions.append({"factor": "Potential Entity Duplicate Warning", "points": -10})

    # 2. Economic & Legal Risk checks
    if bool(company_row.get("has_adverse_legal_status", False)):
        score -= 35
        deductions.append({"factor": "Adverse Legal Status (Liquidation / Extinction)", "points": -35})
    else:
        positives.append("No Adverse Legal Marker")

    if bool(company_row.get("has_negative_latest_ebitda", False)):
        score -= 20
        deductions.append({"factor": "Negative Operating EBITDA", "points": -20})
    else:
        ebitda_val = company_row.get(EBITDA_LATEST)
        if pd.notna(ebitda_val) and ebitda_val > 0:
            positives.append("Positive Operating EBITDA")

    if bool(company_row.get("has_revenue_decline", False)):
        score -= 10
        deductions.append({"factor": "Year-over-Year Revenue Contraction", "points": -10})
    else:
        growth = company_row.get("revenue_growth")
        if pd.notna(growth) and growth > 0:
            positives.append(f"Positive YoY Growth ({growth:+.1%})")

    # Margin bonus / check
    margin = company_row.get("ebitda_margin")
    if pd.notna(margin):
        if margin >= 0.15:
            positives.append(f"Strong EBITDA Margin ({margin:.1%})")
        elif margin > 0.05:
            positives.append(f"Stable EBITDA Margin ({margin:.1%})")

    final_score = int(max(0, min(100, score)))

    # Assign credit / health rating
    if final_score >= 90:
        grade = "AAA"
        grade_color = "#10B981"  # Emerald
        assessment = "Prime Institutional Grade • Clean data and robust operating performance."
    elif final_score >= 80:
        grade = "AA"
        grade_color = "#34D399"
        assessment = "High Grade • Strong fundamental reliability with negligible anomalies."
    elif final_score >= 70:
        grade = "A"
        grade_color = "#60A5FA"  # Blue
        assessment = "Upper Medium Grade • Favorable financial posture with minor review flags."
    elif final_score >= 60:
        grade = "BBB"
        grade_color = "#FBBF24"  # Amber
        assessment = "Investment Grade • Moderate operational profile requiring standard screening."
    elif final_score >= 50:
        grade = "BB"
        grade_color = "#F97316"  # Orange
        assessment = "Speculative Grade • Notable business risk or quality-control observations."
    elif final_score >= 40:
        grade = "B"
        grade_color = "#EF4444"  # Red
        assessment = "High Risk • Substantial operating distress or acute data inconsistencies."
    else:
        grade = "CCC / Distressed"
        grade_color = "#991B1B"  # Dark Red
        assessment = "Severe Distress • Critical solvency impairment or extreme data integrity defects."

    return {
        "health_score": final_score,
        "grade": grade,
        "grade_color": grade_color,
        "assessment": assessment,
        "deductions": deductions,
        "positives": positives,
    }


def generate_executive_briefing(
    dataframe: pd.DataFrame,
    kpis: dict[str, Any],
) -> str:
    """
    Generate an automated algorithmic narrative briefing summarizing cohort economics.
    """
    if dataframe.empty:
        return "No company records available under the currently selected filters to generate a briefing."

    total_companies = kpis.get("total_companies", 0)
    total_rev = kpis.get("total_revenue_k_eur", 0.0)
    median_rev = kpis.get("median_revenue_k_eur", 0.0)
    total_ebitda = kpis.get("total_ebitda_k_eur", 0.0)
    median_margin = kpis.get("median_ebitda_margin", 0.0)
    total_emp = kpis.get("total_employees", 0)
    dq_rate = kpis.get("data_quality_issue_rate", 0.0)
    risk_rate = kpis.get("business_risk_signal_rate", 0.0)
    eligible_count = kpis.get("eligible_companies", 0)

    # Top municipality
    if "municipality" in dataframe.columns and not dataframe["municipality"].empty:
        top_muni = dataframe["municipality"].value_counts().index[0]
        muni_share = (dataframe["municipality"].value_counts().iloc[0] / total_companies)
    else:
        top_muni = "N/A"
        muni_share = 0.0

    briefing_lines = [
        "### 🏛️ Executive Intelligence Briefing",
        "",
        f"**Cohort Overview:** Analysis of **{total_companies:,}** corporate entities representing an aggregated operating revenue of **€{total_rev:,.1f}k** and generating **€{total_ebitda:,.1f}k** in EBITDA across a total workforce of **{total_emp:,}** employees.",
        "",
        "#### 1. Fundamental Profitability & Scale",
        f"- **Median Revenue:** €{median_rev:,.1f}k per entity, indicating significant scale skewness across the distribution.",
        f"- **Operational Margin:** Median EBITDA margin stands at **{median_margin:.1%}**, reflecting baseline corporate operating profitability.",
        f"- **Analytical Eligibility:** **{eligible_count} of {total_companies}** entities ({eligible_count/total_companies:.1%}) meet strict quantitative standards for non-distorted valuation and multi-period modeling.",
        "",
        "#### 2. Risk Screening & Data Quality Summary",
        f"- **Data Quality Issue Rate:** **{dq_rate:.1%}** of records exhibit technical data integrity defects (missing filings, zero denominators, or extreme margin ratios).",
        f"- **Business Risk Signal Rate:** **{risk_rate:.1%}** of active records demonstrate operational distress signals (negative EBITDA, YoY revenue decline, or adverse legal markers).",
        f"- **Geographic Hub:** Primary concentration in **{top_muni}**, accounting for **{muni_share:.1%}** of analyzed entities.",
        "",
        "#### 3. Quantitative Screening Takeaways",
        "> **Screening Rule:** Entities marked with *high_priority_review* or *not_eligible* should be quarantined in automated M&A screening funnels. Conversely, companies maintaining an *Eligible* classification with positive YoY growth represent primary targets for deeper credit or equity assessment.",
    ]

    return "\n".join(briefing_lines)
