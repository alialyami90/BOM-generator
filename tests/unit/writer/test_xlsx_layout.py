"""Writer: merges, column widths, row heights and hidden columns (OUT-4, OUT-6)."""

import pytest
from conftest import WriteAndOpen

from bomgen.models.sheet import (
    Borders,
    BorderStyle,
    Cell,
    CellStyle,
    ColumnFormat,
    Font,
    Formula,
    Merge,
    RowFormat,
    SheetModel,
)

TITLE = CellStyle(
    font=Font(size=24, bold=True), fill="#A6A6A6", borders=Borders.all(BorderStyle.THIN)
)


def test_merges_written(write_and_open: WriteAndOpen) -> None:
    sheet = SheetModel(
        name="1",
        cells={(1, 1): Cell(value="title", style=TITLE), (4, 2): Cell(value="PSA1-FOPP-CCR-A01")},
        merges=(
            Merge(first_row=1, first_col=1, last_row=1, last_col=7),
            Merge(first_row=4, first_col=2, last_row=7, last_col=2),
        ),
    )
    ws = write_and_open(sheet)["1"]
    assert sorted(str(r) for r in ws.merged_cells.ranges) == ["A1:G1", "B4:B7"]
    assert ws["A1"].value == "title"
    assert ws["B4"].value == "PSA1-FOPP-CCR-A01"


def test_merged_anchor_keeps_value_style_and_formula(write_and_open: WriteAndOpen) -> None:
    sheet = SheetModel(
        name="1",
        cells={
            (1, 1): Cell(value="title", style=TITLE),
            (1, 8): Cell(value=Formula(text="=SUM(H3:H9)", result=17)),
            (3, 7): Cell(value=Formula(text="=A1"), style=TITLE),
        },
        merges=(
            Merge(first_row=1, first_col=1, last_row=1, last_col=7),
            Merge(first_row=3, first_col=7, last_row=5, last_col=7),
        ),
    )
    ws = write_and_open(sheet)["1"]
    assert ws["A1"].font.sz == 24
    assert ws["A1"].fill.fgColor.rgb == "FFA6A6A6"
    assert ws["G3"].value == "=A1"
    assert ws["H1"].value == "=SUM(H3:H9)"


def test_merge_border_applies_to_every_cell(write_and_open: WriteAndOpen) -> None:
    sheet = SheetModel(
        name="1",
        cells={(1, 1): Cell(value="title", style=TITLE)},
        merges=(Merge(first_row=1, first_col=1, last_row=1, last_col=7),),
    )
    ws = write_and_open(sheet)["1"]
    assert ws["G1"].border.right.style == "thin"
    assert ws["D1"].border.top.style == "thin"


def test_merge_without_anchor_cell_is_written_empty(write_and_open: WriteAndOpen) -> None:
    sheet = SheetModel(name="1", merges=(Merge(first_row=4, first_col=6, last_row=6, last_col=7),))
    ws = write_and_open(sheet)["1"]
    assert [str(r) for r in ws.merged_cells.ranges] == ["F4:G6"]
    assert ws["F4"].value is None


@pytest.mark.parametrize("width", [12.29, 53.71, 108.71, 4.57])
def test_column_widths_match_excel_ui_width(write_and_open: WriteAndOpen, width: float) -> None:
    sheet = SheetModel(name="1", columns={2: ColumnFormat(width=width)})
    ws = write_and_open(sheet)["1"]
    # Excel shows the width without its 5-pixel cell padding; the file stores it with.
    stored = (int(width * 7 + 0.5) + 5) / 7
    assert ws.column_dimensions["B"].width == pytest.approx(stored, abs=0.01)


def test_hidden_column(write_and_open: WriteAndOpen) -> None:
    sheet = SheetModel(name="1", columns={8: ColumnFormat(width=25, hidden=True)})
    ws = write_and_open(sheet)["1"]
    assert ws.column_dimensions["H"].hidden is True
    assert not ws.column_dimensions["G"].hidden


def test_hidden_column_without_width(write_and_open: WriteAndOpen) -> None:
    sheet = SheetModel(name="1", columns={13: ColumnFormat(hidden=True)})
    ws = write_and_open(sheet)["1"]
    assert ws.column_dimensions["M"].hidden is True


def test_row_heights(write_and_open: WriteAndOpen) -> None:
    sheet = SheetModel(
        name="1", rows={1: RowFormat(height=90), 2: RowFormat(height=26.25), 9: RowFormat()}
    )
    ws = write_and_open(sheet)["1"]
    assert ws.row_dimensions[1].height == 90
    assert ws.row_dimensions[2].height == 26.25
    assert ws.row_dimensions[9].height is None
