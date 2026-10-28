"""Writer: page header and footer per "Output requirements" (Excel print header/footer)."""

import zipfile
from pathlib import Path

import pytest
from conftest import WriteAndOpen, tiny_png
from openpyxl.workbook.workbook import Workbook

from bomgen.models.sheet import HeaderFooter, HFRun, HFZone, SheetModel, WorkbookModel
from bomgen.writer import WriterError, write_workbook

FOOTER_RIGHT = "Rev 0 \u2013 2026-10-28"  # the spec's en dash


def zone_text(book: Workbook, part: str, zone: str) -> str:
    """Text of one header/footer zone of sheet "1" as openpyxl parses it ("" when empty)."""
    item = getattr(book["1"], part)
    assert item is not None
    return str(getattr(item, zone).text or "")


def line(*runs: HFRun) -> tuple[HFRun, ...]:
    return runs


def bom_header_footer(logo: Path | None = None, name: str = "Project") -> HeaderFooter:
    return HeaderFooter(
        header_left=HFZone(image=logo),
        header_center=HFZone(
            lines=(
                line(HFRun(text=name, bold=True, size=28)),
                line(HFRun(text="Bill of Materials for 861-GIS01-PSA-0001")),
                line(HFRun(text="Supplier Doc # D-1")),
            )
        ),
        header_right=HFZone(lines=(line(HFRun(text="Rev : 0")),)),
        footer_left=HFZone(lines=(line(HFRun(text="D-1")),)),
        footer_center=HFZone(
            lines=(
                line(
                    HFRun(text="Page "),
                    HFRun(field="page"),
                    HFRun(text=" of "),
                    HFRun(field="pages"),
                ),
            )
        ),
        footer_right=HFZone(lines=(line(HFRun(text=FOOTER_RIGHT)),)),
    )


def test_header_three_zones_with_bold_28pt_first_line(write_and_open: WriteAndOpen) -> None:
    book = write_and_open(SheetModel(name="1", header_footer=bom_header_footer()))
    assert zone_text(book, "oddHeader", "center") == (
        "Project\nBill of Materials for 861-GIS01-PSA-0001\nSupplier Doc # D-1"
    )
    # openpyxl reports one font per zone; the per-line fonts are checked in the raw XML below.
    assert zone_text(book, "oddHeader", "right") == "Rev : 0"


def test_raw_header_string_bolds_only_the_first_line(out_path: Path) -> None:
    sheet = SheetModel(name="1", header_footer=bom_header_footer())
    write_workbook(WorkbookModel(sheets=(sheet,)), out_path)
    with zipfile.ZipFile(out_path) as archive:
        xml = archive.read("xl/worksheets/sheet1.xml").decode()
    centre = '&amp;C&amp;28&amp;"Calibri,Bold"Project\n&amp;11&amp;"Calibri,Regular"Bill of'
    assert centre in xml
    assert "<oddHeader>" in xml
    assert "<firstHeader>" not in xml
    assert "<evenHeader>" not in xml
    assert 'differentFirst="1"' not in xml
    assert 'differentOddEven="1"' not in xml


def test_footer_page_of_pages(write_and_open: WriteAndOpen) -> None:
    book = write_and_open(SheetModel(name="1", header_footer=bom_header_footer()))
    assert zone_text(book, "oddFooter", "left") == "D-1"
    assert zone_text(book, "oddFooter", "center") == "Page &P of &N"
    assert zone_text(book, "oddFooter", "right") == FOOTER_RIGHT


def test_logo_picture_in_left_zone(
    write_and_open: WriteAndOpen, tmp_path: Path, out_path: Path
) -> None:
    logo = tiny_png(tmp_path / "logo.png")
    book = write_and_open(SheetModel(name="1", header_footer=bom_header_footer(logo)))
    assert zone_text(book, "oddHeader", "left") == "&G"
    with zipfile.ZipFile(out_path) as archive:
        names = archive.namelist()
        sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode()
    assert "xl/media/image1.png" in names
    assert any(n.startswith("xl/drawings/vmlDrawing") for n in names)
    assert "<legacyDrawingHF" in sheet_xml


def test_same_logo_on_every_sheet(tmp_path: Path, out_path: Path) -> None:
    logo = tiny_png(tmp_path / "logo.png")
    sheets = tuple(SheetModel(name=n, header_footer=bom_header_footer(logo)) for n in "12")
    write_workbook(WorkbookModel(sheets=sheets), out_path)
    with zipfile.ZipFile(out_path) as archive:
        for i in (1, 2):
            assert "<legacyDrawingHF" in archive.read(f"xl/worksheets/sheet{i}.xml").decode()


def test_text_starting_with_a_digit_is_not_read_as_font_size(write_and_open: WriteAndOpen) -> None:
    hf = HeaderFooter(footer_left=HFZone(lines=(line(HFRun(text="861-GIS01-PSA-0001")),)))
    book = write_and_open(SheetModel(name="1", header_footer=hf))
    assert zone_text(book, "oddFooter", "left") == "861-GIS01-PSA-0001"


def test_ampersand_in_text_is_escaped(write_and_open: WriteAndOpen) -> None:
    hf = bom_header_footer(name="R&D Substation")
    book = write_and_open(SheetModel(name="1", header_footer=hf))
    assert zone_text(book, "oddHeader", "center").startswith("R&&D Substation\n")


def test_header_over_255_chars_raises(out_path: Path) -> None:
    hf = bom_header_footer(name="x" * 250)
    with pytest.raises(WriterError, match=r"header of sheet '1' is \d+ characters"):
        write_workbook(WorkbookModel(sheets=(SheetModel(name="1", header_footer=hf),)), out_path)


def test_missing_logo_raises_and_writes_no_file(tmp_path: Path, out_path: Path) -> None:
    missing = tmp_path / "nope.png"
    sheet = SheetModel(name="1", header_footer=bom_header_footer(missing))
    with pytest.raises(WriterError, match=r"nope\.png"):
        write_workbook(WorkbookModel(sheets=(sheet,)), out_path)
    assert not out_path.exists()


def test_unreadable_picture_raises_and_writes_no_file(tmp_path: Path, out_path: Path) -> None:
    bad = tmp_path / "logo.png"
    bad.write_text("not a picture")
    sheet = SheetModel(name="1", header_footer=bom_header_footer(bad))
    with pytest.raises(WriterError, match="could not write"):
        write_workbook(WorkbookModel(sheets=(sheet,)), out_path)
    assert not out_path.exists()


def test_no_header_footer_when_model_has_none(write_and_open: WriteAndOpen) -> None:
    book = write_and_open(SheetModel(name="1"))
    assert zone_text(book, "oddHeader", "center") == ""
    assert zone_text(book, "oddFooter", "center") == ""
