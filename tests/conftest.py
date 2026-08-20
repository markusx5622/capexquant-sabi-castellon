"""Shared pytest configuration for public and private test separation."""

import pytest


PRIVATE_TEST_MODULES = {
    "test_analytics.py",
    "test_clean_data.py",
    "test_financial_features.py",
    "test_geography.py",
    "test_load_data.py",
    "test_quality_control.py",
}


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Mark tests that require the private licensed SABI workbook."""

    private_marker = pytest.mark.private_data(
        reason="Requires the private licensed SABI workbook"
    )

    for item in items:
        if item.path.name in PRIVATE_TEST_MODULES:
            item.add_marker(private_marker)