"""The Summary BOM sheet: lines consolidated by ordering code with where-used, after Heat
Calculations when the substation includes it (ADR 0035, plan M63).

Merged title in row 1, header in row 2, rows 1-2 repeated, A4 landscape, the calculation
sheets' 12 pt text with thin borders. A quantity is a formula summing the source BOM
quantity cells (OUT-5).
"""

from collections.abc import Mapping

from bomgen.models.bom import SummaryLine, SummaryTable
from bomgen.models.calc import LineRef
from bomgen.models.sheet import CellRange, CellValue, Formula, HeaderFooter, PrintSetup, SheetModel
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder, quote_sheet

HEADERS = ("SR.NO", "DESCRIPTION", "QUANTITY", "MAKE", "MODEL", "ORDERING CODE", "WHERE USED")
WIDTHS = (8.0, 48.0, 12.0, 16.0, 22.0, 34.0, 60.0)
LAST_COL = len(HEADERS)
TITLE = "Summary BOM"
TITLE_HEIGHT = 48.0
QTY_COL = "D"  # QUANTITY on the BOM sheets (spec: Columns of a panel BOM)

TITLE_STYLE = styles.CALC_HEADER.model_copy(
    update={"font": styles.CALC_TITLE.font, "borders": styles.THIN}
)
HEADER = styles.CALC_HEADER.model_copy(update={"borders": styles.THIN})
CENTRE = styles.CALC_DATA.model_copy(update={"borders": styles.THIN})
TEXT = styles.CALC_DATA_TEXT.model_copy(update={"borders": styles.THIN})
CELL_STYLES = (CENTRE, TEXT, CENTRE, TEXT, TEXT, TEXT, TEXT)


def summary_sheet(
    name: str,
    substation: str,
    summary: SummaryTable,
    cells: Mapping[LineRef, tuple[str, int]],
    sheet_names: Mapping[str | None, str],
    header_footer: HeaderFooter | None = None,
) -> SheetModel:
    """``cells`` gives the sheet and row of every source BOM line; ``sheet_names`` names
    each table (a panel id, ``None`` for the loose material) in WHERE USED."""
    sheet = SheetBuilder(name)
    for col, width in enumerate(WIDTHS, start=1):
        sheet.width(col, width)
    sheet.merge(1, 1, 1, LAST_COL, f"{substation}\n{TITLE}", TITLE_STYLE)
    sheet.height(1, TITLE_HEIGHT)
    for col, label in enumerate(HEADERS, start=1):
        sheet.set(2, col, label, HEADER)
    row = 2
    for line in summary.lines:
        row += 1
        sr_no: CellValue = 1 if row == 3 else Formula(text=f"=A{row - 1}+1", result=row - 2)
        values = (
            sr_no,
            line.description,
            _quantity(line, cells),
            line.make,
            line.model,
            line.ordering_code,
            line.where_used(sheet_names),
        )
        for col, (value, style) in enumerate(zip(values, CELL_STYLES, strict=True), start=1):
            sheet.set(row, col, value, style)
    setup = PrintSetup(
        orientation="landscape",
        fit_to_width=1,
        fit_to_height=0,
        margins=styles.BOM_MARGINS,
        center_horizontally=True,
        print_area=CellRange(first_row=1, first_col=1, last_row=row, last_col=LAST_COL),
        repeat_rows=(1, 2),
    )
    return sheet.build(setup, header_footer)


def _quantity(line: SummaryLine, cells: Mapping[LineRef, tuple[str, int]]) -> Formula:
    """``=SUM('1'!D20:D21,'2'!D20)``, consecutive rows of one sheet as one range; a text
    quantity references its one cell."""
    if isinstance(line.qty, str):
        sheet, row = cells[line.sources[0].ref]
        return Formula(text=f"={quote_sheet(sheet)}!{QTY_COL}{row}", result=line.qty)
    runs: list[tuple[str, int, int]] = []
    for source in line.sources:
        sheet, row = cells[source.ref]
        if runs and runs[-1][0] == sheet and runs[-1][2] == row - 1:
            runs[-1] = (sheet, runs[-1][1], row)
        else:
            runs.append((sheet, row, row))
    parts = [
        f"{quote_sheet(s)}!{QTY_COL}{a}" + (f":{QTY_COL}{b}" if b != a else "") for s, a, b in runs
    ]
    return Formula(text=f"=SUM({','.join(parts)})", result=line.qty)
