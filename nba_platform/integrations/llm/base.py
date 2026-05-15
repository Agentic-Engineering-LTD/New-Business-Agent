"""LLM adapter contract.

Portfolio standard is OpenRouter, routing to Claude Sonnet 4.6 (reasoning-heavy
agents) and Claude Haiku 4.5 (high-frequency lightweight tasks). The interface
sits in front of OpenRouter so the well-documented upgrade paths — direct
Anthropic, Bedrock eu-west-2 — are configuration changes, not code changes.

Agent SKILL.md files reference models by *role* (``reasoning`` or ``light``),
never by name. The customer config maps roles to concrete model identifiers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ModelRole(str, Enum):
    REASONING = "reasoning"  # default: claude-sonnet-4-6
    LIGHT = "light"  # default: claude-haiku-4-5


class CompletionRequest(BaseModel):
    role: ModelRole
    system: str | None = None
    messages: list[dict[str, Any]]
    max_tokens: int = 4096
    temperature: float = 0.2
    tools: list[dict[str, Any]] | None = None


class CompletionResponse(BaseModel):
    text: str
    tool_calls: list[dict[str, Any]] | None = None
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    model: str  # the actual model that served the request


class LlmAdapter(ABC):
    name: str

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse: ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]: ...


class LlmConfigError(Exception):
    pass


def build_llm_adapter(config: dict[str, Any]) -> LlmAdapter:
    kind = config.get("kind", "openrouter")
    if kind == "openrouter":
        from nba_platform.integrations.llm.openrouter import OpenRouterAdapter

        return OpenRouterAdapter(config)
    raise LlmConfigError(f"unknown LLM kind: {kind!r}")


__all__ = [
    "ModelRole",
    "CompletionRequest",
    "CompletionResponse",
    "LlmAdapter",
    "LlmConfigError",
    "build_llm_adapter",
]
