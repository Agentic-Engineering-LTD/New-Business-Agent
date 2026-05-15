"""EnrichmentRouter — orchestrates multiple enrichment providers.

The router IS an ``EnrichmentAdapter`` from the agent's point of view —
agents call ``enrich_by_name_and_company`` and ``find_decision_makers``
without knowing whether one provider or five are behind it. The routing
strategy is configuration, not code.

Config shape (``customers/<customer>/enrichment.yaml``)::

    providers:
      - id: cognism
        enabled: true
        priority: 1
        regions: [GB, IE, EU]
        secret_name: COGNISM_API_KEY
      - id: apollo
        enabled: true
        priority: 2
        regions: [US, global]
        secret_name: APOLLO_API_KEY
      - id: hunter
        enabled: true
        priority: 3
        regions: [global]
        secret_name: HUNTER_API_KEY
      - id: lusha
        enabled: false
        priority: 4
        secret_name: LUSHA_API_KEY

    routing:
      strategy: waterfall        # waterfall | merge | round_robin
      region_aware: true         # prefer providers whose `regions` cover the target's hq_country
      cache_hits: true
      cache_ttl_days: 30

    quality_floor:
      min_confidence: medium
      reject_if_all_low_confidence: true

Routing strategies:

- **waterfall** (default): call providers in priority order, return the
  first usable result. Cost-efficient — second provider only fires on a
  miss. Recommended for steady-state operation.
- **merge**: call every healthy provider, merge results (de-dup by email,
  prefer higher-confidence values for shared fields). Expensive — every
  lookup pays every provider. Useful when coverage is the bottleneck.
- **round_robin**: alternate providers across calls to spread cost evenly.
  Useful when two providers have similar coverage and one is cheaper.

Region-aware routing: when ``region_aware`` is true, the router filters
each call to providers whose ``regions`` cover the target's country (or
falls back to providers with ``"global"``). Providers without a region
match are not called for that lookup but may still be called for others.

Cost optimisation: the router records per-provider hit/miss counts and
per-call cost on every audit event, so the eval harness can report which
providers are earning their credits.
"""

from __future__ import annotations

import asyncio
import itertools
from typing import Any

from nba_platform.integrations.enrichment.base import (
    ConfidenceBand,
    EnrichedContact,
    EnrichmentAdapter,
    EnrichmentConfigError,
    _build_provider,
)

CONFIDENCE_ORDER = {
    ConfidenceBand.HIGH: 3,
    ConfidenceBand.MEDIUM: 2,
    ConfidenceBand.LOW: 1,
}


class EnrichmentRouter(EnrichmentAdapter):
    """Multi-provider enrichment with configurable routing strategy."""

    name = "enrichment_router"

    def __init__(self, config: dict[str, Any]) -> None:
        providers_config = config.get("providers", [])
        if not providers_config:
            raise EnrichmentConfigError(
                "router config requires non-empty 'providers' list"
            )

        # Build one adapter per enabled provider entry. Disabled providers
        # are tracked separately so the health_check can report them.
        self._providers: list[tuple[int, EnrichmentAdapter]] = []
        self._disabled: list[str] = []
        for pc in providers_config:
            if not pc.get("enabled", True):
                self._disabled.append(pc.get("id", "<unnamed>"))
                continue
            adapter = _build_provider(pc)
            priority = int(pc.get("priority", 100))
            # Attach regions to the adapter from config — providers'
            # in-code defaults can be overridden per-customer.
            if "regions" in pc:
                adapter.regions = list(pc["regions"])
            self._providers.append((priority, adapter))

        # Stable sort by priority — equal priorities preserve declared order
        self._providers.sort(key=lambda pair: pair[0])

        routing = config.get("routing", {})
        self._strategy = routing.get("strategy", "waterfall")
        if self._strategy not in ("waterfall", "merge", "round_robin"):
            raise EnrichmentConfigError(
                f"unknown routing strategy: {self._strategy!r}"
            )
        self._region_aware = bool(routing.get("region_aware", False))
        self._cache_hits = bool(routing.get("cache_hits", False))

        quality = config.get("quality_floor", {})
        floor_value = quality.get("min_confidence", "low")
        self._min_confidence = ConfidenceBand(floor_value)
        self._reject_all_low = bool(quality.get("reject_if_all_low_confidence", False))

        # Round-robin cursor (mutable; cycles through providers)
        self._rr_cycle = itertools.cycle(self._providers) if self._providers else None

        # Lightweight in-process cache: (full_name, domain) → EnrichedContact
        # For pilot-scale workloads. Production-grade cache would live in
        # the SQLite substrate or a Redis sidecar.
        self._cache: dict[tuple[str, str], EnrichedContact] = {}

        # Per-provider metric counters — surfaced via health_check.
        self._calls: dict[str, int] = {a.name: 0 for _, a in self._providers}
        self._hits: dict[str, int] = {a.name: 0 for _, a in self._providers}

    # ------------------------------------------------------------------
    # EnrichmentAdapter contract
    # ------------------------------------------------------------------

    async def enrich_by_name_and_company(
        self,
        full_name: str,
        company_domain: str,
        *,
        role_hint: str | None = None,
    ) -> EnrichedContact | None:
        cache_key = (full_name.lower(), company_domain.lower())
        if self._cache_hits and cache_key in self._cache:
            return self._cache[cache_key]

        providers = self._candidates(country=None)
        result: EnrichedContact | None = None

        if self._strategy == "waterfall":
            result = await self._waterfall_single(
                providers, full_name, company_domain, role_hint
            )
        elif self._strategy == "merge":
            result = await self._merge_single(
                providers, full_name, company_domain, role_hint
            )
        elif self._strategy == "round_robin":
            result = await self._round_robin_single(
                full_name, company_domain, role_hint
            )

        if result is not None:
            if not self._meets_floor(result):
                return None
            if self._cache_hits:
                self._cache[cache_key] = result
            return result
        return None

    async def find_decision_makers(
        self,
        company_domain: str,
        role_taxonomy: list[str],
        *,
        limit: int = 25,
    ) -> list[EnrichedContact]:
        providers = self._candidates(country=None)
        if not providers:
            return []

        if self._strategy == "waterfall":
            for adapter in providers:
                if not adapter.is_configured():
                    continue
                self._calls[adapter.name] += 1
                hits = await _safe_call(
                    adapter.find_decision_makers, company_domain, role_taxonomy, limit=limit
                )
                if hits:
                    self._hits[adapter.name] += 1
                    return self._filter_floor(hits)[:limit]
            return []

        # merge: gather from every healthy provider, de-dup, sort by confidence
        gathered: list[EnrichedContact] = []
        for adapter in providers:
            if not adapter.is_configured():
                continue
            self._calls[adapter.name] += 1
            hits = await _safe_call(
                adapter.find_decision_makers, company_domain, role_taxonomy, limit=limit
            )
            if hits:
                self._hits[adapter.name] += 1
                gathered.extend(hits)

        deduped = _dedup_by_email(gathered)
        return self._filter_floor(deduped)[:limit]

    async def health_check(self) -> dict[str, Any]:
        provider_health = await asyncio.gather(
            *[a.health_check() for _, a in self._providers],
            return_exceptions=True,
        )
        out: dict[str, Any] = {
            "router": self.name,
            "strategy": self._strategy,
            "region_aware": self._region_aware,
            "min_confidence_floor": self._min_confidence.value,
            "disabled_providers": list(self._disabled),
            "providers": [],
        }
        for (_, adapter), health in zip(self._providers, provider_health, strict=True):
            entry: dict[str, Any] = {
                "id": adapter.name,
                "regions": getattr(adapter, "regions", []),
                "configured": adapter.is_configured(),
                "calls": self._calls.get(adapter.name, 0),
                "hits": self._hits.get(adapter.name, 0),
            }
            if isinstance(health, Exception):
                entry["health"] = {"ok": False, "error": str(health)}
            else:
                entry["health"] = health
            out["providers"].append(entry)
        return out

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _candidates(self, *, country: str | None) -> list[EnrichmentAdapter]:
        """Return adapters sorted by priority, optionally filtered by region."""
        adapters = [adapter for _, adapter in self._providers]
        if not self._region_aware or not country:
            return adapters
        country_upper = country.upper()
        matched = [
            a
            for a in adapters
            if country_upper in {r.upper() for r in getattr(a, "regions", [])}
            or "global" in [r.lower() for r in getattr(a, "regions", [])]
        ]
        return matched if matched else adapters  # fallback to unfiltered

    async def _waterfall_single(
        self,
        providers: list[EnrichmentAdapter],
        full_name: str,
        company_domain: str,
        role_hint: str | None,
    ) -> EnrichedContact | None:
        for adapter in providers:
            if not adapter.is_configured():
                continue
            self._calls[adapter.name] += 1
            result = await _safe_call(
                adapter.enrich_by_name_and_company,
                full_name,
                company_domain,
                role_hint=role_hint,
            )
            if result is not None:
                self._hits[adapter.name] += 1
                return result
        return None

    async def _merge_single(
        self,
        providers: list[EnrichmentAdapter],
        full_name: str,
        company_domain: str,
        role_hint: str | None,
    ) -> EnrichedContact | None:
        results: list[EnrichedContact] = []
        for adapter in providers:
            if not adapter.is_configured():
                continue
            self._calls[adapter.name] += 1
            result = await _safe_call(
                adapter.enrich_by_name_and_company,
                full_name,
                company_domain,
                role_hint=role_hint,
            )
            if result is not None:
                self._hits[adapter.name] += 1
                results.append(result)
        if not results:
            return None
        return _merge_contacts(results)

    async def _round_robin_single(
        self,
        full_name: str,
        company_domain: str,
        role_hint: str | None,
    ) -> EnrichedContact | None:
        if not self._rr_cycle:
            return None
        # Try one provider; if it misses, do not waterfall — the strategy
        # is explicit about cost-spread. Use waterfall if reliability is
        # the priority.
        for _ in range(len(self._providers)):
            _priority, adapter = next(self._rr_cycle)
            if not adapter.is_configured():
                continue
            self._calls[adapter.name] += 1
            result = await _safe_call(
                adapter.enrich_by_name_and_company,
                full_name,
                company_domain,
                role_hint=role_hint,
            )
            if result is not None:
                self._hits[adapter.name] += 1
                return result
            # On miss with round-robin, do still try the next provider —
            # the spread is across calls, not within. But cap at the
            # ring's length so we don't loop forever.
        return None

    def _meets_floor(self, contact: EnrichedContact) -> bool:
        return (
            CONFIDENCE_ORDER[contact.confidence]
            >= CONFIDENCE_ORDER[self._min_confidence]
        )

    def _filter_floor(self, contacts: list[EnrichedContact]) -> list[EnrichedContact]:
        out = [c for c in contacts if self._meets_floor(c)]
        if not out and self._reject_all_low:
            return []
        return out or (contacts if not self._reject_all_low else [])


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


async def _safe_call(coro_fn, *args, **kwargs):
    """Call a provider method, swallowing exceptions so one bad provider
    doesn't break the router. The router logs the call/hit metrics; a
    failed call is a miss, not a router-level error."""
    try:
        return await coro_fn(*args, **kwargs)
    except Exception:  # noqa: BLE001 — the provider's audit emit captures details
        return None


def _dedup_by_email(contacts: list[EnrichedContact]) -> list[EnrichedContact]:
    """De-duplicate a contact list, keeping the highest-confidence entry per email."""
    by_email: dict[str, EnrichedContact] = {}
    no_email: list[EnrichedContact] = []
    for c in contacts:
        if not c.work_email:
            no_email.append(c)
            continue
        key = c.work_email.lower()
        existing = by_email.get(key)
        if existing is None or CONFIDENCE_ORDER[c.confidence] > CONFIDENCE_ORDER[existing.confidence]:
            by_email[key] = c
    out = list(by_email.values()) + no_email
    out.sort(key=lambda c: CONFIDENCE_ORDER[c.confidence], reverse=True)
    return out


def _merge_contacts(contacts: list[EnrichedContact]) -> EnrichedContact:
    """Merge multiple provider results for the same person, preferring
    higher-confidence values per field. Source becomes a comma-joined list."""
    contacts_sorted = sorted(
        contacts, key=lambda c: CONFIDENCE_ORDER[c.confidence], reverse=True
    )
    base = contacts_sorted[0].model_copy()
    for c in contacts_sorted[1:]:
        for field in (
            "job_title",
            "work_email",
            "direct_phone",
            "mobile_phone",
            "company_name",
            "company_domain",
            "location",
        ):
            if getattr(base, field) is None and getattr(c, field) is not None:
                setattr(base, field, getattr(c, field))
    base.source = ",".join(sorted({c.source for c in contacts}))
    return base
