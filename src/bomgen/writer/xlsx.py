"""Translate a ``WorkbookModel`` into an .xlsx file with XlsxWriter.

This module adds no content of its own: values, formulas, styles, layout, print
setup and header/footer text all come from the sheet models (ADR 0005). XlsxWriter
writes ``fullCalcOnLoad`` into every workbook, so Excel recalculates the live
formulas when the file opens (OUT-5).
"""

import contextlib
import os
import secrets
import struct
from pathlib import Path
from typing import Any

from xlsxwriter import Workbook
from xlsxwriter.exceptions import XlsxWriterException
from xlsxwriter.format import Format
from xlsxwriter.worksheet import Worksheet

from bomgen.models.sheet import (
    BorderStyle,
    Cell,
    CellStyle,
    Formula,
    HFRun,
    HFZone,
    PrintSetup,
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
_A4 = 9
_PAGE_BREAK_PREVIEW = 2
_CM_PER_INCH = 2.54
_MAX_HEADER_FOOTER_CHARS = 255  # Excel's limit; XlsxWriter only warns and drops longer ones
_FIELD_CODES = {"page": "&P", "pages": "&N"}
_ZONE_CODES = ("&L", "&C", "&R")
_IMAGE_OPTIONS = ("image_left", "image_center", "image_right")
# XlsxWriter 3.2 raises struct.error on a truncated picture instead of its own exception.
_XLSXWRITER_ERRORS = (XlsxWriterException, struct.error)


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


def _write_merges(ws: Worksheet, sheet: SheetModel, formats: _Formats) -> None:
    """Merge each range with its anchor's style, then write the anchor's typed value."""
    for merge in sheet.merges:
        anchor = sheet.cells.get((merge.first_row, merge.first_col), Cell())
        fmt = formats.get(anchor.style)
        first = (merge.first_row - 1, merge.first_col - 1)
        last = (merge.last_row - 1, merge.last_col - 1)
        _check(ws.merge_range(*first, *last, "", fmt), f"sheet {ws.name!r} merge {merge.name}")
        _write_cell(ws, merge.first_row, merge.first_col, anchor, fmt)


def _write_dimensions(ws: Worksheet, sheet: SheetModel) -> None:
    for col, column in sorted(sheet.columns.items()):
        ws.set_column(col - 1, col - 1, column.width, None, {"hidden": column.hidden})
    for row, row_format in sorted(sheet.rows.items()):
        ws.set_row(row - 1, row_format.height)


def _write_print_setup(ws: Worksheet, setup: PrintSetup) -> None:
    ws.set_paper(_A4)
    if setup.orientation == "landscape":
        ws.set_landscape()
    else:
        ws.set_portrait()
    if setup.fit_to_page:
        width = 1 if setup.fit_to_width is None else setup.fit_to_width
        height = 1 if setup.fit_to_height is None else setup.fit_to_height
        ws.fit_to_pages(width, height)
    elif setup.scale is not None:
        ws.set_print_scale(setup.scale)
    m = setup.margins
    ws.set_margins(
        left=m.left_cm / _CM_PER_INCH,
        right=m.right_cm / _CM_PER_INCH,
        top=m.top_cm / _CM_PER_INCH,
        bottom=m.bottom_cm / _CM_PER_INCH,
    )
    if setup.center_horizontally:
        ws.center_horizontally()
    if setup.print_area is not None:
        area = setup.print_area
        ws.print_area(area.first_row - 1, area.first_col - 1, area.last_row - 1, area.last_col - 1)
    if setup.repeat_rows is not None:
        ws.repeat_rows(setup.repeat_rows[0] - 1, setup.repeat_rows[1] - 1)
    if setup.page_break_preview:
        ws.set_page_view(_PAGE_BREAK_PREVIEW)
    if setup.zoom is not None:
        ws.set_zoom(setup.zoom)


def _render_zone(code: str, zone: HFZone) -> str:
    """Render one zone as Excel header/footer codes; each run states its font when it changes."""
    if zone.image is None and not zone.lines:
        return ""
    parts = [code, "&G" if zone.image is not None else ""]
    state: tuple[str, bool, int] | None = None
    for i, line in enumerate(zone.lines):
        if i:
            parts.append("\n")
        for run in line:
            if (run.font, run.bold, run.size) != state:
                parts.append(_font_codes(run))
                state = (run.font, run.bold, run.size)
            parts.append(_FIELD_CODES[run.field] if run.field else run.text.replace("&", "&&"))
    return "".join(parts)


def _font_codes(run: HFRun) -> str:
    # Size before font name: a size code directly followed by text starting with a digit
    # ("&11861-GIS01") would be read as one larger size.
    weight = "Bold" if run.bold else "Regular"
    return f'&{run.size}&"{run.font},{weight}"'


def _render(
    zones: tuple[HFZone, HFZone, HFZone], what: str, sheet: str
) -> tuple[str, dict[str, Any]]:
    text = "".join(_render_zone(code, zone) for code, zone in zip(_ZONE_CODES, zones, strict=True))
    if len(text) > _MAX_HEADER_FOOTER_CHARS:
        raise WriterError(
            f"the {what} of sheet {sheet!r} is {len(text)} characters with its formatting codes; "
            f"Excel allows {_MAX_HEADER_FOOTER_CHARS}"
        )
    images = {
        option: str(zone.image)
        for option, zone in zip(_IMAGE_OPTIONS, zones, strict=True)
        if zone.image is not None
    }
    return text, images


def _write_header_footer(ws: Worksheet, sheet: SheetModel) -> None:
    margins = sheet.print_setup.margins
    header, header_images = "", dict[str, Any]()
    footer, footer_images = "", dict[str, Any]()
    if sheet.header_footer is not None:
        hf = sheet.header_footer
        header, header_images = _render(hf.header_zones, "header", sheet.name)
        footer, footer_images = _render(hf.footer_zones, "footer", sheet.name)
    ws.set_header(header, {**header_images, "margin": margins.header_cm / _CM_PER_INCH})
    ws.set_footer(footer, {**footer_images, "margin": margins.footer_cm / _CM_PER_INCH})


def _write_sheet(ws: Worksheet, sheet: SheetModel, formats: _Formats) -> None:
    for (row, col), cell in sorted(sheet.cells.items()):
        _write_cell(ws, row, col, cell, formats.get(cell.style))
    _write_merges(ws, sheet, formats)
    _write_dimensions(ws, sheet)
    _write_print_setup(ws, sheet.print_setup)
    _write_header_footer(ws, sheet)


def _check_images(workbook: WorkbookModel) -> None:
    for sheet in workbook.sheets:
        if sheet.header_footer is None:
            continue
        zones = sheet.header_footer.header_zones + sheet.header_footer.footer_zones
        for zone in zones:
            if zone.image is not None and not zone.image.is_file():
                raise WriterError(f"header/footer picture not found: {zone.image}")


def write_workbook(workbook: WorkbookModel, path: Path) -> Path:
    """Write ``workbook`` to ``path`` (parent directories are created) and return ``path``.

    The file is written beside ``path`` and then moved onto it, so a workbook
    already at ``path`` is replaced only by a complete one. Raises ``WriterError``
    when the workbook cannot be written as modelled or cannot replace ``path``
    (its ``__cause__`` tells a file open in Excel, a ``PermissionError``, from
    other errors); ``path`` is then left as it was.
    """
    _check_images(workbook)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.stem}.tmp-{secrets.token_hex(8)}{path.suffix}")
    try:
        _write(workbook, temp, path)
        os.replace(temp, path)
    except OSError as exc:
        raise WriterError(f"could not write {path}: {exc}") from exc
    finally:
        with contextlib.suppress(OSError):
            temp.unlink(missing_ok=True)  # a half-written file must not linger
    return path


def _write(workbook: WorkbookModel, temp: Path, path: Path) -> None:
    """Write ``workbook`` to ``temp``; errors name ``path``, the file the user asked for."""
    book = Workbook(str(temp), _WORKBOOK_OPTIONS)
    try:
        formats = _Formats(book)
        for sheet in workbook.sheets:
            _write_sheet(book.add_worksheet(sheet.name), sheet, formats)
    except BaseException as exc:
        # Nothing is on disk yet; skip XlsxWriter's close-on-delete. ``fileclosed`` is
        # undocumented; checked against XlsxWriter 3.2.9 and 3.3.0.
        book.fileclosed = True
        if isinstance(exc, _XLSXWRITER_ERRORS):
            raise WriterError(f"could not write {path}: {exc}") from exc
        raise
    try:
        book.close()
    except _XLSXWRITER_ERRORS as exc:
        raise WriterError(f"could not write {path}: {exc}") from exc
