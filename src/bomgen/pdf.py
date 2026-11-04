"""PDF export of an issued workbook (plan M78, ADR 0039).

``render_pdf`` is the built-in renderer: it reads the written workbook with openpyxl and draws
the chosen sheets with ReportLab, following each sheet's print settings (OUT-7). Its pages are
close to Excel's, not identical. ``excel_pdf`` drives Excel on a Windows PC for exact pages.
"""

import math
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.cell.cell import Cell, MergedCell
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet
from reportlab.lib.pagesizes import A3, A4, LETTER
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

PAPER = {1: LETTER, 8: A3, 9: A4}
POINTS_PER_INCH = 72.0
DEFAULT_COLUMN = 8.43  # Excel's default column width in characters
DEFAULT_ROW = 15.0  # points
BORDER_WIDTH = {"hair": 0.25, "thin": 0.5, "medium": 1.0, "thick": 1.5, "double": 1.0}
HEADER_SIZE = 9.0
PADDING = 2.0


class PdfError(Exception):
    """The PDF was not written; the message says why."""


@dataclass(frozen=True)
class _Region:
    first_row: int
    first_col: int
    last_row: int
    last_col: int


def _column_points(width: float | None) -> float:
    """A column width in characters as Excel draws it, in points (7 px per character + 5)."""
    chars = DEFAULT_COLUMN if width is None else width
    return (math.trunc(chars * 7 + 5)) * 0.75


def _rgb(colour: Any) -> tuple[float, float, float] | None:
    value = getattr(colour, "rgb", None)
    if not isinstance(value, str) or len(value) != 8:
        return None  # a theme or indexed colour: drawn as the default
    try:
        red, green, blue = (int(value[i : i + 2], 16) / 255 for i in (2, 4, 6))
    except ValueError:
        return None
    return red, green, blue


def _decimals(number_format: str) -> int | None:
    match = re.search(r"0\.(0+)", number_format)
    if match:
        return len(match.group(1))
    return 0 if "0" in number_format else None


def _text(cell: Cell) -> str:
    value = cell.value
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float):
        fmt = cell.number_format or "General"
        places = _decimals(fmt)
        if "%" in fmt:
            return f"{value * 100:.{places or 0}f}%"
        if places is None:
            return f"{value:.10g}"
        grouping = "," if "#,##0" in fmt else ""
        return f"{value:{grouping}.{places}f}"
    if isinstance(value, datetime | date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _font(cell: Cell) -> tuple[str, float]:
    font = cell.font
    name = "Helvetica-Bold" if font.b else "Helvetica"
    if font.i:
        name = "Helvetica-BoldOblique" if font.b else "Helvetica-Oblique"
    return name, float(font.sz or 11)


def _header_text(item: Any, page: int, pages: int, sheet: str, file: str) -> str:
    text = str(getattr(item, "text", None) or "")
    text = re.sub(r'&"[^"]*"', "", text)
    text = re.sub(r"&\d+", "", text)
    stamp = datetime.now()
    swaps = {
        "&P": str(page),
        "&N": str(pages),
        "&D": stamp.strftime("%Y-%m-%d"),
        "&T": stamp.strftime("%H:%M"),
        "&A": sheet,
        "&F": file,
    }
    text = re.sub(r"&[PNDTAF]", lambda m: swaps[m.group(0)], text)
    text = re.sub(r"&[A-Za-z]", "", text)  # styles and pictures (&G): not drawn
    return text.replace("&&", "&")


class _Sheet:
    """One worksheet's print area laid out in points, with its page chunks."""

    def __init__(self, ws: Worksheet) -> None:
        self.ws = ws
        area = ws.print_area
        ref = area.split("!")[-1] if isinstance(area, str) else ws.dimensions
        first_col, first_row, last_col, last_row = range_boundaries(ref.replace("$", ""))
        assert first_col is not None
        assert first_row is not None
        assert last_col is not None
        assert last_row is not None
        dims = ws.column_dimensions
        letters = get_column_letter
        self.cols = [c for c in range(first_col, last_col + 1) if not dims[letters(c)].hidden]
        self.rows = [r for r in range(first_row, last_row + 1) if not ws.row_dimensions[r].hidden]
        self.widths = {c: _column_points(dims[letters(c)].width) for c in self.cols}
        self.heights = {r: float(ws.row_dimensions[r].height or DEFAULT_ROW) for r in self.rows}
        self.regions: dict[tuple[int, int], _Region] = {}
        for merged in ws.merged_cells.ranges:
            region = _Region(merged.min_row, merged.min_col, merged.max_row, merged.max_col)
            for r in range(merged.min_row, merged.max_row + 1):
                for c in range(merged.min_col, merged.max_col + 1):
                    self.regions[(r, c)] = region
        titles = ws.print_title_rows
        self.titles: list[int] = []
        if titles:
            top, bottom = (int(x) for x in titles.replace("$", "").split(":"))
            self.titles = [r for r in self.rows if top <= r <= bottom]

    def page_size(self) -> tuple[float, float]:
        paper: tuple[float, float] = PAPER.get(int(self.ws.page_setup.paperSize or 9), A4)
        if self.ws.page_setup.orientation == "landscape":
            return paper[1], paper[0]
        return paper

    def margins(self) -> tuple[float, float, float, float, float, float]:
        m = self.ws.page_margins
        return tuple(  # type: ignore[return-value]
            float(v) * POINTS_PER_INCH
            for v in (m.left, m.right, m.top, m.bottom, m.header, m.footer)
        )

    def scale(self, width: float, height: float) -> float:
        setup = self.ws.page_setup
        props = self.ws.sheet_properties.pageSetUpPr
        total_w = sum(self.widths.values())
        total_h = sum(self.heights.values())
        if props is not None and props.fitToPage:
            wide = 1 if setup.fitToWidth is None else int(setup.fitToWidth)
            tall = 1 if setup.fitToHeight is None else int(setup.fitToHeight)
            factor = 1.0
            if wide > 0 and total_w:
                factor = min(factor, width * wide / total_w)
            if tall > 0 and total_h:
                factor = min(factor, height * tall / total_h)
            return factor
        return float(setup.scale or 100) / 100

    def pages(self, width: float, height: float) -> list[tuple[list[int], list[int]]]:
        """The (columns, rows) on each page, down then over, as Excel orders them."""
        col_chunks: list[list[int]] = [[]]
        used = 0.0
        for c in self.cols:
            if col_chunks[-1] and used + self.widths[c] > width:
                col_chunks.append([])
                used = 0.0
            col_chunks[-1].append(c)
            used += self.widths[c]
        titles_h = sum(self.heights[r] for r in self.titles)
        row_chunks: list[list[int]] = [[]]
        used = 0.0
        for r in self.rows:
            if row_chunks[-1] and used + self.heights[r] > height:
                row_chunks.append([t for t in self.titles if t < r])
                used = titles_h if row_chunks[-1] else 0.0
            row_chunks[-1].append(r)
            used += self.heights[r]
        return [(cols, rows) for cols in col_chunks for rows in row_chunks]


def _draw_page(canvas: Canvas, sheet: _Sheet, cols: list[int], rows: list[int]) -> None:
    ws = sheet.ws
    x_of: dict[int, float] = {}
    x = 0.0
    for c in cols:
        x_of[c] = x
        x += sheet.widths[c]
    y_of: dict[int, float] = {}
    y = 0.0
    for r in rows:
        y_of[r] = y
        y += sheet.heights[r]
    drawn: set[_Region] = set()
    for r in rows:
        for c in cols:
            region = sheet.regions.get((r, c))
            if region is not None:
                if region in drawn:
                    continue
                drawn.add(region)
                span_c = [k for k in cols if region.first_col <= k <= region.last_col]
                span_r = [k for k in rows if region.first_row <= k <= region.last_row]
                top_left = ws.cell(region.first_row, region.first_col)
            else:
                span_c, span_r, top_left = [c], [r], ws.cell(r, c)
            left, top = x_of[span_c[0]], y_of[span_r[0]]
            width = sum(sheet.widths[k] for k in span_c)
            height = sum(sheet.heights[k] for k in span_r)
            spill = 0.0 if region is not None else _spill(sheet, r, c, cols, x_of)
            _draw_cell(canvas, top_left, left, top, width, height, spill)
            for rr in span_r:
                for cc in span_c:
                    _draw_borders(canvas, ws.cell(rr, cc), sheet, rr, cc, x_of, y_of)


def _spill(sheet: _Sheet, row: int, col: int, cols: list[int], x_of: dict[int, float]) -> float:
    """How far unwrapped left-aligned text may run on over the empty cells to its right."""
    cell = sheet.ws.cell(row, col)
    if not isinstance(cell.value, str) or cell.alignment.wrap_text:
        return 0.0
    if (cell.alignment.horizontal or "left") not in ("left", "general"):
        return 0.0
    spill = 0.0
    for nxt in cols[cols.index(col) + 1 :]:
        if (row, nxt) in sheet.regions or sheet.ws.cell(row, nxt).value is not None:
            break
        spill += sheet.widths[nxt]
    return spill


def _draw_cell(
    canvas: Canvas,
    cell: Cell | MergedCell,
    left: float,
    top: float,
    width: float,
    height: float,
    spill: float = 0.0,
) -> None:
    fill = cell.fill
    colour = _rgb(fill.fgColor) if fill is not None and fill.patternType == "solid" else None
    if colour is not None:
        canvas.setFillColorRGB(*colour)
        canvas.rect(left, -top - height, width, height, stroke=0, fill=1)
    if not isinstance(cell, Cell):
        return
    text = _text(cell)
    if not text:
        return
    name, size = _font(cell)
    align = cell.alignment
    lines: list[str] = []
    for part in text.split("\n"):
        wrapped = simpleSplit(part, name, size, width - 2 * PADDING) if align.wrap_text else None
        lines.extend(wrapped or [part])
    leading = size * 1.2
    block = leading * len(lines)
    vertical = align.vertical or "bottom"
    if vertical == "top":
        first = top + PADDING + size
    elif vertical == "center":
        first = top + (height - block) / 2 + size
    else:
        first = top + height - PADDING - block + size
    horizontal = align.horizontal or ("right" if isinstance(cell.value, int | float) else "left")
    canvas.saveState()
    clip = canvas.beginPath()
    clip.rect(left, -top - height, width + spill, height)
    canvas.clipPath(clip, stroke=0, fill=0)
    canvas.setFillColorRGB(*(_rgb(cell.font.color) or (0, 0, 0)))
    canvas.setFont(name, size)
    for index, line in enumerate(lines):
        baseline = -(first + index * leading)
        if horizontal in ("center", "centerContinuous"):
            canvas.drawCentredString(left + width / 2, baseline, line)
        elif horizontal == "right":
            canvas.drawRightString(left + width - PADDING, baseline, line)
        else:
            canvas.drawString(left + PADDING, baseline, line)
    canvas.restoreState()


def _draw_borders(
    canvas: Canvas,
    cell: Cell | MergedCell,
    sheet: _Sheet,
    row: int,
    col: int,
    x_of: dict[int, float],
    y_of: dict[int, float],
) -> None:
    region = sheet.regions.get((row, col)) or _Region(row, col, row, col)
    left, top = x_of[col], y_of[row]
    right, bottom = left + sheet.widths[col], top + sheet.heights[row]
    border = cell.border
    edges = (
        (border.left, col == region.first_col, (left, top, left, bottom)),
        (border.right, col == region.last_col, (right, top, right, bottom)),
        (border.top, row == region.first_row, (left, top, right, top)),
        (border.bottom, row == region.last_row, (left, bottom, right, bottom)),
    )
    for side, outer, (x1, y1, x2, y2) in edges:
        style = getattr(side, "style", None)
        if not outer or style is None:
            continue
        canvas.setStrokeColorRGB(*(_rgb(side.color) or (0, 0, 0)))
        canvas.setLineWidth(BORDER_WIDTH.get(style, 0.5))
        canvas.line(x1, -y1, x2, -y2)


def render_pdf(workbook: Path, out: Path, sheets: Sequence[str] | None = None) -> int:
    """Draw ``sheets`` (default: every visible sheet, in order) into ``out``; the page count."""
    book = openpyxl.load_workbook(workbook, data_only=True)
    names = [ws.title for ws in book.worksheets if ws.sheet_state == "visible"]
    chosen = list(names if sheets is None else sheets)
    for name in chosen:
        if name not in book.sheetnames:
            raise PdfError(f"The workbook has no sheet {name!r}.")
    if not chosen:
        raise PdfError("Choose at least one sheet.")
    canvas = Canvas(str(out))
    total = 0
    for name in chosen:
        sheet = _Sheet(book[name])
        page_w, page_h = sheet.page_size()
        left, right, top, bottom, _, _ = sheet.margins()
        area_w, area_h = page_w - left - right, page_h - top - bottom
        factor = sheet.scale(area_w, area_h)
        chunks = sheet.pages(area_w / factor, area_h / factor)
        centred = bool(sheet.ws.print_options.horizontalCentered)
        for number, (cols, rows) in enumerate(chunks, start=1):
            canvas.setPageSize((page_w, page_h))
            used = sum(sheet.widths[c] for c in cols) * factor
            x0 = left + ((area_w - used) / 2 if centred else 0)
            canvas.saveState()
            canvas.translate(x0, page_h - top)
            canvas.scale(factor, factor)
            _draw_page(canvas, sheet, cols, rows)
            canvas.restoreState()
            draw_header_footer(canvas, sheet, number, len(chunks), workbook.name, factor)
            canvas.showPage()
            total += 1
    canvas.save()
    return total


def draw_header_footer(
    canvas: Canvas, sheet: _Sheet, page: int, pages: int, file: str, factor: float
) -> None:
    """The page header and footer, scaled with the sheet as Excel's default does."""
    page_w, page_h = sheet.page_size()
    left, right, _, _, head, foot = sheet.margins()
    ws = sheet.ws
    canvas.setFillColorRGB(0, 0, 0)
    for item, at_top in ((ws.oddHeader, True), (ws.oddFooter, False)):
        if item is None:
            continue
        for part, anchor in ((item.left, "left"), (item.center, "center"), (item.right, "right")):
            text = _header_text(part, page, pages, ws.title, file)
            if not text:
                continue
            size = float(part.size or HEADER_SIZE) * factor
            lines = text.split("\n")
            canvas.setFont("Helvetica-Bold" if "Bold" in (part.font or "") else "Helvetica", size)
            for index, line in enumerate(lines):
                offset = index if at_top else index - len(lines) + 1
                step = offset * size * 1.2
                y = page_h - head - size - step if at_top else foot - step
                if anchor == "left":
                    canvas.drawString(left, y, line)
                elif anchor == "center":
                    canvas.drawCentredString(page_w / 2, y, line)
                else:
                    canvas.drawRightString(page_w - right, y, line)


def excel_refusal() -> str | None:
    """Why Excel can't export here, or None when it can."""
    if sys.platform != "win32":
        return "Export with Excel needs Windows with Excel installed."
    import winreg

    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Excel.Application\CLSID").Close()
    except OSError:
        return "Excel is not installed on this PC."
    return None


def _quoted(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def excel_script(workbook: Path, out: Path, sheets: Sequence[str]) -> str:
    """The PowerShell that has Excel select ``sheets`` and export them as one PDF."""
    select = "\n".join(
        f"  $book.Worksheets.Item({_quoted(name)}).Select(${'true' if i == 0 else 'false'})"
        for i, name in enumerate(sheets)
    )
    return f"""$ErrorActionPreference = 'Stop'
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {{
  $book = $excel.Workbooks.Open({_quoted(workbook.as_posix())}, 0, $true)
{select}
  $excel.ActiveSheet.ExportAsFixedFormat(0, {_quoted(out.as_posix())})
  $book.Close($false)
}} finally {{
  $excel.Quit()
}}
"""


Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def excel_pdf(
    workbook: Path, out: Path, sheets: Sequence[str], run: Runner = subprocess.run
) -> None:
    """Have Excel on this PC print ``sheets`` of ``workbook`` to ``out`` (ADR 0039)."""
    if not sheets:
        raise PdfError("Choose at least one sheet.")
    args = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
    script = excel_script(workbook.resolve(), out.resolve(), sheets)
    try:
        done = run([*args, script], capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PdfError(f"Excel did not write the PDF: {exc}") from None
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip().splitlines()
        raise PdfError(f"Excel did not write the PDF: {detail[0] if detail else 'no reason'}")
    if not out.is_file():
        raise PdfError("Excel did not write the PDF.")
