"""Sheet builder helpers: references, frames and merges."""

import pytest

from bomgen.models.sheet import Borders, BorderStyle, CellStyle, Formula, PrintSetup
from bomgen.sheets.grid import SheetBuilder, quote_sheet, ref

M, T, N = BorderStyle.MEDIUM, BorderStyle.THIN, BorderStyle.NONE


@pytest.mark.parametrize(
    ("name", "quoted"),
    [("1", "'1'"), ("Power Consumption", "'Power Consumption'"), ("O'Brien", "'O''Brien'")],
)
def test_sheet_names_are_always_quoted(name: str, quoted: str) -> None:
    assert quote_sheet(name) == quoted


def test_ref_names_a_cell_on_a_sheet() -> None:
    assert ref("1", 8, 3) == "'1'!C8"
    assert ref("Power Consumption", 12, 10) == "'Power Consumption'!J12"


def test_set_and_build() -> None:
    sheet = SheetBuilder("1")
    sheet.set(3, 1, 1)
    sheet.set(4, 1, Formula(text="=A3+1", result=2))
    model = sheet.build(PrintSetup())
    assert model.name == "1"
    assert model.cells[(4, 1)].value == Formula(text="=A3+1", result=2)
    assert sheet.last_row == 4


def test_box_draws_medium_outside_and_thin_inside() -> None:
    sheet = SheetBuilder("x")
    for row in (2, 3, 4):
        for col in (2, 3, 4):
            sheet.set(row, col, "v", CellStyle())
    sheet.box(2, 2, 4, 4, outer=M, inner=T)
    cells = sheet.build(PrintSetup()).cells
    assert cells[(2, 2)].style is not None
    assert cells[(2, 2)].style.borders == Borders(left=M, top=M, right=T, bottom=T)
    assert cells[(3, 3)].style is not None
    assert cells[(3, 3)].style.borders == Borders.all(T)
    assert cells[(4, 4)].style is not None
    assert cells[(4, 4)].style.borders == Borders(left=T, top=T, right=M, bottom=M)


def test_box_without_inner_keeps_inner_borders_off_and_fills_empty_cells() -> None:
    sheet = SheetBuilder("x")
    sheet.box(1, 1, 2, 2, outer=M)
    cells = sheet.build(PrintSetup()).cells
    assert cells[(1, 2)].style is not None
    assert cells[(1, 2)].style.borders == Borders(top=M, right=M)


def test_box_treats_a_merge_as_one_cell() -> None:
    sheet = SheetBuilder("x")
    sheet.merge(1, 1, 1, 3, "title", CellStyle())
    sheet.set(2, 1, "a", CellStyle())
    sheet.box(1, 1, 2, 3, outer=M, inner=T)
    cells = sheet.build(PrintSetup()).cells
    assert (1, 2) not in cells
    assert cells[(1, 1)].style is not None
    assert cells[(1, 1)].style.borders == Borders(left=M, top=M, right=M, bottom=T)


def test_merge_records_range_and_anchor() -> None:
    sheet = SheetBuilder("1")
    sheet.merge(4, 2, 7, 2, "PSA1-FOPP-CCR-A01", CellStyle())
    model = sheet.build(PrintSetup())
    assert [m.name for m in model.merges] == ["B4:B7"]
    assert model.cells[(4, 2)].value == "PSA1-FOPP-CCR-A01"
    assert sheet.last_row == 7


def test_widths_heights_and_hidden_columns() -> None:
    sheet = SheetBuilder("1")
    sheet.width(8, 25, hidden=True)
    sheet.height(1, 90)
    model = sheet.build(PrintSetup())
    assert model.columns[8].hidden is True
    assert model.rows[1].height == 90
