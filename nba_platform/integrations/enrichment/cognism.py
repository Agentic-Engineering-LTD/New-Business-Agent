"""Cognism enrichment adapter.

UK-headquartered, GDPR-positioned, strong UK + EU coverage. Cognism was the
portfolio default before the router landed and is typically the first
provider in a UK/EU-focused customer's enrichment.yaml waterfall.

Stub-ish: the interface is fully wired but the actual REST calls remain
deferred until the first customer has procured Cognism credentials. When
credentials land, fill in the two marked methods — no agent code changes.

Provider config shape (inside ``enrichment.yaml`` ``providers`` list)::

    - id: cognism
      enabled: true
      priority: 1
      regions: [GB, IE, EU]
      secret_name: COGNISM_API_KEY
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from nba_platform.integrations.enrichment.base import (
    EnrichedContact,
    EnrichmentAdapter,
)

DEFAULT_REGIONS = ["GB", "IE", "EU"]


class CognismAdapter(EnrichmentAdapter):
    name = "cognism"

    def __init__(self, config: dict[str, Any]) -> None:
        # Provider config arrives via the router with the same field shape
        # as legacy single-provider config — both paths land here.
        self.regions = list(config.get("regions", DEFAULT_REGIONS))
        secret_name = config.get("secret_name") or config.get(
            "api_key_secret_name", "COGNISM_API_KEY"
        )
        self._secret_name = secret_name
        self._api_key = os.environ.get(secret_name)
        # Do NOT raise here. Providers must be boot-safe so the router
        # can include them in a customer's declared list before
        # credentials have been provisioned. ``is_configured()`` and
        # ``health_check()`` carry the state outward.

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def enrich_by_name_and_company(
        self,
        full_name: str,
        company_domain: str,
        *,
        role_hint: str | None = None,
    ) -> EnrichedContact | None:
        # TODO(cognism): wire to Cognism's /search endpoint once
        # credentials are provisioned. Map the response to EnrichedContact.
        # For now, return None so the router's waterfall falls through to
        # the next provider.
        return None

    async def find_decision_makers(
        self,
        company_domain: str,
        role_taxonomy: list[str],
        *,
        limit: int = 25,
    ) -> list[EnrichedContact]:
        # TODO(cognism): wire to Cognism's company-search endpoint.
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
