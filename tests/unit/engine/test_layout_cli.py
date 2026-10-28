"""``bomgen layout`` writes the generated panel files; ``bomgen build`` lays them out again."""

import shutil
from pathlib import Path

import openpyxl
import pytest
import yaml
from typer.testing import CliRunner

from bomgen.cli import app

EXAMPLES = Path(__file__).parents[3] / "examples"
runner = CliRunner()


@pytest.fixture
def substation(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "examples")
    path = tmp_path / "examples" / "substations" / "gis01" / "substation.yaml"
    # The example feeds the annunciator from the hand-written psa3, which the layout
    # does not write; feed it from psa1 so the layout has no errors.
    path.write_text(path.read_text().replace("fed_from: psa3", "fed_from: psa1"))
    return path


def test_cli_layout_writes_panels_and_prints_fill(substation: Path, tmp_path: Path) -> None:
    out = tmp_path / "generated"
    result = runner.invoke(app, ["layout", "--substation", str(substation), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in out.iterdir()) == ["psa1.yaml", "psa2.yaml"]
    assert yaml.safe_load((out / "psa1.yaml").read_text())["generated"] is True
    assert "IED count: 40" in result.stdout
    assert "Panel 1: 29 U / 32 U" in result.stdout


def test_cli_layout_keeps_hand_written_panels(substation: Path) -> None:
    before = (substation.parent / "panels" / "psa1.yaml").read_text()
    result = runner.invoke(app, ["layout", "--substation", str(substation)])
    assert result.exit_code == 1
    assert "hand-written panel file" in result.output
    assert (substation.parent / "panels" / "psa1.yaml").read_text() == before


def test_cli_layout_overwrites_its_own_files(substation: Path) -> None:
    args = ["layout", "--substation", str(substation)]
    assert runner.invoke(app, [*args, "--force"]).exit_code == 0
    assert runner.invoke(app, args).exit_code == 0  # now generated: no --force needed


def test_cli_layout_exits_1_on_layout_errors(substation: Path, tmp_path: Path) -> None:
    text = substation.read_text().replace(
        "  overrides: []", "  overrides: [{pair: gw, panel: [9, 10]}]"
    )
    substation.write_text(text)
    result = runner.invoke(
        app, ["layout", "--substation", str(substation), "--out", str(tmp_path / "g")]
    )
    assert result.exit_code == 1
    assert "error: gw" in result.stdout
    assert "unknown-panel" not in result.stdout  # messages, not kinds


def test_cli_build_after_layout_uses_the_generated_panels(substation: Path, tmp_path: Path) -> None:
    assert runner.invoke(app, ["layout", "--substation", str(substation), "--force"]).exit_code == 0
    out = tmp_path / "out"
    result = runner.invoke(app, ["build", str(substation), "--out", str(out)])
    assert result.exit_code == 0, result.output
    book = openpyxl.load_workbook(next(out.glob("*.xlsx")))
    assert book.sheetnames[:3] == ["1", "2", "4"]  # psa3's devices now sit in psa1 and psa2


def test_cli_build_no_layout_builds_the_files_as_they_are(substation: Path, tmp_path: Path) -> None:
    assert runner.invoke(app, ["layout", "--substation", str(substation), "--force"]).exit_code == 0
    out = tmp_path / "out"
    result = runner.invoke(app, ["build", str(substation), "--no-layout", "--out", str(out)])
    assert result.exit_code == 0, result.output
    book = openpyxl.load_workbook(next(out.glob("*.xlsx")))
    assert book.sheetnames[:4] == ["1", "2", "3", "4"]
