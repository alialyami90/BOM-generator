"""Translate a ``WorkbookModel`` into an .xlsx file with XlsxWriter.

This module adds no content of its own: values, formulas, styles, layout, print
setup and header/footer text all come from the sheet models (ADR 0005). XlsxWriter
writes ``fullCalcOnLoad`` into every workbook, so Excel recalculates the live
formulas when the file opens (OUT-5).
"""

from pathlib import Path
from typing import Any

from xlsxwriter import Workbook
from xlsxwriter.format import Format
from xlsxwriter.worksheet import Worksheet

from bomgen.models.sheet import (
    BorderStyle,
    Cell,
    CellStyle,
    Formula,
    SheetModel,
    WorkbookModel,
    cell_name,
)

_WORKBOOK_OPTIONS = {
    # Only Formula cells become formulas; text such as "=24+3", "0012" or a URL stays text.
    "strings_to_numbers": False,
    "strings_to_formulas": False,
    "strings_to_urls": False,
}
_BORDER_CODES = {BorderStyle.NONE: 0, BorderStyle.THIN: 1, BorderStyle.MEDIUM: 2}
_VERTICAL = {"top": "top", "center": "vcenter", "bottom": "bottom"}


class WriterError(Exception):
    """The workbook could not be written as the sheet models describe it."""


class _Formats:
    """One XlsxWriter ``Format`` per distinct ``CellStyle``."""

    def __init__(self, workbook: Workbook) -> None:
        self._workbook = workbook
        self._cache: dict[CellStyle, Format] = {}

    def get(self, style: CellStyle | None) -> Format | None:
        if style is None:
            return None
        if style not in self._cache:
            self._cache[style] = self._workbook.add_format(_format_properties(style))
        return self._cache[style]


def _format_properties(style: CellStyle) -> dict[str, Any]:
    font, align, borders = style.font, style.alignment, style.borders
    props: dict[str, Any] = {
        "font_name": font.name,
        "font_size": font.size,
        "bold": font.bold,
        "underline": 1 if font.underline == "single" else 0,
        "font_color": font.color,
        "valign": _VERTICAL[align.vertical],
        "text_wrap": align.wrap,
        "left": _BORDER_CODES[borders.left],
        "right": _BORDER_CODES[borders.right],
        "top": _BORDER_CODES[borders.top],
        "bottom": _BORDER_CODES[borders.bottom],
        "num_format": style.number_format,
    }
    if align.horizontal != "general":
        props["align"] = align.horizontal
    if style.fill is not None:
        props["pattern"] = 1
        props["bg_color"] = style.fill
    return props


def _check(result: int | None, where: str) -> None:
    """XlsxWriter reports problems as negative return codes; turn them into errors."""
    if result is not None and result < 0:
        raise WriterError(f"{where}: XlsxWriter refused the value (code {result})")


def _write_cell(ws: Worksheet, row: int, col: int, cell: Cell, fmt: Format | None) -> None:
    r, c, value = row - 1, col - 1, cell.value
    if isinstance(value, Formula):
        result = ws.write_formula(r, c, value.text, fmt, value.result)
    elif isinstance(value, str) and value:
        result = ws.write_string(r, c, value, fmt)
    elif isinstance(value, int | float):
        result = ws.write_number(r, c, value, fmt)
    else:
        result = ws.write_blank(r, c, None, fmt)
    _check(result, f"sheet {ws.name!r} cell {cell_name(row, col)}")


def _write_sheet(ws: Worksheet, sheet: SheetModel, formats: _Formats) -> None:
    for (row, col), cell in sorted(sheet.cells.items()):
        _write_cell(ws, row, col, cell, formats.get(cell.style))


def write_workbook(workbook: WorkbookModel, path: Path) -> Path:
    """Write ``workbook`` to ``path`` (parent directories are created) and return ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook(str(path), _WORKBOOK_OPTIONS)
    try:
        formats = _Formats(book)
        for sheet in workbook.sheets:
            _write_sheet(book.add_worksheet(sheet.name), sheet, formats)
    except BaseException:
        book.fileclosed = True  # nothing was written yet; skip XlsxWriter's close-on-delete
        raise
    book.close()
    return path
