"""Tests for reproducible CapexQuant result exports."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.export_results import (
    ANALYTICAL_TABLE_FILENAMES,
    COMPANY_LEVEL_FILENAME,
    DEFAULT_PRIVATE_OUTPUT_DIRECTORY,
    DEFAULT_PUBLIC_OUTPUT_DIRECTORY,
    EXPORT_MANIFEST_FILENAME,
    RUN_METADATA_FILENAME,
    ExportResult,
    calculate_file_sha256,
    create_export_manifest,
    create_run_metadata,
    determine_default_output_directory,
    export_pipeline_result,
    run_and_export,
    validate_export_directory,
    validate_pipeline_result,
    write_dataframe_csv,
    write_json,
)
from src.pipeline import (
    ANALYTICAL_TABLE_NAMES,
    PipelineResult,
    run_pipeline,
)


EXPECTED_SYNTHETIC_ROWS = 120
EXPECTED_ANALYTICAL_TABLES = 7
EXPECTED_PUBLIC_FILE_COUNT = 10
EXPECTED_PRIVATE_DEFAULT_FILE_COUNT = 9


@pytest.fixture(scope="module")
def synthetic_pipeline_result() -> PipelineResult:
    """Execute the public pipeline once."""

    return run_pipeline(
        source="synthetic"
    )


@pytest.fixture()
def synthetic_export_result(
    synthetic_pipeline_result: PipelineResult,
    tmp_path: Path,
) -> ExportResult:
    """Export the public pipeline into an isolated directory."""

    return export_pipeline_result(
        pipeline_result=synthetic_pipeline_result,
        output_directory=(
            tmp_path
            / "synthetic_export"
        ),
    )


def test_analytical_filename_configuration() -> None:
    """Every analytical table must have one export filename."""

    assert set(
        ANALYTICAL_TABLE_FILENAMES
    ) == set(
        ANALYTICAL_TABLE_NAMES
    )

    assert len(
        ANALYTICAL_TABLE_FILENAMES
    ) == EXPECTED_ANALYTICAL_TABLES

    assert len(
        set(
            ANALYTICAL_TABLE_FILENAMES.values()
        )
    ) == EXPECTED_ANALYTICAL_TABLES


def test_default_output_directories() -> None:
    """Public and private sources must use separate directories."""

    assert determine_default_output_directory(
        "synthetic"
    ) == DEFAULT_PUBLIC_OUTPUT_DIRECTORY

    assert determine_default_output_directory(
        "sabi"
    ) == DEFAULT_PRIVATE_OUTPUT_DIRECTORY

    assert (
        DEFAULT_PUBLIC_OUTPUT_DIRECTORY
        != DEFAULT_PRIVATE_OUTPUT_DIRECTORY
    )


def test_unknown_export_source_is_rejected() -> None:
    """An unknown export source must be rejected."""

    with pytest.raises(
        ValueError,
        match="Unsupported export source",
    ):
        determine_default_output_directory(
            "unknown"
        )


def test_missing_file_hash_is_rejected(
    tmp_path: Path,
) -> None:
    """A missing file cannot be hashed."""

    with pytest.raises(
        FileNotFoundError,
        match="Cannot hash missing file",
    ):
        calculate_file_sha256(
            tmp_path / "missing.csv"
        )


def test_file_hash_is_stable(
    tmp_path: Path,
) -> None:
    """Equivalent file content must produce the same hash."""

    first_path = tmp_path / "first.txt"
    second_path = tmp_path / "second.txt"

    first_path.write_text(
        "CapexQuant\n",
        encoding="utf-8",
    )

    second_path.write_text(
        "CapexQuant\n",
        encoding="utf-8",
    )

    assert calculate_file_sha256(
        first_path
    ) == calculate_file_sha256(
        second_path
    )


def test_validate_pipeline_result_accepts_valid_result(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """A complete pipeline result must pass validation."""

    validate_pipeline_result(
        synthetic_pipeline_result
    )


def test_validate_pipeline_result_rejects_wrong_type() -> None:
    """Exporting requires a PipelineResult instance."""

    with pytest.raises(
        TypeError,
        match="must be a PipelineResult",
    ):
        validate_pipeline_result(
            object()
        )


def test_public_export_directory_is_allowed(
    tmp_path: Path,
) -> None:
    """Synthetic outputs may be exported to a public directory."""

    output_directory = (
        tmp_path
        / "reports"
        / "tables"
    )

    result = validate_export_directory(
        source_name="synthetic",
        output_directory=output_directory,
    )

    assert result == output_directory.resolve()


def test_private_reports_export_is_blocked() -> None:
    """SABI exports must not enter reports by default."""

    private_public_directory = (
        Path(__file__).resolve().parents[1]
        / "reports"
        / "private_sabi"
    )

    with pytest.raises(
        ValueError,
        match="Private SABI results cannot be exported",
    ):
        validate_export_directory(
            source_name="sabi",
            output_directory=(
                private_public_directory
            ),
        )


def test_private_reports_export_can_be_explicitly_allowed() -> None:
    """The safety rule may only be bypassed explicitly."""

    private_public_directory = (
        Path(__file__).resolve().parents[1]
        / "reports"
        / "private_sabi"
    )

    result = validate_export_directory(
        source_name="sabi",
        output_directory=private_public_directory,
        allow_private_public_export=True,
    )

    assert result == (
        private_public_directory.resolve()
    )


def test_write_dataframe_csv(
    tmp_path: Path,
) -> None:
    """CSV writing must preserve shape and column order."""

    dataframe = pd.DataFrame(
        {
            "company": [
                "SYNTHETIC A",
                "SYNTHETIC B",
            ],
            "revenue": [
                100.25,
                200.50,
            ],
        }
    )

    output_path = (
        tmp_path
        / "table.csv"
    )

    returned_path = write_dataframe_csv(
        dataframe=dataframe,
        output_path=output_path,
    )

    exported_dataframe = pd.read_csv(
        output_path
    )

    assert returned_path == output_path
    assert exported_dataframe.shape == (2, 2)

    assert exported_dataframe.columns.tolist() == [
        "company",
        "revenue",
    ]


def test_empty_dataframe_export_is_rejected(
    tmp_path: Path,
) -> None:
    """Empty analytical tables must not be exported."""

    with pytest.raises(
        ValueError,
        match="Cannot export an empty DataFrame",
    ):
        write_dataframe_csv(
            dataframe=pd.DataFrame(),
            output_path=tmp_path / "empty.csv",
        )


def test_write_json_uses_valid_encoding(
    tmp_path: Path,
) -> None:
    """JSON exports must preserve Unicode content."""

    output_path = tmp_path / "metadata.json"

    content = {
        "project": "CapexQuant Castellón",
        "valid": True,
    }

    write_json(
        content=content,
        output_path=output_path,
    )

    stored_content = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert stored_content == content


def test_public_export_result_structure(
    synthetic_export_result: ExportResult,
) -> None:
    """The public export must return a complete result object."""

    assert isinstance(
        synthetic_export_result,
        ExportResult,
    )

    assert synthetic_export_result.source_name == (
        "synthetic"
    )

    assert synthetic_export_result.file_count == (
        EXPECTED_PUBLIC_FILE_COUNT
    )

    assert (
        synthetic_export_result.output_directory
        .exists()
    )


def test_every_exported_file_exists(
    synthetic_export_result: ExportResult,
) -> None:
    """Every declared export artifact must exist."""

    for file_path in (
        synthetic_export_result.exported_files
    ):
        assert file_path.exists()
        assert file_path.is_file()
        assert file_path.stat().st_size > 0


@pytest.mark.parametrize(
    ("table_name", "filename"),
    ANALYTICAL_TABLE_FILENAMES.items(),
)
def test_every_analytical_table_is_exported(
    synthetic_export_result: ExportResult,
    table_name: str,
    filename: str,
) -> None:
    """Every standard analytical table must be exported."""

    exported_path = (
        synthetic_export_result.get_file(
            filename
        )
    )

    exported_dataframe = pd.read_csv(
        exported_path
    )

    assert not exported_dataframe.empty


def test_public_company_level_data_is_exported(
    synthetic_export_result: ExportResult,
) -> None:
    """The public synthetic export must include company-level data."""

    company_path = (
        synthetic_export_result.get_file(
            COMPANY_LEVEL_FILENAME
        )
    )

    dataframe = pd.read_csv(
        company_path
    )

    assert len(dataframe) == (
        EXPECTED_SYNTHETIC_ROWS
    )

    assert dataframe[
        "company_name"
    ].str.startswith(
        "SYNTHETIC "
    ).all()


def test_public_metadata_declarations(
    synthetic_export_result: ExportResult,
) -> None:
    """Public metadata must identify a fully synthetic source."""

    metadata = json.loads(
        synthetic_export_result
        .metadata_path
        .read_text(
            encoding="utf-8"
        )
    )

    assert metadata["source"] == "synthetic"
    assert metadata["dataset_type"] == (
        "fully_synthetic"
    )
    assert metadata["contains_sabi_data"] is False
    assert (
        metadata[
            "public_distribution_allowed"
        ]
        is True
    )
    assert metadata["row_count"] == (
        EXPECTED_SYNTHETIC_ROWS
    )


def test_export_manifest_matches_files(
    synthetic_export_result: ExportResult,
) -> None:
    """Manifest entries must match every pre-manifest artifact."""

    manifest = json.loads(
        synthetic_export_result
        .manifest_path
        .read_text(
            encoding="utf-8"
        )
    )

    files_without_manifest = [
        file_path
        for file_path in (
            synthetic_export_result
            .exported_files
        )
        if file_path.name
        != EXPORT_MANIFEST_FILENAME
    ]

    assert manifest["file_count"] == len(
        files_without_manifest
    )

    assert len(manifest["files"]) == len(
        files_without_manifest
    )


def test_manifest_hashes_match_exported_files(
    synthetic_export_result: ExportResult,
) -> None:
    """Every manifest checksum must match its artifact."""

    manifest = json.loads(
        synthetic_export_result
        .manifest_path
        .read_text(
            encoding="utf-8"
        )
    )

    for entry in manifest["files"]:
        file_path = (
            synthetic_export_result
            .output_directory
            / entry["filename"]
        )

        assert entry["sha256"] == (
            calculate_file_sha256(
                file_path
            )
        )

        assert entry["size_bytes"] == (
            file_path.stat().st_size
        )


def test_get_missing_exported_file_is_rejected(
    synthetic_export_result: ExportResult,
) -> None:
    """Unknown export filenames must be rejected."""

    with pytest.raises(
        ValueError,
        match="Exported file not found",
    ):
        synthetic_export_result.get_file(
            "missing.csv"
        )


def test_overwrite_false_rejects_nonempty_directory(
    synthetic_pipeline_result: PipelineResult,
    tmp_path: Path,
) -> None:
    """Existing artifacts must be protected when overwrite is false."""

    output_directory = (
        tmp_path
        / "existing"
    )

    output_directory.mkdir()

    (
        output_directory
        / "existing.txt"
    ).write_text(
        "existing",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="overwrite=False",
    ):
        export_pipeline_result(
            pipeline_result=(
                synthetic_pipeline_result
            ),
            output_directory=(
                output_directory
            ),
            overwrite=False,
        )


def test_overwrite_true_replaces_existing_directory(
    synthetic_pipeline_result: PipelineResult,
    tmp_path: Path,
) -> None:
    """Overwrite mode must remove stale artifacts."""

    output_directory = (
        tmp_path
        / "replace"
    )

    output_directory.mkdir()

    stale_path = (
        output_directory
        / "stale.txt"
    )

    stale_path.write_text(
        "stale",
        encoding="utf-8",
    )

    export_pipeline_result(
        pipeline_result=(
            synthetic_pipeline_result
        ),
        output_directory=output_directory,
        overwrite=True,
    )

    assert not stale_path.exists()

    assert (
        output_directory
        / RUN_METADATA_FILENAME
    ).exists()


def test_company_level_export_can_be_disabled(
    synthetic_pipeline_result: PipelineResult,
    tmp_path: Path,
) -> None:
    """Company-level exports must be optional."""

    result = export_pipeline_result(
        pipeline_result=synthetic_pipeline_result,
        output_directory=(
            tmp_path
            / "without_companies"
        ),
        include_company_level_data=False,
    )

    filenames = {
        file_path.name
        for file_path in result.exported_files
    }

    assert COMPANY_LEVEL_FILENAME not in filenames

    assert result.file_count == (
        EXPECTED_PRIVATE_DEFAULT_FILE_COUNT
    )


def test_run_metadata_matches_pipeline(
    synthetic_pipeline_result: PipelineResult,
) -> None:
    """Metadata counts must match the pipeline result."""

    metadata = create_run_metadata(
        synthetic_pipeline_result
    )

    assert metadata["row_count"] == (
        synthetic_pipeline_result.row_count
    )

    assert metadata[
        "final_column_count"
    ] == (
        synthetic_pipeline_result
        .final_column_count
    )

    assert metadata[
        "analytical_table_count"
    ] == EXPECTED_ANALYTICAL_TABLES


def test_manifest_creation(
    tmp_path: Path,
) -> None:
    """Manifest creation must sort and hash files."""

    first_path = tmp_path / "b.csv"
    second_path = tmp_path / "a.csv"

    first_path.write_text(
        "b\n",
        encoding="utf-8",
    )

    second_path.write_text(
        "a\n",
        encoding="utf-8",
    )

    manifest = create_export_manifest(
        exported_files=[
            first_path,
            second_path,
        ],
        base_directory=tmp_path,
    )

    assert manifest["file_count"] == 2

    assert [
        entry["filename"]
        for entry in manifest["files"]
    ] == [
        "a.csv",
        "b.csv",
    ]


def test_run_and_export_public_pipeline(
    tmp_path: Path,
) -> None:
    """The public pipeline must execute and export end to end."""

    result = run_and_export(
        source="synthetic",
        output_directory=(
            tmp_path
            / "end_to_end"
        ),
        ranking_size=8,
    )

    assert result.source_name == "synthetic"
    assert result.file_count == (
        EXPECTED_PUBLIC_FILE_COUNT
    )

    ranking = pd.read_csv(
        result.get_file(
            ANALYTICAL_TABLE_FILENAMES[
                "company_ranking"
            ]
        )
    )

    assert len(ranking) == 8