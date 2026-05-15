"""Contact-enrichment adapter contract.

Used by the Contact Enricher agent to verify and enrich named decision-makers
once the Org Mapper has identified them. The platform supports many
providers behind one interface — Cognism, Apollo, Hunter, Lusha at first;
ZoomInfo, Clay, and others as customers need them. A customer's config
declares which providers are enabled and in what priority; the
``EnrichmentRouter`` (in ``router.py``) orchestrates them.

This file defines:

- ``EnrichedContact`` — the unified result type.
- ``ConfidenceBand`` — high / medium / low.
- ``EnrichmentAdapter`` — the abstract base every provider implements.
- ``EnrichmentConfigError`` — raised when config is invalid.
- ``build_enrichment_adapter`` — the factory. Returns either a single
  provider adapter (legacy config shape) or an ``EnrichmentRouter``
  wrapping multiple providers (current shape).

Provider implementations should NOT raise at construction time on missing
credentials — they should mark themselves unhealthy and let
``health_check`` report the state. This keeps the router boot-safe
across partial provider availability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ConfidenceBand(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnrichedContact(BaseModel):
    full_name: str
    job_title: str | None = None
    work_email: str | None = None
    direct_phone: str | None = None
    mobile_phone: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    location: str | None = None
    confidence: ConfidenceBand
    source: str
    raw_provider_id: str | None = None


class EnrichmentAdapter(ABC):
    """Each provider implementation subclasses this.

    The ``name`` attribute is the provider identifier ("cognism", "apollo",
    etc.) — used in audit events and as the ``source`` field on returned
    contacts. ``regions`` is a list of ISO-3166 alpha-2 codes plus optional
    macro-regions ("EU", "global") declaring where the provider has
    meaningful coverage; the router uses this for region-aware routing.
    """

    name: str
    regions: list[str]

    @abstractmethod
    async def enrich_by_name_and_company(
        self,
        full_name: str,
        company_domain: str,
        *,
        role_hint: str | None = None,
    ) -> EnrichedContact | None: ...

    @abstractmethod
    async def find_decision_makers(
        self,
        company_domain: str,
        role_taxonomy: list[str],
        *,
        limit: int = 25,
    ) -> list[EnrichedContact]:
        """Find named decision-makers at a target organisation matching the
        vertical pack's role taxonomy. The taxonomy is industry-specific
        — this adapter takes it as input and treats it opaquely."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]: ...

    def is_configured(self) -> bool:
        """True if the provider has the credentials/config it needs.

        The router uses this to skip providers that have been declared
        but not yet provisioned (e.g. customer has Apollo in their YAML
        but the credentials are still in procurement). Default
        implementation returns ``True``; providers override.
        """
        return True


class EnrichmentConfigError(Exception):
    pass


def build_enrichment_adapter(config: dict[str, Any]) -> EnrichmentAdapter:
    """Factory — returns a single provider or an EnrichmentRouter.

    Two config shapes are accepted:

    - **Multi-provider (current).** ``config`` contains a ``providers``
      list. Each entry has ``id``, ``priority``, optional ``regions``,
      and a ``secret_name``. The factory builds each provider and wraps
      them in an ``EnrichmentRouter`` driven by the same config's
      ``routing`` block.

    - **Single-provider (legacy).** ``config`` has a top-level ``kind``
      field. Resolved directly to one provider adapter. Retained for
      backward compatibility — existing customers who configured a single
      provider before the router landed don't have to migrate.
    """
    if "providers" in config:
        from nba_platform.integrations.enrichment.router import EnrichmentRouter

        return EnrichmentRouter(config)

    kind = config.get("kind")
    if not kind:
        raise EnrichmentConfigError(
            "enrichment config must specify either 'providers' (multi-provider) "
            "or 'kind' (single-provider legacy shape)"
        )
    return _build_provider({"id": kind, **config})


def _build_provider(provider_config: dict[str, Any]) -> EnrichmentAdapter:
    """Resolve one provider id → one concrete EnrichmentAdapter."""
    provider_id = provider_config.get("id") or provider_config.get("kind")
    if not provider_id:
        raise EnrichmentConfigError("provider config requires 'id'")

    if provider_id == "cognism":
        from nba_platform.integrations.enrichment.cognism import CognismAdapter

        return CognismAdapter(provider_config)
    if provider_id == "apollo":
        from nba_platform.integrations.enrichment.apollo import ApolloAdapter

        return ApolloAdapter(provider_config)
    if provider_id == "hunter":
        from nba_platform.integrations.enrichment.hunter import HunterAdapter

        return HunterAdapter(provider_config)
    if provider_id == "lusha":
        from nba_platform.integrations.enrichment.lusha import LushaAdapter

        return LushaAdapter(provider_config)

    raise EnrichmentConfigError(f"unknown enrichment provider id: {provider_id!r}")


__all__ = [
    "ConfidenceBand",
    "EnrichedContact",
    "EnrichmentAdapter",
    "EnrichmentConfigError",
    "build_enrichment_adapter",
    "_build_provider",
]
