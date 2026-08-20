"""Tests for the end-to-end CapexQuant pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.generate_synthetic_data import (
    RANDOM_SEED,
    export_synthetic_dataset,
)
from src.load_data import DEFAULT_DATA_PATH
from src.pipeline import (
    ANALYTICAL_TABLE_NAMES,
    DEFAULT_RANKING_SIZE,
    PIPELINE_STAGE_NAMES,
    PipelineResult,
    build_argument_parser,
    create_analytical_tables,
    run_pipeline,
    validate_pipeline_integrity,
)


EXPECTED_SYNTHETIC_ROWS = 120
EXPECTED_SABI_ROWS = 6_711

EXPECTED_SOURCE_COLUMNS = 10
EXPECTED_CLEAN_COLUMNS = 16
EXPECTED_FINANCIAL_COLUMNS = 28
EXPECTED_QUALITY_COLUMNS = 36
EXPECTED_ANALYTICAL_TABLES = 7


@pytest.fixture(scope="module")
def synthetic_pipeline_result() -> PipelineResult:
    """Execute the default public pipeline once."""

    return run_pipeline(
        source="synthetic"
    )


def test_pipeline_stage_names_are_stable() -> None:
    """The standard pipeline stages must remain explicit."""

    assert PIPELINE_STAGE_NAMES == (
        "source",
        "clean",
        "financial",
        "quality",
    )


def test_analytical_table_names_are_stable() -> None:
    """The standard analytical outputs must remain explicit."""

    assert ANALYTICAL_TABLE_NAMES == (
        "scope_comparison",
        "coverage",
        "quality_summary",
        "revenue_concentration",
        "revenue_percentiles",
        "company_ranking",
        "municipality_summary",
    )


def test_default_ranking_size_is_stable() -> None:
    """The default public ranking must contain twenty companies."""

    assert DEFAULT_RANKING_SIZE == 20


def test_pipeline_returns_result_container(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """The orchestrator must return a PipelineResult."""

    assert isinstance(
        synthetic_pipeline_result,
        PipelineResult,
    )


def test_synthetic_pipeline_source_name(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """The result must preserve the normalized source name."""

    assert (
        synthetic_pipeline_result.source_name
        == "synthetic"
    )


def test_synthetic_pipeline_dimensions(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Each pipeline stage must expose the expected dimensions."""

    assert (
        synthetic_pipeline_result
        .source_dataframe
        .shape
        == (
            EXPECTED_SYNTHETIC_ROWS,
            EXPECTED_SOURCE_COLUMNS,
        )
    )

    assert (
        synthetic_pipeline_result
        .clean_dataframe
        .shape
        == (
            EXPECTED_SYNTHETIC_ROWS,
            EXPECTED_CLEAN_COLUMNS,
        )
    )

    assert (
        synthetic_pipeline_result
        .financial_dataframe
        .shape
        == (
            EXPECTED_SYNTHETIC_ROWS,
            EXPECTED_FINANCIAL_COLUMNS,
        )
    )

    assert (
        synthetic_pipeline_result
        .quality_dataframe
        .shape
        == (
            EXPECTED_SYNTHETIC_ROWS,
            EXPECTED_QUALITY_COLUMNS,
        )
    )


def test_pipeline_result_properties(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Convenience properties must reflect the final dataset."""

    assert (
        synthetic_pipeline_result.row_count
        == EXPECTED_SYNTHETIC_ROWS
    )

    assert (
        synthetic_pipeline_result.final_column_count
        == EXPECTED_QUALITY_COLUMNS
    )


def test_pipeline_preserves_record_order(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Every company-level stage must preserve record order."""

    expected_order = (
        synthetic_pipeline_result
        .source_dataframe[
            "record_order"
        ]
        .reset_index(
            drop=True
        )
    )

    for stage_name in PIPELINE_STAGE_NAMES:
        stage_dataframe = (
            synthetic_pipeline_result.get_stage(
                stage_name
            )
        )

        actual_order = stage_dataframe[
            "record_order"
        ].reset_index(drop=True)

        assert actual_order.equals(
            expected_order
        )


def test_pipeline_creates_every_analytical_table(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Every declared analytical table must be generated."""

    actual_table_names = tuple(
        synthetic_pipeline_result
        .analytical_tables
    )

    assert actual_table_names == (
        ANALYTICAL_TABLE_NAMES
    )

    assert len(actual_table_names) == (
        EXPECTED_ANALYTICAL_TABLES
    )


@pytest.mark.parametrize(
    "table_name",
    ANALYTICAL_TABLE_NAMES,
)
def test_analytical_tables_are_nonempty(
    synthetic_pipeline_result: PipelineResult,
    table_name: str,
) -> None:
    """Every standard analytical output must contain records."""

    table = synthetic_pipeline_result.get_table(
        table_name
    )

    assert isinstance(table, pd.DataFrame)
    assert not table.empty


def test_default_company_ranking_size(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """The standard ranking must contain twenty companies."""

    ranking = synthetic_pipeline_result.get_table(
        "company_ranking"
    )

    assert len(ranking) == DEFAULT_RANKING_SIZE

    assert ranking["rank"].tolist() == list(
        range(
            1,
            DEFAULT_RANKING_SIZE + 1,
        )
    )


def test_custom_ranking_size() -> None:
    """The pipeline must support a custom ranking size."""

    result = run_pipeline(
        source="synthetic",
        ranking_size=7,
    )

    ranking = result.get_table(
        "company_ranking"
    )

    assert len(ranking) == 7
    assert ranking["rank"].tolist() == list(
        range(1, 8)
    )


@pytest.mark.parametrize(
    "invalid_ranking_size",
    [
        0,
        -1,
        1.5,
        True,
        "20",
    ],
)
def test_invalid_ranking_size_is_rejected(
    synthetic_pipeline_result: PipelineResult,
    invalid_ranking_size: object,
) -> None:
    """Ranking size must be a strictly positive integer."""

    with pytest.raises(
        ValueError,
        match="ranking_size must be a positive integer",
    ):
        create_analytical_tables(
            quality_dataframe=(
                synthetic_pipeline_result
                .quality_dataframe
            ),
            ranking_size=invalid_ranking_size,
        )


def test_get_stage_returns_defensive_copy(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Modifying a retrieved stage must not alter the result."""

    retrieved_dataframe = (
        synthetic_pipeline_result.get_stage(
            "quality"
        )
    )

    retrieved_dataframe.loc[
        retrieved_dataframe.index[0],
        "company_name",
    ] = "MODIFIED"

    assert (
        synthetic_pipeline_result
        .quality_dataframe
        .iloc[0][
            "company_name"
        ]
        != "MODIFIED"
    )


def test_get_table_returns_defensive_copy(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Modifying a retrieved table must not alter the result."""

    retrieved_table = (
        synthetic_pipeline_result.get_table(
            "scope_comparison"
        )
    )

    retrieved_table.loc[
        retrieved_table.index[0],
        "company_count",
    ] = -1

    original_table = (
        synthetic_pipeline_result
        .analytical_tables[
            "scope_comparison"
        ]
    )

    assert original_table.iloc[0][
        "company_count"
    ] != -1


def test_unknown_stage_is_rejected(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Unknown company-level stages must be rejected."""

    with pytest.raises(
        ValueError,
        match="Unknown pipeline stage",
    ):
        synthetic_pipeline_result.get_stage(
            "unknown"
        )


def test_unknown_analytical_table_is_rejected(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Unknown analytical outputs must be rejected."""

    with pytest.raises(
        ValueError,
        match="Unknown analytical table",
    ):
        synthetic_pipeline_result.get_table(
            "unknown"
        )


def test_integrity_validation_rejects_row_loss(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """A lost company record must fail pipeline integrity."""

    source_dataframe = (
        synthetic_pipeline_result
        .source_dataframe
    )

    clean_dataframe = (
        synthetic_pipeline_result
        .clean_dataframe
        .iloc[:-1]
        .copy()
    )

    with pytest.raises(
        ValueError,
        match="row-count integrity failed",
    ):
        validate_pipeline_integrity(
            source_dataframe=source_dataframe,
            clean_dataframe=clean_dataframe,
            financial_dataframe=(
                synthetic_pipeline_result
                .financial_dataframe
            ),
            quality_dataframe=(
                synthetic_pipeline_result
                .quality_dataframe
            ),
        )


def test_integrity_validation_rejects_reordering(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """A reordered stage must fail pipeline integrity."""

    reordered_quality = (
        synthetic_pipeline_result
        .quality_dataframe
        .iloc[::-1]
        .copy()
    )

    with pytest.raises(
        ValueError,
        match="record-order integrity failed",
    ):
        validate_pipeline_integrity(
            source_dataframe=(
                synthetic_pipeline_result
                .source_dataframe
            ),
            clean_dataframe=(
                synthetic_pipeline_result
                .clean_dataframe
            ),
            financial_dataframe=(
                synthetic_pipeline_result
                .financial_dataframe
            ),
            quality_dataframe=reordered_quality,
        )


def test_custom_synthetic_source_path(
    tmp_path: Path,
) -> None:
    """The end-to-end pipeline must support a custom public source."""

    output_path = (
        tmp_path
        / "custom_synthetic.csv"
    )

    metadata_path = (
        tmp_path
        / "custom_metadata.json"
    )

    export_synthetic_dataset(
        output_path=output_path,
        metadata_path=metadata_path,
        company_count=30,
        random_seed=RANDOM_SEED,
    )

    result = run_pipeline(
        source="synthetic",
        file_path=output_path,
        ranking_size=10,
    )

    assert result.row_count == 30

    assert len(
        result.get_table(
            "company_ranking"
        )
    ) == 10


def test_pipeline_is_deterministic() -> None:
    """Equivalent public executions must produce identical results."""

    first_result = run_pipeline(
        source="synthetic"
    )

    second_result = run_pipeline(
        source="synthetic"
    )

    assert_frame_equal(
        first_result.quality_dataframe,
        second_result.quality_dataframe,
        check_exact=True,
    )

    for table_name in ANALYTICAL_TABLE_NAMES:
        assert_frame_equal(
            first_result.analytical_tables[table_name],
            second_result.analytical_tables[table_name],
            check_exact=True,
        )
               