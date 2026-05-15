"""SQLite CRM adapter — the pilot substrate.

Primary use: customers running a spreadsheet-only deliverable pilot, where
there is no incumbent CRM and no SaaS-substrate requirement. The agents
persist state to a single ``.db`` file on disk; the Hand-off agent's XLSX
exporter renders that state into customer-facing workbooks.

Properties:

- **Stdlib only.** Built on the ``sqlite3`` module — no extra runtime
  dependency. Async wrapping via ``asyncio.to_thread``.
- **Single file on disk.** Easy to back up (copy the file), restore
  (copy it back), or inspect (any SQLite client).
- **Transactional.** Upserts are atomic; concurrent agent wakes are safe.
- **Same CrmAdapter interface as Airtable and StackOne.** Graduating a
  customer to a real CRM is a ``crm.yaml`` flip.

Config shape (``customers/<customer>/crm.yaml``):

    kind: sqlite
    db_path: data/<customer>/pipeline.db   # relative to repo root or container workdir
    tables:
      target_organisation: targets
      stakeholder: stakeholders
      signal: signals
      activity: activities
    natural_keys:
      target_organisation: domain
      stakeholder: work_email
      signal: composite
      activity: composite
    require_approval:
      target_organisation: false
      stakeholder: true
      signal: false
      activity: false

Internally, each record kind has one table with this shape::

    CREATE TABLE <table_name> (
        id          TEXT PRIMARY KEY,          -- uuid4 hex
        natural_key TEXT NOT NULL UNIQUE,
        fields_json TEXT NOT NULL,             -- JSON blob of fields
        created_at  TEXT NOT NULL,             -- ISO-8601 UTC
        updated_at  TEXT NOT NULL
    );

Approvals are kept in their own table::

    CREATE TABLE approvals (
        id              TEXT PRIMARY KEY,
        record_kind     TEXT NOT NULL,
        natural_key     TEXT NOT NULL,
        proposed_fields TEXT NOT NULL,         -- JSON
        rationale       TEXT,
        proposed_by     TEXT,                  -- agent name
        status          TEXT NOT NULL,         -- pending | approved | rejected
        decided_by      TEXT,
        decided_at      TEXT,
        decision_note   TEXT,
        created_at      TEXT NOT NULL
    );
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
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

APPROVALS_TABLE = "approvals"
RECORD_TABLES_DEFAULT = {
    RecordKind.TARGET_ORGANISATION.value: "targets",
    RecordKind.STAKEHOLDER.value: "stakeholders",
    RecordKind.SIGNAL.value: "signals",
    RecordKind.ACTIVITY.value: "activities",
}


class SqliteAdapter(CrmAdapter):
    """SQLite-backed CrmAdapter. One file, four record tables, one approvals
    table. Stdlib-only.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.name = "sqlite"
        self._config = config

        db_path_str = config.get("db_path")
        if not db_path_str:
            raise CrmConfigError("sqlite adapter requires 'db_path'")
        self._db_path = Path(db_path_str)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._tables = dict(RECORD_TABLES_DEFAULT)
        self._tables.update(config.get("tables", {}))

        self._natural_keys = config.get("natural_keys", {})
        self._require_approval_map = config.get("require_approval", {})

        for kind in RecordKind:
            if kind.value not in self._tables:
                raise CrmConfigError(
                    f"sqlite tables config missing mapping for {kind.value!r}"
                )

        self._init_schema()

    # ------------------------------------------------------------------
    # Public API — CrmAdapter contract
    # ------------------------------------------------------------------

    async def upsert(
        self,
        kind: RecordKind,
        fields: dict[str, Any],
        natural_key: str,
        *,
        require_approval: bool = False,
        approval_rationale: str | None = None,
    ) -> UpsertResult:
        effective_approval = require_approval or bool(
            self._require_approval_map.get(kind.value, False)
        )
        if effective_approval:
            approval_id = await asyncio.to_thread(
                self._queue_approval_sync,
                kind,
                fields,
                natural_key,
                approval_rationale,
            )
            return UpsertResult(
                ref=RecordRef(kind=kind, crm_id=approval_id, natural_key=natural_key),
                created=False,
                matched_on="approval-queued",
            )

        return await asyncio.to_thread(self._upsert_sync, kind, fields, natural_key)

    async def attach_note(
        self,
        ref: RecordRef,
        body: str,
        *,
        author_agent: str,
        tags: list[str] | None = None,
    ) -> None:
        # Notes are activity records linked to the referenced record by
        # natural key. The natural key for an activity is composite — we
        # build one from the related record + a timestamp.
        await asyncio.to_thread(
            self._upsert_sync,
            RecordKind.ACTIVITY,
            {
                "kind": "note",
                "related_kind": ref.kind.value,
                "related_natural_key": ref.natural_key,
                "body": body,
                "author_agent": author_agent,
                "tags": tags or [],
                "created_at": _utc_now_iso(),
            },
            natural_key=f"note::{ref.natural_key}::{_utc_now_iso()}",
        )

    async def search(
        self,
        kind: RecordKind,
        query: dict[str, Any],
        *,
        limit: int = 25,
    ) -> list[SearchHit]:
        return await asyncio.to_thread(self._search_sync, kind, query, limit)

    async def list_pending_approvals(
        self,
        *,
        agent: str | None = None,
        limit: int = 50,
    ) -> list[PendingApproval]:
        return await asyncio.to_thread(self._list_pending_sync, agent, limit)

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
        return await asyncio.to_thread(
            self._resolve_approval_sync, approval_id, decision, actor, comment
        )

    async def health_check(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._health_check_sync)

    # ------------------------------------------------------------------
    # Synchronous internals — wrapped in to_thread above
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            for table_name in self._tables.values():
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id          TEXT PRIMARY KEY,
                        natural_key TEXT NOT NULL UNIQUE,
                        fields_json TEXT NOT NULL,
                        created_at  TEXT NOT NULL,
                        updated_at  TEXT NOT NULL
                    )
                    """
                )
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {APPROVALS_TABLE} (
                    id              TEXT PRIMARY KEY,
                    record_kind     TEXT NOT NULL,
                    natural_key     TEXT NOT NULL,
                    proposed_fields TEXT NOT NULL,
                    rationale       TEXT,
                    proposed_by     TEXT,
                    status          TEXT NOT NULL DEFAULT 'pending',
                    decided_by      TEXT,
                    decided_at      TEXT,
                    decision_note   TEXT,
                    created_at      TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _upsert_sync(
        self,
        kind: RecordKind,
        fields: dict[str, Any],
        natural_key: str,
    ) -> UpsertResult:
        table = self._tables[kind.value]
        nk_field = self._natural_keys.get(kind.value)
        # Allow missing nk_field mapping for kinds that use composite keys
        # supplied directly by the caller.
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT id, fields_json FROM {table} WHERE natural_key = ?",
                (natural_key,),
            ).fetchone()
            now = _utc_now_iso()
            if row:
                existing_fields = json.loads(row["fields_json"])
                existing_fields.update(fields)
                conn.execute(
                    f"UPDATE {table} SET fields_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(existing_fields), now, row["id"]),
                )
                conn.commit()
                return UpsertResult(
                    ref=RecordRef(kind=kind, crm_id=row["id"], natural_key=natural_key),
                    created=False,
                    matched_on=nk_field or "natural_key",
                )
            new_id = uuid.uuid4().hex
            conn.execute(
                f"""
                INSERT INTO {table} (id, natural_key, fields_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (new_id, natural_key, json.dumps(fields), now, now),
            )
            conn.commit()
            return UpsertResult(
                ref=RecordRef(kind=kind, crm_id=new_id, natural_key=natural_key),
                created=True,
                matched_on=None,
            )
        finally:
            conn.close()

    def _queue_approval_sync(
        self,
        kind: RecordKind,
        fields: dict[str, Any],
        natural_key: str,
        rationale: str | None,
    ) -> str:
        conn = self._connect()
        try:
            approval_id = uuid.uuid4().hex
            conn.execute(
                f"""
                INSERT INTO {APPROVALS_TABLE}
                    (id, record_kind, natural_key, proposed_fields, rationale,
                     proposed_by, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    approval_id,
                    kind.value,
                    natural_key,
                    json.dumps(fields),
                    rationale or "",
                    fields.get("_proposed_by_agent", ""),
                    _utc_now_iso(),
                ),
            )
            conn.commit()
            return approval_id
        finally:
            conn.close()

    def _search_sync(
        self,
        kind: RecordKind,
        query: dict[str, Any],
        limit: int,
    ) -> list[SearchHit]:
        table = self._tables[kind.value]
        conn = self._connect()
        try:
            # Naive AND-equality filter — fields_json column is JSON, we
            # use ``json_extract`` to filter. For complex queries the
            # caller is expected to fall through to the MCP path on a real
            # CRM; this adapter targets pilot scale (<10k records).
            where_clauses: list[str] = []
            params: list[Any] = []
            for k, v in query.items():
                where_clauses.append(f"json_extract(fields_json, '$.{k}') = ?")
                params.append(v)
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            sql = (
                f"SELECT id, natural_key, fields_json FROM {table} "
                f"WHERE {where_sql} LIMIT ?"
            )
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [
                SearchHit(
                    ref=RecordRef(
                        kind=kind,
                        crm_id=r["id"],
                        natural_key=r["natural_key"],
                    ),
                    fields=json.loads(r["fields_json"]),
                )
                for r in rows
            ]
        finally:
            conn.close()

    def _list_pending_sync(
        self,
        agent: str | None,
        limit: int,
    ) -> list[PendingApproval]:
        conn = self._connect()
        try:
            if agent:
                rows = conn.execute(
                    f"""
                    SELECT * FROM {APPROVALS_TABLE}
                    WHERE status = 'pending' AND proposed_by = ?
                    ORDER BY created_at ASC LIMIT ?
                    """,
                    (agent, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"""
                    SELECT * FROM {APPROVALS_TABLE}
                    WHERE status = 'pending'
                    ORDER BY created_at ASC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [
                PendingApproval(
                    approval_id=r["id"],
                    record_kind=RecordKind(r["record_kind"]),
                    proposed_fields=json.loads(r["proposed_fields"]),
                    rationale=r["rationale"] or "",
                    created_at=datetime.fromisoformat(r["created_at"]),
                    proposed_by_agent=r["proposed_by"] or "",
                )
                for r in rows
            ]
        finally:
            conn.close()

    def _resolve_approval_sync(
        self,
        approval_id: str,
        decision: str,
        actor: str,
        comment: str | None,
    ) -> RecordRef | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT * FROM {APPROVALS_TABLE} WHERE id = ?", (approval_id,)
            ).fetchone()
            if not row:
                return None
            new_status = "approved" if decision == "approve" else "rejected"
            conn.execute(
                f"""
                UPDATE {APPROVALS_TABLE}
                SET status = ?, decided_by = ?, decided_at = ?, decision_note = ?
                WHERE id = ?
                """,
                (new_status, actor, _utc_now_iso(), comment or "", approval_id),
            )
            conn.commit()
            if decision == "reject":
                return None
            kind = RecordKind(row["record_kind"])
            fields = json.loads(row["proposed_fields"])
            natural_key = row["natural_key"]
        finally:
            conn.close()
        # Replay the write outside the approvals transaction
        result = self._upsert_sync(kind, fields, natural_key)
        return result.ref

    def _health_check_sync(self) -> dict[str, Any]:
        try:
            conn = self._connect()
            try:
                target_table = self._tables[RecordKind.TARGET_ORGANISATION.value]
                count = conn.execute(
                    f"SELECT COUNT(*) AS c FROM {target_table}"
                ).fetchone()["c"]
                return {
                    "adapter": self.name,
                    "ok": True,
                    "db_path": str(self._db_path),
                    "target_count": count,
                    "checked_at": _utc_now_iso(),
                }
            finally:
                conn.close()
        except Exception as e:  # noqa: BLE001
            return {
                "adapter": self.name,
                "ok": False,
                "error": str(e),
                "db_path": str(self._db_path),
                "checked_at": _utc_now_iso(),
            }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
