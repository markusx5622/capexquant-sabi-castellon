"""Tests for auditable geographic normalization."""

import pandas as pd
import pytest

from src.geography import (
    MAPPING_REQUIRED_COLUMNS,
    create_mapping_template,
    create_municipality_inventory,
    create_municipality_match_key,
    normalize_geographic_text,
    remove_geographic_accents,
    validate_geography_schema,
)
from src.quality_control import add_quality_controls


EXPECTED_COMPANIES = 6_711
EXPECTED_RAW_MUNICIPALITIES = 133


@pytest.fixture(scope="module")
def analytical_dataframe() -> pd.DataFrame:
    """Load the validated company dataset once."""

    return add_quality_controls()


@pytest.fixture(scope="module")
def municipality_inventory(
    analytical_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Create the municipality audit inventory once."""

    return create_municipality_inventory(
        analytical_dataframe
    )


def test_normalize_geographic_text() -> None:
    """Whitespace and case must be standardized."""

    assert normalize_geographic_text(
        "  Castelló   de la Plana "
    ) == "CASTELLÓ DE LA PLANA"


def test_normalize_geographic_text_preserves_missing() -> None:
    """Missing values must remain missing."""

    assert pd.isna(normalize_geographic_text(pd.NA))
    assert pd.isna(normalize_geographic_text("   "))


def test_remove_geographic_accents() -> None:
    """Accents must be removed only for matching."""

    assert remove_geographic_accents(
        "CASTELLÓ PEÑÍSCOLA"
    ) == "CASTELLO PENISCOLA"


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        (
            "Castelló de la Plana",
            "CASTELLO DE LA PLANA",
        ),
        (
            "Peñíscola/Peniscola",
            "PENISCOLA PENISCOLA",
        ),
        (
            "L'Alcora",
            "L ALCORA",
        ),
    ],
)
def test_create_municipality_match_key(
    original: str,
    expected: str,
) -> None:
    """Match keys must be reproducible."""

    assert create_municipality_match_key(
        original
    ) == expected


def test_geography_schema_accepts_valid_data(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """The validated dataset must satisfy the geographic schema."""

    validate_geography_schema(analytical_dataframe)


def test_geography_schema_rejects_missing_column(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Missing geographic fields must raise an explicit error."""

    invalid_dataframe = analytical_dataframe.drop(
        columns=["municipality"]
    )

    with pytest.raises(
        ValueError,
        match="Missing columns required for geographic analysis",
    ):
        validate_geography_schema(invalid_dataframe)


def test_inventory_preserves_all_companies(
    municipality_inventory: pd.DataFrame,
) -> None:
    """Municipality aggregation must preserve the population."""

    assert (
        municipality_inventory["company_count"].sum()
        == EXPECTED_COMPANIES
    )


def test_inventory_contains_expected_categories(
    municipality_inventory: pd.DataFrame,
) -> None:
    """The raw source must contain the audited category count."""

    assert (
        len(municipality_inventory)
        == EXPECTED_RAW_MUNICIPALITIES
    )


def test_inventory_ids_are_unique(
    municipality_inventory: pd.DataFrame,
) -> None:
    """Every raw municipality category needs a unique audit ID."""

    assert municipality_inventory[
        "inventory_id"
    ].is_unique

    assert municipality_inventory[
        "inventory_id"
    ].tolist() == list(
        range(
            1,
            EXPECTED_RAW_MUNICIPALITIES + 1,
        )
    )


def test_inventory_does_not_mutate_input(
    analytical_dataframe: pd.DataFrame,
) -> None:
    """Inventory creation must not modify company-level data."""

    original_columns = analytical_dataframe.columns.tolist()
    original_shape = analytical_dataframe.shape

    create_municipality_inventory(
        analytical_dataframe
    )

    assert analytical_dataframe.shape == original_shape
    assert (
        analytical_dataframe.columns.tolist()
        == original_columns
    )


def test_mapping_template_structure(
    municipality_inventory: pd.DataFrame,
) -> None:
    """The mapping template must follow the documented schema."""

    mapping = create_mapping_template(
        municipality_inventory
    )

    assert mapping.columns.tolist() == MAPPING_REQUIRED_COLUMNS
    assert len(mapping) == EXPECTED_RAW_MUNICIPALITIES
    assert mapping["municipality_original"].is_unique


def test_mapping_template_starts_pending(
    municipality_inventory: pd.DataFrame,
) -> None:
    """New mappings must require explicit review."""

    mapping = create_mapping_template(
        municipality_inventory
    )

    assert mapping["review_status"].eq("pending").all()

    assert mapping["normalization_rule"].eq(
        "identity_pending_review"
    ).all()


def test_empty_inventory_is_rejected() -> None:
    """An empty dataset cannot produce a geographic inventory."""

    with pytest.raises(
        ValueError,
        match="empty DataFrame",
    ):
        create_municipality_inventory(
            pd.DataFrame()
        )