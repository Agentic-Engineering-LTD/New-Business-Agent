"""Stricter assertions about PowerPlay's config shape.

The platform-level loader test verifies the bundle loads at all; this
file goes further and pins behavioural expectations that the rest of
the platform relies on.
"""

from __future__ import annotations

import yaml
from pathlib import Path

from nba_platform.lib.config_loader import load_customer_bundle

REPO_ROOT = Path(__file__).resolve().parents[1]
POWERPLAY_DIR = REPO_ROOT / "customers" / "powerplay"


def test_powerplay_vertical_pinning() -> None:
    bundle = load_customer_bundle("powerplay")
    assert bundle.vertical == "brand_licensing_b2b"


def test_powerplay_agent_toggles() -> None:
    bundle = load_customer_bundle("powerplay")
    expected_enabled = {
        "target_identifier",
        "org_mapper",
        "contact_enricher",
        "opportunity_assessor",
        "hand_off",
        "refresh_watch",
        "outreach_drafter",
    }
    enabled = {name for name, toggle in bundle.agents.items() if toggle.enabled}
    assert expected_enabled.issubset(enabled), (
        f"expected enabled agents {expected_enabled - enabled} are off"
    )
    assert bundle.agents["proactive_recommender"].enabled is False, (
        "proactive_recommender is interface-only and must be disabled for PowerPlay"
    )


def test_powerplay_crm_is_sqlite_with_full_table_map() -> None:
    bundle = load_customer_bundle("powerplay")
    assert bundle.crm.get("kind") == "sqlite"
    assert bundle.crm.get("db_path"), "crm.yaml must specify db_path for sqlite substrate"
    tables = bundle.crm.get("tables", {})
    for required in ("target_organisation", "stakeholder", "signal", "activity"):
        assert required in tables, f"crm.yaml tables map missing {required!r}"


def test_powerplay_enrichment_is_multi_provider() -> None:
    """PowerPlay uses the EnrichmentRouter (Cognism + Apollo + Hunter; Lusha off)."""
    bundle = load_customer_bundle("powerplay")
    enrichment = bundle.enrichment
    providers = enrichment.get("providers", [])
    assert len(providers) >= 3, "PowerPlay must declare at least three enrichment providers"
    provider_ids = {p["id"] for p in providers}
    assert {"cognism", "apollo", "hunter"}.issubset(provider_ids), (
        f"expected cognism + apollo + hunter in providers, got {provider_ids}"
    )
    strategy = enrichment.get("routing", {}).get("strategy")
    assert strategy == "waterfall", "PowerPlay should default to waterfall for cost efficiency"


def test_powerplay_outputs_specify_xlsx_csv() -> None:
    """Pilot deliverable shape — XLSX + CSV snapshots, not a SaaS dashboard."""
    bundle = load_customer_bundle("powerplay")
    assert bundle.outputs.get("output_dir"), "outputs.yaml must specify output_dir"
    snapshot = bundle.outputs.get("pipeline_snapshot", {})
    assert snapshot.get("enabled") is True, "pipeline snapshot must be enabled"
    formats = snapshot.get("format", [])
    assert "xlsx" in formats and "csv" in formats, (
        "pipeline snapshot must produce both xlsx and csv formats"
    )


def test_powerplay_personas_subset_is_valid() -> None:
    """The persona subset must be drawn from the vertical's role taxonomy."""
    bundle = load_customer_bundle("powerplay")
    vertical_stakeholder = bundle.vertical_pack["schemas"]["stakeholder"]
    allowed = set(vertical_stakeholder["fields"]["role_band"]["values"])
    chosen = set(bundle.personas.get("role_bands_in_scope", []))
    assert chosen, "personas.yaml must declare role_bands_in_scope"
    assert chosen.issubset(allowed), (
        f"personas.yaml references role_bands outside the vertical taxonomy: "
        f"{chosen - allowed}"
    )


def test_powerplay_outreach_disabled_in_calibration_for_personal_contact() -> None:
    bundle = load_customer_bundle("powerplay")
    assert bundle.thresholds["enrichment"]["allow_personal_contact"] is False


def test_powerplay_targets_geographies_non_empty() -> None:
    bundle = load_customer_bundle("powerplay")
    geos = bundle.targets.get("geographies_in_scope", [])
    assert isinstance(geos, list) and len(geos) > 0, (
        "PowerPlay must declare at least one geography in scope"
    )


def test_powerplay_brand_has_opt_out_footer() -> None:
    """The Outreach Drafter relies on this."""
    bundle = load_customer_bundle("powerplay")
    footer = bundle.brand.get("opt_out_footer")
    assert footer and len(footer.strip()) > 0, "brand.yaml must define opt_out_footer"


def test_powerplay_required_files_all_exist() -> None:
    """Spot-check the eight expected customer files are present on disk."""
    required = [
        "company.yaml",
        "targets.yaml",
        "brand.yaml",
        "personas.yaml",
        "thresholds.yaml",
        "crm.yaml",
        "enrichment.yaml",
        "outputs.yaml",
        "agents.yaml",
        "README.md",
    ]
    for filename in required:
        path = POWERPLAY_DIR / filename
        assert path.exists(), f"customers/powerplay/{filename} is missing"


def test_powerplay_yaml_files_parse() -> None:
    """Belt-and-braces: every YAML in customers/powerplay/ parses."""
    for path in POWERPLAY_DIR.glob("*.yaml"):
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None, f"{path.name} parsed as None"
