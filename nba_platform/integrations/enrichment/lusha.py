"""Lusha enrichment adapter.

Lusha's strengths: direct-dial / mobile phone numbers (where lawfully
licensed), strong on senior decision-maker contact details. Useful as a
late-stage provider in the waterfall when email-only enrichment isn't
enough and the customer's outreach pattern includes phone touch.

Note on personal data: Lusha returns mobile numbers for some contacts.
The platform's enrichment.yaml ``allow_personal_contact`` flag and the
vertical pack's compliance notes govern whether those numbers are
written to the stakeholder record. The router enforces the floor; the
provider returns what's available.

Endpoints we plan to wire:

- ``POST /v2/person`` — person enrichment by name + company
- ``POST /v2/prospecting/contact/search`` — find decision-makers

Provider config shape (inside ``enrichment.yaml`` ``providers`` list)::

    - id: lusha
      enabled: true
      priority: 4
      regions: [global]
      secret_name: LUSHA_API_KEY
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


class LushaAdapter(EnrichmentAdapter):
    name = "lusha"

    def __init__(self, config: dict[str, Any]) -> None:
        self.regions = list(config.get("regions", DEFAULT_REGIONS))
        self._secret_name = config.get("secret_name", "LUSHA_API_KEY")
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
        # TODO(lusha): POST /v2/person with name + company. Confidence
        # in Lusha's response (``confidence`` field per email/phone)
        # maps to our ConfidenceBand. Mobile fields populate
        # EnrichedContact.mobile_phone only when the customer's config
        # allows it; otherwise the field stays None.
        return None

    async def find_decision_makers(
        self,
        company_domain: str,
        role_taxonomy: list[str],
        *,
        limit: int = 25,
    ) -> list[EnrichedContact]:
        # TODO(lusha): POST /v2/prospecting/contact/search with
        # job_titles + company filter.
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
