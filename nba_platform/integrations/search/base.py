"""Web search adapter contract.

Agents do not call a specific search vendor. The Target Identifier, Org Mapper,
and Refresh / Watch agents need to look things up on the open web; this
interface keeps the choice of backend (Tavily, Brave, Google CSE, Bing,
SerpAPI) configurable.

For Paperclip-managed deployments the recommended path is to wire the
search adapter to whatever MCP search server is available in the customer's
Paperclip instance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    published_at: str | None = None
    source_domain: str | None = None


class SearchAdapter(ABC):
    name: str

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        recency_days: int | None = None,
    ) -> list[SearchResult]: ...

    @abstractmethod
    async def fetch(self, url: str) -> str:
        """Return text content of the URL. Implementations should respect
        robots.txt and reasonable politeness."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]: ...


class SearchConfigError(Exception):
    pass


def build_search_adapter(config: dict[str, Any]) -> SearchAdapter:
    kind = config.get("kind", "tavily")
    if kind == "tavily":
        from nba_platform.integrations.search.tavily import TavilyAdapter

        return TavilyAdapter(config)
    raise SearchConfigError(f"unknown search kind: {kind!r}")


__all__ = [
    "SearchResult",
    "SearchAdapter",
    "SearchConfigError",
    "build_search_adapter",
]
