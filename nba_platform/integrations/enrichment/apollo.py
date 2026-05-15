"""Apollo.io enrichment adapter.

Apollo's strengths: very large person database, strong US coverage, mid-market
outbound focus. Useful as a fallback to Cognism when the target is US-based or
when the target organisation falls outside Cognism's curated UK/EU coverage.

Endpoints we plan to wire:

- ``POST /v1/people/match`` — person enrichment by name + domain
- ``POST /v1/mixed_people/search`` — find decision-makers at a company

Credit model: Apollo charges per-credit; person-enrichment typically 1 credit,
search results 1 credit per row. The router's per-provider call counters
feed straight into the eval harness for credit-usage attribution.

Provider config shape (inside ``enrichment.yaml`` ``providers`` list)::

    - id: apollo
      enabled: true
      priority: 2
      regions: [US, global]
      secret_name: APOLLO_API_KEY
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from nba_platform.integrations.enrichment.base import (
    EnrichedContact,
    EnrichmentAdapter,
)

DEFAULT_REGIONS = ["US", "CA", "global"]


class ApolloAdapter(EnrichmentAdapter):
    name = "apollo"

    def __init__(self, config: dict[str, Any]) -> None:
        self.regions = list(config.get("regions", DEFAULT_REGIONS))
        self._secret_name = config.get("secret_name", "APOLLO_API_KEY")
        self._api_key = os.environ.get(self._secret_name)

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def enrich_by_name_and_company(
        self,
        full_name: str,
        company_domain: str,
        *,
        role_hint: str | None = None,
    ) -> EnrichedContact | None:
        # TODO(apollo): POST /v1/people/match with x-api-key header.
        # Map response → EnrichedContact. Apollo's ``email_status`` field
        # informs confidence (verified=high, guessed=medium, etc.).
        return None

    async def find_decision_makers(
        self,
        company_domain: str,
        role_taxonomy: list[str],
        *,
        limit: int = 25,
    ) -> list[EnrichedContact]:
        # TODO(apollo): POST /v1/mixed_people/search with person_titles
        # constructed from the role_taxonomy.
        return []

    async def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": self.is_configured(),
            "regions": list(self.regions),
            "secret_name": self._secret_name,
            "implementation": "stub_pending_credentials",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
