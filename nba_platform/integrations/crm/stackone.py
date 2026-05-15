"""StackOne CRM adapter.

Stub. Activated when a customer graduates to a real CRM — Bullhorn (Eligo's
path), Salesforce, HubSpot, Pipedrive, Attio, etc. StackOne provides one
unified MCP interface over 270+ connectors; the customer's ``crm.yaml`` picks
which one. Same ``CrmAdapter`` contract, same agent code.

This file intentionally raises ``NotImplementedError`` everywhere until the
first customer needs it. Filling it in is a platform-layer change that
benefits every future customer in every vertical.
"""

from __future__ import annotations

from typing import Any

from nba_platform.integrations.crm.base import (
    CrmAdapter,
    CrmConfigError,
    PendingApproval,
    RecordKind,
    RecordRef,
    SearchHit,
    UpsertResult,
)


class StackOneAdapter(CrmAdapter):
    """Not yet implemented — first customer needing it triggers the build."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.name = "stackone"
        self._connector = config.get("connector")  # e.g. "bullhorn", "salesforce"
        if not self._connector:
            raise CrmConfigError("stackone adapter requires 'connector'")
        self._config = config

    async def upsert(  # noqa: D401
        self,
        kind: RecordKind,
        fields: dict[str, Any],
        natural_key: str,
        *,
        require_approval: bool = False,
        approval_rationale: str | None = None,
    ) -> UpsertResult:
        raise NotImplementedError(
            "StackOne adapter not yet implemented — see platform/integrations/crm/stackone.py"
        )

    async def attach_note(
        self,
        ref: RecordRef,
        body: str,
        *,
        author_agent: str,
        tags: list[str] | None = None,
    ) -> None:
        raise NotImplementedError

    async def search(
        self,
        kind: RecordKind,
        query: dict[str, Any],
        *,
        limit: int = 25,
    ) -> list[SearchHit]:
        raise NotImplementedError

    async def list_pending_approvals(
        self,
        *,
        agent: str | None = None,
        limit: int = 50,
    ) -> list[PendingApproval]:
        raise NotImplementedError

    async def resolve_approval(
        self,
        approval_id: str,
        *,
        decision: str,
        actor: str,
        comment: str | None = None,
    ) -> RecordRef | None:
        raise NotImplementedError

    async def health_check(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "ok": False,
            "error": "not implemented",
        }
