"""Financial data-quality controls for CapexQuant SABI Castellón."""

from collections.abc import Sequence

import pandas as pd

from src.financial_features import add_financial_features


DATA_QUALITY_FLAGS = [
    "has_incomplete_financial_data",
    "has_negative_latest_revenue",
    "has_zero_latest_revenue",
    "has_extreme_ebitda_margin",
    "potential_duplicate",
]

BUSINESS_RISK_FLAGS = [
    "has_adverse_legal_status",
    "has_negative_latest_ebitda",
    "has_revenue_decline",
]

REQUIRED_QUALITY_COLUMNS = (
    DATA_QUALITY_FLAGS
    + BUSINESS_RISK_FLAGS
)

QUALITY_CONTROL_COLUMNS = [
    "data_quality_issue_count",
    "business_risk_signal_count",
    "has_data_quality_issue",
    "has_business_risk_signal",
    "data_quality_status",
    "analytical_eligibility",
    "data_quality_reasons",
    "business_risk_reasons",
]

DATA_QUALITY_REASON_LABELS = {
    "has_incomplete_financial_data": (
        "incomplete_financial_data"
    ),
    "has_negative_latest_revenue": (
        "negative_latest_revenue"
    ),
    "has_zero_latest_revenue": (
        "zero_latest_revenue"
    ),
    "has_extreme_ebitda_margin": (
        "extreme_ebitda_margin"
    ),
    "potential_duplicate": (
        "potential_duplicate"
    ),
}

BUSINESS_RISK_REASON_LABELS = {
    "has_adverse_legal_status": (
        "adverse_legal_status"
    ),
    "has_negative_latest_ebitda": (
        "negative_latest_ebitda"
    ),
    "has_revenue_decline": (
        "revenue_decline"
    ),
}


def validate_quality_schema(
    dataframe: pd.DataFrame,
) -> None:
    """Validate fields required by the quality-control layer."""

    missing_columns = [
        column
        for column in REQUIRED_QUALITY_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns required for quality control: "
            f"{missing_columns}"
        )


def validate_boolean_flags(
    dataframe: pd.DataFrame,
    flag_columns: Sequence[str],
) -> None:
    """
    Validate that quality and risk fields contain boolean values.

    Missing flags are rejected because every record must be explicitly
    classified as True or False before quality aggregation.
    """

    invalid_columns = []

    for column in flag_columns:
        series = dataframe[column]

        if series.isna().any():
            invalid_columns.append(column)
            continue

        valid_values = series.isin([True, False])

        if not valid_values.all():
            invalid_columns.append(column)

    if invalid_columns:
        raise ValueError(
            "Quality-control flags must contain only "
            f"non-missing boolean values: {invalid_columns}"
        )


def combine_flag_reasons(
    dataframe: pd.DataFrame,
    reason_labels: dict[str, str],
) -> pd.Series:
    """
    Combine active flag labels into a traceable reason string.

    Records without active flags receive an empty string.
    """

    def collect_reasons(row: pd.Series) -> str:
        active_reasons = [
            label
            for flag, label in reason_labels.items()
            if bool(row[flag])
        ]

        return "|".join(active_reasons)

    return dataframe[
        list(reason_labels)
    ].apply(
        collect_reasons,
        axis=1,
    )


def classify_data_quality_status(
    issue_count: pd.Series,
) -> pd.Series:
    """
    Classify records by the number of data-quality issues.

    Classification
    --------------
    0 issues:
        clean
    1 issue:
        review
    2 or more issues:
        high_priority_review
    """

    status = pd.Series(
        "clean",
        index=issue_count.index,
        dtype="string",
    )

    status.loc[
        issue_count.eq(1)
    ] = "review"

    status.loc[
        issue_count.ge(2)
    ] = "high_priority_review"

    return status


def classify_analytical_eligibility(
    dataframe: pd.DataFrame,
) -> pd.Series:
    """
    Classify whether a record is suitable for standard financial analysis.

    Eligibility does not assert that a company is legally active or
    economically healthy. It only describes whether the record can be
    used in conventional revenue and EBITDA analysis without an
    immediate denominator or completeness problem.

    Classification
    --------------
    eligible:
        Complete core financial data, nonzero latest revenue and no
        extreme EBITDA margin.
    eligible_with_review:
        Financial calculations are possible, but another quality flag
        requires analyst review.
    not_eligible:
        Incomplete financial data, zero latest revenue or extreme
        EBITDA margin.
    """

    blocking_issue = (
        dataframe[
            "has_incomplete_financial_data"
        ]
        | dataframe[
            "has_zero_latest_revenue"
        ]
        | dataframe[
            "has_extreme_ebitda_margin"
        ]
    )

    nonblocking_review_issue = (
        dataframe[
            "has_negative_latest_revenue"
        ]
        | dataframe[
            "potential_duplicate"
        ]
    )

    eligibility = pd.Series(
        "eligible",
        index=dataframe.index,
        dtype="string",
    )

    eligibility.loc[
        nonblocking_review_issue
    ] = "eligible_with_review"

    eligibility.loc[
        blocking_issue
    ] = "not_eligible"

    return eligibility


def add_quality_controls(
    dataframe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Add data-quality and business-risk classifications.

    The function does not remove observations, overwrite source data,
    impute missing values or treat negative performance as a data error.
    """

    if dataframe is None:
        dataframe = add_financial_features()

    if dataframe.empty:
        raise ValueError(
            "Cannot perform quality control on an empty DataFrame."
        )

    validate_quality_schema(dataframe)

    validate_boolean_flags(
        dataframe,
        REQUIRED_QUALITY_COLUMNS,
    )

    controlled_dataframe = dataframe.copy()

    controlled_dataframe[
        "data_quality_issue_count"
    ] = controlled_dataframe[
        DATA_QUALITY_FLAGS
    ].sum(
        axis=1
    ).astype("Int64")

    controlled_dataframe[
        "business_risk_signal_count"
    ] = controlled_dataframe[
        BUSINESS_RISK_FLAGS
    ].sum(
        axis=1
    ).astype("Int64")

    controlled_dataframe[
        "has_data_quality_issue"
    ] = controlled_dataframe[
        "data_quality_issue_count"
    ].gt(0)

    controlled_dataframe[
        "has_business_risk_signal"
    ] = controlled_dataframe[
        "business_risk_signal_count"
    ].gt(0)

    controlled_dataframe[
        "data_quality_status"
    ] = classify_data_quality_status(
        controlled_dataframe[
            "data_quality_issue_count"
        ]
    )

    controlled_dataframe[
        "analytical_eligibility"
    ] = classify_analytical_eligibility(
        controlled_dataframe
    )

    controlled_dataframe[
        "data_quality_reasons"
    ] = combine_flag_reasons(
        controlled_dataframe,
        DATA_QUALITY_REASON_LABELS,
    )

    controlled_dataframe[
        "business_risk_reasons"
    ] = combine_flag_reasons(
        controlled_dataframe,
        BUSINESS_RISK_REASON_LABELS,
    )

    return controlled_dataframe


def create_quality_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Produce a compact summary of quality and risk indicators.

    The summary contains observation counts and percentages over the
    complete supplied dataset.
    """

    if dataframe.empty:
        raise ValueError(
            "Cannot summarize quality for an empty DataFrame."
        )

    summary_flags = (
        DATA_QUALITY_FLAGS
        + BUSINESS_RISK_FLAGS
        + [
            "has_data_quality_issue",
            "has_business_risk_signal",
        ]
    )

    missing_columns = [
        column
        for column in summary_flags
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns required for quality summary: "
            f"{missing_columns}"
        )

    total_records = len(dataframe)

    summary_rows = []

    for flag in summary_flags:
        count = int(
            dataframe[flag].sum()
        )

        summary_rows.append(
            {
                "indicator": flag,
                "record_count": count,
                "record_percentage": (
                    count / total_records
                ),
            }
        )

    return pd.DataFrame(summary_rows)


if __name__ == "__main__":
    quality_dataframe = add_quality_controls()

    quality_summary = create_quality_summary(
        quality_dataframe
    )

    print("Quality controls created successfully.")
    print(f"Rows: {len(quality_dataframe):,}")
    print(f"Columns: {len(quality_dataframe.columns)}")

    print("\nData-quality status distribution:")
    print(
        quality_dataframe[
            "data_quality_status"
        ].value_counts(
            dropna=False
        )
    )

    print("\nAnalytical-eligibility distribution:")
    print(
        quality_dataframe[
            "analytical_eligibility"
        ].value_counts(
            dropna=False
        )
    )

    print("\nBusiness-risk signal distribution:")
    print(
        quality_dataframe[
            "business_risk_signal_count"
        ].value_counts(
            dropna=False
        ).sort_index()
    )

    print("\nQuality-control summary:")
    print(
        quality_summary.to_string(
            index=False,
            formatters={
                "record_percentage": (
                    lambda value: f"{value:.2%}"
                )
            },
        )
    )