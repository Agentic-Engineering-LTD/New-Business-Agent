"""Tavily web-search adapter.

Tavily is the default web-search backend — AI-friendly snippets, recency
filtering, and a permissive ToS for agent use. Swap to Brave / Bing / Google
CSE behind the same interface if the customer prefers.

Config shape:

    kind: tavily
    api_key_secret_name: TAVILY_API_KEY
    default_max_results: 10
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from nba_platform.integrations.search.base import (
    SearchAdapter,
    SearchConfigError,
    SearchResult,
)

TAVILY_API = "https://api.tavily.com"


class TavilyAdapter(SearchAdapter):
    def __init__(self, config: dict[str, Any]) -> None:
        self.name = "tavily"
        secret_name = config.get("api_key_secret_name", "TAVILY_API_KEY")
        self._api_key = os.environ.get(secret_name)
        if not self._api_key:
            raise SearchConfigError(
                f"tavily api key not found in env var {secret_name!r}"
            )
        self._default_max_results = int(config.get("default_max_results", 10))
        self._client = httpx.AsyncClient(base_url=TAVILY_API, timeout=30.0)

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        recency_days: int | None = None,
    ) -> list[SearchResult]:
        payload: dict[str, Any] = {
            "api_key": self._api_key,
            "query": query,
            "max_results": max_results or self._default_max_results,
            "search_depth": "advanced",
        }
        if recency_days is not None:
            payload["days"] = recency_days

        resp = await self._client.post("/search", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                published_at=r.get("published_date"),
                source_domain=_domain_of(r.get("url", "")),
            )
            for r in data.get("results", [])
        ]

    async def fetch(self, url: str) -> str:
        # Tavily exposes a separate extract endpoint; using a generic HTTP
        # fetch keeps the contract minimal. Implementations may upgrade to
        # vendor extraction APIs without changing this interface.
        resp = await self._client.get(url, follow_redirects=True, timeout=30.0)
        resp.raise_for_status()
        return resp.text

    async def health_check(self) -> dict[str, Any]:
        try:
            results = await self.search("agentic engineering", max_results=1)
            return {
                "adapter": self.name,
                "ok": True,
                "result_count": len(results),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:  # noqa: BLE001
            return {
                "adapter": self.name,
                "ok": False,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    async def aclose(self) -> None:
        await self._client.aclose()


def _domain_of(url: str) -> str | None:
    if not url:
        return None
    from urllib.parse import urlparse

    try:
        return urlparse(url).netloc or None
    except Exception:  # noqa: BLE001
        return None
