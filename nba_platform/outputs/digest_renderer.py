"""Weekly digest renderer.

Produces a structured markdown body suitable for email or Slack. Templates
live in the vertical pack at ``verticals/<vertical>/outputs/weekly_digest.template.md``
and bind against ``RenderRequest.data`` via Jinja2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

from nba_platform.outputs.base import Output, OutputKind, OutputRenderer, RenderRequest

REPO_ROOT = Path(__file__).resolve().parents[2]


class WeeklyDigestRenderer(OutputRenderer):
    kind = OutputKind.WEEKLY_DIGEST

    async def render(self, request: RenderRequest) -> Output:
        # Locate the template in the vertical pack. The customer's outputs.yaml
        # tells us which vertical pack to pull from via the vertical pinning.
        vertical = request.data.get("__vertical")
        if not vertical:
            raise ValueError(
                "WeeklyDigestRenderer: RenderRequest.data must include '__vertical'; "
                "callers should set this from ConfigBundle.vertical"
            )

        template_path = (
            REPO_ROOT
            / "verticals"
            / vertical
            / "outputs"
            / f"{request.template_id}.template.md"
        )
        if not template_path.exists():
            raise FileNotFoundError(
                f"weekly digest template not found: {template_path}"
            )

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_path.parent)),
            autoescape=False,
            keep_trailing_newline=True,
        )
        template = env.get_template(template_path.name)

        body = template.render(
            data=request.data,
            brand=request.brand,
            customer=request.customer,
            generated_at=request.generated_at,
        )

        return Output(
            customer=request.customer,
            kind=self.kind,
            body_text=body,
            metadata={"template_id": request.template_id, "format": "markdown"},
        )
