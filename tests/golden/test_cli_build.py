"""``bomgen build`` on the example project (plan M7): one workbook per substation."""

import json
from pathlib import Path

import openpyxl
import pytest
from typer.testing import CliRunner

from bomgen import build as build_module
from bomgen.cli import app
from bomgen.models.report import CheckItem, CheckReport, CheckStatus

pytestmark = pytest.mark.golden

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
# Output requirements (OUT-2): '<project doc no.>_PSA_BOM_Rev<rev>.xlsx'; the register's
# gis01-bom entry is VD-EL0009-861GISPSA-001 rev 02.
FILE_NAME = "VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx"
SHEETS = ["1", "2", "3", "4", "Power Consumption", "Heat Dissipation", "Heat Calculations"]

runner = CliRunner()


@pytest.mark.parametrize(
    "args",
    [
        ["build", str(EXAMPLES / "project.yaml")],
        ["build", str(EXAMPLES / "project.yaml"), "--substation", "gis01"],
        ["build", str(EXAMPLES / "substations" / "gis01" / "substation.yaml")],
    ],
)
def test_build_writes_the_example_workbook(tmp_path: Path, args: list[str]) -> None:
    result = runner.invoke(app, [*args, "--out", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    written = tmp_path / "out" / FILE_NAME
    assert result.stdout.splitlines()[0] == str(written)
    assert openpyxl.load_workbook(written).sheetnames == SHEETS


def test_build_prints_and_writes_the_check_report(tmp_path: Path) -> None:
    result = runner.invoke(app, ["build", str(EXAMPLES / "project.yaml"), "-o", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # Two warnings: the 16 A main MCB override on psa1/psa2 (plan Q3).
    assert result.stdout.splitlines()[-1] == "0 failed, 2 warnings, 14 passed"
    assert "PASS  psa1  PSA1-EXT-FW-A  sfp_slots  2 SFPs in 2 SFP slots" in result.stdout
    report = json.loads((tmp_path / FILE_NAME).with_suffix(".checks.json").read_text("utf-8"))
    assert report["failed"] is False
    assert len(report["items"]) == 16


def test_no_checks_skips_the_report(tmp_path: Path) -> None:
    args = ["build", str(EXAMPLES / "project.yaml"), "-o", str(tmp_path), "--no-checks"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == str(tmp_path / FILE_NAME)
    assert not list(tmp_path.glob("*.checks.json"))


def test_a_failed_check_exits_1_after_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failing = CheckReport(
        items=(CheckItem(check="di_capacity", status=CheckStatus.FAIL, message="too few"),)
    )
    monkeypatch.setattr(build_module, "check_report", lambda loaded, result: failing)
    result = runner.invoke(app, ["build", str(EXAMPLES / "project.yaml"), "-o", str(tmp_path)])
    assert result.exit_code == 1
    assert (tmp_path / FILE_NAME).is_file()
    assert "FAIL  di_capacity  too few" in result.stdout


def test_compare_with_an_identical_previous_issue_marks_nothing(tmp_path: Path) -> None:
    project = str(EXAMPLES / "project.yaml")
    first = runner.invoke(app, ["build", project, "-o", str(tmp_path / "before"), "--no-checks"])
    assert first.exit_code == 0, first.output
    previous = tmp_path / "before" / FILE_NAME
    args = ["build", project, "-o", str(tmp_path / "after"), "--no-checks"]
    result = runner.invoke(app, [*args, "--compare", str(previous)])
    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines()[-1] == f"against {FILE_NAME}: 0 changed, 0 added, 0 removed"


def test_compare_with_an_unreadable_file_exits_1(tmp_path: Path) -> None:
    bogus = tmp_path / "old.xlsx"
    bogus.write_text("not a workbook", encoding="utf-8")
    args = ["build", str(EXAMPLES / "project.yaml"), "-o", str(tmp_path), "--compare", str(bogus)]
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "not a readable .xlsx workbook" in result.stderr
    assert not (tmp_path / FILE_NAME).exists()
