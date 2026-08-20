# CapexQuant Data Dictionary

## Conventions

- `k_eur` means thousands of euros.
- Ratios are decimal values.
- Boolean fields contain `True` or `False` after validation.
- Missing values are allowed only where stated.
- The source, clean, financial and quality layers contain 10, 16, 28 and 36 columns respectively.

## Source layer: 10 columns

| Column | Type | Unit | Created in | Description | Missing allowed |
|---|---|---|---|---|---|
| `record_order` | Integer | None | Source adapter | Stable source-order identifier used to verify preservation and ordering. | No |
| `company_name` | String | None | Source adapter | Original company name. Synthetic names are explicitly prefixed with `SYNTHETIC`. | No |
| `website` | String | URL | Source adapter | Company website when available. Synthetic websites use `.example`. | Yes |
| `municipality` | String | None | Source adapter | Original municipality label supplied by the selected source. | Source-dependent |
| `employees_latest` | Integer | Employees | Source adapter | Latest available employee count. | Source-dependent |
| `operating_revenue_latest_k_eur` | Numeric | Thousand EUR | Source adapter | Latest available operating revenue. | Yes |
| `operating_revenue_previous_k_eur` | Numeric | Thousand EUR | Source adapter | Previous available operating revenue. | Yes |
| `ebitda_latest_k_eur` | Numeric | Thousand EUR | Source adapter | Latest available EBITDA. | Yes |
| `ebitda_previous_k_eur` | Numeric | Thousand EUR | Source adapter | Previous available EBITDA. | Yes |
| `shareholder_name` | String | None | Source adapter | Shareholder information when available. | Yes |

## Clean layer: 6 added columns, 16 total

| Column | Type | Unit | Created in | Description | Missing allowed |
|---|---|---|---|---|---|
| `company_name_normalized` | String | None | `clean_data.py` | Uppercase, accent-free, punctuation-normalised name for matching. Original name is preserved. | If source name missing, but source validation rejects missing names |
| `legal_status` | String category | None | `clean_data.py` | Marker inferred from explicit wording in the company name: `no_adverse_marker`, `extinct`, `in_liquidation`, `in_dissolution` or `unknown`. | No after classification |
| `has_adverse_legal_status` | Boolean | None | `clean_data.py` | True when the inferred legal status is explicitly adverse. | No |
| `company_match_key` | String | None | `clean_data.py` | Normalised matching key with explicit legal-status wording removed. | No for valid company names |
| `potential_duplicate` | Boolean | None | `clean_data.py` | Warning that the match key occurs more than once. It does not confirm a duplicate legal entity. | No |
| `potential_duplicate_count` | Nullable integer | Records | `clean_data.py` | Number of observations sharing the company match key. | No |

## Financial layer: 12 added columns, 28 total

| Column | Type | Unit | Created in | Description | Missing allowed |
|---|---|---|---|---|---|
| `revenue_growth` | Numeric | Decimal ratio | `financial_features.py` | Latest-minus-previous revenue divided by previous revenue using safe division. | Yes |
| `revenue_change_k_eur` | Numeric | Thousand EUR | `financial_features.py` | Absolute change in operating revenue. | Yes |
| `ebitda_margin` | Numeric | Decimal ratio | `financial_features.py` | Latest EBITDA divided by latest revenue using safe division. | Yes |
| `ebitda_change_k_eur` | Numeric | Thousand EUR | `financial_features.py` | Absolute change in EBITDA. | Yes |
| `revenue_per_employee_k_eur` | Numeric | Thousand EUR per employee | `financial_features.py` | Latest revenue divided by latest employee count. | Yes |
| `ebitda_per_employee_k_eur` | Numeric | Thousand EUR per employee | `financial_features.py` | Latest EBITDA divided by latest employee count. | Yes |
| `has_negative_latest_revenue` | Boolean | None | `financial_features.py` | Latest revenue is below zero. | No |
| `has_zero_latest_revenue` | Boolean | None | `financial_features.py` | Latest revenue equals zero. | No |
| `has_negative_latest_ebitda` | Boolean | None | `financial_features.py` | Latest EBITDA is below zero. | No |
| `has_revenue_decline` | Boolean | None | `financial_features.py` | Latest revenue is below previous revenue where comparison is available. | No |
| `has_extreme_ebitda_margin` | Boolean | None | `financial_features.py` | EBITDA margin exceeds the configured plausibility threshold in absolute or directional terms. | No |
| `has_incomplete_financial_data` | Boolean | None | `financial_features.py` | One or more financial observations required by the standard calculations are unavailable. | No |

## Quality layer: 8 added columns, 36 total

| Column | Type | Unit | Created in | Description | Missing allowed |
|---|---|---|---|---|---|
| `data_quality_issue_count` | Nullable integer | Active flags | `quality_control.py` | Count of active data-quality flags. | No |
| `business_risk_signal_count` | Nullable integer | Active flags | `quality_control.py` | Count of active business-risk flags. | No |
| `has_data_quality_issue` | Boolean | None | `quality_control.py` | True when `data_quality_issue_count` is greater than zero. | No |
| `has_business_risk_signal` | Boolean | None | `quality_control.py` | True when `business_risk_signal_count` is greater than zero. | No |
| `data_quality_status` | String category | None | `quality_control.py` | `clean`, `review` or `high_priority_review`, based on issue count. | No |
| `analytical_eligibility` | String category | None | `quality_control.py` | `eligible`, `eligible_with_review` or `not_eligible`. | No |
| `data_quality_reasons` | String | Pipe-delimited labels | `quality_control.py` | Traceable labels for active data-quality flags; empty when no issue exists. | No, empty string represents no reason |
| `business_risk_reasons` | String | Pipe-delimited labels | `quality_control.py` | Traceable labels for active business-risk flags; empty when no signal exists. | No, empty string represents no reason |

## Analytical tables

The company-level dictionary above does not include columns created only in aggregate outputs. Those columns include counts, totals, medians, rates, scope labels, percentile labels, rank and concentration metrics. Aggregate monetary columns retain the `_k_eur` suffix.

## Geographic audit fields

Geographic audit artefacts use fields such as:

- `municipality_original`
- `municipality_match_key`
- `municipality_canonical`
- `review_status`
- `normalization_rule`
- `notes`

These fields support traceability and are not part of the standard 36-column quality dataset unless an explicit geographic enrichment step is applied.
