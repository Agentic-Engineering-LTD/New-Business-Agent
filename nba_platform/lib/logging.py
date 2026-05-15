"""Structured logging configuration.

Single ``configure()`` call to set up structlog the way every agent and
adapter expects. Idempotent — safe to call multiple times.
"""

from __future__ import annotations

import logging
import os

import structlog

_configured = False


def configure(level: str | None = None) -> None:
    global _configured
    if _configured:
        return

    effective_level = (level or os.environ.get("NBA_LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(level=effective_level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(effective_level)),
        cache_logger_on_first_use=True,
    )
    _configured = True
