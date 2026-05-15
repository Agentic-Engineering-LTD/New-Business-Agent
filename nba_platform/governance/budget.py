"""Budget caps.

Paperclip enforces per-agent monthly budgets natively. This helper exists for
in-process pre-checks — e.g. an agent that would burn a large amount on one
call can decide to skip rather than start work. The hard stop is still
Paperclip's.
"""

from __future__ import annotations

from typing import Any


class BudgetExceeded(Exception):
    """Raised when a planned action would exceed the agent's remaining budget."""

    def __init__(self, agent: str, estimated_cost: float, remaining: float) -> None:
        super().__init__(
            f"agent {agent!r} would exceed budget: estimated ${estimated_cost:.4f}, "
            f"remaining ${remaining:.4f}"
        )
        self.agent = agent
        self.estimated_cost = estimated_cost
        self.remaining = remaining


def check_budget(
    *,
    agent: str,
    estimated_cost: float,
    remaining: float,
    headroom_factor: float = 1.1,
) -> None:
    """Raise ``BudgetExceeded`` if ``estimated_cost * headroom_factor > remaining``.

    Call before any expensive operation. The headroom factor (10% by default)
    leaves room for under-estimation.
    """
    if estimated_cost * headroom_factor > remaining:
        raise BudgetExceeded(agent, estimated_cost, remaining)


def estimate_completion_cost(
    *,
    model: str,
    prompt_tokens: int,
    expected_completion_tokens: int,
) -> float:
    """Rough cost estimate for an LLM completion. Reads pricing from a static
    table that the eval harness reconciles against OpenRouter's billing daily.

    Add new models as they enter use; an unknown model returns 0 and emits a
    warning rather than blocking the agent."""
    pricing = _PRICING.get(model)
    if not pricing:
        # Unknown model: don't block on the budget check. Eval harness will
        # flag the gap on the next reconcile.
        return 0.0
    prompt_cost = prompt_tokens * pricing["prompt"] / 1_000_000
    completion_cost = expected_completion_tokens * pricing["completion"] / 1_000_000
    return prompt_cost + completion_cost


# Per-million-token USD pricing for the models we use. Update from OpenRouter's
# model list when prices change; the eval harness reconciles actuals daily.
_PRICING: dict[str, dict[str, float]] = {
    "anthropic/claude-sonnet-4-6": {"prompt": 3.0, "completion": 15.0},
    "anthropic/claude-haiku-4-5": {"prompt": 0.80, "completion": 4.0},
}


def register_model_pricing(model: str, *, prompt_per_million: float, completion_per_million: float) -> None:
    """Register or override pricing for a model. Useful for tests and for adding
    new models without a code change to the table above."""
    _PRICING[model] = {"prompt": prompt_per_million, "completion": completion_per_million}
