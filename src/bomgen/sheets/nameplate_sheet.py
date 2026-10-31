"""The Nameplates sheet: every plate's text per panel, after Loose Material (ADR 0026).

Laid out and printed like a panel BOM ("Formatting → Panel BOM sheets"): merged title in
row 1, header in row 2, rows 1-2 repeated, A4 portrait.
"""

from collections.abc import Mapping, Sequence

from bomgen.models.bom import PanelNameplates
from bomgen.models.sheet import CellRange, CellValue, Formula, HeaderFooter, PrintSetup, SheetModel
from bomgen.sheets import styles
from bomgen.sheets.bom_sheet import BODY_MIN_HEIGHT, HEADER_HEIGHT, TITLE_HEIGHT, ZOOM
from bomgen.sheets.grid import SheetBuilder

HEADERS = ("SR.NO", "PANEL", "PLATE TEXT", "DEVICE")
WIDTHS = (12.29, 43.43, 53.71, 108.71)
LAST_COL = len(HEADERS)
TITLE = "Device Nameplates"


def nameplate_sheet(
    name: str,
    substation: str,
    panels: Sequence[PanelNameplates],
    cabinet_numbers: Mapping[str, str],
    header_footer: HeaderFooter | None = None,
) -> SheetModel:
    """One row per plate, panel by panel, SR.NO continuing."""
    sheet = SheetBuilder(name)
    for col, width in enumerate(WIDTHS, start=1):
        sheet.width(col, width)
    sheet.merge(1, 1, 1, LAST_COL, f"{substation}\n{TITLE}", styles.BOM_TITLE)
    sheet.height(1, TITLE_HEIGHT)
    for col, label in enumerate(HEADERS, start=1):
        sheet.set(2, col, label, styles.BOM_HEADER)
    sheet.height(2, HEADER_HEIGHT)
    row = 2
    for panel in panels:
        for plate in panel.plates:
            row += 1
            sr_no: CellValue = 1 if row == 3 else Formula(text=f"=A{row - 1}+1", result=row - 2)
            values = (sr_no, cabinet_numbers[panel.panel_id], plate.text, plate.device)
            cell_styles = (
                styles.BOM_CENTRE,
                styles.BOM_CENTRE,
                styles.BOM_DESIGNATION,
                styles.BOM_DESCRIPTION,
            )
            for col, (value, style) in enumerate(zip(values, cell_styles, strict=True), start=1):
                sheet.set(row, col, value, style)
            sheet.height(row, BODY_MIN_HEIGHT)
    setup = PrintSetup(
        orientation="portrait",
        fit_to_width=1,
        fit_to_height=0,
        margins=styles.BOM_MARGINS,
        center_horizontally=True,
        print_area=CellRange(first_row=1, first_col=1, last_row=row, last_col=LAST_COL),
        repeat_rows=(1, 2),
        zoom=ZOOM,
    )
    return sheet.build(setup, header_footer)
