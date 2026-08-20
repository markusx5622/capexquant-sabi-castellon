# CapexQuant Limitations

## Purpose of this document

CapexQuant provides a tested analytical pipeline, not a complete valuation, credit-scoring or legal-status system. Results must be interpreted within the limits of the source, variables and transformation rules.

## Temporal heterogeneity

The SABI fields labelled `latest` and `previous` refer to each company’s latest and preceding available observations. Companies may therefore be represented by different fiscal years or reporting dates.

Consequences include:

- total values are not necessarily a same-period economic snapshot;
- growth rates may refer to different year pairs;
- cross-company comparisons can contain timing effects;
- macroeconomic conclusions require additional period harmonisation.

## Incomplete financial statements

The standard source schema contains operating revenue, EBITDA and employees but not a complete income statement, balance sheet or cash-flow statement.

The project cannot directly assess:

- total assets and liabilities;
- working capital;
- equity and solvency structure;
- interest coverage;
- tax position;
- depreciation and amortisation detail;
- accounting policy differences.

## Missing debt, cash, CAPEX and cash flow

The current schema does not provide complete:

- gross or net debt;
- cash and cash equivalents;
- capital expenditure;
- operating cash flow;
- free cash flow;
- debt maturity schedules.

As a result, CapexQuant cannot perform a full leverage, liquidity or free-cash-flow assessment.

## EBITDA is not cash flow

EBITDA excludes important economic items and timing effects. EBITDA does not account fully for:

- capital expenditure;
- working-capital movements;
- cash taxes;
- interest payments;
- debt repayments;
- exceptional cash items.

Positive EBITDA does not guarantee positive cash generation, and negative EBITDA does not by itself determine insolvency.

## Legal-status inference

`legal_status` is inferred from explicit wording contained in the company-name field. Therefore:

- an adverse marker is evidence of text in the source name;
- absence of an adverse marker does not prove legal activity;
- names may be stale, incomplete or inconsistently formatted;
- authoritative legal conclusions require current registry information.

The label `no_adverse_marker` is intentionally not named `active`.

## Potential duplicates

`potential_duplicate` identifies repeated normalised matching keys. It does not confirm duplicate legal entities because companies can have:

- similar or identical names;
- different legal identifiers;
- historical and current records;
- branches or related entities;
- source-specific naming inconsistencies.

Potential duplicates require manual or identifier-based resolution and are not automatically deleted.

## Extreme margins

An extreme EBITDA margin can arise from:

- a denominator close to zero;
- source or unit errors;
- exceptional accounting events;
- genuinely unusual economics.

CapexQuant flags extreme values but does not automatically winsorise or remove them.

## Missing values

Missing information is preserved. Coverage varies by metric because ratios require multiple valid observations. Aggregate results based on available data can differ from results for the full company count.

## Concentration and outliers

Company-level revenue distributions are typically right-skewed. A small number of large companies can dominate totals and means. Concentration metrics reveal this dependence but do not remove it.

## Geographic normalization

Geographic matching keys standardise text but cannot prove that two labels are equivalent. Bilingual, compound, historical or ambiguous categories require documented review. Canonical labels reflect project conventions and may require future updates.

## No public sector classification

The public synthetic schema does not currently include a validated sector or activity classification. Therefore the public analysis cannot support robust industry benchmarking, sector-adjusted margins or sector concentration.

## Synthetic dataset

The public sample is fully synthetic and deterministic. It:

- does not represent the Castellón economy;
- does not reproduce the private source distribution;
- uses simplified financial relationships;
- exists to demonstrate software behaviour, testing and reproducibility.

Results from the synthetic notebook must not be presented as empirical findings about real companies or municipalities.

## Licensing and confidentiality

The original SABI workbook and private company-level derived data are excluded from version control. Public artefacts must not reconstruct or redistribute licensed records.

## Decision-use prohibition

CapexQuant outputs must not be used as the sole or primary basis for:

- investment decisions;
- credit decisions;
- lending or pricing decisions;
- legal conclusions;
- regulatory determinations;
- employment or procurement decisions affecting real entities.

Independent source verification and appropriate professional judgement are required for any real-world use.
