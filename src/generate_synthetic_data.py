"""Generate a reproducible and fully synthetic public company dataset."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "sample"
    / "companies_synthetic.csv"
)

DEFAULT_METADATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "sample"
    / "companies_synthetic_metadata.json"
)

RANDOM_SEED = 20260820
COMPANY_COUNT = 120

STANDARD_COLUMNS = [
    "record_order",
    "company_name",
    "website",
    "municipality",
    "employees_latest",
    "operating_revenue_latest_k_eur",
    "operating_revenue_previous_k_eur",
    "ebitda_latest_k_eur",
    "ebitda_previous_k_eur",
    "shareholder_name",
]

MUNICIPALITIES = [
    "CASTELLO DE LA PLANA",
    "VILA-REAL",
    "ONDA",
    "ALMASSORA",
    "L'ALCORA",
    "NULES",
    "BENICARLO",
    "VINAROS",
]

COMPANY_PREFIXES = [
    "NORTHSTAR",
    "BLUEHAVEN",
    "SOLARIDGE",
    "IRONVALE",
    "RIVERSTONE",
    "NOVACORE",
    "GREENFORGE",
    "CLEARPATH",
    "PRIMEFIELD",
    "VECTORLINE",
    "BRIGHTMILL",
    "AURORA",
]

COMPANY_SUFFIXES = [
    "INDUSTRIES",
    "SYSTEMS",
    "MATERIALS",
    "SOLUTIONS",
    "TECHNOLOGIES",
    "OPERATIONS",
    "MANUFACTURING",
    "LOGISTICS",
]


def build_company_names(
    company_count: int,
) -> list[str]:
    """Create unique and unambiguously fictional company names."""

    company_names = []

    for index in range(1, company_count + 1):
        prefix = COMPANY_PREFIXES[
            (index - 1) % len(COMPANY_PREFIXES)
        ]

        suffix = COMPANY_SUFFIXES[
            (
                (index - 1)
                // len(COMPANY_PREFIXES)
            )
            % len(COMPANY_SUFFIXES)
        ]

        company_name = (
            f"SYNTHETIC {prefix} "
            f"{suffix} {index:03d} SL"
        )

        if index % 25 == 0:
            company_name += " (EXTINGUIDA)"
        elif index % 33 == 0:
            company_name += " (EN LIQUIDACION)"
        elif index == company_count:
            company_name += " (EN DISOLUCION)"

        company_names.append(company_name)

    return company_names


def generate_synthetic_companies(
    company_count: int = COMPANY_COUNT,
    random_seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generate fictional company-level financial observations."""

    if (
        not isinstance(company_count, int)
        or isinstance(company_count, bool)
        or company_count <= 0
    ):
        raise ValueError(
            "company_count must be a positive integer."
        )

    if (
        not isinstance(random_seed, int)
        or isinstance(random_seed, bool)
    ):
        raise ValueError(
            "random_seed must be an integer."
        )

    rng = np.random.default_rng(random_seed)

    employee_count = np.clip(
        np.rint(
            rng.lognormal(
                mean=3.0,
                sigma=0.85,
                size=company_count,
            )
        ),
        5,
        600,
    ).astype(int)

    revenue_per_employee = rng.lognormal(
        mean=np.log(115.0),
        sigma=0.45,
        size=company_count,
    )

    revenue_previous = (
        employee_count
        * revenue_per_employee
    )

    revenue_growth = np.clip(
        rng.normal(
            loc=0.045,
            scale=0.16,
            size=company_count,
        ),
        -0.55,
        0.70,
    )

    revenue_latest = (
        revenue_previous
        * (1 + revenue_growth)
    )

    previous_margin = np.clip(
        rng.normal(
            loc=0.09,
            scale=0.10,
            size=company_count,
        ),
        -0.30,
        0.40,
    )

    latest_margin = np.clip(
        previous_margin
        + rng.normal(
            loc=0.005,
            scale=0.06,
            size=company_count,
        ),
        -0.40,
        0.45,
    )

    ebitda_previous = (
        revenue_previous
        * previous_margin
    )

    ebitda_latest = (
        revenue_latest
        * latest_margin
    )

    municipalities = rng.choice(
        MUNICIPALITIES,
        size=company_count,
        replace=True,
    )

    website_available = (
        rng.random(company_count) < 0.78
    )

    shareholder_available = (
        rng.random(company_count) < 0.68
    )

    websites = [
        (
            f"https://synthetic-company-{index:03d}.example"
            if is_available
            else pd.NA
        )
        for index, is_available in enumerate(
            website_available,
            start=1,
        )
    ]

    shareholders = [
        (
            f"SYNTHETIC HOLDING {(index % 12) + 1:02d} SL"
            if is_available
            else pd.NA
        )
        for index, is_available in enumerate(
            shareholder_available,
            start=1,
        )
    ]

    dataframe = pd.DataFrame(
        {
            "record_order": range(
                1,
                company_count + 1,
            ),
            "company_name": build_company_names(
                company_count
            ),
            "website": websites,
            "municipality": municipalities,
            "employees_latest": employee_count,
            "operating_revenue_latest_k_eur": (
                revenue_latest
            ),
            "operating_revenue_previous_k_eur": (
                revenue_previous
            ),
            "ebitda_latest_k_eur": (
                ebitda_latest
            ),
            "ebitda_previous_k_eur": (
                ebitda_previous
            ),
            "shareholder_name": shareholders,
        }
    )

    missing_latest_revenue_count = max(
        1,
        company_count // 40,
    )

    missing_previous_revenue_count = max(
        1,
        company_count // 30,
    )

    missing_latest_ebitda_count = max(
        1,
        company_count // 50,
    )

    dataframe.loc[
        dataframe.index[
            -missing_latest_revenue_count:
        ],
        "operating_revenue_latest_k_eur",
    ] = np.nan

    dataframe.loc[
        dataframe.index[
            -missing_previous_revenue_count:
        ],
        "operating_revenue_previous_k_eur",
    ] = np.nan

    dataframe.loc[
        dataframe.index[
            -missing_latest_ebitda_count:
        ],
        "ebitda_latest_k_eur",
    ] = np.nan

    numeric_columns = [
        "operating_revenue_latest_k_eur",
        "operating_revenue_previous_k_eur",
        "ebitda_latest_k_eur",
        "ebitda_previous_k_eur",
    ]

    dataframe[
        numeric_columns
    ] = dataframe[
        numeric_columns
    ].round(6)

    return dataframe[
        STANDARD_COLUMNS
    ]


def calculate_file_sha256(
    file_path: Path,
) -> str:
    """Calculate a SHA-256 checksum for an exported file."""

    digest = hashlib.sha256()

    with file_path.open("rb") as file_handle:
        for block in iter(
            lambda: file_handle.read(65_536),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def export_synthetic_dataset(
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
    metadata_path: Path | str = DEFAULT_METADATA_PATH,
    company_count: int = COMPANY_COUNT,
    random_seed: int = RANDOM_SEED,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Generate and export the synthetic dataset and metadata."""

    normalized_output_path = Path(output_path)
    normalized_metadata_path = Path(
        metadata_path
    )

    normalized_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized_metadata_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = generate_synthetic_companies(
        company_count=company_count,
        random_seed=random_seed,
    )

    dataframe.to_csv(
        normalized_output_path,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
        float_format="%.6f",
    )

    checksum = calculate_file_sha256(
        normalized_output_path
    )

    metadata = {
        "dataset_name": (
            "CapexQuant synthetic companies"
        ),
        "dataset_type": "fully_synthetic",
        "contains_sabi_data": False,
        "contains_real_companies": False,
        "contains_personal_data": False,
        "generation_method": (
            "Deterministic statistical simulation"
        ),
        "random_seed": random_seed,
        "company_count": len(dataframe),
        "column_count": len(
            dataframe.columns
        ),
        "sha256": checksum,
        "currency_unit": "thousand_eur",
        "intended_use": (
            "Public demonstration, testing "
            "and recruitment review"
        ),
        "limitations": [
            (
                "Not representative of the "
                "Castellón economy."
            ),
            (
                "Not suitable for credit or "
                "investment decisions."
            ),
            (
                "Does not reproduce confidential "
                "company records."
            ),
            (
                "Financial relationships are "
                "simplified."
            ),
        ],
    }

    normalized_metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return dataframe, metadata


if __name__ == "__main__":
    synthetic_dataframe, synthetic_metadata = (
        export_synthetic_dataset()
    )

    print(
        "Synthetic public dataset "
        "created successfully."
    )
    print(
        f"Rows: {len(synthetic_dataframe):,}"
    )
    print(
        "Columns: "
        f"{len(synthetic_dataframe.columns)}"
    )
    print(
        "Random seed: "
        f"{synthetic_metadata['random_seed']}"
    )
    print(
        "SHA-256: "
        f"{synthetic_metadata['sha256']}"
    )

    print("\nFiles created:")
    print(DEFAULT_OUTPUT_PATH)
    print(DEFAULT_METADATA_PATH)