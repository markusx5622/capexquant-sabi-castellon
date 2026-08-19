"""Reproducible financial analytics for CapexQuant SABI Castellón."""

from collections.abc import Sequence

import pandas as pd

from src.financial_features import (
    EBITDA_LATEST,
    EMPLOYEES_LATEST,
    REVENUE_LATEST,
)
from src.quality_control import add_quality_controls


REQUIRED_ANALYTICS_COLUMNS = [
    "company_name",
    "municipality",
    EMPLOYEES_LATEST,
    REVENUE_LATEST,
    EBITDA_LATEST,
    "revenue_growth",
    "ebitda_margin",
    "has_adverse_legal_status",
    "has_negative_latest_ebitda",
    "has_revenue_decline",
    "analytical_eligibility",
]

VALID_ANALYTICAL_SCOPES = {
    "all",
    "no_adverse_marker",
    "eligible",
    "no_adverse_eligible",
}

DEFAULT_CONCENTRATION_LEVELS = [1, 2, 5, 10, 20, 50, 100]

DEFAULT_REVENUE_PERCENTILES = [
    0.25,
    0.50,
    0.75,
    0.90,
    0.95,
    0.99,
]


def validate_analytics_schema(dataframe: pd.DataFrame) -> None:
    """Validate that all fields required for analytics are available."""

    missing_columns = [
        column
        for column in REQUIRED_ANALYTICS_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns required for analytics: "
            f"{missing_columns}"
        )


def filter_analytical_scope(
    dataframe: pd.DataFrame,
    scope: str = "all",
) -> pd.DataFrame:
    """Filter the dataset according to a documented analytical scope."""

    if scope not in VALID_ANALYTICAL_SCOPES:
        raise ValueError(
            f"Invalid analytical scope: {scope}. "
            f"Expected one of: {sorted(VALID_ANALYTICAL_SCOPES)}"
        )

    validate_analytics_schema(dataframe)

    if scope == "all":
        mask = pd.Series(True, index=dataframe.index)

    elif scope == "no_adverse_marker":
        mask = ~dataframe["has_adverse_legal_status"].fillna(False)

    elif scope == "eligible":
        mask = dataframe["analytical_eligibility"].eq("eligible")

    else:
        mask = (
            ~dataframe["has_adverse_legal_status"].fillna(False)
            & dataframe["analytical_eligibility"].eq("eligible")
        )

    return dataframe.loc[mask].copy()


def calculate_coverage(
    dataframe: pd.DataFrame,
    columns: Sequence[str],
) -> pd.DataFrame:
    """Calculate non-missing observation counts and coverage rates."""

    if dataframe.empty:
        raise ValueError(
            "Cannot calculate coverage for an empty DataFrame."
        )

    missing_columns = [
        column for column in columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns required for coverage calculation: "
            f"{missing_columns}"
        )

    total_records = len(dataframe)
    coverage_rows = []

    for column in columns:
        available_records = int(dataframe[column].notna().sum())

        coverage_rows.append(
            {
                "variable": column,
                "available_records": available_records,
                "missing_records": (
                    total_records - available_records
                ),
                "coverage_rate": (
                    available_records / total_records
                ),
            }
        )

    return pd.DataFrame(coverage_rows)


def create_overview_summary(
    dataframe: pd.DataFrame,
    scope: str = "all",
) -> pd.DataFrame:
    """Create a one-row financial overview for a defined scope."""

    scoped_dataframe = filter_analytical_scope(
        dataframe,
        scope,
    )

    if scoped_dataframe.empty:
        raise ValueError(
            f"Analytical scope '{scope}' contains no records."
        )

    summary = {
        "scope": scope,
        "company_count": len(scoped_dataframe),
        "employee_count": int(
            scoped_dataframe[EMPLOYEES_LATEST].sum()
        ),
        "revenue_available_count": int(
            scoped_dataframe[REVENUE_LATEST].notna().sum()
        ),
        "ebitda_available_count": int(
            scoped_dataframe[EBITDA_LATEST].notna().sum()
        ),
        "revenue_total_k_eur": scoped_dataframe[
            REVENUE_LATEST
        ].sum(min_count=1),
        "ebitda_total_k_eur": scoped_dataframe[
            EBITDA_LATEST
        ].sum(min_count=1),
        "median_employees": scoped_dataframe[
            EMPLOYEES_LATEST
        ].median(),
        "median_revenue_k_eur": scoped_dataframe[
            REVENUE_LATEST
        ].median(),
        "median_ebitda_k_eur": scoped_dataframe[
            EBITDA_LATEST
        ].median(),
        "median_revenue_growth": scoped_dataframe[
            "revenue_growth"
        ].median(),
        "median_ebitda_margin": scoped_dataframe[
            "ebitda_margin"
        ].median(),
        "negative_ebitda_count": int(
            scoped_dataframe[
                "has_negative_latest_ebitda"
            ].sum()
        ),
        "revenue_decline_count": int(
            scoped_dataframe[
                "has_revenue_decline"
            ].sum()
        ),
    }

    return pd.DataFrame([summary])


def create_scope_comparison(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Compare the principal analytical scopes."""

    summaries = [
        create_overview_summary(dataframe, scope)
        for scope in sorted(VALID_ANALYTICAL_SCOPES)
    ]

    return pd.concat(
        summaries,
        ignore_index=True,
    )


def calculate_revenue_concentration(
    dataframe: pd.DataFrame,
    top_levels: Sequence[int] = DEFAULT_CONCENTRATION_LEVELS,
    scope: str = "all",
) -> pd.DataFrame:
    """Calculate cumulative Top-N revenue concentration."""

    scoped_dataframe = filter_analytical_scope(
        dataframe,
        scope,
    )

    revenue = (
        scoped_dataframe[REVENUE_LATEST]
        .dropna()
        .sort_values(ascending=False)
    )

    if revenue.empty:
        raise ValueError(
            "Cannot calculate concentration without revenue data."
        )

    total_revenue = revenue.sum()

    if total_revenue == 0:
        raise ValueError(
            "Cannot calculate concentration when total revenue is zero."
        )

    concentration_rows = []

    for top_n in top_levels:
        if (
            not isinstance(top_n, int)
            or isinstance(top_n, bool)
            or top_n <= 0
        ):
            raise ValueError(
                "Concentration levels must be positive integers."
            )

        companies_included = min(
            top_n,
            len(revenue),
        )

        top_revenue = revenue.iloc[
            :companies_included
        ].sum()

        concentration_rows.append(
            {
                "scope": scope,
                "top_n": top_n,
                "companies_included": companies_included,
                "revenue_k_eur": top_revenue,
                "concentration_rate": (
                    top_revenue / total_revenue
                ),
            }
        )

    return pd.DataFrame(concentration_rows)


def calculate_revenue_percentiles(
    dataframe: pd.DataFrame,
    percentiles: Sequence[float] = DEFAULT_REVENUE_PERCENTILES,
    scope: str = "all",
) -> pd.DataFrame:
    """Calculate operating-revenue percentiles for a defined scope."""

    scoped_dataframe = filter_analytical_scope(
        dataframe,
        scope,
    )

    revenue = scoped_dataframe[
        REVENUE_LATEST
    ].dropna()

    if revenue.empty:
        raise ValueError(
            "Cannot calculate percentiles without revenue data."
        )

    invalid_percentiles = [
        percentile
        for percentile in percentiles
        if (
            not isinstance(percentile, (int, float))
            or isinstance(percentile, bool)
            or percentile < 0
            or percentile > 1
        )
    ]

    if invalid_percentiles:
        raise ValueError(
            "Percentiles must remain between zero and one: "
            f"{invalid_percentiles}"
        )

    quantiles = revenue.quantile(
        list(percentiles)
    )

    return pd.DataFrame(
        {
            "scope": scope,
            "percentile": quantiles.index.astype(float),
            "revenue_k_eur": quantiles.values,
        }
    )


def create_company_ranking(
    dataframe: pd.DataFrame,
    metric: str = REVENUE_LATEST,
    top_n: int = 20,
    scope: str = "all",
    ascending: bool = False,
) -> pd.DataFrame:
    """Create a company ranking using a numeric analytical metric."""

    scoped_dataframe = filter_analytical_scope(
        dataframe,
        scope,
    )

    if metric not in scoped_dataframe.columns:
        raise ValueError(
            f"Ranking metric not found: {metric}"
        )

    if not pd.api.types.is_numeric_dtype(
        scoped_dataframe[metric]
    ):
        raise ValueError(
            f"Ranking metric must be numeric: {metric}"
        )

    if (
        not isinstance(top_n, int)
        or isinstance(top_n, bool)
        or top_n <= 0
    ):
        raise ValueError(
            "Ranking top_n must be a positive integer."
        )

    possible_ranking_columns = [
        "company_name",
        "municipality",
        EMPLOYEES_LATEST,
        REVENUE_LATEST,
        EBITDA_LATEST,
        "revenue_growth",
        "ebitda_margin",
        "legal_status",
        "analytical_eligibility",
    ]

    ranking_columns = [
        column
        for column in possible_ranking_columns
        if column in scoped_dataframe.columns
    ]

    ranking = (
        scoped_dataframe
        .dropna(subset=[metric])
        .sort_values(
            by=metric,
            ascending=ascending,
            kind="mergesort",
        )
        .head(top_n)
        .loc[:, ranking_columns]
        .copy()
    )

    ranking.insert(
        0,
        "rank",
        range(1, len(ranking) + 1),
    )

    return ranking.reset_index(drop=True)


def create_municipality_summary(
    dataframe: pd.DataFrame,
    scope: str = "all",
) -> pd.DataFrame:
    """Aggregate company, employment, revenue and EBITDA by municipality."""

    scoped_dataframe = filter_analytical_scope(
        dataframe,
        scope,
    )

    municipality_summary = (
        scoped_dataframe
        .groupby(
            "municipality",
            dropna=False,
        )
        .agg(
            company_count=("company_name", "size"),
            employee_count=(EMPLOYEES_LATEST, "sum"),
            revenue_total_k_eur=(REVENUE_LATEST, "sum"),
            ebitda_total_k_eur=(EBITDA_LATEST, "sum"),
            median_revenue_k_eur=(REVENUE_LATEST, "median"),
            median_ebitda_margin=("ebitda_margin", "median"),
            adverse_status_count=(
                "has_adverse_legal_status",
                "sum",
            ),
            negative_ebitda_count=(
                "has_negative_latest_ebitda",
                "sum",
            ),
        )
        .reset_index()
    )

    municipality_summary["adverse_status_rate"] = (
        municipality_summary["adverse_status_count"]
        / municipality_summary["company_count"]
    )

    municipality_summary["negative_ebitda_rate"] = (
        municipality_summary["negative_ebitda_count"]
        / municipality_summary["company_count"]
    )

    return municipality_summary.sort_values(
        "revenue_total_k_eur",
        ascending=False,
    ).reset_index(drop=True)


if __name__ == "__main__":
    analytical_dataframe = add_quality_controls()

    scope_comparison = create_scope_comparison(
        analytical_dataframe
    )

    concentration = calculate_revenue_concentration(
        analytical_dataframe,
        scope="all",
    )

    revenue_percentiles = calculate_revenue_percentiles(
        analytical_dataframe,
        scope="all",
    )

    top_companies = create_company_ranking(
        analytical_dataframe,
        metric=REVENUE_LATEST,
        top_n=10,
        scope="all",
    )

    municipality_summary = create_municipality_summary(
        analytical_dataframe,
        scope="all",
    )

    coverage = calculate_coverage(
        analytical_dataframe,
        [
            EMPLOYEES_LATEST,
            REVENUE_LATEST,
            EBITDA_LATEST,
            "revenue_growth",
            "ebitda_margin",
        ],
    )

    print("Analytical summaries created successfully.")
    print(f"Rows: {len(analytical_dataframe):,}")
    print(f"Columns: {len(analytical_dataframe.columns)}")

    print("\nScope comparison:")
    print(scope_comparison.to_string(index=False))

    print("\nRevenue concentration:")
    print(concentration.to_string(index=False))

    print("\nRevenue percentiles:")
    print(revenue_percentiles.to_string(index=False))

    print("\nTop 10 companies by revenue:")
    print(top_companies.to_string(index=False))

    print("\nTop 15 raw municipality categories:")
    print(
        municipality_summary.head(15).to_string(
            index=False
        )
    )

    print("\nVariable coverage:")
    print(coverage.to_string(index=False))