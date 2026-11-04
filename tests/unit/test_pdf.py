"""PDF export of the issued sheets (plan M78, ADR 0039): the built-in renderer draws the
written workbook with its print settings; Excel on the PC is the exact alternative."""

import subprocess
import sys
from pathlib import Path

import pypdf
import pytest

from bomgen import pdf
from bomgen.build import build_substation
from bomgen.io.loader import load_substation

EXAMPLE = Path(__file__).parents[2] / "examples" / "substations" / "gis01" / "substation.yaml"
A4 = (595, 842)


@pytest.fixture(scope="module")
def workbook(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("pdf") / "issued.xlsx"
    build_substation(load_substation(EXAMPLE), out)
    return out


@pytest.fixture(scope="module")
def pages(workbook: Path) -> list[pypdf.PageObject]:
    out = workbook.with_suffix(".pdf")
    count = pdf.render_pdf(workbook, out)
    reader = pypdf.PdfReader(out)
    assert count == len(reader.pages)
    return list(reader.pages)


def size(page: pypdf.PageObject) -> tuple[int, int]:
    return round(float(page.mediabox.width)), round(float(page.mediabox.height))


def test_every_visible_sheet_is_drawn_in_order_on_its_paper(pages: list[pypdf.PageObject]) -> None:
    first = pages[0].extract_text()
    assert "PSA1-FOPP-CCR-A01" in first
    assert size(pages[0]) == A4  # BOM sheets are A4 portrait (OUT-7)
    assert size(pages[-1]) == A4[::-1]  # Heat Calculations is landscape
    assert "Heat Calculations" in pages[-1].extract_text()


def test_the_page_header_and_footer_are_printed_with_page_numbers(
    pages: list[pypdf.PageObject],
) -> None:
    first = pages[0].extract_text()
    assert "Rev : 02" in first
    assert "Bill of Materials for 861-GIS01-PSA-0001" in first
    assert "Page 1 of" in first
    assert "&P" not in first


def test_title_rows_repeat_on_each_page_of_a_sheet(pages: list[pypdf.PageObject]) -> None:
    second = pages[1].extract_text()
    assert "Bill of Materials for 861-GIS01-PSA-0001" in second  # still sheet 1
    assert "Page 2 of" in second
    assert "SR.NO" in second
    assert "ITEM DESIGNATION" in second


def test_hidden_columns_are_left_out(pages: list[pypdf.PageObject]) -> None:
    assert "HWIO" not in pages[0].extract_text()  # OUT-4: the HWIO column is hidden


def test_formulas_print_the_results_written_with_them(pages: list[pypdf.PageObject]) -> None:
    text = "".join(p.extract_text() for p in pages)
    assert "2,177.5" in text or "2177.5" in text  # the DC power total


def test_only_the_chosen_sheets_are_drawn(workbook: Path, tmp_path: Path) -> None:
    out = tmp_path / "loose.pdf"
    count = pdf.render_pdf(workbook, out, ["Loose Material"])
    reader = pypdf.PdfReader(out)
    assert count == len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "Bill of Materials for Loose Material" in text
    assert "PSA1-FOPP" not in text


def test_an_unknown_sheet_is_refused(workbook: Path, tmp_path: Path) -> None:
    with pytest.raises(pdf.PdfError, match="no sheet 'Nope'"):
        pdf.render_pdf(workbook, tmp_path / "x.pdf", ["Nope"])
    assert not (tmp_path / "x.pdf").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="the refusal is for other systems")
def test_excel_is_refused_off_windows() -> None:
    assert pdf.excel_refusal() == "Export with Excel needs Windows with Excel installed."


def test_the_excel_script_selects_the_chosen_sheets_and_exports_them() -> None:
    script = pdf.excel_script(Path("C:/p/it's.xlsx"), Path("C:/p/out.pdf"), ["1", "Loose Material"])
    assert "New-Object -ComObject Excel.Application" in script
    assert "Workbooks.Open('C:/p/it''s.xlsx', 0, $true)" in script
    assert "Worksheets.Item('1').Select($true)" in script
    assert "Worksheets.Item('Loose Material').Select($false)" in script
    assert "ActiveSheet.ExportAsFixedFormat(0, 'C:/p/out.pdf')" in script
    assert "$excel.Quit()" in script


def test_an_excel_failure_is_reported(workbook: Path, tmp_path: Path) -> None:
    def failed(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        assert args[:2] == ["powershell", "-NoProfile"]
        return subprocess.CompletedProcess(args, 1, "", "Exception calling Open")

    with pytest.raises(pdf.PdfError, match="Excel did not write the PDF: Exception calling Open"):
        pdf.excel_pdf(workbook, tmp_path / "x.pdf", ["1"], run=failed)
