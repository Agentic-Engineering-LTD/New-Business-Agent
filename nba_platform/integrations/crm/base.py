"""CRM adapter contract.

Every CRM-like data store — Airtable, Bullhorn (via StackOne MCP), HubSpot,
Salesforce, Pipedrive — sits behind this interface. Agents call the interface,
not vendor SDKs. Swapping CRM is a configuration change, never a code change.

This is the central platform abstraction that lets a customer start on
a lightweight substrate (e.g. Airtable) and graduate to a real CRM later
without touching agent code.

All operations are intentionally idempotent — agents may retry safely.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecordKind(str, Enum):
    """The four record shapes every agent in the system knows about.

    Vertical packs define what fields populate each shape; this contract
    only fixes the kinds.
    """

    TARGET_ORGANISATION = "target_organisation"
    STAKEHOLDER = "stakeholder"
    SIGNAL = "signal"
    ACTIVITY = "activity"


class RecordRef(BaseModel):
    """Opaque CRM-side identifier returned by upsert calls."""

    kind: RecordKind
    crm_id: str
    natural_key: str | None = None  # e.g. company domain, stakeholder email


class UpsertResult(BaseModel):
    """Outcome of an upsert operation."""

    ref: RecordRef
    created: bool  # True if newly created, False if matched + updated
    matched_on: str | None = None  # which natural-key strategy matched, for audit


class SearchHit(BaseModel):
    ref: RecordRef
    fields: dict[str, Any]
    score: float | None = None  # match confidence when fuzzy matching


class PendingApproval(BaseModel):
    """A record awaiting human approval before being written to the CRM."""

    approval_id: str
    record_kind: RecordKind
    proposed_fields: dict[str, Any]
    rationale: str
    created_at: datetime
    proposed_by_agent: str


class CrmAdapter(ABC):
    """Agents call this interface. Implementations wrap MCP servers or SDKs.

    Implementations must:
    - Be idempotent on upsert (use the natural_key to de-duplicate).
    - Honour HITL approval gates: when ``require_approval=True`` is configured,
      ``upsert`` returns a pending-approval reference rather than writing.
    - Emit an audit event for every write via the governance layer.
    - Never raise on transient network errors without backoff; surface
      structured errors so callers can record-and-continue.
    """

    name: str  # e.g. "airtable", "stackone-bullhorn"

    @abstractmethod
    async def upsert(
        self,
        kind: RecordKind,
        fields: dict[str, Any],
        natural_key: str,
        *,
        require_approval: bool = False,
        approval_rationale: str | None = None,
    ) -> UpsertResult:
        """Create-or-update a record. Idempotent on ``natural_key``.

        If ``require_approval`` is set, the implementation queues a pending
        approval and returns a ``RecordRef`` whose ``crm_id`` is the approval id;
        the caller treats the record as not-yet-written.
        """

    @abstractmethod
    async def attach_note(
        self,
        ref: RecordRef,
        body: str,
        *,
        author_agent: str,
        tags: list[str] | None = None,
    ) -> None:
        """Attach a note to an existing record. Used for rationales, signals,
        and the audit trail visible to the customer's commercial team."""

    @abstractmethod
    async def search(
        self,
        kind: RecordKind,
        query: dict[str, Any],
        *,
        limit: int = 25,
    ) -> list[SearchHit]:
        """Structured search. Implementations should support at minimum exact
        match on natural-key fields plus a free-text contains query."""

    @abstractmethod
    async def list_pending_approvals(
        self,
        *,
        agent: str | None = None,
        limit: int = 50,
    ) -> list[PendingApproval]:
        """List approvals waiting on a human. Used by Paperclip's approval UI
        and by the Hand-off agent to surface state."""

    @abstractmethod
    async def resolve_approval(
        self,
        approval_id: str,
        *,
        decision: str,  # "approve" | "reject"
        actor: str,
        comment: str | None = None,
    ) -> RecordRef | None:
        """Apply a human decision to a pending approval. Returns the resulting
        ``RecordRef`` on approval, ``None`` on rejection."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Return adapter health: connectivity, auth state, last-write timestamp,
        any vendor-side rate-limit headroom. Used by the eval harness."""


class CrmConfigError(Exception):
    """Raised when CRM config is invalid or insufficient to construct an adapter."""


def build_crm_adapter(config: dict[str, Any]) -> CrmAdapter:
    """Factory — resolves ``config['kind']`` to a concrete adapter.

    The customer's ``crm.yaml`` sets ``kind`` (e.g. ``airtable``, ``stackone``)
    and the relevant credentials. Adding a new CRM means adding a new
    implementation here and a new entry in ``customer config crm.yaml`` — no
    agent code changes.
    """
    kind = config.get("kind")
    if not kind:
        raise CrmConfigError("crm.yaml must specify 'kind'")

    if kind == "sqlite":
        from nba_platform.integrations.crm.sqlite import SqliteAdapter

        return SqliteAdapter(config)
    if kind == "airtable":
        from nba_platform.integrations.crm.airtable import AirtableAdapter

        return AirtableAdapter(config)
    if kind == "stackone":
        from nba_platform.integrations.crm.stackone import StackOneAdapter

        return StackOneAdapter(config)

    raise CrmConfigError(f"unknown CRM kind: {kind!r}")


__all__ = [
    "RecordKind",
    "RecordRef",
    "UpsertResult",
    "SearchHit",
    "PendingApproval",
    "CrmAdapter",
    "CrmConfigError",
    "build_crm_adapter",
]
