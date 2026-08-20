"""Tests for CapexQuant visualizations."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

from src.pipeline import run_pipeline
from src.visualization import (
    SUPPORTED_VISUALIZATIONS,
    create_company_ranking_figure,
    create_coverage_figure,
    create_municipality_summary_figure,
    create_revenue_concentration_figure,
    create_revenue_percentiles_figure,
    create_standard_figures,
    export_figure,
    export_standard_figures,
    validate_columns,
)


@pytest.fixture(scope="module")
def synthetic_pipeline_result():
    """Execute the reproducible public pipeline once."""

    return run_pipeline(
        source="synthetic"
    )


def test_validate_columns_accepts_valid_table() -> None:
    """Valid tables must pass schema validation."""

    dataframe = pd.DataFrame(
        {
            "column_a": [1],
            "column_b": [2],
        }
    )

    validate_columns(
        dataframe,
        ["column_a", "column_b"],
        "Test chart",
    )


def test_validate_columns_rejects_empty_table() -> None:
    """Empty analytical tables must be rejected."""

    with pytest.raises(
        ValueError,
        match="empty table",
    ):
        validate_columns(
            pd.DataFrame(),
            ["column_a"],
            "Test chart",
        )


def test_validate_columns_rejects_missing_fields() -> None:
    """Missing visual fields must raise an explicit error."""

    dataframe = pd.DataFrame(
        {
            "column_a": [1],
        }
    )

    with pytest.raises(
        ValueError,
        match="missing required columns",
    ):
        validate_columns(
            dataframe,
            ["column_a", "column_b"],
            "Test chart",
        )


@pytest.mark.parametrize(
    ("table_name", "creation_function"),
    [
        (
            "revenue_concentration",
            create_revenue_concentration_figure,
        ),
        (
            "revenue_percentiles",
            create_revenue_percentiles_figure,
        ),
        (
            "company_ranking",
            create_company_ranking_figure,
        ),
        (
            "municipality_summary",
            create_municipality_summary_figure,
        ),
        (
            "coverage",
            create_coverage_figure,
        ),
    ],
)
def test_individual_visualizations_return_figures(
    synthetic_pipeline_result,
    table_name: str,
    creation_function,
) -> None:
    """Every standard visualization must return a Figure."""

    figure = creation_function(
        synthetic_pipeline_result.get_table(
            table_name
        )
    )

    try:
        assert isinstance(figure, Figure)
        assert len(figure.axes) == 1
    finally:
        plt.close(figure)


def test_standard_figures_have_expected_names(
    synthetic_pipeline_result,
) -> None:
    """Standard figure registry must remain stable."""

    figures = create_standard_figures(
        synthetic_pipeline_result
    )

    try:
        assert tuple(figures) == (
            SUPPORTED_VISUALIZATIONS
        )

        assert all(
            isinstance(figure, Figure)
            for figure in figures.values()
        )
    finally:
        for figure in figures.values():
            plt.close(figure)


def test_export_figure_creates_png(
    tmp_path: Path,
) -> None:
    """One figure must be exported as a non-empty PNG."""

    figure, axis = plt.subplots()
    axis.plot([1, 2], [3, 4])

    output_path = (
        tmp_path
        / "test_figure.png"
    )

    try:
        exported_path = export_figure(
            figure,
            output_path,
        )
    finally:
        plt.close(figure)

    assert exported_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert output_path.read_bytes()[:8] == (
        b"\x89PNG\r\n\x1a\n"
    )


def test_export_rejects_non_png_path(
    tmp_path: Path,
) -> None:
    """Public visualization exports must use PNG."""

    figure, _ = plt.subplots()

    try:
        with pytest.raises(
            ValueError,
            match="PNG",
        ):
            export_figure(
                figure,
                tmp_path / "figure.pdf",
            )
    finally:
        plt.close(figure)


def test_export_rejects_invalid_dpi(
    tmp_path: Path,
) -> None:
    """Export resolution must be a positive integer."""

    figure, _ = plt.subplots()

    try:
        with pytest.raises(
            ValueError,
            match="positive integer",
        ):
            export_figure(
                figure,
                tmp_path / "figure.png",
                dpi=0,
            )
    finally:
        plt.close(figure)


def test_invalid_ranking_size_is_rejected(
    synthetic_pipeline_result,
) -> None:
    """Ranking chart size must be positive."""

    ranking = synthetic_pipeline_result.get_table(
        "company_ranking"
    )

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        create_company_ranking_figure(
            ranking,
            top_n=0,
        )


def test_standard_export_creates_all_files(
    synthetic_pipeline_result,
    tmp_path: Path,
) -> None:
    """The full public export must create every chart."""

    exported_paths = export_standard_figures(
        pipeline_result=synthetic_pipeline_result,
        output_directory=tmp_path,
    )

    assert tuple(exported_paths) == (
        SUPPORTED_VISUALIZATIONS
    )

    for figure_name, output_path in (
        exported_paths.items()
    ):
        assert output_path == (
            tmp_path
            / f"{figure_name}.png"
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        assert output_path.read_bytes()[:8] == (
            b"\x89PNG\r\n\x1a\n"
        )


def test_standard_export_closes_figures(
    synthetic_pipeline_result,
    tmp_path: Path,
) -> None:
    """Batch export must not leave open matplotlib figures."""

    initial_figures = set(
        plt.get_fignums()
    )

    export_standard_figures(
        pipeline_result=synthetic_pipeline_result,
        output_directory=tmp_path,
    )

    assert set(plt.get_fignums()) == initial_figures