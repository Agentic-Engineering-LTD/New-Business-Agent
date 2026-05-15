"""Structured audit events.

Every agent action — CRM write, outreach approval, LLM cost incurred,
output generated — emits an ``AuditEvent``. In production these are emitted
into Paperclip's immutable ticket-comment trail; in tests / local dev they
go to a structured logger.

Audit is non-negotiable. There is no "skip audit" code path. If a write
happens, an event is emitted.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

EventCategory = Literal[
    "crm_write",
    "crm_search",
    "llm_completion",
    "enrichment_lookup",
    "approval_requested",
    "approval_resolved",
    "output_generated",
    "agent_invocation",
    "config_load",
    "error",
]


class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    customer: str
    agent: str
    category: EventCategory
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    cost_usd: float | None = None
    ticket_id: str | None = None  # Paperclip ticket this event belongs to


_logger = structlog.get_logger("nba.audit")


def log_event(event: AuditEvent) -> None:
    """Emit an audit event.

    In production this should be wired to Paperclip's ticket API (the
    ``@paperclipai/mcp-server`` exposes the relevant operations). Here we
    emit structured logs which the deployment ships to Paperclip via the
    Paperclip agent harness.
    """
    _logger.info(
        event.category,
        timestamp=event.timestamp.isoformat(),
        customer=event.customer,
        agent=event.agent,
        summary=event.summary,
        cost_usd=event.cost_usd,
        ticket_id=event.ticket_id,
        **event.payload,
    )

    # Belt-and-braces local audit log for early pilot. Paperclip's ticket
    # trail is the canonical store; this file is for sanity-checking during
    # the first weeks of a deployment.
    audit_path = os.environ.get("NBA_AUDIT_LOG_PATH")
    if audit_path:
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump(mode="json"), default=str) + "\n")
