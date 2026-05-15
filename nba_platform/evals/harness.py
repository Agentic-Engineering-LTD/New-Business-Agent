"""Eval harness.

Every agent invocation records an ``EvalRun``: which agent, which customer,
inputs, outputs, latency, cost, success/failure, human feedback (when an
approval is resolved). Runs are appended to a JSONL file per customer.

Aggregation lives in ``metrics.py`` — this module is the writer.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EvalRun(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    customer: str
    vertical: str
    agent: str
    inputs_summary: str  # one-line description of what the agent was asked
    outputs_summary: str  # one-line description of what was produced
    success: bool
    latency_ms: int
    cost_usd: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    approval_outcome: str | None = None  # "approved" | "rejected" | None (pending or not-required)
    notes: str | None = None


class MetricSnapshot(BaseModel):
    """Aggregate of many runs."""

    customer: str
    vertical: str
    agent: str
    window_start: datetime
    window_end: datetime
    invocations: int
    success_rate: float
    p50_latency_ms: int
    p95_latency_ms: int
    total_cost_usd: float
    approval_rate: float | None  # None if no approvals in window


def _runs_path(customer: str) -> Path:
    base = Path(os.environ.get("NBA_EVAL_DIR", "evals/runs"))
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{customer}.jsonl"


def record_run(run: EvalRun) -> None:
    path = _runs_path(run.customer)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(run.model_dump(mode="json"), default=str) + "\n")


def load_runs(customer: str) -> list[EvalRun]:
    path = _runs_path(customer)
    if not path.exists():
        return []
    runs: list[EvalRun] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(EvalRun(**json.loads(line)))
            except Exception:  # noqa: BLE001 — corrupted lines should never block reads
                continue
    return runs
