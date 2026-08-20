# CapexQuant Architecture

## Purpose

CapexQuant is a modular, tested financial-data pipeline for validating, cleaning and analysing heterogeneous company-level information. The repository supports two source modes:

- **`synthetic`**: a deterministic, fully public demonstration dataset.
- **`sabi`**: a private, licensed workbook that remains outside version control.

The pipeline deliberately separates source access, deterministic transformation, financial feature engineering, data-quality control, analytical aggregation, exports and presentation.

## Repository structure

```text
capexquant-sabi-castellon/
├── data/
│   ├── raw/                  # Private licensed source, ignored by Git
│   ├── processed/            # Private derived outputs, ignored by Git
│   ├── reference/            # Public auditable reference mappings
│   └── sample/               # Public synthetic source and metadata
├── docs/                     # Technical documentation
├── notebooks/                # Public analytical narrative
├── reports/
│   ├── figures/              # Reproducible public figures
│   └── tables/               # Reproducible analytical exports
├── src/                      # Production Python modules
├── tests/                    # Automated unit, integration and regression tests
├── sql/                      # Reserved for future SQL artefacts
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## End-to-end flow

```text
Synthetic CSV or private SABI workbook
                  ↓
           src/data_sources.py
                  ↓
             10-column schema
                  ↓
           src/clean_data.py
                  ↓
             16-column layer
                  ↓
      src/financial_features.py
                  ↓
             28-column layer
                  ↓
        src/quality_control.py
                  ↓
             36-column layer
                  ↓
     src/geography.py / reference mapping
                  ↓
           src/analytics.py
                  ↓
          seven analytical tables
                  ↓
 src/export_results.py and src/visualization.py
                  ↓
 public tables, figures and analytical notebook
```

`src/pipeline.py` orchestrates the common source-to-analysis sequence through a single interface. The public workflow is:

```bash
python -m src.pipeline --source synthetic
```

The private workflow is:

```bash
python -m src.pipeline --source sabi
```

## Module responsibilities

### `src/load_data.py`

Reads and validates the private SABI workbook, standardises the licensed source columns and returns the common ten-column schema. The workbook is never generated or committed.

### `src/generate_synthetic_data.py`

Generates a deterministic public dataset of fictional companies, exports its metadata and calculates a SHA-256 checksum for reproducibility.

### `src/data_sources.py`

Provides a unified source interface. Both `synthetic` and `sabi` return the same ordered ten-column schema and validated numeric and text types.

### `src/clean_data.py`

Performs deterministic text cleaning, preserves original names, derives legal-status markers, creates matching keys, handles explicit no-shareholder-information messages and adds potential-duplicate indicators.

### `src/financial_features.py`

Creates financial ratios, changes, productivity measures and preventive validation flags using safe division and explicit missing-value preservation.

### `src/quality_control.py`

Separates data-quality issues from business-risk signals, counts active flags, creates traceable reason fields and assigns data-quality status and analytical eligibility.

### `src/geography.py`

Creates an auditable municipality inventory and matching keys, validates the geographic reference schema and supports reviewable canonical labels through `data/reference/municipality_mapping.csv`.

### `src/analytics.py`

Produces overview metrics, coverage, scope comparisons, revenue concentration, percentiles, company rankings and municipality summaries without mutating the company-level dataset.

### `src/pipeline.py`

Orchestrates source loading, cleaning, feature engineering, quality control and analytical-table creation. It validates row-count and record-order integrity across stages.

### `src/export_results.py`

Exports analytical tables, optional company-level synthetic results, metadata and checksum manifests. Public synthetic and private SABI output locations are separated.

### `src/visualization.py`

Generates reproducible figures from the public analytical outputs.

## Standard pipeline dimensions

| Layer | Rows | Columns | Purpose |
|---|---:|---:|---|
| Source | Source-dependent | 10 | Common input contract |
| Clean | Preserved | 16 | Deterministic cleaning and traceability |
| Financial | Preserved | 28 | Financial metrics and financial flags |
| Quality | Preserved | 36 | Quality and risk aggregation |

The public sample contains 120 rows. The private configured extraction contains 6,711 rows. The pipeline requires row count and `record_order` to remain unchanged across company-level stages.

## Analytical outputs

The standard pipeline creates seven tables:

1. `scope_comparison`
2. `coverage`
3. `quality_summary`
4. `revenue_concentration`
5. `revenue_percentiles`
6. `company_ranking`
7. `municipality_summary`

The public visual layer generates:

- `coverage.png`
- `revenue_percentiles.png`
- `revenue_concentration.png`
- `company_ranking.png`
- `municipality_summary.png`

## Public and private artefacts

### Public

- Source code and tests.
- Synthetic CSV and metadata under `data/sample/`.
- Geographic reference mapping under `data/reference/`.
- Synthetic analytical exports and figures.
- Executed public notebook.
- Technical documentation.

### Private

- Original SABI workbook under `data/raw/`.
- Derived SABI inventories and company-level exports under `data/processed/`.
- Any outputs that reproduce licensed company-level information.

The `.gitignore` excludes raw and processed data, spreadsheet files, databases, secrets, caches and local environment artefacts.
