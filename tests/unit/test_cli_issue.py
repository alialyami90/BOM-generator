"""``bomgen build --issue`` and the automatic compare with the last issue (ADR 0036)."""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from bomgen.cli import app
from bomgen.io.loader import load_substation

EXAMPLES = Path(__file__).parents[2] / "examples"
runner = CliRunner()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "project")
    return tmp_path / "project" / "project.yaml"


def substation_file(project: Path) -> Path:
    return project.parent / "substations" / "gis01" / "substation.yaml"


def issue(project: Path, out: Path) -> Result:
    return runner.invoke(app, ["build", str(project), "-o", str(out), "--issue", "x"])


def test_build_issue_records_the_issue(project: Path) -> None:
    out = project.parent / "out"
    result = runner.invoke(app, ["build", str(project), "-o", str(out), "--issue", "For review"])
    assert result.exit_code == 0, result.output
    (record,) = load_substation(substation_file(project)).substation.issues
    assert (record.rev, record.description) == ("02", "For review")
    assert record.file == Path("../../out/VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx")
    assert "Recorded rev 02" in result.output


def test_the_same_rev_is_not_issued_twice(project: Path) -> None:
    args = ["build", str(project), "-o", str(project.parent / "out"), "--issue", "x"]
    assert runner.invoke(app, args).exit_code == 0
    result = runner.invoke(app, [*args, "--out", str(project.parent / "out2")])
    assert result.exit_code == 1
    assert "Rev 02 is already issued" in result.output


def test_the_next_build_compares_with_the_recorded_issue(project: Path) -> None:
    out = project.parent / "out"
    assert (
        runner.invoke(app, ["build", str(project), "-o", str(out), "--issue", "x"]).exit_code == 0
    )
    result = runner.invoke(app, ["build", str(project), "-o", str(project.parent / "next")])
    assert result.exit_code == 0, result.output
    assert "against VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx:" in result.output


def test_a_changed_issue_file_warns_and_builds_without_compare(project: Path) -> None:
    out = project.parent / "out"
    assert (
        runner.invoke(app, ["build", str(project), "-o", str(out), "--issue", "x"]).exit_code == 0
    )
    (out / "VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx").write_bytes(b"changed")
    result = runner.invoke(app, ["build", str(project), "-o", str(project.parent / "next")])
    assert result.exit_code == 0, result.output
    assert "has changed since it was issued" in result.output
