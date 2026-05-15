"""Test config loading end-to-end for known customers.

Loads each customer in ``customers/*/`` through ``load_customer_bundle`` and
asserts the bundle validates. Catches missing files, broken YAML, and
vertical-pinning mismatches.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nba_platform.lib.config_loader import ConfigBundle, ConfigError, load_customer_bundle

REPO_ROOT = Path(__file__).resolve().parents[1]


def _customer_dirs() -> list[str]:
    customers_root = REPO_ROOT / "customers"
    return sorted(
        p.name for p in customers_root.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


@pytest.mark.parametrize("customer", _customer_dirs())
def test_customer_bundle_loads_cleanly(customer: str) -> None:
    """Every customer in ``customers/`` should load without raising."""
    bundle = load_customer_bundle(customer)
    assert isinstance(bundle, ConfigBundle)
    assert bundle.customer == customer
    assert bundle.vertical, "customer must declare a vertical"
    assert bundle.vertical_root.is_dir(), (
        f"customer {customer!r} pinned to vertical {bundle.vertical!r} "
        f"but pack directory not found"
    )


def test_powerplay_bundle_has_expected_shape() -> None:
    """Spot-check PowerPlay's bundle against known-expected facts."""
    bundle = load_customer_bundle("powerplay")
    assert bundle.vertical == "brand_licensing_b2b"
    assert bundle.meta.timezone == "Europe/London"
    assert "outreach_drafter" in bundle.agents
    assert bundle.agents["outreach_drafter"].enabled is True
    assert bundle.agents["proactive_recommender"].enabled is False
    # Vertical pack must load — at least one schema, one ranking file
    assert bundle.vertical_pack["schemas"], "vertical pack schemas not loaded"
    assert "target_organisation" in bundle.vertical_pack["schemas"]
    assert "fit_score" in bundle.vertical_pack["ranking"]


def test_missing_customer_raises() -> None:
    with pytest.raises(ConfigError):
        load_customer_bundle("this_customer_does_not_exist")
