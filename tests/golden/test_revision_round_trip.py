"""Revision comparison against the written example workbook (spec: Output
requirements, OUT-8; plan M7, Q10; ADR 0016)."""

from pathlib import Path

import openpyxl
import pytest

from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.report import RevisionKind
from bomgen.revision import compare_with_previous, read_previous_issue
from bomgen.sheets.workbook import build_workbook
from bomgen.writer import write_workbook

pytestmark = pytest.mark.golden

SUBSTATION_FILE = (
    Path(__file__).resolve().parents[2] / "examples" / "substations" / "gis01" / "substation.yaml"
)


@pytest.fixture(scope="module")
def loaded() -> LoadedSubstation:
    return load_substation(SUBSTATION_FILE)


@pytest.fixture(scope="module")
def issued(loaded: LoadedSubstation, tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("rev0") / "gis01.xlsx"
    return write_workbook(build_workbook(loaded, build(loaded)), path)


def test_the_issue_reads_back_as_its_build(loaded: LoadedSubstation, issued: Path) -> None:
    previous = read_previous_issue(issued)
    assert list(previous.sheets) == ["1", "2", "3", "4", "Loose Material"]
    tables = {sheet: [len(t.rows) for t in found] for sheet, found in previous.sheets.items()}
    # ADR 0020: the loose material has its own sheet; the console's sheet holds one table.
    assert tables == {"1": [71], "2": [74], "3": [62], "4": [39], "Loose Material": [14]}
    result = build(loaded)
    marked, report = compare_with_previous(result, previous)
    assert report.changes == ()
    assert marked == result


def test_a_changed_description_is_highlighted_in_the_next_issue(
    loaded: LoadedSubstation, issued: Path, tmp_path: Path
) -> None:
    result = build(loaded)
    panel = result.panels[0]
    index = next(i for i, line in enumerate(panel.lines) if line.tag == "PSA1-Q1")
    lines = list(panel.lines)
    lines[index] = lines[index].model_copy(update={"description": "20A, 2P MCB For Main"})
    changed = result.model_copy(
        update={"panels": (panel.model_copy(update={"lines": tuple(lines)}), *result.panels[1:])}
    )
    marked, report = compare_with_previous(changed, read_previous_issue(issued))
    assert [(c.kind, c.sheet, c.tag, c.columns) for c in report.changes] == [
        (RevisionKind.CHANGED, "1", "PSA1-Q1", frozenset({"C"}))
    ]
    path = write_workbook(build_workbook(loaded, marked), tmp_path / "rev1.xlsx")
    sheet = openpyxl.load_workbook(path)["1"]
    (row,) = [c.row for c in sheet["B"] if c.value == "PSA1-Q1"]
    assert sheet[f"C{row}"].fill.fgColor.rgb == "FFFFFF00"
    assert sheet[f"D{row}"].fill.fgColor.rgb != "FFFFFF00"
