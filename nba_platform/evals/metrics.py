"""Aggregate metrics from eval runs.

Three rollup levels:

- Per-agent: success rate, latency, cost, approval rate
- Per-customer: union of per-agent metrics for that customer + draft approval
  rate, time-to-value
- Per-vertical: aggregate across customers in the same vertical — what tells
  us a vertical-pack change improved or regressed quality
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Iterable

from nba_platform.evals.harness import EvalRun, MetricSnapshot, load_runs


def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p * (len(s) - 1)))))
    return s[k]


def aggregate_for_agent(
    runs: Iterable[EvalRun],
    *,
    agent: str,
    window_start: datetime,
    window_end: datetime,
) -> MetricSnapshot | None:
    in_window = [r for r in runs if r.agent == agent and window_start <= r.timestamp <= window_end]
    if not in_window:
        return None

    successes = sum(1 for r in in_window if r.success)
    latencies = [r.latency_ms for r in in_window]
    approvals = [r for r in in_window if r.approval_outcome in ("approved", "rejected")]
    approval_rate: float | None = None
    if approvals:
        approval_rate = sum(1 for r in approvals if r.approval_outcome == "approved") / len(approvals)

    first = in_window[0]
    return MetricSnapshot(
        customer=first.customer,
        vertical=first.vertical,
        agent=agent,
        window_start=window_start,
        window_end=window_end,
        invocations=len(in_window),
        success_rate=successes / len(in_window),
        p50_latency_ms=int(median(latencies)),
        p95_latency_ms=_percentile(latencies, 0.95),
        total_cost_usd=sum(r.cost_usd for r in in_window),
        approval_rate=approval_rate,
    )


class AgentMetric(MetricSnapshot):
    pass


class CustomerMetric:
    """Per-customer rollup across all agents in a window."""

    def __init__(
        self,
        customer: str,
        vertical: str,
        window_start: datetime,
        window_end: datetime,
        per_agent: dict[str, MetricSnapshot],
    ) -> None:
        self.customer = customer
        self.vertical = vertical
        self.window_start = window_start
        self.window_end = window_end
        self.per_agent = per_agent

    @property
    def total_cost_usd(self) -> float:
        return sum(m.total_cost_usd for m in self.per_agent.values())

    @property
    def overall_success_rate(self) -> float:
        total_invocations = sum(m.invocations for m in self.per_agent.values())
        if total_invocations == 0:
            return 0.0
        weighted = sum(m.success_rate * m.invocations for m in self.per_agent.values())
        return weighted / total_invocations


def aggregate_for_customer(
    customer: str,
    *,
    window_days: int = 7,
    end: datetime | None = None,
) -> CustomerMetric | None:
    end_dt = end or datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=window_days)
    runs = load_runs(customer)
    if not runs:
        return None

    agents = sorted({r.agent for r in runs})
    per_agent: dict[str, MetricSnapshot] = {}
    vertical = ""
    for agent in agents:
        snap = aggregate_for_agent(runs, agent=agent, window_start=start_dt, window_end=end_dt)
        if snap:
            per_agent[agent] = snap
            vertical = snap.vertical

    if not per_agent:
        return None
    return CustomerMetric(customer, vertical, start_dt, end_dt, per_agent)


def aggregate_for_vertical(
    vertical: str,
    customers: list[str],
    *,
    window_days: int = 7,
) -> dict[str, CustomerMetric]:
    """Roll up the same window across every customer in the vertical. Used by
    the platform team to detect regressions when a vertical pack ships an
    update."""
    rollup: dict[str, CustomerMetric] = {}
    for customer in customers:
        snap = aggregate_for_customer(customer, window_days=window_days)
        if snap and snap.vertical == vertical:
            rollup[customer] = snap
    return rollup
