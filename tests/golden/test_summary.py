"""Golden: the example's Summary BOM when the substation includes it (ADR 0035, plan M63).

Expected quantities are the sums of the example's panel BOM rows (spec: Columns of a panel
BOM; `expected_groups_a_d.py` and `expected_groups_e_h.py`): the 2 A, 2P MCB A9F74202 is
29 rows on cabinet 001, 29 on 002, 13 on 003 and 6 on the WS console, one each.
"""

from dataclasses import replace
from pathlib import Path

import openpyxl
import pytest
from pycel import ExcelCompiler

from bomgen.engine.pipeline import build
from bomgen.io.loader import load_substation
from bomgen.sheets.workbook import build_workbook
from bomgen.writer import write_workbook

pytestmark = [
    pytest.mark.golden,
    pytest.mark.filterwarnings("ignore:Attribute s is deprecated:DeprecationWarning"),
    pytest.mark.filterwarnings("ignore:ast.Str is deprecated:DeprecationWarning"),
]

SUBSTATION_FILE = (
    Path(__file__).resolve().parents[2] / "examples" / "substations" / "gis01" / "substation.yaml"
)
SHEET = "Summary BOM"


@pytest.fixture(scope="module")
def path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    loaded = load_substation(SUBSTATION_FILE)
    output = loaded.substation.output.model_copy(update={"include": {"summary_bom"}})
    loaded = replace(loaded, substation=loaded.substation.model_copy(update={"output": output}))
    workbook = build_workbook(loaded, build(loaded))
    return write_workbook(workbook, tmp_path_factory.mktemp("golden") / "gis01.xlsx")


@pytest.fixture(scope="module")
def book(path: Path) -> openpyxl.Workbook:
    return openpyxl.load_workbook(path)


def row_of(book: openpyxl.Workbook, code: str) -> int:
    for cell in book[SHEET]["F"]:
        if cell.value == code:
            return int(cell.row)
    raise AssertionError(f"{code} not on the Summary BOM")


def test_summary_is_the_last_sheet(book: openpyxl.Workbook) -> None:
    assert book.sheetnames[-2:] == ["Heat Calculations", SHEET]


def test_one_line_per_part_or_item(book: openpyxl.Workbook) -> None:
    # 264 BOM rows across the four cabinets and the loose material make 63 lines.
    assert book[SHEET].max_row == 2 + 63


def test_2a_mcb_sums_every_cabinet(path: Path, book: openpyxl.Workbook) -> None:
    row = row_of(book, "A9F74202")
    compiler = ExcelCompiler(filename=str(path))
    assert compiler.evaluate(f"'{SHEET}'!C{row}") == 77
    where = book[SHEET][f"G{row}"].value
    assert where.startswith("1: PSA1-C2, PSA1-C3, PSA1-C5, PSA1-Q1.1")
    assert where.endswith("4: WS-Q1.1, WS-Q1.2, WS-Q2.1, WS-Q2.2, WS-QCOD-1, WS-QCOD-2 (6)")


def test_l1_switches_and_mm_sfps(path: Path, book: openpyxl.Workbook) -> None:
    compiler = ExcelCompiler(filename=str(path))
    switch = row_of(book, "6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05")
    sfp = row_of(book, "6GK6000-8FG51-0AA0")
    assert compiler.evaluate(f"'{SHEET}'!C{switch}") == 12
    assert compiler.evaluate(f"'{SHEET}'!C{sfp}") == 84


def test_text_quantity_references_the_loose_sheet(book: openpyxl.Workbook) -> None:
    sheet = book[SHEET]
    row = next(c.row for c in sheet["B"] if c.value == "Fiber Optic Patch Cords")
    assert sheet[f"C{row}"].value.startswith("='Loose Material'!D")
    assert sheet[f"G{row}"].value == "Loose Material: FO (1 Lot)"


def test_print_setup_and_header(book: openpyxl.Workbook) -> None:
    sheet = book[SHEET]
    assert sheet.page_setup.orientation == "landscape"
    assert sheet.print_title_rows == "$1:$2"
    assert sheet.print_area == f"'{SHEET}'!$A$1:$G$65"
    header = sheet.oddHeader
    assert header is not None
    assert "Bill of Materials for GIS Substation" in (header.center.text or "")
