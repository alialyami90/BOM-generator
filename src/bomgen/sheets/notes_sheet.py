"""The Notes sheet: every BOM row that carries a note, with its sheet and tag (plan M71,
ADR 0035 amendment). Written only when ``output.include`` names it and a row has a note;
a note is printed nowhere else.

Laid out like the Summary BOM sheet, A4 landscape.
"""

from bomgen.models.bom import BuildResult
from bomgen.models.sheet import CellRange, CellValue, Formula, HeaderFooter, PrintSetup, SheetModel
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder
from bomgen.sheets.summary_sheet import CENTRE, HEADER, TEXT, TITLE_HEIGHT, TITLE_STYLE

HEADERS = ("SR.NO", "SHEET", "TAG", "DESCRIPTION", "NOTE")
WIDTHS = (8.0, 20.0, 30.0, 50.0, 60.0)
CELL_STYLES = (CENTRE, TEXT, TEXT, TEXT, TEXT)
TITLE = "Notes"


def noted_rows(result: BuildResult, loose_sheet: str) -> list[tuple[str, str | None, str, str]]:
    """(sheet, tag, description's first line, note) for every noted line, in sheet order."""
    tables = [(p.sheet_name, p.lines) for p in result.panels]
    if result.loose is not None:
        tables.append((loose_sheet, result.loose.lines))
    return [
        (sheet, line.tag, line.description.split("\n")[0], line.note)
        for sheet, lines in tables
        for line in lines
        if line.note
    ]


def notes_sheet(
    name: str,
    substation: str,
    rows: list[tuple[str, str | None, str, str]],
    header_footer: HeaderFooter | None = None,
) -> SheetModel:
    sheet = SheetBuilder(name)
    for col, width in enumerate(WIDTHS, start=1):
        sheet.width(col, width)
    last_col = len(HEADERS)
    sheet.merge(1, 1, 1, last_col, f"{substation}\n{TITLE}", TITLE_STYLE)
    sheet.height(1, TITLE_HEIGHT)
    for col, label in enumerate(HEADERS, start=1):
        sheet.set(2, col, label, HEADER)
    row = 2
    for values in rows:
        row += 1
        sr_no: CellValue = 1 if row == 3 else Formula(text=f"=A{row - 1}+1", result=row - 2)
        for col, (value, style) in enumerate(zip((sr_no, *values), CELL_STYLES, strict=True), 1):
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
