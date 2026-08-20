"""End-to-end orchestration for the CapexQuant analytical pipeline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd

from src.analytics import (
    calculate_coverage,
    calculate_revenue_concentration,
    calculate_revenue_percentiles,
    create_company_ranking,
    create_municipality_summary,
    create_scope_comparison,
)
from src.clean_data import clean_sabi_data
from src.data_sources import (
    load_data_source,
    normalize_source_name,
)
from src.financial_features import (
    EBITDA_LATEST,
    EMPLOYEES_LATEST,
    REVENUE_LATEST,
    add_financial_features,
)
from src.quality_control import (
    add_quality_controls,
    create_quality_summary,
)


PIPELINE_STAGE_NAMES: Final[tuple[str, ...]] = (
    "source",
    "clean",
    "financial",
    "quality",
)

ANALYTICAL_TABLE_NAMES: Final[tuple[str, ...]] = (
    "scope_comparison",
    "coverage",
    "quality_summary",
    "revenue_concentration",
    "revenue_percentiles",
    "company_ranking",
    "municipality_summary",
)

DEFAULT_RANKING_SIZE: Final[int] = 20


@dataclass(frozen=True)
class PipelineResult:
    """Container holding all CapexQuant pipeline outputs."""

    source_name: str
    source_dataframe: pd.DataFrame
    clean_dataframe: pd.DataFrame
    financial_dataframe: pd.DataFrame
    quality_dataframe: pd.DataFrame
    analytical_tables: dict[str, pd.DataFrame]

    @property
    def row_count(self) -> int:
        """Return the number of processed company records."""

        return len(self.quality_dataframe)

    @property
    def final_column_count(self) -> int:
        """Return the final number of company-level columns."""

        return len(self.quality_dataframe.columns)

    def get_stage(
        self,
        stage_name: str,
    ) -> pd.DataFrame:
        """Return a defensive copy of a pipeline stage."""

        stages = {
            "source": self.source_dataframe,
            "clean": self.clean_dataframe,
            "financial": self.financial_dataframe,
            "quality": self.quality_dataframe,
        }

        if stage_name not in stages:
            raise ValueError(
                f"Unknown pipeline stage: {stage_name!r}. "
                f"Expected one of: {PIPELINE_STAGE_NAMES}."
            )

        return stages[stage_name].copy()

    def get_table(
        self,
        table_name: str,
    ) -> pd.DataFrame:
        """Return a defensive copy of an analytical table."""

        if table_name not in self.analytical_tables:
            raise ValueError(
                f"Unknown analytical table: {table_name!r}. "
                f"Expected one of: {ANALYTICAL_TABLE_NAMES}."
            )

        return self.analytical_tables[
            table_name
        ].copy()


def validate_pipeline_integrity(
    source_dataframe: pd.DataFrame,
    clean_dataframe: pd.DataFrame,
    financial_dataframe: pd.DataFrame,
    quality_dataframe: pd.DataFrame,
) -> None:
    """
    Validate record preservation across all company-level stages.

    The pipeline must never add, remove or reorder company records
    during cleaning, financial engineering or quality control.
    """

    dataframes = {
        "source": source_dataframe,
        "clean": clean_dataframe,
        "financial": financial_dataframe,
        "quality": quality_dataframe,
    }

    row_counts = {
        name: len(dataframe)
        for name, dataframe in dataframes.items()
    }

    if len(set(row_counts.values())) != 1:
        raise ValueError(
            "Pipeline row-count integrity failed: "
            f"{row_counts}"
        )

    source_order = source_dataframe[
        "record_order"
    ].reset_index(drop=True)

    for stage_name, dataframe in dataframes.items():
        stage_order = dataframe[
            "record_order"
        ].reset_index(drop=True)

        if not source_order.equals(stage_order):
            raise ValueError(
                "Pipeline record-order integrity failed "
                f"at stage: {stage_name}"
            )


def create_analytical_tables(
    quality_dataframe: pd.DataFrame,
    ranking_size: int = DEFAULT_RANKING_SIZE,
) -> dict[str, pd.DataFrame]:
    """Create all standard CapexQuant analytical outputs."""

    if (
        not isinstance(ranking_size, int)
        or isinstance(ranking_size, bool)
        or ranking_size <= 0
    ):
        raise ValueError(
            "ranking_size must be a positive integer."
        )

    analytical_tables = {
        "scope_comparison": create_scope_comparison(
            quality_dataframe
        ),
        "coverage": calculate_coverage(
            quality_dataframe,
            [
                EMPLOYEES_LATEST,
                REVENUE_LATEST,
                EBITDA_LATEST,
                "revenue_growth",
                "ebitda_margin",
            ],
        ),
        "quality_summary": create_quality_summary(
            quality_dataframe
        ),
        "revenue_concentration": (
            calculate_revenue_concentration(
                quality_dataframe,
                scope="all",
            )
        ),
        "revenue_percentiles": (
            calculate_revenue_percentiles(
                quality_dataframe,
                scope="all",
            )
        ),
        "company_ranking": create_company_ranking(
            quality_dataframe,
            metric=REVENUE_LATEST,
            top_n=ranking_size,
            scope="all",
        ),
        "municipality_summary": (
            create_municipality_summary(
                quality_dataframe,
                scope="all",
            )
        ),
    }

    if tuple(analytical_tables) != (
        ANALYTICAL_TABLE_NAMES
    ):
        raise RuntimeError(
            "Unexpected analytical table configuration."
        )

    return analytical_tables


def run_pipeline(
    source: str = "synthetic",
    file_path: Path | str | None = None,
    generate_if_missing: bool = True,
    ranking_size: int = DEFAULT_RANKING_SIZE,
) -> PipelineResult:
    """
    Execute the complete company-level CapexQuant pipeline.

    Parameters
    ----------
    source:
        ``synthetic`` for the public reproducible source or ``sabi``
        for the private licensed workbook.

    file_path:
        Optional custom path for the selected source.

    generate_if_missing:
        When using the synthetic source, generate the deterministic
        CSV automatically if it is unavailable.

    ranking_size:
        Number of companies included in the standard ranking.

    Returns
    -------
    PipelineResult
        Immutable container exposing every pipeline stage and all
        standard analytical tables.
    """

    normalized_source = normalize_source_name(
        source
    )

    source_dataframe = load_data_source(
        source=normalized_source,
        file_path=file_path,
        generate_if_missing=generate_if_missing,
    )

    clean_dataframe = clean_sabi_data(
        source_dataframe
    )

    financial_dataframe = add_financial_features(
        clean_dataframe
    )

    quality_dataframe = add_quality_controls(
        financial_dataframe
    )

    validate_pipeline_integrity(
        source_dataframe=source_dataframe,
        clean_dataframe=clean_dataframe,
        financial_dataframe=financial_dataframe,
        quality_dataframe=quality_dataframe,
    )

    analytical_tables = create_analytical_tables(
        quality_dataframe=quality_dataframe,
        ranking_size=ranking_size,
    )

    return PipelineResult(
        source_name=normalized_source,
        source_dataframe=source_dataframe,
        clean_dataframe=clean_dataframe,
        financial_dataframe=financial_dataframe,
        quality_dataframe=quality_dataframe,
        analytical_tables=analytical_tables,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line interface parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Execute the CapexQuant financial-data pipeline."
        )
    )

    parser.add_argument(
        "--source",
        choices=[
            "synthetic",
            "sabi",
        ],
        default="synthetic",
        help=(
            "Input source. Synthetic is public and reproducible; "
            "SABI requires the private workbook."
        ),
    )

    parser.add_argument(
        "--file-path",
        type=Path,
        default=None,
        help="Optional custom source path.",
    )

    parser.add_argument(
        "--ranking-size",
        type=int,
        default=DEFAULT_RANKING_SIZE,
        help="Number of companies in the standard ranking.",
    )

    parser.add_argument(
        "--no-generate",
        action="store_true",
        help=(
            "Do not generate a missing synthetic dataset."
        ),
    )

    return parser


def main() -> int:
    """Execute the command-line pipeline."""

    parser = build_argument_parser()
    arguments = parser.parse_args()

    pipeline_result = run_pipeline(
        source=arguments.source,
        file_path=arguments.file_path,
        generate_if_missing=(
            not arguments.no_generate
        ),
        ranking_size=arguments.ranking_size,
    )

    quality_dataframe = (
        pipeline_result.quality_dataframe
    )

    print("CapexQuant pipeline completed successfully.")
    print(f"Source: {pipeline_result.source_name}")
    print(
        f"Rows processed: {pipeline_result.row_count:,}"
    )
    print(
        "Final company-level columns: "
        f"{pipeline_result.final_column_count}"
    )
    print(
        "Analytical tables created: "
        f"{len(pipeline_result.analytical_tables)}"
    )
    print(
        "Records with data-quality issues: "
        f"{int(quality_dataframe['has_data_quality_issue'].sum()):,}"
    )
    print(
        "Records with business-risk signals: "
        f"{int(quality_dataframe['has_business_risk_signal'].sum()):,}"
    )

    print("\nAnalytical outputs:")
    for table_name, table in (
        pipeline_result.analytical_tables.items()
    ):
        print(
            f"- {table_name}: "
            f"{len(table):,} rows x "
            f"{len(table.columns):,} columns"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())