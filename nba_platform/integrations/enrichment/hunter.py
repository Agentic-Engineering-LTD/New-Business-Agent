"""Hunter.io enrichment adapter.

Hunter's strengths: best-in-class email finder, email verification, and a
free tier that makes it useful for warm-up validation. Where Cognism and
Apollo return rich person records, Hunter is narrower but cheaper and very
accurate on the email-address dimension specifically.

Useful as a verification step in the router waterfall — once a higher-tier
provider returns a proposed email, Hunter's ``email-verifier`` endpoint
confirms deliverability before the Contact Enricher writes the record.

Endpoints we plan to wire:

- ``GET /v2/email-finder`` — find an email from name + domain
- ``GET /v2/email-verifier`` — verify a proposed email
- ``GET /v2/domain-search`` — find people at a company

Provider config shape (inside ``enrichment.yaml`` ``providers`` list)::

    - id: hunter
      enabled: true
      priority: 3
      regions: [global]
      secret_name: HUNTER_API_KEY
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from nba_platform.integrations.enrichment.base import (
    EnrichedContact,
    EnrichmentAdapter,
)

DEFAULT_REGIONS = ["global"]


class HunterAdapter(EnrichmentAdapter):
    name = "hunter"

    def __init__(self, config: dict[str, Any]) -> None:
        self.regions = list(config.get("regions", DEFAULT_REGIONS))
        self._secret_name = config.get("secret_name", "HUNTER_API_KEY")
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
        # TODO(hunter): GET /v2/email-finder?domain=...&first_name=...&last_name=...
        # Hunter's ``confidence`` score (0–100) maps to our ConfidenceBand:
        # ≥90 → high, 50–89 → medium, <50 → low.
        return None

    async def find_decision_makers(
        self,
        company_domain: str,
        role_taxonomy: list[str],
        *,
        limit: int = 25,
    ) -> list[EnrichedContact]:
        # TODO(hunter): GET /v2/domain-search?domain=...&type=personal
        # Filter results by job-title match against the role_taxonomy.
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
