"""Reproducible result exports for the CapexQuant pipeline."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

import pandas as pd

from src.pipeline import (
    ANALYTICAL_TABLE_NAMES,
    PipelineResult,
    run_pipeline,
)


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

DEFAULT_PUBLIC_OUTPUT_DIRECTORY: Final[Path] = (
    PROJECT_ROOT
    / "reports"
    / "tables"
    / "synthetic"
)

DEFAULT_PRIVATE_OUTPUT_DIRECTORY: Final[Path] = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pipeline_exports"
)

COMPANY_LEVEL_FILENAME: Final[str] = (
    "companies_quality_controlled.csv"
)

RUN_METADATA_FILENAME: Final[str] = "run_metadata.json"

EXPORT_MANIFEST_FILENAME: Final[str] = "export_manifest.json"

ANALYTICAL_TABLE_FILENAMES: Final[dict[str, str]] = {
    "scope_comparison": "scope_comparison.csv",
    "coverage": "coverage.csv",
    "quality_summary": "quality_summary.csv",
    "revenue_concentration": "revenue_concentration.csv",
    "revenue_percentiles": "revenue_percentiles.csv",
    "company_ranking": "company_ranking.csv",
    "municipality_summary": "municipality_summary.csv",
}

PUBLIC_EXPORT_SOURCE: Final[str] = "synthetic"
PRIVATE_EXPORT_SOURCE: Final[str] = "sabi"


@dataclass(frozen=True)
class ExportResult:
    """Container describing one completed export operation."""

    source_name: str
    output_directory: Path
    exported_files: tuple[Path, ...]
    manifest_path: Path
    metadata_path: Path

    @property
    def file_count(self) -> int:
        """Return the number of exported files."""

        return len(self.exported_files)

    def get_file(
        self,
        filename: str,
    ) -> Path:
        """Return a specific exported file path."""

        matching_files = [
            file_path
            for file_path in self.exported_files
            if file_path.name == filename
        ]

        if not matching_files:
            raise ValueError(
                f"Exported file not found: {filename!r}"
            )

        return matching_files[0]


def calculate_file_sha256(
    file_path: Path | str,
) -> str:
    """Calculate the SHA-256 checksum of an exported file."""

    normalized_path = Path(file_path)

    if not normalized_path.exists():
        raise FileNotFoundError(
            f"Cannot hash missing file: {normalized_path}"
        )

    digest = hashlib.sha256()

    with normalized_path.open("rb") as file_handle:
        for block in iter(
            lambda: file_handle.read(65_536),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def determine_default_output_directory(
    source_name: str,
) -> Path:
    """
    Return the safe default output directory for a source.

    Synthetic outputs are public artifacts under reports/tables.
    SABI outputs remain private under data/processed.
    """

    if source_name == PUBLIC_EXPORT_SOURCE:
        return DEFAULT_PUBLIC_OUTPUT_DIRECTORY

    if source_name == PRIVATE_EXPORT_SOURCE:
        return DEFAULT_PRIVATE_OUTPUT_DIRECTORY

    raise ValueError(
        f"Unsupported export source: {source_name!r}"
    )


def validate_export_directory(
    source_name: str,
    output_directory: Path | str,
    allow_private_public_export: bool = False,
) -> Path:
    """
    Validate that private data cannot be exported publicly by accident.

    By default, SABI exports are prohibited from any location inside
    the repository's reports directory.
    """

    normalized_directory = Path(
        output_directory
    ).resolve()

    reports_directory = (
        PROJECT_ROOT
        / "reports"
    ).resolve()

    if (
        source_name == PRIVATE_EXPORT_SOURCE
        and not allow_private_public_export
        and (
            normalized_directory == reports_directory
            or reports_directory
            in normalized_directory.parents
        )
    ):
        raise ValueError(
            "Private SABI results cannot be exported "
            "inside reports/ unless "
            "allow_private_public_export=True."
        )

    return normalized_directory


def validate_pipeline_result(
    pipeline_result: PipelineResult,
) -> None:
    """Validate the pipeline result before export."""

    if not isinstance(
        pipeline_result,
        PipelineResult,
    ):
        raise TypeError(
            "pipeline_result must be a PipelineResult."
        )

    if pipeline_result.quality_dataframe.empty:
        raise ValueError(
            "Cannot export an empty pipeline result."
        )

    actual_table_names = tuple(
        pipeline_result.analytical_tables
    )

    if actual_table_names != ANALYTICAL_TABLE_NAMES:
        raise ValueError(
            "Pipeline result does not contain the expected "
            "analytical tables."
        )


def write_dataframe_csv(
    dataframe: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    """Write a DataFrame to a deterministic UTF-8 CSV."""

    normalized_path = Path(output_path)

    if dataframe.empty:
        raise ValueError(
            f"Cannot export an empty DataFrame: {normalized_path.name}"
        )

    normalized_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        normalized_path,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
        float_format="%.10g",
    )

    return normalized_path


def create_run_metadata(
    pipeline_result: PipelineResult,
) -> dict[str, object]:
    """Create descriptive metadata for one pipeline execution."""

    quality_dataframe = (
        pipeline_result.quality_dataframe
    )

    return {
        "project": "CapexQuant SABI Castellón",
        "source": pipeline_result.source_name,
        "dataset_type": (
            "fully_synthetic"
            if pipeline_result.source_name
            == PUBLIC_EXPORT_SOURCE
            else "private_licensed_source"
        ),
        "contains_sabi_data": (
            pipeline_result.source_name
            == PRIVATE_EXPORT_SOURCE
        ),
        "public_distribution_allowed": (
            pipeline_result.source_name
            == PUBLIC_EXPORT_SOURCE
        ),
        "row_count": pipeline_result.row_count,
        "source_column_count": len(
            pipeline_result.source_dataframe.columns
        ),
        "final_column_count": (
            pipeline_result.final_column_count
        ),
        "analytical_table_count": len(
            pipeline_result.analytical_tables
        ),
        "data_quality_issue_count": int(
            quality_dataframe[
                "has_data_quality_issue"
            ].sum()
        ),
        "business_risk_signal_count": int(
            quality_dataframe[
                "has_business_risk_signal"
            ].sum()
        ),
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "currency_unit": "thousand_eur",
        "limitations": [
            (
                "The synthetic source is not representative "
                "of the Castellón economy."
                if pipeline_result.source_name
                == PUBLIC_EXPORT_SOURCE
                else (
                    "The SABI source combines each company's "
                    "latest available financial period."
                )
            ),
            (
                "Results must not be used for credit, "
                "investment or legal decisions."
            ),
            (
                "Adverse legal status is inferred from "
                "explicit company-name markers."
            ),
        ],
    }


def write_json(
    content: dict[str, object],
    output_path: Path | str,
) -> Path:
    """Write a JSON object using stable formatting."""

    normalized_path = Path(output_path)

    normalized_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized_path.write_text(
        json.dumps(
            content,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return normalized_path


def create_export_manifest(
    exported_files: list[Path],
    base_directory: Path,
) -> dict[str, object]:
    """Create a checksum manifest for exported artifacts."""

    manifest_entries = []

    for file_path in sorted(
        exported_files,
        key=lambda path: path.name,
    ):
        manifest_entries.append(
            {
                "filename": str(
                    file_path.relative_to(
                        base_directory
                    )
                ).replace("\\", "/"),
                "size_bytes": file_path.stat().st_size,
                "sha256": calculate_file_sha256(
                    file_path
                ),
            }
        )

    return {
        "file_count": len(manifest_entries),
        "files": manifest_entries,
    }


def export_pipeline_result(
    pipeline_result: PipelineResult,
    output_directory: Path | str | None = None,
    include_company_level_data: bool | None = None,
    overwrite: bool = True,
    allow_private_public_export: bool = False,
) -> ExportResult:
    """
    Export analytical tables, metadata and optional company-level data.

    Synthetic exports include the final company-level dataset by
    default. Private SABI exports exclude company-level data by
    default and remain under data/processed.

    Existing output directories are replaced when overwrite=True.
    """

    validate_pipeline_result(
        pipeline_result
    )

    selected_directory = (
        determine_default_output_directory(
            pipeline_result.source_name
        )
        if output_directory is None
        else Path(output_directory)
    )

    normalized_directory = validate_export_directory(
        source_name=pipeline_result.source_name,
        output_directory=selected_directory,
        allow_private_public_export=(
            allow_private_public_export
        ),
    )

    if include_company_level_data is None:
        include_company_level_data = (
            pipeline_result.source_name
            == PUBLIC_EXPORT_SOURCE
        )

    if normalized_directory.exists():
        existing_items = list(
            normalized_directory.iterdir()
        )

        if existing_items and not overwrite:
            raise FileExistsError(
                "Export directory is not empty and "
                "overwrite=False: "
                f"{normalized_directory}"
            )

        if overwrite:
            shutil.rmtree(
                normalized_directory
            )

    normalized_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    exported_files: list[Path] = []

    for table_name in ANALYTICAL_TABLE_NAMES:
        filename = ANALYTICAL_TABLE_FILENAMES[
            table_name
        ]

        table_path = write_dataframe_csv(
            dataframe=(
                pipeline_result
                .analytical_tables[
                    table_name
                ]
            ),
            output_path=(
                normalized_directory
                / filename
            ),
        )

        exported_files.append(
            table_path
        )

    if include_company_level_data:
        company_level_path = write_dataframe_csv(
            dataframe=(
                pipeline_result
                .quality_dataframe
            ),
            output_path=(
                normalized_directory
                / COMPANY_LEVEL_FILENAME
            ),
        )

        exported_files.append(
            company_level_path
        )

    metadata = create_run_metadata(
        pipeline_result
    )

    metadata_path = write_json(
        content=metadata,
        output_path=(
            normalized_directory
            / RUN_METADATA_FILENAME
        ),
    )

    exported_files.append(
        metadata_path
    )

    manifest = create_export_manifest(
        exported_files=exported_files,
        base_directory=normalized_directory,
    )

    manifest_path = write_json(
        content=manifest,
        output_path=(
            normalized_directory
            / EXPORT_MANIFEST_FILENAME
        ),
    )

    exported_files.append(
        manifest_path
    )

    return ExportResult(
        source_name=pipeline_result.source_name,
        output_directory=normalized_directory,
        exported_files=tuple(
            exported_files
        ),
        manifest_path=manifest_path,
        metadata_path=metadata_path,
    )


def run_and_export(
    source: str = "synthetic",
    file_path: Path | str | None = None,
    output_directory: Path | str | None = None,
    ranking_size: int = 20,
    include_company_level_data: bool | None = None,
    overwrite: bool = True,
) -> ExportResult:
    """Execute the complete pipeline and export its results."""

    pipeline_result = run_pipeline(
        source=source,
        file_path=file_path,
        ranking_size=ranking_size,
    )

    return export_pipeline_result(
        pipeline_result=pipeline_result,
        output_directory=output_directory,
        include_company_level_data=(
            include_company_level_data
        ),
        overwrite=overwrite,
    )


def main() -> int:
    """Run and export the public synthetic pipeline."""

    export_result = run_and_export(
        source="synthetic"
    )

    print("CapexQuant results exported successfully.")
    print(f"Source: {export_result.source_name}")
    print(
        "Output directory: "
        f"{export_result.output_directory}"
    )
    print(
        f"Files exported: {export_result.file_count}"
    )

    print("\nExported files:")
    for file_path in (
        export_result.exported_files
    ):
        print(
            f"- {file_path.name}: "
            f"{file_path.stat().st_size:,} bytes"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())