"""The shared build sequence (``bomgen.build``) that ``bomgen build`` and the app call."""

import json
from pathlib import Path

import pytest

from bomgen import build as build_module
from bomgen.build import build_substation, workbook_name
from bomgen.engine.layout import LayoutIssue, LayoutReport
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.revision import read_previous_issue

SUBSTATION_FILE = (
    Path(__file__).resolve().parents[2] / "examples" / "substations" / "gis01" / "substation.yaml"
)


@pytest.fixture(scope="module")
def loaded() -> LoadedSubstation:
    return load_substation(SUBSTATION_FILE)


def test_workbook_name_follows_the_output_template(loaded: LoadedSubstation) -> None:
    # Output requirements (OUT-2): the register's gis01-bom entry is ...-001 rev 02.
    assert workbook_name(loaded) == "VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx"


def test_build_writes_the_workbook_and_its_check_report(
    loaded: LoadedSubstation, tmp_path: Path
) -> None:
    outcome = build_substation(loaded, tmp_path / "bom.xlsx")
    assert outcome.path == tmp_path / "bom.xlsx"
    assert outcome.path.is_file()
    assert outcome.result is not None
    assert outcome.revisions is None
    assert outcome.layout is None  # the example's panels are hand-written
    assert outcome.checks is not None
    assert outcome.failed is False
    written = json.loads((tmp_path / "bom.checks.json").read_text("utf-8"))
    assert written["failed"] is False
    assert len(written["items"]) == len(outcome.checks.items)


def test_build_without_checks_writes_no_report(loaded: LoadedSubstation, tmp_path: Path) -> None:
    outcome = build_substation(loaded, tmp_path / "bom.xlsx", checks=False)
    assert outcome.checks is None
    assert not (tmp_path / "bom.checks.json").exists()


def test_build_compares_with_a_previous_issue(loaded: LoadedSubstation, tmp_path: Path) -> None:
    first = build_substation(loaded, tmp_path / "before.xlsx", checks=False)
    assert first.path is not None
    previous = read_previous_issue(first.path)
    outcome = build_substation(loaded, tmp_path / "after.xlsx", previous=previous)
    assert outcome.revisions is not None
    assert outcome.revisions.changes == ()


def test_layout_errors_stop_the_build_before_writing(
    loaded: LoadedSubstation, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    issue = LayoutIssue("device-too-tall", "gw", "too tall")
    report = LayoutReport(ied_count=40, port_lines=[], fill_lines=[], issues=[issue])
    monkeypatch.setattr(build_module, "with_layout", lambda target: (target, report))
    outcome = build_substation(loaded, tmp_path / "bom.xlsx")
    assert (outcome.path, outcome.result, outcome.checks) == (None, None, None)
    assert outcome.layout is report
    assert outcome.failed is True
    assert not list(tmp_path.iterdir())


def test_layout_false_builds_the_panel_files_as_they_are(
    loaded: LoadedSubstation, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_layout(target: LoadedSubstation) -> None:
        raise AssertionError("the layout ran")

    monkeypatch.setattr(build_module, "with_layout", no_layout)
    outcome = build_substation(loaded, tmp_path / "bom.xlsx", layout=False, checks=False)
    assert outcome.path is not None
    assert outcome.path.is_file()
