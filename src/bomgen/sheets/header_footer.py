"""Page header and footer per sheet (spec: Output requirements; plan M5, step 13).

Every zone uses the sheet's header size, so the text stays readable when the sheet
prints scaled down; only the project name is bold. BOM sheets use 28 pt; a calculation
sheet uses the largest size, up to 20 pt (Q11), whose three scaled header lines still
fit between the header margin and the top margin.
"""

import math
from pathlib import Path

from bomgen.models.panel import DocumentInfo
from bomgen.models.sheet import HeaderFooter, HFRun, HFZone, Margins

BOM_SIZE = 28
CALC_MAX_SIZE = 20
HEADER_LINES = 3
LINE_SPACING = 1.2  # line height as a multiple of the font size
POINTS_PER_CM = 72 / 2.54


def fitting_size(margins: Margins, scale_percent: int, max_size: int = CALC_MAX_SIZE) -> int:
    """The largest header size up to ``max_size`` whose lines fit in the top margin."""
    room = (margins.top_cm - margins.header_cm) * POINTS_PER_CM
    size = room / (HEADER_LINES * LINE_SPACING * scale_percent / 100)
    return max(1, min(max_size, math.floor(size)))


def bom_header_footer(
    project_name: str, cabinet_number: str, document: DocumentInfo, logo: Path | None
) -> HeaderFooter:
    return _header_footer(
        project_name, f"Bill of Materials for {cabinet_number}", document, logo, BOM_SIZE
    )


def calc_header_footer(
    project_name: str, title: str, document: DocumentInfo, logo: Path | None, size: int
) -> HeaderFooter:
    """``title`` is the sheet's second header line, e.g. "Power Consumption for <scope>"."""
    return _header_footer(project_name, title, document, logo, size)


def _header_footer(
    project_name: str, title: str, document: DocumentInfo, logo: Path | None, size: int
) -> HeaderFooter:
    def text(value: str) -> HFZone:
        return HFZone(lines=((HFRun(text=value, size=size),),))

    page = (
        HFRun(text="Page ", size=size),
        HFRun(field="page", size=size),
        HFRun(text=" of ", size=size),
        HFRun(field="pages", size=size),
    )
    return HeaderFooter(
        header_left=HFZone(image=logo),
        header_center=HFZone(
            lines=(
                (HFRun(text=project_name, bold=True, size=size),),
                (HFRun(text=title, size=size),),
                (HFRun(text=f"Supplier Doc # {document.doc_no}", size=size),),
            )
        ),
        header_right=text(f"Rev : {document.rev}"),
        footer_left=text(document.doc_no),
        footer_center=HFZone(lines=(page,)),
        footer_right=text(f"Rev {document.rev} – {document.issue_date.isoformat()}"),  # noqa: RUF001 - the spec's dash
    )
