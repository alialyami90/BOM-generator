"""Branch MCB sizing and the float checks with the shipped library (plan Q38, M15).

The example project is built twice: with its own library, whose devices carry no inrush
figures, and with data/library/psa-devices.yaml, which adds each original's datasheet
inrush and input range. The goldens stay on examples/ (Q38).
"""

import shutil
from pathlib import Path

import pytest

from bomgen.checks import check_report
from bomgen.engine.pipeline import build
from bomgen.io.loader import load_substation
from bomgen.models.bom import BuildResult, Group
from bomgen.models.report import CheckReport, CheckStatus

REPO = Path(__file__).resolve().parents[3]
SHIPPED = REPO / "data" / "library" / "psa-devices.yaml"
SEL_LOADS = {
    ("psa1", "GW_1"),  # SEL-3555-GW, with the shipped library's neutral tag
    ("psa2", "GW_2"),
    ("psa3", "RTAC"),  # SEL-3555-RTAC
    ("ws", "SRV/OAS/EAS"),  # SEL-3355
}

Built = tuple[BuildResult, CheckReport]


def _build(tmp: Path, library: Path | None) -> Built:
    project = tmp / "examples"
    shutil.copytree(REPO / "examples", project)
    if library is not None:
        shutil.copyfile(library, project / "library.yaml")
    loaded = load_substation(project / "substations" / "gis01" / "substation.yaml")
    result = build(loaded)
    return result, check_report(loaded, result)


@pytest.fixture(scope="module")
def shipped(tmp_path_factory: pytest.TempPathFactory) -> Built:
    return _build(tmp_path_factory.mktemp("shipped"), SHIPPED)


@pytest.fixture(scope="module")
def example(tmp_path_factory: pytest.TempPathFactory) -> Built:
    return _build(tmp_path_factory.mktemp("example"), None)


def _ratings(result: BuildResult) -> dict[tuple[str, str], set[int]]:
    ratings: dict[tuple[str, str], set[int]] = {}
    for branch in result.branch_mcbs:
        load = branch.load.removesuffix(" PS1").removesuffix(" PS2")
        ratings.setdefault((branch.panel_id, load), set()).add(branch.rating_a)
    return ratings


def test_sel_branches_clear_their_datasheet_inrush_at_6a(shipped: Built) -> None:
    # 20 A inrush / the iC60N's DC trip multiple 9.05 = 2.2 A -> 6 A (ADR 0019 item 1).
    result, _report = shipped
    for branch in result.branch_mcbs:
        load = branch.load.removesuffix(" PS1").removesuffix(" PS2")
        if (branch.panel_id, load) in SEL_LOADS:
            assert (branch.rating_a, branch.set_by) == (6, ("inrush",)), branch.tag


def test_other_branches_keep_the_2a_floor(shipped: Built) -> None:
    result, _report = shipped
    others = {key: r for key, r in _ratings(result).items() if key not in SEL_LOADS}
    assert others
    assert all(r == {2} for r in others.values()), others


def test_spares_repeat_the_largest_branch_on_their_feed(shipped: Built) -> None:
    # ADR 0019: spares take the largest used branch, so every feed with a SEL is 6 A.
    result, _report = shipped
    spares = {
        panel.panel_id: {
            line.description
            for line in panel.lines
            if line.group is Group.F and line.description.endswith("MCB For SPARE")
        }
        for panel in result.panels
    }
    assert spares == {
        "psa1": {"6A, 2P MCB For SPARE"},
        "psa2": {"6A, 2P MCB For SPARE"},
        "psa3": {"6A, 2P MCB For SPARE", "2A, 2P MCB For SPARE"},  # the QCOD spare: 2 A
        "ws": {"6A, 2P MCB For SPARE", "2A, 2P MCB For SPARE"},
    }


def test_the_example_library_keeps_every_branch_at_2a(example: Built) -> None:
    # Q38: the example library has no inrush figures, so the goldens' 2 A hold.
    result, _report = example
    assert all(r == {2} for r in _ratings(result).values())


def test_mains_do_not_change_with_the_shipped_library(shipped: Built, example: Built) -> None:
    assert shipped[0].mains == example[0].mains


def test_float_check_warns_for_the_ic60n_and_the_125v_firewall(shipped: Built) -> None:
    _result, report = shipped
    warned = {
        item.subject
        for item in report.items
        if item.check == "dc_float" and item.status is CheckStatus.WARN
    }
    assert warned == {"Acti9 2P", "FGR-60F"}
    passed = {
        item.subject
        for item in report.items
        if item.check == "dc_float" and item.status is CheckStatus.PASS
    }
    assert {"SEL-3555-GW", "SEL-3555-RTAC", "SEL-3355"} <= passed
    assert not report.failed
