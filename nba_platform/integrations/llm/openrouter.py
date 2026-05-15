"""OpenRouter LLM adapter.

Uses OpenRouter's OpenAI-compatible API. Customer config maps ``ModelRole`` to
concrete model identifiers; defaults follow the portfolio standard:

    role: reasoning  ->  anthropic/claude-sonnet-4-6
    role: light      ->  anthropic/claude-haiku-4-5

Config shape (``customers/<customer>/llm.yaml`` or a section in another config):

    kind: openrouter
    api_key_secret_name: OPENROUTER_API_KEY
    models:
      reasoning: anthropic/claude-sonnet-4-6
      light: anthropic/claude-haiku-4-5
    headers:
      HTTP-Referer: https://agenticengineering.co.uk
      X-Title: New Business Agent
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from nba_platform.integrations.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LlmAdapter,
    LlmConfigError,
    ModelRole,
)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

DEFAULT_MODELS = {
    ModelRole.REASONING: "anthropic/claude-sonnet-4-6",
    ModelRole.LIGHT: "anthropic/claude-haiku-4-5",
}


class OpenRouterAdapter(LlmAdapter):
    def __init__(self, config: dict[str, Any]) -> None:
        self.name = "openrouter"
        secret_name = config.get("api_key_secret_name", "OPENROUTER_API_KEY")
        self._api_key = os.environ.get(secret_name)
        if not self._api_key:
            raise LlmConfigError(
                f"openrouter api key not found in env var {secret_name!r}; "
                "Paperclip should inject this from its secrets store"
            )

        configured_models = config.get("models", {})
        self._models = {
            ModelRole.REASONING: configured_models.get(
                ModelRole.REASONING.value, DEFAULT_MODELS[ModelRole.REASONING]
            ),
            ModelRole.LIGHT: configured_models.get(
                ModelRole.LIGHT.value, DEFAULT_MODELS[ModelRole.LIGHT]
            ),
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        headers.update(config.get("headers", {}))

        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE,
            headers=headers,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model = self._models[request.role]
        messages = list(request.messages)
        if request.system:
            messages = [{"role": "system", "content": request.system}, *messages]

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.tools:
            payload["tools"] = request.tools

        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage", {})

        # OpenRouter returns total_cost in the X-Total-Cost header on most models;
        # falling back to 0 here is intentional — agents must never block on cost
        # observability, and the eval harness reconciles spend from OpenRouter's
        # activity endpoint daily.
        cost_usd = float(resp.headers.get("X-Total-Cost", "0") or 0)

        return CompletionResponse(
            text=message.get("content") or "",
            tool_calls=message.get("tool_calls"),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            cost_usd=cost_usd,
            model=data.get("model", model),
        )

    async def health_check(self) -> dict[str, Any]:
        try:
            resp = await self._client.get("/models", timeout=10.0)
            return {
                "adapter": self.name,
                "ok": resp.status_code == 200,
                "status_code": resp.status_code,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "models": self._models,
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
