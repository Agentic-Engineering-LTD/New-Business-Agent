"""Contact enrichment adapter interface and implementations.

Multi-provider via the ``EnrichmentRouter``. Customer config declares a
list of providers in priority order; the router picks one (waterfall),
all (merge), or alternates (round_robin) per the customer's strategy.
Provider implementations: Cognism, Apollo, Hunter, Lusha. Adding a new
provider is one file in this package plus a factory entry — no agent or
router changes.
"""

from nba_platform.integrations.enrichment.base import (
    ConfidenceBand,
    EnrichedContact,
    EnrichmentAdapter,
    EnrichmentConfigError,
    build_enrichment_adapter,
)
from nba_platform.integrations.enrichment.router import EnrichmentRouter

__all__ = [
    "ConfidenceBand",
    "EnrichedContact",
    "EnrichmentAdapter",
    "EnrichmentConfigError",
    "EnrichmentRouter",
    "build_enrichment_adapter",
]
