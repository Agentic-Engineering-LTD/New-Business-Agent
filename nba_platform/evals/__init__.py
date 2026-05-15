"""Eval harness — per-agent, per-customer, per-vertical metrics from day one.

Tracks: success rate, latency, cost, draft approval rate, accuracy of
stakeholder resolution, time-to-value per opportunity, opportunity assessor
calibration vs human judgement.

The eval harness exists to make sure platform / vertical-pack improvements
never silently regress quality across the customer base.
"""

from nba_platform.evals.harness import EvalRun, MetricSnapshot, record_run
from nba_platform.evals.metrics import (
    AgentMetric,
    CustomerMetric,
    aggregate_for_customer,
    aggregate_for_vertical,
)

__all__ = [
    "EvalRun",
    "MetricSnapshot",
    "record_run",
    "AgentMetric",
    "CustomerMetric",
    "aggregate_for_customer",
    "aggregate_for_vertical",
]
