"""Airtable CRM adapter.

Primary use: customers without an incumbent CRM. Airtable acts as the
system of record while the agents prove value; the customer can graduate
to a real CRM (Salesforce / HubSpot / Pipedrive via StackOne MCP) later
as a configuration swap, with no agent-code changes.

This adapter has two paths:

1. **MCP path (preferred):** agents interact with the Airtable MCP server
   (https://support.airtable.com/docs/using-the-airtable-mcp-server) through
   Paperclip's MCP integration. Tools like ``list_records``, ``create_record``,
   ``update_record`` are exposed natively.

2. **REST fallback path (this module):** used for operations that the MCP
   server does not expose efficiently — bulk reads for the Refresh / Watch
   agent, batched writes constrained by Airtable's 10-records-per-request
   limit, and the health-check probe.

The interface (``CrmAdapter``) is the same regardless of which path actually
moves the data. Agents do not know or care which is used.

Config shape (``customers/<customer>/crm.yaml``):

    kind: airtable
    base_id: appXXXXXXXXXXXXXX
    pat_secret_name: AIRTABLE_PAT       # name of secret in Paperclip secrets store
    tables:
      target_organisation: Targets
      stakeholder: Stakeholders
      signal: Signals
      activity: Activities
    natural_keys:
      target_organisation: domain
      stakeholder: email
    require_approval:
      target_organisation: false
      stakeholder: true
      signal: false
      activity: false
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from nba_platform.integrations.crm.base import (
    CrmAdapter,
    CrmConfigError,
    PendingApproval,
    RecordKind,
    RecordRef,
    SearchHit,
    UpsertResult,
)

AIRTABLE_API = "https://api.airtable.com/v0"
APPROVALS_TABLE = "Approvals"  # standard table all customer Airtable bases must include


class AirtableAdapter(CrmAdapter):
    """REST-fallback Airtable implementation of the CRM adapter contract.

    For most operations agents will use the Airtable MCP server through
    Paperclip; this REST adapter is the fallback and the path the eval
    harness uses for deterministic health checks.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.name = "airtable"
        self._config = config

        self._base_id = config.get("base_id")
        if not self._base_id:
            raise CrmConfigError("airtable adapter requires 'base_id'")

        pat_secret_name = config.get("pat_secret_name", "AIRTABLE_PAT")
        self._pat = os.environ.get(pat_secret_name)
        if not self._pat:
            raise CrmConfigError(
                f"airtable PAT not found in env var {pat_secret_name!r}; "
                "Paperclip should inject this from its secrets store"
            )

        self._tables = config.get("tables", {})
        self._natural_keys = config.get("natural_keys", {})
        self._require_approval_map = config.get("require_approval", {})

        # Validate every RecordKind has a table mapping
        for kind in RecordKind:
            if kind.value not in self._tables:
                raise CrmConfigError(
                    f"airtable config missing table mapping for {kind.value!r}"
                )

        self._client = httpx.AsyncClient(
            base_url=f"{AIRTABLE_API}/{self._base_id}",
            headers={"Authorization": f"Bearer {self._pat}"},
            timeout=30.0,
        )

    async def upsert(
        self,
        kind: RecordKind,
        fields: dict[str, Any],
        natural_key: str,
        *,
        require_approval: bool = False,
        approval_rationale: str | None = None,
    ) -> UpsertResult:
        table = self._tables[kind.value]
        nk_field = self._natural_keys.get(kind.value)
        if not nk_field:
            raise CrmConfigError(
                f"natural_keys must define a field for {kind.value!r} to support idempotent upsert"
            )

        effective_approval = require_approval or bool(
            self._require_approval_map.get(kind.value, False)
        )

        if effective_approval:
            return await self._queue_approval(kind, fields, natural_key, approval_rationale)

        # Find existing record by natural key
        existing = await self._find_by_natural_key(table, nk_field, natural_key)

        if existing:
            resp = await self._client.patch(
                f"/{table}/{existing['id']}", json={"fields": fields}
            )
            resp.raise_for_status()
            return UpsertResult(
                ref=RecordRef(kind=kind, crm_id=existing["id"], natural_key=natural_key),
                created=False,
                matched_on=nk_field,
            )

        # Create new
        resp = await self._client.post(f"/{table}", json={"fields": fields})
        resp.raise_for_status()
        created_id = resp.json()["id"]
        return UpsertResult(
            ref=RecordRef(kind=kind, crm_id=created_id, natural_key=natural_key),
            created=True,
            matched_on=None,
        )

    async def attach_note(
        self,
        ref: RecordRef,
        body: str,
        *,
        author_agent: str,
        tags: list[str] | None = None,
    ) -> None:
        activity_table = self._tables[RecordKind.ACTIVITY.value]
        await self._client.post(
            f"/{activity_table}",
            json={
                "fields": {
                    "RelatedRecord": [ref.crm_id],
                    "RelatedKind": ref.kind.value,
                    "Body": body,
                    "AuthorAgent": author_agent,
                    "Tags": ",".join(tags or []),
                    "CreatedAt": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    async def search(
        self,
        kind: RecordKind,
        query: dict[str, Any],
        *,
        limit: int = 25,
    ) -> list[SearchHit]:
        table = self._tables[kind.value]
        formula = self._build_formula(query)
        params: dict[str, Any] = {"maxRecords": limit}
        if formula:
            params["filterByFormula"] = formula

        resp = await self._client.get(f"/{table}", params=params)
        resp.raise_for_status()
        records = resp.json().get("records", [])

        hits: list[SearchHit] = []
        nk_field = self._natural_keys.get(kind.value)
        for r in records:
            fields = r.get("fields", {})
            natural_key = fields.get(nk_field) if nk_field else None
            hits.append(
                SearchHit(
                    ref=RecordRef(kind=kind, crm_id=r["id"], natural_key=natural_key),
                    fields=fields,
                )
            )
        return hits

    async def list_pending_approvals(
        self,
        *,
        agent: str | None = None,
        limit: int = 50,
    ) -> list[PendingApproval]:
        params: dict[str, Any] = {"maxRecords": limit}
        if agent:
            params["filterByFormula"] = f"AND({{Status}}='pending',{{ProposedByAgent}}='{agent}')"
        else:
            params["filterByFormula"] = "{Status}='pending'"

        resp = await self._client.get(f"/{APPROVALS_TABLE}", params=params)
        resp.raise_for_status()
        records = resp.json().get("records", [])

        return [
            PendingApproval(
                approval_id=r["id"],
                record_kind=RecordKind(r["fields"]["RecordKind"]),
                proposed_fields=r["fields"].get("ProposedFields", {}),
                rationale=r["fields"].get("Rationale", ""),
                created_at=datetime.fromisoformat(r["fields"]["CreatedAt"]),
                proposed_by_agent=r["fields"].get("ProposedByAgent", ""),
            )
            for r in records
        ]

    async def resolve_approval(
        self,
        approval_id: str,
        *,
        decision: str,
        actor: str,
        comment: str | None = None,
    ) -> RecordRef | None:
        if decision not in ("approve", "reject"):
            raise ValueError(f"decision must be 'approve' or 'reject', got {decision!r}")

        # Fetch the pending approval
        resp = await self._client.get(f"/{APPROVALS_TABLE}/{approval_id}")
        resp.raise_for_status()
        record = resp.json()
        fields = record["fields"]

        new_status = "approved" if decision == "approve" else "rejected"
        await self._client.patch(
            f"/{APPROVALS_TABLE}/{approval_id}",
            json={
                "fields": {
                    "Status": new_status,
                    "ResolvedBy": actor,
                    "ResolutionComment": comment or "",
                    "ResolvedAt": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        if decision == "reject":
            return None

        # Apply the proposed write
        kind = RecordKind(fields["RecordKind"])
        proposed = fields.get("ProposedFields", {})
        natural_key_value = fields.get("NaturalKey", "")
        result = await self.upsert(kind, proposed, natural_key_value, require_approval=False)
        return result.ref

    async def health_check(self) -> dict[str, Any]:
        try:
            resp = await self._client.get(
                f"/{self._tables[RecordKind.TARGET_ORGANISATION.value]}",
                params={"maxRecords": 1},
            )
            ok = resp.status_code == 200
            return {
                "adapter": self.name,
                "ok": ok,
                "status_code": resp.status_code,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:  # noqa: BLE001 — surface to caller, never crash health
            return {
                "adapter": self.name,
                "ok": False,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_by_natural_key(
        self,
        table: str,
        nk_field: str,
        natural_key: str,
    ) -> dict[str, Any] | None:
        formula = f"{{{nk_field}}}='{self._escape(natural_key)}'"
        resp = await self._client.get(
            f"/{table}",
            params={"filterByFormula": formula, "maxRecords": 1},
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        return records[0] if records else None

    async def _queue_approval(
        self,
        kind: RecordKind,
        fields: dict[str, Any],
        natural_key: str,
        rationale: str | None,
    ) -> UpsertResult:
        resp = await self._client.post(
            f"/{APPROVALS_TABLE}",
            json={
                "fields": {
                    "RecordKind": kind.value,
                    "ProposedFields": fields,
                    "NaturalKey": natural_key,
                    "Rationale": rationale or "",
                    "Status": "pending",
                    "CreatedAt": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        resp.raise_for_status()
        approval_id = resp.json()["id"]
        return UpsertResult(
            ref=RecordRef(kind=kind, crm_id=approval_id, natural_key=natural_key),
            created=False,
            matched_on="approval-queued",
        )

    @staticmethod
    def _build_formula(query: dict[str, Any]) -> str:
        """Naive AND-of-equals translator. Sufficient for our agents' needs;
        complex queries should be served by the MCP path, not this fallback."""
        if not query:
            return ""
        parts: list[str] = []
        for k, v in query.items():
            if isinstance(v, str):
                parts.append(f"{{{k}}}='{AirtableAdapter._escape(v)}'")
            else:
                parts.append(f"{{{k}}}={v}")
        if len(parts) == 1:
            return parts[0]
        return f"AND({','.join(parts)})"

    @staticmethod
    def _escape(s: str) -> str:
        return s.replace("'", "\\'")
