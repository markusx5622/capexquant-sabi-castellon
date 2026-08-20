# CapexQuant Data-Quality Rules

## Design principle

CapexQuant separates **data-quality issues** from **business-risk signals**. A record can contain reliable data and still describe an economically weak or legally adverse company. Conversely, a profitable company can have incomplete or structurally problematic data.

## Data-quality flags

The configured quality set contains five flags:

1. `has_incomplete_financial_data`
2. `has_negative_latest_revenue`
3. `has_zero_latest_revenue`
4. `has_extreme_ebitda_margin`
5. `potential_duplicate`

### `has_incomplete_financial_data`

Indicates that one or more required financial observations are unavailable. Missing values are retained rather than replaced with zero.

### `has_negative_latest_revenue`

Indicates latest operating revenue below zero. This is treated as a data-quality concern because operating revenue is normally expected to be non-negative in the configured source context.

### `has_zero_latest_revenue`

Indicates latest operating revenue equal to zero. Zero is retained as an observation, but it blocks conventional revenue-based ratios.

### `has_extreme_ebitda_margin`

Indicates a margin outside the configured plausibility range. The record is flagged, not automatically clipped, winsorised or deleted.

### `potential_duplicate`

Indicates that the legal-status-neutral company matching key occurs more than once. This is a review signal only and does not establish that two records are the same legal entity.

## Business-risk signals

The configured business-risk set contains three flags:

1. `has_adverse_legal_status`
2. `has_negative_latest_ebitda`
3. `has_revenue_decline`

### `has_adverse_legal_status`

True when explicit company-name wording indicates extinction, liquidation or dissolution. `no_adverse_marker` does not certify legal activity.

### `has_negative_latest_ebitda`

True when latest EBITDA is negative. This is a valid economic outcome and is not automatically a data error.

### `has_revenue_decline`

True when latest revenue is lower than previous revenue for comparable observations.

## Counts and booleans

```text
data_quality_issue_count = sum(active data-quality flags)
business_risk_signal_count = sum(active business-risk flags)
```

```text
has_data_quality_issue = data_quality_issue_count > 0
has_business_risk_signal = business_risk_signal_count > 0
```

All input flags are validated as non-missing boolean values before aggregation.

## Data-quality status

### `clean`

No active data-quality flags.

```text
data_quality_issue_count = 0
```

### `review`

Exactly one active data-quality flag.

```text
data_quality_issue_count = 1
```

### `high_priority_review`

Two or more active data-quality flags.

```text
data_quality_issue_count >= 2
```

This status prioritises review; it does not itself remove records.

## Analytical eligibility

### `eligible`

No data-quality issue is present.

### `eligible_with_review`

Only a non-blocking issue is present. In the current design, a potential duplicate can remain analytically available with explicit review.

### `not_eligible`

At least one blocking data-quality issue is present.

## Blocking and non-blocking logic

### Blocking issues

- incomplete financial information;
- negative latest revenue;
- zero latest revenue;
- extreme EBITDA margin.

These conditions prevent use in the strict standard analytical scope.

### Non-blocking issue

- potential duplicate without another blocking condition.

A blocking issue overrides `eligible_with_review`. A record with both a potential duplicate and a blocking issue is `not_eligible`.

Business-risk signals do not determine data-quality eligibility. A record with negative EBITDA, declining revenue or an adverse legal-status marker may remain `eligible` if its data structure is valid.

## Reason fields

### `data_quality_reasons`

Contains pipe-delimited labels corresponding to active quality flags. The field is an empty string when no quality issue exists.

### `business_risk_reasons`

Contains pipe-delimited labels corresponding to active risk flags. The field is an empty string when no business-risk signal exists.

Reason labels make each classification auditable and prevent summary categories from hiding the underlying causes.

## No silent correction

CapexQuant does not automatically:

- replace missing values with zero;
- delete potential duplicates;
- remove negative EBITDA;
- remove adverse legal-status records;
- cap extreme margins;
- alter original company names.

Filtering is explicit through analytical scopes, and source fields remain preserved.
