"""The shared build sequence (``bomgen.build``) that ``bomgen build`` and the app call;
both lay out first."""

import json
from dataclasses import replace
from pathlib import Path

import openpyxl
import pytest

from bomgen.build import build_substation, workbook_name
from bomgen.engine.errors import EngineError
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
    assert outcome.checks is not None
    assert outcome.failed is False
    assert outcome.sheets == tuple(openpyxl.load_workbook(outcome.path).sheetnames)
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


def test_a_substation_without_panels_does_not_build(
    loaded: LoadedSubstation, tmp_path: Path
) -> None:
    with pytest.raises(EngineError, match="has no panels yet"):
        build_substation(replace(loaded, panels=()), tmp_path / "bom.xlsx")
    assert not (tmp_path / "bom.xlsx").exists()
