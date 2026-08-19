"""Auditable geographic normalization for CapexQuant SABI Castellón."""

from pathlib import Path
import re
import unicodedata

import pandas as pd

from src.quality_control import add_quality_controls


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INVENTORY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "municipality_inventory.csv"
)

DEFAULT_MAPPING_PATH = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "municipality_mapping.csv"
)

MUNICIPALITY_COLUMN = "municipality"

MAPPING_REQUIRED_COLUMNS = [
    "municipality_original",
    "municipality_match_key",
    "municipality_canonical",
    "review_status",
    "normalization_rule",
    "notes",
]

VALID_REVIEW_STATUSES = {
    "pending",
    "reviewed",
    "not_applicable",
}


def normalize_geographic_text(
    value: object,
) -> object:
    """
    Normalize geographic text while preserving missing values.

    The function:
    - strips leading and trailing whitespace;
    - collapses repeated whitespace;
    - converts text to uppercase.

    Accents and punctuation are preserved because they may form part
    of the official municipality name.
    """

    if pd.isna(value):
        return pd.NA

    normalized_value = re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()

    if not normalized_value:
        return pd.NA

    return normalized_value.upper()


def remove_geographic_accents(
    value: object,
) -> object:
    """Remove Unicode accents for geographic matching purposes."""

    if pd.isna(value):
        return pd.NA

    normalized = unicodedata.normalize(
        "NFKD",
        str(value),
    )

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def create_municipality_match_key(
    value: object,
) -> object:
    """
    Create a conservative match key for municipality comparison.

    The key:
    - standardizes whitespace and case;
    - removes accents;
    - replaces punctuation with spaces;
    - preserves all meaningful words.

    The key is a candidate-matching aid. It does not automatically
    establish that two municipality labels are equivalent.
    """

    normalized_value = normalize_geographic_text(value)

    if pd.isna(normalized_value):
        return pd.NA

    match_key = remove_geographic_accents(
        normalized_value
    )

    match_key = re.sub(
        r"[^A-Z0-9\s]",
        " ",
        str(match_key),
    )

    match_key = re.sub(
        r"\s+",
        " ",
        match_key,
    ).strip()

    return match_key


def validate_geography_schema(
    dataframe: pd.DataFrame,
) -> None:
    """Validate data required for geographic inventory creation."""

    required_columns = [
        "company_name",
        MUNICIPALITY_COLUMN,
        "employees_latest",
        "operating_revenue_latest_k_eur",
        "ebitda_latest_k_eur",
        "has_adverse_legal_status",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns required for geographic analysis: "
            f"{missing_columns}"
        )


def create_municipality_inventory(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create an audit inventory of raw municipality categories.

    The inventory preserves source labels and adds aggregate counts
    solely for local review. It does not modify the source dataset.
    """

    if dataframe.empty:
        raise ValueError(
            "Cannot create a municipality inventory "
            "from an empty DataFrame."
        )

    validate_geography_schema(dataframe)

    working_dataframe = dataframe.copy()

    working_dataframe[
        "municipality_original"
    ] = working_dataframe[
        MUNICIPALITY_COLUMN
    ].apply(
        normalize_geographic_text
    )

    working_dataframe[
        "municipality_match_key"
    ] = working_dataframe[
        "municipality_original"
    ].apply(
        create_municipality_match_key
    )

    inventory = (
        working_dataframe
        .groupby(
            [
                "municipality_original",
                "municipality_match_key",
            ],
            dropna=False,
        )
        .agg(
            company_count=(
                "company_name",
                "size",
            ),
            employee_count=(
                "employees_latest",
                "sum",
            ),
            revenue_total_k_eur=(
                "operating_revenue_latest_k_eur",
                "sum",
            ),
            ebitda_total_k_eur=(
                "ebitda_latest_k_eur",
                "sum",
            ),
            adverse_status_count=(
                "has_adverse_legal_status",
                "sum",
            ),
        )
        .reset_index()
        .sort_values(
            [
                "company_count",
                "revenue_total_k_eur",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .reset_index(
            drop=True
        )
    )

    inventory.insert(
        0,
        "inventory_id",
        range(
            1,
            len(inventory) + 1,
        ),
    )

    return inventory


def create_mapping_template(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a review template from a municipality inventory.

    Aggregate financial values are deliberately excluded from the
    mapping file. The committed mapping should contain rules and
    labels, not proprietary company-level financial information.
    """

    required_inventory_columns = [
        "municipality_original",
        "municipality_match_key",
    ]

    missing_columns = [
        column
        for column in required_inventory_columns
        if column not in inventory.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing inventory columns required for mapping: "
            f"{missing_columns}"
        )

    mapping = (
        inventory[
            required_inventory_columns
        ]
        .drop_duplicates()
        .sort_values(
            "municipality_original",
            na_position="last",
        )
        .reset_index(
            drop=True
        )
    )

    mapping[
        "municipality_canonical"
    ] = mapping[
        "municipality_original"
    ]

    mapping[
        "review_status"
    ] = "pending"

    mapping[
        "normalization_rule"
    ] = "identity_pending_review"

    mapping[
        "notes"
    ] = ""

    return mapping[
        MAPPING_REQUIRED_COLUMNS
    ]


def export_geographic_audit(
    dataframe: pd.DataFrame | None = None,
    inventory_path: Path | str = DEFAULT_INVENTORY_PATH,
    mapping_path: Path | str = DEFAULT_MAPPING_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Export the local inventory and the reviewable mapping template.

    The inventory is written to data/processed and should remain
    private. The mapping template is written to data/reference and
    may be versioned after manual review.
    """

    if dataframe is None:
        dataframe = add_quality_controls()

    inventory = create_municipality_inventory(
        dataframe
    )

    mapping = create_mapping_template(
        inventory
    )

    normalized_inventory_path = Path(
        inventory_path
    )

    normalized_mapping_path = Path(
        mapping_path
    )

    normalized_inventory_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized_mapping_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    inventory.to_csv(
        normalized_inventory_path,
        index=False,
        encoding="utf-8-sig",
    )

    mapping.to_csv(
        normalized_mapping_path,
        index=False,
        encoding="utf-8-sig",
    )

    return inventory, mapping


if __name__ == "__main__":
    municipality_inventory, mapping_template = (
        export_geographic_audit()
    )

    print("Geographic audit created successfully.")
    print(
        "Distinct raw municipality categories: "
        f"{len(municipality_inventory):,}"
    )
    print(
        "Companies represented: "
        f"{municipality_inventory['company_count'].sum():,}"
    )
    print(
        "Pending mapping reviews: "
        f"{mapping_template['review_status'].eq('pending').sum():,}"
    )

    print("\nTop 20 raw municipality categories:")
    print(
        municipality_inventory.head(
            20
        ).to_string(
            index=False
        )
    )

    print("\nFiles created:")
    print(DEFAULT_INVENTORY_PATH)
    print(DEFAULT_MAPPING_PATH)