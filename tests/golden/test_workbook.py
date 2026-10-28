"""The written example workbook (plan M5): every formula evaluates (Q15) to the value
the writer cached, and the evaluated totals are the ones the spec states."""

from collections.abc import Callable
from pathlib import Path

import openpyxl
import pytest
from openpyxl.worksheet.worksheet import Worksheet
from pycel import ExcelCompiler

from bomgen.engine.pipeline import build
from bomgen.io.loader import load_substation
from bomgen.sheets.workbook import build_workbook
from bomgen.writer import write_workbook

pytestmark = pytest.mark.golden

SUBSTATION_FILE = (
    Path(__file__).resolve().parents[2] / "examples" / "substations" / "gis01" / "substation.yaml"
)

Evaluate = Callable[[str, str], object]


@pytest.fixture(scope="module")
def path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    loaded = load_substation(SUBSTATION_FILE)
    workbook = build_workbook(loaded, build(loaded))
    return write_workbook(workbook, tmp_path_factory.mktemp("golden") / "gis01.xlsx")


@pytest.fixture(scope="module")
def formulas(path: Path) -> openpyxl.Workbook:
    return openpyxl.load_workbook(path)


@pytest.fixture(scope="module")
def evaluate(path: Path) -> Evaluate:
    compiler = ExcelCompiler(filename=str(path))

    def run(sheet: str, cell: str) -> object:
        return compiler.evaluate(f"{sheet}!{cell}")

    return run


def row_of(sheet: Worksheet, column: str, label: str) -> int:
    for cell in sheet[column]:
        if cell.value == label:
            return int(cell.row)
    raise AssertionError(f"{label!r} not found in column {column} of {sheet.title!r}")


def test_sheet_order(formulas: openpyxl.Workbook) -> None:
    # Output requirements: a BOM sheet per cabinet, then the three calculation sheets.
    assert formulas.sheetnames == [
        "1", "2", "3", "4", "Power Consumption", "Heat Dissipation", "Heat Calculations",
    ]  # fmt: skip


def test_bom_sheet_merges(formulas: openpyxl.Workbook) -> None:
    # Formatting → BOM sheets: the merged title; a designation spanning its kit rows; make
    # and model spanning the kit children that leave them empty.
    merges = {str(m) for m in formulas["1"].merged_cells.ranges}
    assert {"A1:G1", "B4:B7", "F4:F6", "G4:G6"} <= merges


def test_every_formula_evaluates_to_its_cached_value(
    path: Path, formulas: openpyxl.Workbook, evaluate: Evaluate
) -> None:
    # Output requirements (OUT-5): live formulas; the cached results must agree, so the
    # file shows the right numbers before Excel recalculates.
    cached = openpyxl.load_workbook(path, data_only=True)
    checked, wrong = 0, []
    for sheet in formulas.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if not (isinstance(cell.value, str) and cell.value.startswith("=")):
                    continue
                checked += 1
                got = evaluate(sheet.title, cell.coordinate)
                want = cached[sheet.title][cell.coordinate].value
                if isinstance(want, int | float) and not isinstance(want, bool):
                    same = isinstance(got, int | float) and got == pytest.approx(want)
                else:
                    same = got == want
                if not same:
                    where = f"{sheet.title}!{cell.coordinate} {cell.value}"
                    wrong.append(f"{where}: {got!r} != {want!r}")
    assert checked > 900
    assert wrong == []


def test_power_consumption_totals(formulas: openpyxl.Workbook, evaluate: Evaluate) -> None:
    # Power Consumption sheet: 2,177.5 W DC + 1,090.3 W AC = 3,267.8 W.
    sheet = formulas["Power Consumption"]
    dc = row_of(sheet, "C", "125V DC LOAD")
    ac = row_of(sheet, "C", "230V AUX AC LOAD")
    total = row_of(sheet, "E", "TOTAL POWER (W)")
    assert evaluate(sheet.title, f"G{dc}") == pytest.approx(2177.5)
    assert evaluate(sheet.title, f"G{ac}") == pytest.approx(1090.3)
    assert evaluate(sheet.title, f"G{total}") == pytest.approx(3267.8)


def test_required_airflow(formulas: openpyxl.Workbook, evaluate: Evaluate) -> None:
    # Heat Dissipation and Heat Calculations sheets: 391, 391 and 172 m³/h against 716.
    sheet = formulas["Heat Calculations"]
    labels = [c.row for c in sheet["B"] if c.value == "Air Flow Rate in m³/h ="]
    airflow = [evaluate(sheet.title, f"E{row + 1}") for row in labels]
    fans = [evaluate(sheet.title, f"E{row + 3}") for row in labels]
    assert [round(float(str(a))) for a in airflow] == [391, 391, 172]
    assert fans == [716, 716, 716]


def test_line_up_check(formulas: openpyxl.Workbook, evaluate: Evaluate) -> None:
    # Heat Calculations: Σ required = 954.8 m³/h against 3 x 716 = 2,148 m³/h.
    sheet = formulas["Heat Calculations"]
    required = row_of(sheet, "B", "Total required air flow =") + 1
    fans = row_of(sheet, "B", "Total fans capacity =") + 1
    assert evaluate(sheet.title, f"D{required}") == pytest.approx(954.8, abs=0.05)
    assert evaluate(sheet.title, f"D{fans}") == pytest.approx(2148)


def test_console_natural_convection(formulas: openpyxl.Workbook, evaluate: Evaluate) -> None:
    # Heat Calculations: A = 4.848 m² and ΔT = 6.96 °C, under the 10 °C limit.
    sheet = formulas["Heat Calculations"]
    area = row_of(sheet, "B", "Surface area of panel =") + 1
    rise = row_of(sheet, "B", "Heat rise inside the panel =") + 1
    assert evaluate(sheet.title, f"D{area}") == pytest.approx(4.848)
    assert evaluate(sheet.title, f"D{rise}") == pytest.approx(6.96, abs=0.005)
    conclusion = evaluate(sheet.title, f"B{rise + 1}")
    assert isinstance(conclusion, str)
    assert "within the limit" in conclusion
