"""Sheet models: library-agnostic workbook layout that the writer translates to .xlsx.

The sheet layer builds these from the engine's results (ADR 0005); the writer is
the only code that knows about XlsxWriter (ADR 0003). Units follow the spec's
"Formatting" section: widths in Excel character units as Excel shows them,
heights in points, margins in cm. Rows and columns are 1-based (row 1, column 1
is A1).
"""

import math
import re
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from bomgen.models._base import ExcelSheetName

MAX_ROW = 1_048_576
MAX_COL = 16_384

_HEX_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class SheetBase(BaseModel):
    """Base for every sheet model: unknown fields are errors and instances are immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _check_colour(value: str) -> str:
    if not _HEX_COLOUR.match(value):
        raise ValueError("colour must be #RRGGBB")
    return value.upper()


def _check_finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("number must be finite")
    return value


Color = Annotated[str, AfterValidator(_check_colour)]
Number = StrictInt | Annotated[StrictFloat, AfterValidator(_check_finite)]
RowIndex = Annotated[int, Field(ge=1, le=MAX_ROW)]
ColIndex = Annotated[int, Field(ge=1, le=MAX_COL)]


def column_letter(col: int) -> str:
    """Return the Excel column letters of a 1-based column number (1 → A, 28 → AB)."""
    letters = ""
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def cell_name(row: int, col: int) -> str:
    """Return the A1-style name of a 1-based cell."""
    return f"{column_letter(col)}{row}"


class Formula(SheetBase):
    """A live Excel formula; ``result`` is the cached value shown before Excel recalculates."""

    text: StrictStr
    result: Number | StrictStr | None = None

    @field_validator("text")
    @classmethod
    def _starts_with_equals(cls, value: str) -> str:
        if not value.startswith("="):
            raise ValueError("formula text must start with '='")
        return value


CellValue = StrictStr | Number | Formula | None


class Font(SheetBase):
    name: str = "Calibri"
    size: Annotated[float, Field(gt=0, le=409)] = 11.0
    bold: bool = False
    underline: Literal["none", "single"] = "none"
    color: Color = "#000000"


class Alignment(SheetBase):
    horizontal: Literal["general", "left", "center", "right"] = "general"
    vertical: Literal["top", "center", "bottom"] = "bottom"
    wrap: bool = False


class BorderStyle(StrEnum):
    NONE = "none"
    THIN = "thin"
    MEDIUM = "medium"


class Borders(SheetBase):
    left: BorderStyle = BorderStyle.NONE
    right: BorderStyle = BorderStyle.NONE
    top: BorderStyle = BorderStyle.NONE
    bottom: BorderStyle = BorderStyle.NONE

    @classmethod
    def all(cls, style: BorderStyle) -> "Borders":
        return cls(left=style, right=style, top=style, bottom=style)


class CellStyle(SheetBase):
    """Everything about how one cell looks; equal styles share one Excel format."""

    font: Font = Font()
    fill: Color | None = None
    alignment: Alignment = Alignment()
    borders: Borders = Borders()
    number_format: str = "General"


class Cell(SheetBase):
    value: CellValue = None
    style: CellStyle | None = None


class CellRange(SheetBase):
    """A rectangle of cells, first corner top-left."""

    first_row: RowIndex
    first_col: ColIndex
    last_row: RowIndex
    last_col: ColIndex

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.last_row < self.first_row or self.last_col < self.first_col:
            raise ValueError("first row/column must not come after the last row/column")
        return self

    def contains(self, row: int, col: int) -> bool:
        return self.first_row <= row <= self.last_row and self.first_col <= col <= self.last_col

    def overlaps(self, other: "CellRange") -> bool:
        return not (
            other.first_row > self.last_row
            or other.last_row < self.first_row
            or other.first_col > self.last_col
            or other.last_col < self.first_col
        )

    @property
    def name(self) -> str:
        first = cell_name(self.first_row, self.first_col)
        return f"{first}:{cell_name(self.last_row, self.last_col)}"


class Merge(CellRange):
    """Merged cells; the top-left cell holds the value and its style covers the range."""

    @model_validator(mode="after")
    def _two_or_more_cells(self) -> Self:
        if self.first_row == self.last_row and self.first_col == self.last_col:
            raise ValueError("a merge must span at least two cells")
        return self


class ColumnFormat(SheetBase):
    width: Annotated[float, Field(ge=0, le=255)] | None = None
    hidden: bool = False


class RowFormat(SheetBase):
    height: Annotated[float, Field(ge=0, le=409)] | None = None


class Margins(SheetBase):
    """Page margins in cm; header/footer margins are the distance from the paper edge."""

    left_cm: Annotated[float, Field(ge=0)] = 1.0
    right_cm: Annotated[float, Field(ge=0)] = 1.0
    top_cm: Annotated[float, Field(ge=0)] = 3.0
    bottom_cm: Annotated[float, Field(ge=0)] = 2.0
    header_cm: Annotated[float, Field(ge=0)] = 0.8
    footer_cm: Annotated[float, Field(ge=0)] = 0.8


Percent = Annotated[int, Field(ge=10, le=400)]


class PrintSetup(SheetBase):
    paper: Literal["A4"] = "A4"
    orientation: Literal["portrait", "landscape"] = "portrait"
    scale: Percent | None = None
    fit_to_width: Annotated[int, Field(ge=0)] | None = None
    fit_to_height: Annotated[int, Field(ge=0)] | None = None
    margins: Margins = Margins()
    center_horizontally: bool = False
    print_area: CellRange | None = None
    repeat_rows: tuple[RowIndex, RowIndex] | None = None
    page_break_preview: bool = True
    zoom: Percent | None = None

    @property
    def fit_to_page(self) -> bool:
        return self.fit_to_width is not None or self.fit_to_height is not None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.scale is not None and self.fit_to_page:
            raise ValueError("set either scale or fit-to-page, not both")
        if self.repeat_rows is not None and self.repeat_rows[1] < self.repeat_rows[0]:
            raise ValueError("repeat_rows must be (first, last) with first <= last")
        return self


class HFRun(SheetBase):
    """A piece of header/footer text, or a page field, with optional bold and size."""

    text: str = ""
    field: Literal["page", "pages"] | None = None
    bold: bool = False
    size: Annotated[float, Field(gt=0, le=409)] | None = None


HFLine = tuple[HFRun, ...]


class HFZone(SheetBase):
    """One header/footer zone: an optional picture followed by lines of runs."""

    lines: tuple[HFLine, ...] = ()
    image: Path | None = None


class HeaderFooter(SheetBase):
    """Print header and footer; the same on every page of the sheet."""

    header_left: HFZone = HFZone()
    header_center: HFZone = HFZone()
    header_right: HFZone = HFZone()
    footer_left: HFZone = HFZone()
    footer_center: HFZone = HFZone()
    footer_right: HFZone = HFZone()

    @model_validator(mode="after")
    def _one_picture_each(self) -> Self:
        for part, zones in (("header", self.header_zones), ("footer", self.footer_zones)):
            if sum(zone.image is not None for zone in zones) > 1:
                raise ValueError(f"the {part} may hold only one picture")
        return self

    @property
    def header_zones(self) -> tuple[HFZone, HFZone, HFZone]:
        return (self.header_left, self.header_center, self.header_right)

    @property
    def footer_zones(self) -> tuple[HFZone, HFZone, HFZone]:
        return (self.footer_left, self.footer_center, self.footer_right)


class SheetModel(SheetBase):
    name: ExcelSheetName
    cells: dict[tuple[int, int], Cell] = {}
    merges: tuple[Merge, ...] = ()
    columns: dict[ColIndex, ColumnFormat] = {}
    rows: dict[RowIndex, RowFormat] = {}
    print_setup: PrintSetup = PrintSetup()
    header_footer: HeaderFooter | None = None

    @model_validator(mode="after")
    def _cells_consistent(self) -> Self:
        for row, col in self.cells:
            if not (1 <= row <= MAX_ROW and 1 <= col <= MAX_COL):
                raise ValueError(f"cell (row {row}, column {col}) is outside the sheet")
        for i, merge in enumerate(self.merges):
            for other in self.merges[i + 1 :]:
                if merge.overlaps(other):
                    raise ValueError(f"merges {merge.name} and {other.name} overlap")
        for row, col in self.cells:
            for merge in self.merges:
                anchor = (row, col) == (merge.first_row, merge.first_col)
                if merge.contains(row, col) and not anchor:
                    raise ValueError(
                        f"cell {cell_name(row, col)} is covered by merge {merge.name}; "
                        "only its top-left cell may hold a value or style"
                    )
        return self


class WorkbookModel(SheetBase):
    """Sheets in workbook order."""

    sheets: Annotated[tuple[SheetModel, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _unique_names(self) -> Self:
        seen: set[str] = set()
        for sheet in self.sheets:
            key = sheet.name.casefold()
            if key in seen:
                raise ValueError(f"duplicate sheet name {sheet.name!r}")
            seen.add(key)
        return self
