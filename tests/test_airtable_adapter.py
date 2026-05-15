"""Unit tests for the Airtable REST adapter, with mocked HTTPX.

These tests assert two key behaviours:

1. Idempotent upsert — a second write with the same natural key updates
   rather than creates.
2. Approval-gated upsert — when ``require_approval`` is set (either by
   the call site or by the config map), the record lands in the
   Approvals table, not the target table.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nba_platform.integrations.crm.airtable import AirtableAdapter
from nba_platform.integrations.crm.base import RecordKind


@pytest.fixture
def config() -> dict:
    return {
        "base_id": "appTEST123",
        "pat_secret_name": "AIRTABLE_PAT_TEST",
        "tables": {
            "target_organisation": "Targets",
            "stakeholder": "Stakeholders",
            "signal": "Signals",
            "activity": "Activities",
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


@pytest.fixture(autouse=True)
def airtable_pat_env() -> None:
    os.environ["AIRTABLE_PAT_TEST"] = "pat_dummy_value"
    yield
    os.environ.pop("AIRTABLE_PAT_TEST", None)


def _mock_response(status: int = 200, body: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    resp.json.return_value = body or {}
    return resp


@pytest.mark.asyncio
async def test_upsert_creates_when_no_match(config: dict) -> None:
    adapter = AirtableAdapter(config)
    # Mock _client: GET returns no records (no match), POST returns a new id
    adapter._client = MagicMock()
    adapter._client.get = AsyncMock(return_value=_mock_response(200, {"records": []}))
    adapter._client.post = AsyncMock(
        return_value=_mock_response(200, {"id": "recNEW123"})
    )

    result = await adapter.upsert(
        RecordKind.TARGET_ORGANISATION,
        fields={"legal_name": "Acme Retail", "domain": "acme.example"},
        natural_key="acme.example",
    )

    assert result.created is True
    assert result.ref.crm_id == "recNEW123"
    assert result.ref.natural_key == "acme.example"
    adapter._client.post.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_updates_when_match_found(config: dict) -> None:
    adapter = AirtableAdapter(config)
    adapter._client = MagicMock()
    # First GET returns an existing record
    adapter._client.get = AsyncMock(
        return_value=_mock_response(
            200,
            {"records": [{"id": "recEXIST456", "fields": {"domain": "acme.example"}}]},
        )
    )
    adapter._client.patch = AsyncMock(return_value=_mock_response(200, {"id": "recEXIST456"}))

    result = await adapter.upsert(
        RecordKind.TARGET_ORGANISATION,
        fields={"legal_name": "Acme Retail Group", "domain": "acme.example"},
        natural_key="acme.example",
    )

    assert result.created is False
    assert result.ref.crm_id == "recEXIST456"
    assert result.matched_on == "domain"
    adapter._client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_queues_approval_when_required(config: dict) -> None:
    adapter = AirtableAdapter(config)
    adapter._client = MagicMock()
    # Stakeholder require_approval=true in the config, so the path
    # should POST to the Approvals table and never query Stakeholders.
    adapter._client.get = AsyncMock(
        side_effect=AssertionError("must not query the target table when approval gated")
    )
    adapter._client.post = AsyncMock(
        return_value=_mock_response(200, {"id": "recAPPR789"})
    )

    result = await adapter.upsert(
        RecordKind.STAKEHOLDER,
        fields={"work_email": "jane@retailer.example", "full_name": "Jane Doe"},
        natural_key="jane@retailer.example",
        approval_rationale="calibration-window default",
    )

    assert result.matched_on == "approval-queued"
    assert result.ref.crm_id == "recAPPR789"
    # Confirm the POST went to the Approvals endpoint
    called_url = adapter._client.post.call_args.args[0]
    assert "Approvals" in called_url
