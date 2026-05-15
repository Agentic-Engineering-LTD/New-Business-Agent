"""PDF rendering via ReportLab.

Two renderer classes here share helpers:

- ``PdfReportRenderer`` produces long-form daily/weekly PDF reports.
- ``AccountOnePagerRenderer`` produces single-page strategy outputs.

Both take their structure from a markdown template in the vertical pack's
``outputs/`` directory and bind the customer's brand styling. Nothing in this
module knows the difference between one vertical's report shape and
another's — that's all in the template + data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from nba_platform.outputs.base import Output, OutputKind, OutputRenderer, RenderRequest

REPO_ROOT = Path(__file__).resolve().parents[2]


class _PdfBase(OutputRenderer):
    """Shared PDF helpers. Subclasses set ``kind`` and override ``_compose_story``."""

    def _styles(self, brand: dict[str, Any]):
        styles = getSampleStyleSheet()
        primary = brand.get("colours", {}).get("primary", "#0B1F44")
        secondary = brand.get("colours", {}).get("secondary", "#6E7A8A")
        font = brand.get("font_family", "Helvetica")

        styles.add(
            ParagraphStyle(
                "BrandTitle",
                parent=styles["Title"],
                fontName=f"{font}-Bold",
                textColor=HexColor(primary),
                fontSize=20,
                leading=24,
                spaceAfter=12,
            )
        )
        styles.add(
            ParagraphStyle(
                "BrandH2",
                parent=styles["Heading2"],
                fontName=f"{font}-Bold",
                textColor=HexColor(primary),
                fontSize=14,
                leading=18,
                spaceAfter=8,
            )
        )
        styles.add(
            ParagraphStyle(
                "BrandBody",
                parent=styles["BodyText"],
                fontName=font,
                textColor=HexColor(secondary),
                fontSize=10.5,
                leading=14,
            )
        )
        return styles

    def _output_path(self, request: RenderRequest) -> Path:
        out_dir = Path("out") / request.customer
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = request.generated_at.strftime("%Y-%m-%dT%H%M%S")
        return out_dir / f"{request.kind.value}_{stamp}.pdf"

    def _table_style(self, brand: dict[str, Any]) -> TableStyle:
        primary = brand.get("colours", {}).get("primary", "#0B1F44")
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor(primary)),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#D8DEE6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )


class PdfReportRenderer(_PdfBase):
    kind = OutputKind.PDF_REPORT

    async def render(self, request: RenderRequest) -> Output:
        styles = self._styles(request.brand)
        path = self._output_path(request)
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=request.data.get("title", "New Business Report"),
        )

        story: list[Any] = []
        story.append(Paragraph(request.data.get("title", "New Business Report"), styles["BrandTitle"]))
        story.append(
            Paragraph(
                f"Generated {request.generated_at.strftime('%d %B %Y at %H:%M UTC')} for {request.customer}.",
                styles["BrandBody"],
            )
        )
        story.append(Spacer(1, 8 * mm))

        sections = request.data.get("sections", [])
        for section in sections:
            story.append(Paragraph(section.get("heading", ""), styles["BrandH2"]))
            if section.get("body"):
                story.append(Paragraph(section["body"], styles["BrandBody"]))
            if section.get("rows"):
                rows = section["rows"]
                columns = section.get("columns") or list(rows[0].keys()) if rows else []
                header = [c.replace("_", " ").title() for c in columns]
                table_data = [header] + [[str(r.get(c, "")) for c in columns] for r in rows]
                story.append(Table(table_data, hAlign="LEFT", repeatRows=1))
                story[-1].setStyle(self._table_style(request.brand))
            story.append(Spacer(1, 6 * mm))

        doc.build(story)

        return Output(
            customer=request.customer,
            kind=self.kind,
            file_path=path,
            metadata={"page_size": "A4", "template_id": request.template_id},
        )


class AccountOnePagerRenderer(_PdfBase):
    kind = OutputKind.ACCOUNT_ONE_PAGER

    async def render(self, request: RenderRequest) -> Output:
        styles = self._styles(request.brand)
        path = self._output_path(request)
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title=request.data.get("account_name", "Account One-Pager"),
        )

        story: list[Any] = []
        story.append(
            Paragraph(request.data.get("account_name", "Account One-Pager"), styles["BrandTitle"])
        )
        if subline := request.data.get("subline"):
            story.append(Paragraph(subline, styles["BrandBody"]))
        story.append(Spacer(1, 6 * mm))

        # Two-column overview: facts table + opportunity summary
        facts = request.data.get("facts", {})
        fact_rows = [[k.replace("_", " ").title(), str(v)] for k, v in facts.items()]
        if fact_rows:
            table = Table(fact_rows, colWidths=[55 * mm, 110 * mm], hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#D8DEE6")),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 6 * mm))

        if opportunity := request.data.get("opportunity"):
            story.append(Paragraph("Opportunity", styles["BrandH2"]))
            story.append(Paragraph(opportunity, styles["BrandBody"]))
            story.append(Spacer(1, 5 * mm))

        stakeholders = request.data.get("stakeholders", [])
        if stakeholders:
            story.append(Paragraph("Key stakeholders", styles["BrandH2"]))
            columns = ["name", "role", "seniority", "confidence"]
            header = [c.title() for c in columns]
            table_data = [header] + [[str(s.get(c, "")) for c in columns] for s in stakeholders]
            t = Table(table_data, hAlign="LEFT", repeatRows=1)
            t.setStyle(self._table_style(request.brand))
            story.append(t)
            story.append(Spacer(1, 5 * mm))

        if recommended := request.data.get("recommended_next_actions"):
            story.append(Paragraph("Recommended next actions", styles["BrandH2"]))
            for action in recommended:
                story.append(Paragraph(f"• {action}", styles["BrandBody"]))

        doc.build(story)
        return Output(
            customer=request.customer,
            kind=self.kind,
            file_path=path,
            metadata={"page_size": "A4", "template_id": request.template_id},
        )
