# Public Synthetic Dataset

## Purpose

CapexQuant includes a fully synthetic source so that the public repository can be cloned, tested and executed without access to the licensed SABI workbook.

The synthetic dataset is intended for:

- public demonstration;
- automated testing;
- recruitment review;
- reproducibility checks;
- end-to-end pipeline validation.

It is not intended to represent the economy of Castellón.

## Files

```text
data/sample/companies_synthetic.csv
data/sample/companies_synthetic_metadata.json
```

The generator is:

```text
src/generate_synthetic_data.py
```

## Deterministic configuration

- **Random seed:** `20260820`
- **Default company count:** `120`
- **Source columns:** `10`
- **Currency unit:** thousand EUR
- **Generation method:** deterministic statistical simulation

Equivalent executions with the same implementation, seed and export settings produce the same CSV bytes and SHA-256 checksum.

## Standard schema

The generated source uses the same ordered schema as the private source adapter:

1. `record_order`
2. `company_name`
3. `website`
4. `municipality`
5. `employees_latest`
6. `operating_revenue_latest_k_eur`
7. `operating_revenue_previous_k_eur`
8. `ebitda_latest_k_eur`
9. `ebitda_previous_k_eur`
10. `shareholder_name`

This compatibility allows the synthetic source to traverse cleaning, financial features, quality controls and analytics without a parallel pipeline.

## Fictional company names

Names are deterministically composed from predefined fictional prefixes and suffixes and include a sequential identifier. Every generated company name begins with:

```text
SYNTHETIC
```

The design makes the fictional nature of each observation explicit and supports uniqueness checks.

## Simulated legal-status markers

Selected fictional names contain supported markers such as:

```text
(EXTINGUIDA)
(EN LIQUIDACION)
(EN DISOLUCION)
```

`clean_data.py` derives `legal_status` from these markers using the same logic as the private workflow.

## Financial simulation

The generator creates:

- integer employee counts bounded by the configured simulation rules;
- positive revenue observations based on employees and simulated revenue per employee;
- positive and negative revenue changes;
- positive and negative EBITDA cases;
- previous and latest EBITDA margins;
- controlled missing financial observations.

Financial relationships are simplified and are not calibrated to reproduce confidential company records.

## Controlled missing values

The dataset deliberately includes missing latest revenue, previous revenue and latest EBITDA observations. These cases test:

- safe ratio calculation;
- coverage reporting;
- incomplete-financial-data flags;
- analytical eligibility;
- pipeline robustness.

Missing values are not replaced with zero.

## Websites and shareholders

Available websites use the reserved `.example` top-level domain, for example:

```text
https://synthetic-company-001.example
```

Available shareholder names begin with `SYNTHETIC HOLDING`. Missing websites and shareholders are deliberately included.

## SHA-256 reproducibility

After CSV export, the generator calculates a SHA-256 checksum and records it in the metadata JSON. Tests verify that:

- two equivalent exports have identical hashes;
- the metadata hash matches the exported file;
- metadata dimensions match the CSV;
- stored and returned metadata agree.

A checksum verifies file identity, not economic realism or data quality.

## Privacy declaration

The public synthetic dataset:

- contains **no SABI data**;
- contains **no real companies**;
- contains **no personal data**;
- does not reproduce licensed company records;
- is safe for public demonstration under the project’s stated limitations.

## Execution

Generate the public source:

```bash
python -m src.generate_synthetic_data
```

Run the complete public pipeline:

```bash
python -m src.pipeline --source synthetic
```

## Limitations

- The sample is not statistically representative of Castellón.
- Financial relationships are intentionally simplified.
- The sample must not be used for investment, credit, legal or policy decisions.
- Public municipality frequencies do not reproduce the licensed source distribution.
