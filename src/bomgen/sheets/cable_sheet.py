"""The Cable Schedule sheet: the loose rows that carry cable data, after the Summary BOM
(ADR 0035, plan M65).

Laid out like the Summary BOM sheet, A4 landscape. A quantity is a formula on the row's
Loose Material quantity cell (OUT-5).
"""

from collections.abc import Mapping

from bomgen.models.bom import BomLine, LooseTable
from bomgen.models.calc import LineRef
from bomgen.models.sheet import CellRange, CellValue, Formula, HeaderFooter, PrintSetup, SheetModel
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder, quote_sheet
from bomgen.sheets.summary_sheet import CENTRE, HEADER, QTY_COL, TEXT, TITLE_HEIGHT, TITLE_STYLE

HEADERS = (
    "SR.NO",
    "FROM",
    "TO",
    "TYPE",
    "LENGTH (m)",
    "QUANTITY",
    "MAKE",
    "MODEL",
    "ORDERING CODE",
)
WIDTHS = (8.0, 24.0, 24.0, 44.0, 12.0, 12.0, 16.0, 22.0, 30.0)
CELL_STYLES = (CENTRE, TEXT, TEXT, TEXT, CENTRE, CENTRE, TEXT, TEXT, TEXT)
TITLE = "Cable Schedule"


def has_cables(loose: LooseTable | None) -> bool:
    return loose is not None and any(line.cable is not None for line in loose.lines)


def cable_type(line: BomLine) -> str:
    """The TYPE cell: the description's first line, then the speed and media given."""
    kind = line.description.split("\n")[0]
    cable = line.cable
    if cable is not None and (cable.speed is not None or cable.media is not None):
        given = (c.value for c in (cable.speed, cable.media) if c is not None)
        kind += f" ({' '.join(given)})"
    return kind


def cable_sheet(
    name: str,
    substation: str,
    loose: LooseTable,
    cells: Mapping[LineRef, tuple[str, int]],
    header_footer: HeaderFooter | None = None,
) -> SheetModel:
    """``cells`` gives the sheet and row of every loose line."""
    sheet = SheetBuilder(name)
    for col, width in enumerate(WIDTHS, start=1):
        sheet.width(col, width)
    last_col = len(HEADERS)
    sheet.merge(1, 1, 1, last_col, f"{substation}\n{TITLE}", TITLE_STYLE)
    sheet.height(1, TITLE_HEIGHT)
    for col, label in enumerate(HEADERS, start=1):
        sheet.set(2, col, label, HEADER)
    row = 2
    for index, line in enumerate(loose.lines):
        cable = line.cable
        if cable is None:
            continue
        row += 1
        sr_no: CellValue = 1 if row == 3 else Formula(text=f"=A{row - 1}+1", result=row - 2)
        source, source_row = cells[LineRef(panel_id=None, line=index)]
        values = (
            sr_no,
            cable.from_tag,
            cable.to_tag,
            cable_type(line),
            cable.length_m,
            Formula(text=f"={quote_sheet(source)}!{QTY_COL}{source_row}", result=line.qty),
            line.make,
            line.model,
            line.ordering_code,
        )
        for col, (value, style) in enumerate(zip(values, CELL_STYLES, strict=True), start=1):
            sheet.set(row, col, value, style)
    setup = PrintSetup(
        orientation="landscape",
        fit_to_width=1,
        fit_to_height=0,
        margins=styles.BOM_MARGINS,
        center_horizontally=True,
        print_area=CellRange(first_row=1, first_col=1, last_row=row, last_col=last_col),
        repeat_rows=(1, 2),
    )
    return sheet.build(setup, header_footer)
