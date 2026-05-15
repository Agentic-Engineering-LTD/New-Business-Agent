"""Governance helpers: approval gates, budgets, audit trail.

These wrap Paperclip's native governance primitives. The platform never
implements its own approval UI — Paperclip is the control plane.
"""

from nba_platform.governance.audit import AuditEvent, log_event
from nba_platform.governance.budget import BudgetExceeded, check_budget

__all__ = ["AuditEvent", "BudgetExceeded", "check_budget", "log_event"]
