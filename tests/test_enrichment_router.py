"""Tests for the multi-provider EnrichmentRouter.

Uses small in-process fake providers so the routing behaviour is tested
without any network or provider-credential setup. Real provider stubs
(Cognism, Apollo, Hunter, Lusha) are not exercised here — they're
deferred-implementation by design and have their own boot-safe tests
via the contract test below.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from nba_platform.integrations.enrichment.apollo import ApolloAdapter
from nba_platform.integrations.enrichment.base import (
    ConfidenceBand,
    EnrichedContact,
    EnrichmentAdapter,
    EnrichmentConfigError,
    build_enrichment_adapter,
)
from nba_platform.integrations.enrichment.cognism import CognismAdapter
from nba_platform.integrations.enrichment.hunter import HunterAdapter
from nba_platform.integrations.enrichment.lusha import LushaAdapter
from nba_platform.integrations.enrichment.router import EnrichmentRouter


# ----------------------------------------------------------------------
# Fake provider used to make routing behaviour testable
# ----------------------------------------------------------------------


class FakeProvider(EnrichmentAdapter):
    """A test double that returns a canned contact (or None) and tracks calls."""

    def __init__(
        self,
        name: str,
        *,
        regions: list[str] | None = None,
        result: EnrichedContact | None = None,
        people: list[EnrichedContact] | None = None,
        configured: bool = True,
    ) -> None:
        self.name = name
        self.regions = regions or ["global"]
        self._result = result
        self._people = people or []
        self._configured = configured
        self.calls = 0
        self.search_calls = 0

    def is_configured(self) -> bool:
        return self._configured

    async def enrich_by_name_and_company(self, full_name, company_domain, *, role_hint=None):
        self.calls += 1
        return self._result

    async def find_decision_makers(self, company_domain, role_taxonomy, *, limit=25):
        self.search_calls += 1
        return list(self._people)

    async def health_check(self):
        return {"provider": self.name, "configured": self._configured, "ok": True}


def _contact(source: str, *, confidence: ConfidenceBand = ConfidenceBand.HIGH, **fields) -> EnrichedContact:
    defaults: dict[str, Any] = {
        "full_name": "Jane Doe",
        "job_title": "Head of Category",
        "work_email": "jane@retailer.example",
    }
    defaults.update(fields)
    return EnrichedContact(confidence=confidence, source=source, **defaults)


def _router(*, providers: list[FakeProvider], **routing) -> EnrichmentRouter:
    """Build a router around a list of FakeProviders, bypassing the factory."""
    r = EnrichmentRouter.__new__(EnrichmentRouter)
    r.name = "enrichment_router"
    r._providers = [(i + 1, p) for i, p in enumerate(providers)]
    r._disabled = []
    r._strategy = routing.get("strategy", "waterfall")
    r._region_aware = routing.get("region_aware", False)
    r._cache_hits = routing.get("cache_hits", False)
    r._min_confidence = ConfidenceBand(routing.get("min_confidence", "low"))
    r._reject_all_low = routing.get("reject_if_all_low_confidence", False)
    import itertools

    r._rr_cycle = itertools.cycle(r._providers)
    r._cache = {}
    r._calls = {p.name: 0 for p in providers}
    r._hits = {p.name: 0 for p in providers}
    return r


# ----------------------------------------------------------------------
# Waterfall
# ----------------------------------------------------------------------


async def test_waterfall_returns_first_hit_does_not_call_second() -> None:
    p1 = FakeProvider("p1", result=_contact("p1"))
    p2 = FakeProvider("p2", result=_contact("p2"))
    r = _router(providers=[p1, p2], strategy="waterfall")

    out = await r.enrich_by_name_and_company("Jane Doe", "retailer.example")

    assert out is not None
    assert out.source == "p1"
    assert p1.calls == 1
    assert p2.calls == 0, "waterfall must not call provider 2 when provider 1 hits"


async def test_waterfall_falls_through_on_first_miss() -> None:
    p1 = FakeProvider("p1", result=None)
    p2 = FakeProvider("p2", result=_contact("p2"))
    r = _router(providers=[p1, p2], strategy="waterfall")

    out = await r.enrich_by_name_and_company("Jane Doe", "retailer.example")

    assert out is not None
    assert out.source == "p2"
    assert p1.calls == 1
    assert p2.calls == 1


async def test_waterfall_skips_unconfigured_providers() -> None:
    p1 = FakeProvider("p1", configured=False, result=_contact("p1"))
    p2 = FakeProvider("p2", result=_contact("p2"))
    r = _router(providers=[p1, p2], strategy="waterfall")

    out = await r.enrich_by_name_and_company("Jane Doe", "retailer.example")

    assert out.source == "p2"
    assert p1.calls == 0, "unconfigured providers must not be invoked"
    assert p2.calls == 1


# ----------------------------------------------------------------------
# Merge
# ----------------------------------------------------------------------


async def test_merge_strategy_calls_all_providers_and_combines() -> None:
    p1 = FakeProvider("p1", result=_contact("p1", confidence=ConfidenceBand.MEDIUM, work_email=None, direct_phone="+44-20-0001"))
    p2 = FakeProvider("p2", result=_contact("p2", confidence=ConfidenceBand.HIGH, work_email="jane@retailer.example"))
    r = _router(providers=[p1, p2], strategy="merge")

    out = await r.enrich_by_name_and_company("Jane Doe", "retailer.example")

    assert out is not None
    assert p1.calls == 1 and p2.calls == 1
    # Higher-confidence base wins, but p1's phone fills the gap
    assert out.work_email == "jane@retailer.example"
    assert out.direct_phone == "+44-20-0001"
    assert "p1" in out.source and "p2" in out.source


# ----------------------------------------------------------------------
# Quality floor
# ----------------------------------------------------------------------


async def test_quality_floor_rejects_below_threshold() -> None:
    p1 = FakeProvider("p1", result=_contact("p1", confidence=ConfidenceBand.LOW))
    r = _router(providers=[p1], strategy="waterfall", min_confidence="medium")

    out = await r.enrich_by_name_and_company("Jane Doe", "retailer.example")

    assert out is None, "router must reject results below the configured floor"


# ----------------------------------------------------------------------
# find_decision_makers — waterfall returns the first non-empty list
# ----------------------------------------------------------------------


async def test_find_decision_makers_waterfall_first_non_empty_wins() -> None:
    p1 = FakeProvider("p1", people=[])
    p2 = FakeProvider("p2", people=[_contact("p2"), _contact("p2", work_email="other@retailer.example")])
    r = _router(providers=[p1, p2], strategy="waterfall")

    people = await r.find_decision_makers("retailer.example", role_taxonomy=["head_of_category"])

    assert len(people) == 2
    assert all(c.source == "p2" for c in people)
    assert p1.search_calls == 1
    assert p2.search_calls == 1


# ----------------------------------------------------------------------
# Factory + boot-safety
# ----------------------------------------------------------------------


def test_factory_builds_router_from_multi_provider_config() -> None:
    # No env vars set — every provider should construct but be unconfigured.
    for var in ("COGNISM_API_KEY", "APOLLO_API_KEY", "HUNTER_API_KEY", "LUSHA_API_KEY"):
        os.environ.pop(var, None)
    adapter = build_enrichment_adapter(
        {
            "providers": [
                {"id": "cognism", "enabled": True, "priority": 1, "regions": ["GB"]},
                {"id": "apollo", "enabled": True, "priority": 2, "regions": ["US"]},
                {"id": "hunter", "enabled": True, "priority": 3},
                {"id": "lusha", "enabled": False, "priority": 4},
            ],
            "routing": {"strategy": "waterfall"},
        }
    )
    assert isinstance(adapter, EnrichmentRouter)


def test_factory_legacy_single_provider_shape() -> None:
    """Backward-compat — the single-provider kind: cognism shape still works."""
    os.environ.pop("COGNISM_API_KEY", None)
    adapter = build_enrichment_adapter({"kind": "cognism"})
    assert isinstance(adapter, CognismAdapter)
    assert adapter.is_configured() is False, "no env var → boot-safe unconfigured"


def test_factory_rejects_empty_config() -> None:
    with pytest.raises(EnrichmentConfigError):
        build_enrichment_adapter({})


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(EnrichmentConfigError):
        build_enrichment_adapter({"providers": [{"id": "fictional_co", "enabled": True}]})


def test_each_provider_boot_safe_without_env() -> None:
    """All four provider classes must construct without raising when no env var is set."""
    for var in ("COGNISM_API_KEY", "APOLLO_API_KEY", "HUNTER_API_KEY", "LUSHA_API_KEY"):
        os.environ.pop(var, None)
    for cls in (CognismAdapter, ApolloAdapter, HunterAdapter, LushaAdapter):
        adapter = cls({})
        assert adapter.is_configured() is False


async def test_router_health_check_reports_per_provider_state() -> None:
    p1 = FakeProvider("p1", regions=["EU"])
    p2 = FakeProvider("p2", configured=False)
    r = _router(providers=[p1, p2], strategy="waterfall")

    h = await r.health_check()

    assert h["router"] == "enrichment_router"
    assert h["strategy"] == "waterfall"
    provider_entries = {entry["id"]: entry for entry in h["providers"]}
    assert provider_entries["p1"]["configured"] is True
    assert provider_entries["p2"]["configured"] is False
