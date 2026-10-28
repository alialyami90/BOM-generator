"""Panel BOM sheets and the Loose Material sheet (plan M5, step 12; M18).

Layout per the spec sections "How each panel BOM groups its materials", "Columns of a
panel BOM" and "Formatting → Panel BOM sheets"; one sheet per cabinet with column H
(HWIO) hidden (ADR 0004). The loose-material table has its own sheet with the same
layout (ADR 0020).
"""

from dataclasses import dataclass

from bomgen.models.bom import BomLine, BomTable, Group, LooseTable, PanelBom, QtySum
from bomgen.models.calc import LineRef
from bomgen.models.sheet import (
    CellRange,
    CellStyle,
    CellValue,
    Formula,
    HeaderFooter,
    PrintSetup,
    SheetModel,
)
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder

HEADERS = ("SR.NO", "ITEM DESIGNATION", "DESCRIPTION", "QUANTITY", "MAKE", "MODEL", "ORDERING CODE")
HWIO_HEADER = "HWIO"
WIDTHS = (12.29, 53.71, 108.71, 23.14, 22.29, 43.43, 60.57)
HWIO_WIDTH = 25.0
SPACER_WIDTH = 4.57
LAST_COL = 7  # G
HWIO_COL = 8  # H
SPACER_COL = 9  # I

TITLE_HEIGHT = 90.0
HEADER_HEIGHT = 26.25
LINE_HEIGHT = 26.25  # per line of wrapped text
BODY_MIN_HEIGHT = 30.0
LONG_CODE_HEIGHT = 52.5
LONG_CODE_CHARS = 40
ZOOM = 60

_COLUMN_LETTERS = "ABCDEFG"


@dataclass(frozen=True)
class BomSheet:
    model: SheetModel
    rows: dict[LineRef, int]  # the row of every BOM line on this sheet


def bom_sheet(panel: PanelBom, header_footer: HeaderFooter | None = None) -> BomSheet:
    """Lay out ``panel``'s BOM on its own sheet."""
    return _table_sheet(panel.sheet_name, panel, panel.panel_id, header_footer)


def loose_sheet(
    name: str, loose: LooseTable, header_footer: HeaderFooter | None = None
) -> BomSheet:
    """Lay out the loose-material table on its own sheet ``name`` (ADR 0020)."""
    return _table_sheet(name, loose, None, header_footer)


def _table_sheet(
    name: str, table: BomTable, panel_id: str | None, header_footer: HeaderFooter | None
) -> BomSheet:
    """``table`` with its title in row 1, header in row 2 and lines from row 3; the
    rows map ``LineRef(panel_id, line)``."""
    sheet = SheetBuilder(name)
    for col, width in enumerate(WIDTHS, start=1):
        sheet.width(col, width)
    sheet.width(HWIO_COL, HWIO_WIDTH, hidden=True)
    sheet.width(SPACER_COL, SPACER_WIDTH)

    _title(sheet, 1, table.title)
    _header(sheet, 2, HEADER_HEIGHT)
    sheet.set(2, HWIO_COL, HWIO_HEADER, styles.BOM_HEADER)
    line_rows = _lines(sheet, table, first_row=3)
    rows = {LineRef(panel_id=panel_id, line=i): r for i, r in line_rows.items()}
    last = max(line_rows.values(), default=2)
    hwio = sum(line.hwio for line in table.lines)
    sheet.set(1, HWIO_COL, Formula(text=f"=SUM(H3:H{last})", result=hwio), styles.BOM_HEADER)

    setup = PrintSetup(
        orientation="portrait",
        fit_to_width=1,
        fit_to_height=0,
        margins=styles.BOM_MARGINS,
        center_horizontally=True,
        print_area=CellRange(first_row=1, first_col=1, last_row=last, last_col=LAST_COL),
        repeat_rows=(1, 2),
        zoom=ZOOM,
    )
    return BomSheet(model=sheet.build(setup, header_footer), rows=rows)


def _title(sheet: SheetBuilder, row: int, title: tuple[str, str]) -> None:
    sheet.merge(row, 1, row, LAST_COL, "\n".join(title), styles.BOM_TITLE)
    sheet.height(row, TITLE_HEIGHT)


def _header(sheet: SheetBuilder, row: int, height: float) -> None:
    for col, label in enumerate(HEADERS, start=1):
        sheet.set(row, col, label, styles.BOM_HEADER)
    sheet.height(row, height)


def _lines(sheet: SheetBuilder, table: BomTable, first_row: int) -> dict[int, int]:
    """Write ``table``'s lines from ``first_row``; return line index → row."""
    separators = set(table.separators_before())
    line_rows: dict[int, int] = {}
    row = first_row
    previous: int | None = None
    for index, line in enumerate(table.lines):
        if index in separators:
            for col in range(1, LAST_COL + 1):
                sheet.set(row, col, None, styles.BOM_SEPARATOR)
            sheet.height(row, BODY_MIN_HEIGHT)
            row += 1
        number = len(line_rows) + 1
        sr_no: CellValue = 1 if previous is None else Formula(text=f"=A{previous}+1", result=number)
        _line(sheet, row, line, sr_no)
        line_rows[index] = row
        previous = row
        row += 1
    _merges(sheet, table.lines, line_rows)
    return line_rows


def _line(sheet: SheetBuilder, row: int, line: BomLine, sr_no: CellValue) -> None:
    grounding = line.group is Group.H
    values: tuple[CellValue, ...] = (
        sr_no,
        line.tag,
        line.description,
        _qty(line),
        line.make,
        line.model,
        line.ordering_code,
    )
    cell_styles = (
        styles.BOM_CENTRE,
        styles.BOM_DESIGNATION,
        styles.BOM_DESCRIPTION,
        styles.BOM_CENTRE,
        styles.BOM_CENTRE,
        styles.BOM_CENTRE_WRAP,
        styles.BOM_CENTRE_WRAP,
    )
    for col, (value, style) in enumerate(zip(values, cell_styles, strict=True), start=1):
        letter = _COLUMN_LETTERS[col - 1]
        sheet.set(row, col, value, _cell_style(style, grounding, letter in line.revised))
    if line.hwio:
        sheet.set(row, HWIO_COL, line.hwio, styles.BOM_CENTRE)
    sheet.height(row, _height(line))


def _cell_style(style: CellStyle, grounding: bool, revised: bool) -> CellStyle:
    if grounding:
        style = styles.with_fill(style, styles.WHITE)
    if revised:
        style = styles.with_fill(style, styles.YELLOW)
    return style


def _qty(line: BomLine) -> CellValue:
    qty = line.qty
    if isinstance(qty, QtySum):
        return Formula(text="=" + "+".join(str(part) for part in qty.parts), result=qty.value)
    return qty


def _height(line: BomLine) -> float:
    text_lines = line.description.count("\n") + 1
    if line.group is Group.H:
        return LINE_HEIGHT * (text_lines + 2)
    height = max(BODY_MIN_HEIGHT, LINE_HEIGHT * text_lines)
    if len(line.ordering_code or "") > LONG_CODE_CHARS:
        height = max(height, LONG_CODE_HEIGHT)
    return height


def _merges(sheet: SheetBuilder, lines: tuple[BomLine, ...], line_rows: dict[int, int]) -> None:
    """Parent tag over its children; with ``merge_fg``, F and G over the empty children."""
    for index, line in enumerate(lines):
        children = [i for i, child in enumerate(lines) if child.parent == index]
        if not children:
            continue
        first = line_rows[index]
        sheet.span(first, 2, line_rows[max(children)], 2)
        if not line.merge_fg:
            continue
        for col, field in ((6, "model"), (7, "ordering_code")):
            end = index
            while end + 1 in children and getattr(lines[end + 1], field) is None:
                end += 1
            if end > index:
                sheet.span(first, col, line_rows[end], col)
