# CapexQuant Methodology

## Scope

This document defines the financial calculations and analytical decisions implemented by CapexQuant. Financial values ending in `_k_eur` are expressed in **thousands of euros**. Ratios are stored as decimal values, not percentage points.

## Source-period convention

`latest` and `previous` refer to each company’s latest and preceding available observations in the source. They do not necessarily represent one homogeneous fiscal year across every company. Aggregate interpretation must therefore acknowledge temporal heterogeneity.

## Financial formulas

Let:

- `R_t` = `operating_revenue_latest_k_eur`
- `R_t-1` = `operating_revenue_previous_k_eur`
- `E_t` = `ebitda_latest_k_eur`
- `E_t-1` = `ebitda_previous_k_eur`
- `N_t` = `employees_latest`

### Revenue growth

```text
revenue_growth = (R_t - R_t-1) / R_t-1
```

The value is available only when both revenue observations are present and the previous value is a valid non-zero denominator.

### Absolute revenue change

```text
revenue_change_k_eur = R_t - R_t-1
```

This measure remains interpretable when percentage growth is unavailable because of a zero denominator, provided both source values exist.

### EBITDA margin

```text
ebitda_margin = E_t / R_t
```

The ratio is unavailable when latest EBITDA or revenue is missing, or when latest revenue is zero.

### Absolute EBITDA change

```text
ebitda_change_k_eur = E_t - E_t-1
```

An absolute change is preferred to a percentage EBITDA growth rate because EBITDA can be negative, zero or change sign. Percentage growth in those cases can be misleading or undefined.

### Revenue per employee

```text
revenue_per_employee_k_eur = R_t / N_t
```

### EBITDA per employee

```text
ebitda_per_employee_k_eur = E_t / N_t
```

Both productivity measures require a present, positive employee denominator.

## Safe division

CapexQuant uses safe division instead of direct unrestricted division. A ratio is calculated only when:

- numerator and denominator are available;
- the denominator is not zero;
- the denominator satisfies the semantic requirement of the metric, such as positive employment.

Invalid divisions produce missing values rather than `inf`, `-inf` or an artificial zero.

## Missing values

Missing information is preserved throughout the pipeline. CapexQuant does not replace unavailable financial information with zero because:

- zero is an economic observation;
- missing is an information-availability condition;
- conflating both would distort totals, ratios, growth and eligibility.

Aggregation uses the available observations and reports coverage separately.

## Financial flags

The financial layer creates preventive indicators:

- `has_negative_latest_revenue`
- `has_zero_latest_revenue`
- `has_negative_latest_ebitda`
- `has_revenue_decline`
- `has_extreme_ebitda_margin`
- `has_incomplete_financial_data`

A negative EBITDA or revenue decline is a business characteristic. It is not automatically a data-quality error.

## Revenue concentration

For a requested Top-N level:

```text
revenue_share_N = sum(N largest non-missing latest revenues)
                  / sum(all non-missing latest revenues)
```

Missing revenue observations are excluded from both numerator and denominator. Results include requested and effective company counts when the requested N exceeds the available population.

Concentration is cumulative and must not decrease as N increases.

## Percentiles

Revenue percentiles are calculated on non-missing latest revenue observations. The default levels are:

```text
25%, 50%, 75%, 90%, 95%, 99%
```

The 50th percentile is the median. Percentiles describe distribution shape and are more robust than the mean to a highly right-skewed company-size distribution.

## Analytical scopes

### `all`

Includes every record after quality controls.

### `no_adverse_marker`

Excludes records with an explicit adverse legal-status marker. Absence of an adverse marker does not prove that a company is legally active.

### `eligible`

Includes only records whose `analytical_eligibility` equals `eligible`. Records marked `eligible_with_review` are excluded from this strict scope.

### `no_adverse_eligible`

Combines strict analytical eligibility with absence of an explicit adverse legal-status marker.

## Aggregate, mean and median

- **Aggregate total** measures the combined magnitude of the population and is strongly influenced by large companies.
- **Mean** divides the aggregate by observation count and remains sensitive to outliers and concentration.
- **Median** represents the central ordered observation and is more robust to skewness.

CapexQuant reports totals and medians for different analytical purposes. An aggregate EBITDA margin, if required, must be computed as total EBITDA divided by total revenue, not as the unweighted mean of company margins.

## Negative EBITDA

Negative EBITDA is retained. It is economically meaningful and may indicate operating losses, temporary stress, restructuring or a business model with weak operating profitability. It is classified as a business-risk signal, not automatically as invalid data.

## No automatic removal or winsorisation

Potential duplicates, extreme margins, adverse legal markers and negative financial outcomes are flagged rather than silently deleted or modified. Exclusions occur only through explicit analytical scopes.
