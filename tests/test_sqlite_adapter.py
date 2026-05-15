"""Tests for the SQLite CRM adapter — the pilot substrate.

Covers:

- Idempotent upsert (same natural key → update, not duplicate).
- Approval-gated upsert (writes land in approvals queue, not target table).
- Search by field equality.
- list_pending_approvals + resolve_approval round trip.
- Health check returns OK on a fresh database.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nba_platform.integrations.crm.base import RecordKind
from nba_platform.integrations.crm.sqlite import SqliteAdapter


@pytest.fixture
def adapter(tmp_path: Path) -> SqliteAdapter:
    config = {
        "kind": "sqlite",
        "db_path": str(tmp_path / "test.db"),
        "tables": {
            "target_organisation": "targets",
            "stakeholder": "stakeholders",
            "signal": "signals",
            "activity": "activities",
        },
        "natural_keys": {
            "target_organisation": "domain",
            "stakeholder": "work_email",
        },
        "require_approval": {
            "target_organisation": False,
            "stakeholder": True,
            "signal": False,
            "activity": False,
        },
    }
    return SqliteAdapter(config)


async def test_upsert_creates_then_updates(adapter: SqliteAdapter) -> None:
    first = await adapter.upsert(
        RecordKind.TARGET_ORGANISATION,
        fields={"legal_name": "Acme Retail", "domain": "acme.example"},
        natural_key="acme.example",
    )
    assert first.created is True
    crm_id = first.ref.crm_id

    second = await adapter.upsert(
        RecordKind.TARGET_ORGANISATION,
        fields={"legal_name": "Acme Retail Group", "store_count_band": "200-1000"},
        natural_key="acme.example",
    )
    assert second.created is False
    assert second.ref.crm_id == crm_id, "same natural_key must resolve to same row"

    # Verify the update merged fields rather than overwriting.
    hits = await adapter.search(RecordKind.TARGET_ORGANISATION, query={"domain": "acme.example"})
    assert len(hits) == 1
    fields = hits[0].fields
    assert fields["legal_name"] == "Acme Retail Group"
    assert fields["store_count_band"] == "200-1000"


async def test_stakeholder_upsert_queues_approval(adapter: SqliteAdapter) -> None:
    # require_approval=true for stakeholder per the fixture config.
    result = await adapter.upsert(
        RecordKind.STAKEHOLDER,
        fields={"work_email": "jane@retailer.example", "full_name": "Jane Doe"},
        natural_key="jane@retailer.example",
        approval_rationale="calibration default",
    )
    assert result.matched_on == "approval-queued"

    # Should NOT appear in the stakeholders table yet.
    hits = await adapter.search(
        RecordKind.STAKEHOLDER,
        query={"work_email": "jane@retailer.example"},
    )
    assert hits == []

    # Should appear in pending approvals.
    pending = await adapter.list_pending_approvals()
    assert len(pending) == 1
    assert pending[0].record_kind == RecordKind.STAKEHOLDER
    assert pending[0].proposed_fields["full_name"] == "Jane Doe"


async def test_resolve_approval_approve_writes_record(adapter: SqliteAdapter) -> None:
    await adapter.upsert(
        RecordKind.STAKEHOLDER,
        fields={"work_email": "jane@retailer.example", "full_name": "Jane Doe"},
        natural_key="jane@retailer.example",
    )
    pending = await adapter.list_pending_approvals()
    approval_id = pending[0].approval_id

    ref = await adapter.resolve_approval(
        approval_id, decision="approve", actor="jon", comment="ok"
    )
    assert ref is not None
    assert ref.kind == RecordKind.STAKEHOLDER
    assert ref.natural_key == "jane@retailer.example"

    # Record now exists in the live table.
    hits = await adapter.search(
        RecordKind.STAKEHOLDER, query={"work_email": "jane@retailer.example"}
    )
    assert len(hits) == 1


async def test_resolve_approval_reject_writes_nothing(adapter: SqliteAdapter) -> None:
    await adapter.upsert(
        RecordKind.STAKEHOLDER,
        fields={"work_email": "spam@retailer.example", "full_name": "Spam Bot"},
        natural_key="spam@retailer.example",
    )
    pending = await adapter.list_pending_approvals()
    approval_id = pending[0].approval_id

    ref = await adapter.resolve_approval(
        approval_id, decision="reject", actor="jon", comment="not a real person"
    )
    assert ref is None
    hits = await adapter.search(
        RecordKind.STAKEHOLDER, query={"work_email": "spam@retailer.example"}
    )
    assert hits == []


async def test_health_check_reports_ok_for_empty_db(adapter: SqliteAdapter) -> None:
    health = await adapter.health_check()
    assert health["ok"] is True
    assert health["adapter"] == "sqlite"
    assert health["target_count"] == 0


async def test_invalid_decision_raises(adapter: SqliteAdapter) -> None:
    with pytest.raises(ValueError):
        await adapter.resolve_approval("nonexistent", decision="maybe", actor="jon")
