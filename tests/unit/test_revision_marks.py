"""Mark as revised and the change list before issuing (plan M79): a row the compare can't
see is marked for the next issue, highlighted like the spec's revision rule (OUT-8),
listed with the compare's changes before Build as issued writes, and recorded with the
issue, which clears it."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from bomgen.build import record_issue
from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_project, load_substation
from bomgen.models.report import RevisionChange, RevisionKind, RevisionReport
from bomgen.models.substation import RowMark
from bomgen.revision import change_list

EXAMPLES = Path(__file__).parents[2] / "examples"
EXAMPLE = EXAMPLES / "substations" / "gis01" / "substation.yaml"
L2 = "PSA1-L2-ESW-A01"


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def marked(loaded: LoadedSubstation, *marks: RowMark) -> LoadedSubstation:
    substation = loaded.substation.model_copy(update={"revision_marks": list(marks)})
    return replace(loaded, substation=substation)


def test_a_marked_row_is_highlighted_on_its_sheet_only(example: LoadedSubstation) -> None:
    result = build(marked(example, RowMark(panel_id="psa1", tag=L2, reason="New firmware")))
    psa1 = next(p for p in result.panels if p.panel_id == "psa1")
    line = next(x for x in psa1.lines if x.tag == L2)
    assert line.revised == frozenset("BCDEFGH")
    others = [x for p in result.panels for x in p.lines if x.revised]
    assert others == [line]


def test_a_mark_can_name_its_columns_and_a_loose_row(example: LoadedSubstation) -> None:
    mark = RowMark(panel_id=None, tag="SRV/OAS -HMI Software", columns=["E"])
    result = build(marked(example, mark))
    assert result.loose is not None
    line = next(x for x in result.loose.lines if x.tag == "SRV/OAS -HMI Software")
    assert line.revised == frozenset("E")


def test_a_mark_whose_row_is_gone_is_ignored_by_the_build(example: LoadedSubstation) -> None:
    result = build(marked(example, RowMark(panel_id="psa1", tag="PSA1-GONE")))
    assert not [x for p in result.panels for x in p.lines if x.revised]


def test_the_change_list_has_the_compare_then_the_marked_rows(example: LoadedSubstation) -> None:
    gone = RowMark(panel_id="psa1", tag="PSA1-GONE", reason="Renamed")
    target = marked(example, RowMark(panel_id="psa1", tag=L2, reason="New firmware"), gone)
    report = RevisionReport(
        previous="rev 01",
        changes=(
            RevisionChange(
                sheet="2",
                kind=RevisionKind.CHANGED,
                tag="PSA2-L2-ESW-B01",
                description="Switch",
                columns=frozenset("E"),
            ),
        ),
    )
    rows = change_list(target, build(target), report)
    assert [(r["kind"], r["sheet"], r["tag"]) for r in rows] == [
        ("changed", "2", "PSA2-L2-ESW-B01"),
        ("marked", "1", L2),
        ("marked", "1", "PSA1-GONE"),
    ]
    assert rows[0]["detail"] == "E"
    assert rows[1]["detail"] == "New firmware"
    assert rows[2]["detail"] == "Renamed (the row is no longer on the sheet)"


def test_recording_the_issue_keeps_the_marks_and_clears_them(tmp_path: Path) -> None:
    shutil.copytree(EXAMPLES, tmp_path / "p")
    project = tmp_path / "p" / "project.yaml"
    sub = tmp_path / "p" / "substations" / "gis01" / "substation.yaml"
    sub.write_text(
        sub.read_text("utf-8")
        + f"revision_marks:\n  - {{ panel_id: psa1, tag: {L2}, reason: New firmware }}\n",
        "utf-8",
    )
    (target,) = load_project(project).substations
    workbook = tmp_path / "out.xlsx"
    workbook.write_bytes(b"issued")
    record = record_issue(project, target, workbook, "For construction")
    assert [(m.tag, m.reason) for m in record.marked] == [(L2, "New firmware")]
    (after,) = load_project(project).substations
    assert after.substation.revision_marks == []
    assert [(m.tag, m.reason) for m in after.substation.issues[-1].marked] == [(L2, "New firmware")]
