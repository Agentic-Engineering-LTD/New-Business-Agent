"""Web search adapter interface and implementations."""

from nba_platform.integrations.search.base import (
    SearchAdapter,
    SearchConfigError,
    SearchResult,
    build_search_adapter,
)

__all__ = ["SearchAdapter", "SearchConfigError", "SearchResult", "build_search_adapter"]
