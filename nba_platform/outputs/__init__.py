"""Output rendering engine.

Templates supplied by the vertical pack; brand assets and recipients by the
customer config; the platform engine renders.

Three output types currently supported:

- ``pdf_renderer``: long-form PDF reports (e.g. daily-pipeline reports,
  account one-pagers)
- ``digest_renderer``: markdown / email weekly digest
- ``xlsx_exporter``: customer-facing pipeline-state snapshot — XLSX
  workbook (one sheet per record kind + Pending_Approvals) plus a CSV
  zip equivalent and an editable ``approvals_inbox.csv``
- (future) ``slack_renderer``: structured Slack message

Adding a new output type means a new renderer module here + a new template
shape in the vertical pack — never a customer-specific renderer.
"""

from nba_platform.outputs.base import (
    Output,
    OutputKind,
    OutputRenderer,
    RenderRequest,
    build_renderer,
)

__all__ = ["Output", "OutputKind", "OutputRenderer", "RenderRequest", "build_renderer"]
