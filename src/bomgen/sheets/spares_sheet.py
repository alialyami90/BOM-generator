"""The Spare Parts sheet: the spares list after the Summary BOM (ADR 0035, plan M64).

Laid out like the Summary BOM sheet, A4 landscape. INSTALLED QTY references the Summary
BOM quantity when that sheet is written, else is the summed value; a policy line's SPARE
QTY is a formula on it (OUT-5), an overridden line or an extra a value.
"""

from bomgen.models.bom import SparesTable
from bomgen.models.sheet import CellRange, CellValue, Formula, HeaderFooter, PrintSetup, SheetModel
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder, quote_sheet
from bomgen.sheets.summary_sheet import CENTRE, HEADER, TEXT, TITLE_HEIGHT, TITLE_STYLE

HEADERS = (
    "SR.NO",
    "DESCRIPTION",
    "INSTALLED QTY",
    "SPARE QTY",
    "MAKE",
    "MODEL",
    "ORDERING CODE",
    "BASIS",
)
WIDTHS = (8.0, 48.0, 12.0, 12.0, 16.0, 22.0, 30.0, 30.0)
CELL_STYLES = (CENTRE, TEXT, CENTRE, CENTRE, TEXT, TEXT, TEXT, TEXT)
TITLE = "Spare Parts"
SUMMARY_QTY_COL = "C"  # QUANTITY on the Summary BOM sheet
SUMMARY_FIRST_ROW = 3


def spares_sheet(
    name: str,
    substation: str,
    table: SparesTable,
    summary_sheet: str | None,
    header_footer: HeaderFooter | None = None,
) -> SheetModel:
    """``summary_sheet`` names the Summary BOM sheet when the workbook has one."""
    sheet = SheetBuilder(name)
    for col, width in enumerate(WIDTHS, start=1):
        sheet.width(col, width)
    last_col = len(HEADERS)
    sheet.merge(1, 1, 1, last_col, f"{substation}\n{TITLE}", TITLE_STYLE)
    sheet.height(1, TITLE_HEIGHT)
    for col, label in enumerate(HEADERS, start=1):
        sheet.set(2, col, label, HEADER)
    row = 2
    for line in table.lines:
        row += 1
        sr_no: CellValue = 1 if row == 3 else Formula(text=f"=A{row - 1}+1", result=row - 2)
        installed: CellValue = line.installed
        if summary_sheet is not None and line.summary_line is not None:
            source = SUMMARY_FIRST_ROW + line.summary_line
            text = f"={quote_sheet(summary_sheet)}!{SUMMARY_QTY_COL}{source}"
            installed = Formula(text=text, result=line.installed)
        spare: CellValue = line.spare
        if line.percent is not None:
            text = f"=MAX({line.minimum},ROUNDUP(C{row}*{line.percent:g}/100,0))"
            spare = Formula(text=text, result=line.spare)
        values = (
            sr_no,
            line.description,
            installed,
            spare,
            line.make,
            line.model,
            line.ordering_code,
            line.basis,
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
