"""Approval-flow helpers.

The CRM adapter contract carries pending-approval primitives natively (so
that approvals live with the record being written). This module is a thin
convenience layer that agents call instead of building approval payloads
ad hoc.
"""

from __future__ import annotations

from typing import Any

from nba_platform.governance.audit import AuditEvent, log_event
from nba_platform.integrations.crm.base import (
    CrmAdapter,
    PendingApproval,
    RecordKind,
    UpsertResult,
)


async def request_approval(
    crm: CrmAdapter,
    *,
    customer: str,
    agent: str,
    kind: RecordKind,
    proposed_fields: dict[str, Any],
    natural_key: str,
    rationale: str,
) -> UpsertResult:
    """Queue a write for human approval. Logs the request to the audit trail."""
    result = await crm.upsert(
        kind,
        proposed_fields,
        natural_key,
        require_approval=True,
        approval_rationale=rationale,
    )
    log_event(
        AuditEvent(
            customer=customer,
            agent=agent,
            category="approval_requested",
            summary=f"queued approval for {kind.value} {natural_key!r}",
            payload={"approval_id": result.ref.crm_id, "rationale": rationale},
        )
    )
    return result


async def list_pending_for_agent(
    crm: CrmAdapter, *, agent: str, limit: int = 50
) -> list[PendingApproval]:
    return await crm.list_pending_approvals(agent=agent, limit=limit)
