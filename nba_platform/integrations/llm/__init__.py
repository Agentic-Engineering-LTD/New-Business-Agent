"""LLM adapter interface and implementations."""

from nba_platform.integrations.llm.base import (
    CompletionRequest,
    CompletionResponse,
    LlmAdapter,
    LlmConfigError,
    ModelRole,
    build_llm_adapter,
)

__all__ = [
    "CompletionRequest",
    "CompletionResponse",
    "LlmAdapter",
    "LlmConfigError",
    "ModelRole",
    "build_llm_adapter",
]
