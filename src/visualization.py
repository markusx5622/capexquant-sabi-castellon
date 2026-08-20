"""Reproducible visualizations for CapexQuant analytical outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from src.pipeline import PipelineResult


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

DEFAULT_OUTPUT_DIRECTORY: Final[Path] = (
    PROJECT_ROOT
    / "reports"
    / "figures"
)

SUPPORTED_VISUALIZATIONS: Final[tuple[str, ...]] = (
    "revenue_concentration",
    "revenue_percentiles",
    "company_ranking",
    "municipality_summary",
    "coverage",
)

FIGURE_DPI: Final[int] = 150


def validate_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
    chart_name: str,
) -> None:
    """Validate that a non-empty table contains required columns."""

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            f"{chart_name} requires a pandas DataFrame."
        )

    if dataframe.empty:
        raise ValueError(
            f"{chart_name} cannot be created from an empty table."
        )

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{chart_name} is missing required columns: "
            f"{missing_columns}"
        )


def create_revenue_concentration_figure(
    dataframe: pd.DataFrame,
) -> Figure:
    """Create a cumulative Top-N revenue concentration chart."""

    validate_columns(
        dataframe,
        [
            "top_n",
            "concentration_rate",
        ],
        "Revenue concentration chart",
    )

    plotting_data = dataframe.sort_values(
        "top_n"
    ).copy()

    figure, axis = plt.subplots(
        figsize=(8, 5)
    )

    axis.plot(
        plotting_data["top_n"],
        plotting_data["concentration_rate"] * 100,
        marker="o",
    )

    axis.set_title(
        "Cumulative revenue concentration"
    )
    axis.set_xlabel("Top N companies")
    axis.set_ylabel("Share of total revenue (%)")
    axis.set_ylim(
        0,
        max(
            100,
            float(
                plotting_data[
                    "concentration_rate"
                ].max()
                * 110
            ),
        ),
    )
    axis.grid(
        visible=True,
        alpha=0.3,
    )

    figure.tight_layout()

    return figure


def create_revenue_percentiles_figure(
    dataframe: pd.DataFrame,
) -> Figure:
    """Create a revenue percentile chart."""

    validate_columns(
        dataframe,
        [
            "percentile",
            "revenue_k_eur",
        ],
        "Revenue percentiles chart",
    )

    plotting_data = dataframe.sort_values(
        "percentile"
    ).copy()

    percentile_labels = [
        f"P{int(percentile * 100)}"
        for percentile in plotting_data[
            "percentile"
        ]
    ]

    figure, axis = plt.subplots(
        figsize=(8, 5)
    )

    axis.bar(
        percentile_labels,
        plotting_data["revenue_k_eur"],
    )

    axis.set_title(
        "Operating revenue percentiles"
    )
    axis.set_xlabel("Percentile")
    axis.set_ylabel(
        "Operating revenue (thousand EUR)"
    )

    figure.tight_layout()

    return figure


def create_company_ranking_figure(
    dataframe: pd.DataFrame,
    top_n: int = 10,
) -> Figure:
    """Create a horizontal ranking of companies by revenue."""

    if (
        not isinstance(top_n, int)
        or isinstance(top_n, bool)
        or top_n <= 0
    ):
        raise ValueError(
            "top_n must be a positive integer."
        )

    validate_columns(
        dataframe,
        [
            "company_name",
            "operating_revenue_latest_k_eur",
        ],
        "Company ranking chart",
    )

    plotting_data = (
        dataframe
        .dropna(
            subset=[
                "operating_revenue_latest_k_eur"
            ]
        )
        .nlargest(
            top_n,
            "operating_revenue_latest_k_eur",
        )
        .sort_values(
            "operating_revenue_latest_k_eur",
            ascending=True,
        )
    )

    figure_height = max(
        5.0,
        len(plotting_data) * 0.45,
    )

    figure, axis = plt.subplots(
        figsize=(10, figure_height)
    )

    axis.barh(
        plotting_data["company_name"],
        plotting_data[
            "operating_revenue_latest_k_eur"
        ],
    )

    axis.set_title(
        f"Top {len(plotting_data)} companies by revenue"
    )
    axis.set_xlabel(
        "Operating revenue (thousand EUR)"
    )
    axis.set_ylabel("Company")

    figure.tight_layout()

    return figure


def create_municipality_summary_figure(
    dataframe: pd.DataFrame,
    top_n: int = 10,
) -> Figure:
    """Create a municipal revenue ranking."""

    if (
        not isinstance(top_n, int)
        or isinstance(top_n, bool)
        or top_n <= 0
    ):
        raise ValueError(
            "top_n must be a positive integer."
        )

    validate_columns(
        dataframe,
        [
            "municipality",
            "revenue_total_k_eur",
        ],
        "Municipality summary chart",
    )

    plotting_data = (
        dataframe
        .dropna(
            subset=[
                "municipality",
                "revenue_total_k_eur",
            ]
        )
        .nlargest(
            top_n,
            "revenue_total_k_eur",
        )
        .sort_values(
            "revenue_total_k_eur",
            ascending=True,
        )
    )

    figure_height = max(
        5.0,
        len(plotting_data) * 0.45,
    )

    figure, axis = plt.subplots(
        figsize=(10, figure_height)
    )

    axis.barh(
        plotting_data["municipality"],
        plotting_data["revenue_total_k_eur"],
    )

    axis.set_title(
        f"Top {len(plotting_data)} municipality categories by revenue"
    )
    axis.set_xlabel(
        "Aggregated revenue (thousand EUR)"
    )
    axis.set_ylabel("Municipality category")

    figure.tight_layout()

    return figure


def create_coverage_figure(
    dataframe: pd.DataFrame,
) -> Figure:
    """Create a variable-coverage chart."""

    validate_columns(
        dataframe,
        [
            "variable",
            "coverage_rate",
        ],
        "Variable coverage chart",
    )

    plotting_data = dataframe.sort_values(
        "coverage_rate",
        ascending=True,
    ).copy()

    figure_height = max(
        4.5,
        len(plotting_data) * 0.55,
    )

    figure, axis = plt.subplots(
        figsize=(9, figure_height)
    )

    axis.barh(
        plotting_data["variable"],
        plotting_data["coverage_rate"] * 100,
    )

    axis.set_title("Variable coverage")
    axis.set_xlabel("Available observations (%)")
    axis.set_ylabel("Variable")
    axis.set_xlim(0, 100)

    figure.tight_layout()

    return figure


def create_standard_figures(
    pipeline_result: PipelineResult,
) -> dict[str, Figure]:
    """Create the standard public analytical figures."""

    if not isinstance(
        pipeline_result,
        PipelineResult,
    ):
        raise TypeError(
            "pipeline_result must be a PipelineResult."
        )

    return {
        "revenue_concentration": (
            create_revenue_concentration_figure(
                pipeline_result.get_table(
                    "revenue_concentration"
                )
            )
        ),
        "revenue_percentiles": (
            create_revenue_percentiles_figure(
                pipeline_result.get_table(
                    "revenue_percentiles"
                )
            )
        ),
        "company_ranking": (
            create_company_ranking_figure(
                pipeline_result.get_table(
                    "company_ranking"
                )
            )
        ),
        "municipality_summary": (
            create_municipality_summary_figure(
                pipeline_result.get_table(
                    "municipality_summary"
                )
            )
        ),
        "coverage": (
            create_coverage_figure(
                pipeline_result.get_table(
                    "coverage"
                )
            )
        ),
    }


def export_figure(
    figure: Figure,
    output_path: Path | str,
    dpi: int = FIGURE_DPI,
) -> Path:
    """Export one figure as a reproducible PNG artifact."""

    if not isinstance(figure, Figure):
        raise TypeError(
            "figure must be a matplotlib Figure."
        )

    if (
        not isinstance(dpi, int)
        or isinstance(dpi, bool)
        or dpi <= 0
    ):
        raise ValueError(
            "dpi must be a positive integer."
        )

    normalized_output_path = Path(
        output_path
    )

    if (
        normalized_output_path.suffix.lower()
        != ".png"
    ):
        raise ValueError(
            "Visualizations must be exported as PNG files."
        )

    normalized_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure.savefig(
        normalized_output_path,
        dpi=dpi,
        bbox_inches="tight",
        metadata={
            "Software": "CapexQuant",
            "Creation Time": None,
        },
    )

    return normalized_output_path


def export_standard_figures(
    pipeline_result: PipelineResult,
    output_directory: Path | str = (
        DEFAULT_OUTPUT_DIRECTORY
    ),
) -> dict[str, Path]:
    """Create, export and close all standard figures."""

    normalized_output_directory = Path(
        output_directory
    )

    normalized_output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    figures = create_standard_figures(
        pipeline_result
    )

    exported_paths: dict[str, Path] = {}

    try:
        for figure_name, figure in figures.items():
            output_path = (
                normalized_output_directory
                / f"{figure_name}.png"
            )

            exported_paths[figure_name] = (
                export_figure(
                    figure=figure,
                    output_path=output_path,
                )
            )
    finally:
        for figure in figures.values():
            plt.close(figure)

    return exported_paths


if __name__ == "__main__":
    from src.pipeline import run_pipeline

    result = run_pipeline(
        source="synthetic"
    )

    paths = export_standard_figures(
        pipeline_result=result
    )

    print(
        "Visualizations created successfully."
    )

    for name, path in paths.items():
        print(f"- {name}: {path}")