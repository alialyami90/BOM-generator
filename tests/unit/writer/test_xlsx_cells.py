"""Writer: values, live formulas and cell styles survive the round trip (OUT-1, OUT-5, OUT-6)."""

import zipfile
from pathlib import Path

import pytest
from conftest import WriteAndOpen

from bomgen.models.sheet import (
    Alignment,
    Borders,
    BorderStyle,
    Cell,
    CellStyle,
    Font,
    Formula,
    SheetModel,
    WorkbookModel,
)
from bomgen.writer import WriterError, write_workbook

THIN = Borders.all(BorderStyle.THIN)


def test_sheets_written_in_model_order(write_and_open: WriteAndOpen) -> None:
    names = ["1", "2", "Power Consumption", "Heat Dissipation"]
    book = write_and_open(*(SheetModel(name=n) for n in names))
    assert book.sheetnames == names


def test_numbers_and_text_keep_their_type(write_and_open: WriteAndOpen) -> None:
    cells = {(3, 1): Cell(value=1), (3, 4): Cell(value=27), (3, 5): Cell(value="Ruggedcom")}
    cells[(4, 9)] = Cell(value=77.5)
    ws = write_and_open(SheetModel(name="1", cells=cells))["1"]
    assert ws["A3"].value == 1
    assert ws["D3"].value == 27
    assert ws["E3"].value == "Ruggedcom"
    assert ws["I4"].value == 77.5


@pytest.mark.parametrize("text", ["=24+3", "1 Lot", "0012", "http://example.com", "3044199"])
def test_text_that_looks_like_a_formula_number_or_url_stays_text(
    write_and_open: WriteAndOpen, text: str
) -> None:
    ws = write_and_open(SheetModel(name="1", cells={(1, 1): Cell(value=text)}))["1"]
    assert ws["A1"].value == text
    assert ws["A1"].data_type == "s"
    assert ws["A1"].hyperlink is None


def test_formula_written_live_with_cached_result(write_and_open: WriteAndOpen) -> None:
    cells = {
        (3, 1): Cell(value=1),
        (4, 1): Cell(value=Formula(text="=A3+1", result=2)),
        (5, 4): Cell(value=Formula(text="=24+3", result=27)),
    }
    sheet = SheetModel(name="1", cells=cells)
    ws = write_and_open(sheet)["1"]
    assert ws["A4"].value == "=A3+1"
    assert ws["D5"].value == "=24+3"
    cached = write_and_open(sheet, data_only=True)["1"]
    assert cached["A4"].value == 2
    assert cached["D5"].value == 27


def test_cross_sheet_formula_reference(write_and_open: WriteAndOpen) -> None:
    bom = SheetModel(name="1", cells={(8, 3): Cell(value="L2 switch")})
    power = SheetModel(
        name="Power Consumption", cells={(8, 5): Cell(value=Formula(text="='1'!C8"))}
    )
    ws = write_and_open(bom, power)["Power Consumption"]
    assert ws["E8"].value == "='1'!C8"


def test_workbook_recalculates_fully_on_open(out_path: Path) -> None:
    write_workbook(WorkbookModel(sheets=(SheetModel(name="1"),)), out_path)
    with zipfile.ZipFile(out_path) as archive:
        workbook_xml = archive.read("xl/workbook.xml").decode()
        names = archive.namelist()
    assert 'fullCalcOnLoad="1"' in workbook_xml
    assert not any(name.endswith(".bin") or "vbaProject" in name for name in names)


def test_font_fill_alignment_border_number_format_round_trip(write_and_open: WriteAndOpen) -> None:
    style = CellStyle(
        font=Font(size=24, bold=True, underline="single", color="#1F497D"),
        fill="#A6A6A6",
        alignment=Alignment(horizontal="center", vertical="center", wrap=True),
        borders=Borders(
            left=BorderStyle.THIN,
            right=BorderStyle.MEDIUM,
            top=BorderStyle.THIN,
            bottom=BorderStyle.MEDIUM,
        ),
        number_format="0.00",
    )
    ws = write_and_open(SheetModel(name="1", cells={(1, 1): Cell(value=1.5, style=style)}))["1"]
    cell = ws["A1"]
    assert cell.font.name == "Calibri"
    assert cell.font.sz == 24
    assert cell.font.b is True
    assert cell.font.u == "single"
    assert cell.font.color.rgb == "FF1F497D"
    assert cell.fill.fill_type == "solid"
    assert cell.fill.fgColor.rgb == "FFA6A6A6"
    assert cell.alignment.horizontal == "center"
    assert cell.alignment.vertical == "center"
    assert cell.alignment.wrap_text is True
    assert cell.border.left.style == "thin"
    assert cell.border.right.style == "medium"
    assert cell.border.top.style == "thin"
    assert cell.border.bottom.style == "medium"
    assert cell.number_format == "0.00"


def test_unstyled_cell_uses_calibri_11_without_border(write_and_open: WriteAndOpen) -> None:
    ws = write_and_open(SheetModel(name="1", cells={(1, 1): Cell(value="x")}))["1"]
    assert ws["A1"].font.name == "Calibri"
    assert ws["A1"].font.sz == 11
    assert ws["A1"].border.left.style is None


def test_styled_blank_cell_keeps_its_border(write_and_open: WriteAndOpen) -> None:
    cells = {(20, col): Cell(style=CellStyle(borders=THIN)) for col in range(1, 8)}
    ws = write_and_open(SheetModel(name="1", cells=cells))["1"]
    for col in "ABCDEFG":
        assert ws[f"{col}20"].value is None
        assert ws[f"{col}20"].border.left.style == "thin"


def test_overlong_text_raises_writer_error(out_path: Path) -> None:
    sheet = SheetModel(name="1", cells={(1, 1): Cell(value="x" * 40_000)})
    with pytest.raises(WriterError, match="A1"):
        write_workbook(WorkbookModel(sheets=(sheet,)), out_path)


def test_creates_missing_parent_directory(out_path: Path) -> None:
    assert not out_path.parent.exists()
    written = write_workbook(WorkbookModel(sheets=(SheetModel(name="1"),)), out_path)
    assert written == out_path
    assert out_path.is_file()
