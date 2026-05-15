"""Output renderer contract.

The Hand-off Agent produces an ``Output`` by calling a renderer. Renderers are
chosen by ``OutputKind`` (config-driven from ``customers/<customer>/outputs.yaml``)
and pull templates from the vertical pack.

The platform engine is responsible for:

- Loading the template from the vertical pack
- Resolving brand assets and recipient lists from the customer config
- Rendering and emitting the result

The platform engine is NOT responsible for:

- Knowing what fields make sense (that's the vertical pack's schema)
- Customer-specific copy (that's the customer config)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class OutputKind(str, Enum):
    PDF_REPORT = "pdf_report"
    WEEKLY_DIGEST = "weekly_digest"
    ACCOUNT_ONE_PAGER = "account_one_pager"


class RenderRequest(BaseModel):
    customer: str
    kind: OutputKind
    template_id: str  # references a template in the vertical pack
    data: dict[str, Any]  # the structured data the template binds against
    brand: dict[str, Any]  # logo, colours, voice, signature — from customer config
    recipients: list[str] = Field(default_factory=list)  # email addresses for delivery
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Output(BaseModel):
    customer: str
    kind: OutputKind
    file_path: Path | None = None  # set when the renderer writes a file
    body_text: str | None = None  # set when the output is text (digest, slack)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class OutputRenderer(ABC):
    kind: OutputKind

    @abstractmethod
    async def render(self, request: RenderRequest) -> Output: ...


def build_renderer(kind: OutputKind) -> OutputRenderer:
    if kind == OutputKind.PDF_REPORT:
        from nba_platform.outputs.pdf_renderer import PdfReportRenderer

        return PdfReportRenderer()
    if kind == OutputKind.WEEKLY_DIGEST:
        from nba_platform.outputs.digest_renderer import WeeklyDigestRenderer

        return WeeklyDigestRenderer()
    if kind == OutputKind.ACCOUNT_ONE_PAGER:
        from nba_platform.outputs.pdf_renderer import AccountOnePagerRenderer

        return AccountOnePagerRenderer()

    raise ValueError(f"no renderer registered for kind {kind!r}")
