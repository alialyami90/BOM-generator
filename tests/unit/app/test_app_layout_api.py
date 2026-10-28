"""The app lays out generated panels as ``bomgen build`` does (plan M10d, M1c)."""

import json
import shutil
from pathlib import Path
from typing import Any

import openpyxl
import pytest
from typer.testing import CliRunner

from bomgen.app import api
from bomgen.cli import app as cli

EXAMPLES = Path(__file__).parents[3] / "examples"
runner = CliRunner()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


@pytest.fixture
def substation(project: Path) -> Path:
    path = project.parent / "substations" / "gis01" / "substation.yaml"
    # As in the CLI layout tests: feed the annunciator from psa1, which the layout writes
    path.write_text(path.read_text().replace("fed_from: psa3", "fed_from: psa1"))
    return path


@pytest.fixture
def generated(substation: Path) -> Path:
    result = runner.invoke(cli, ["layout", "--substation", str(substation), "--force"])
    assert result.exit_code == 0, result.output
    return substation


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
    return api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
            "BOMGEN_APP_HOME": str(tmp_path / "app"),
        }
    )


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)
    return envelope["data"]


def refused(envelope: dict[str, object]) -> str:
    assert envelope["ok"] is False, envelope
    return envelope["error"]["kind"]  # type: ignore[index,no-any-return]


def values(path: Path) -> dict[str, list[tuple[object, ...]]]:
    book = openpyxl.load_workbook(path)
    return {sheet.title: list(sheet.iter_rows(values_only=True)) for sheet in book}


def test_the_app_builds_generated_panels_as_the_cli_does(
    app: api.Api, project: Path, generated: Path, tmp_path: Path
) -> None:
    # An override added after the last `bomgen layout`: the files on disk are stale
    text = generated.read_text().replace(
        "  overrides: []", "  overrides: [{device: gps, panel: 2}]"
    )
    generated.write_text(text)
    result = runner.invoke(cli, ["build", str(generated), "--out", str(tmp_path / "cli")])
    assert result.exit_code == 0, result.output

    built = ok(app.build_workbook(str(project), "gis01", str(tmp_path / "app")))

    assert built["sheets"][:3] == ["1", "2", "4"]  # psa3's devices sit in psa1 and psa2
    assert "SEL-2488" in str(values(Path(built["path"]))["2"])  # the GPS clock moved
    assert values(Path(built["path"])) == values(next((tmp_path / "cli").glob("*.xlsx")))


def test_preview_and_build_target_show_the_laid_out_panels(
    app: api.Api, project: Path, generated: Path
) -> None:
    preview = ok(app.preview_substation(str(project), "gis01"))
    target = ok(app.build_target(str(project), "gis01"))

    assert [p["sheet"] for p in preview["panels"]][:3] == ["1", "2", "4"]
    assert [s["name"] for s in target["sheets"]][:3] == ["1", "2", "4"]


def test_a_layout_error_blocks_build_and_preview(
    app: api.Api, project: Path, generated: Path, tmp_path: Path
) -> None:
    text = generated.read_text().replace(
        "  overrides: []", "  overrides: [{pair: gw, panel: [9, 10]}]"
    )
    generated.write_text(text)

    checks = ok(app.run_checks(str(project), "gis01"))
    layout = [p for p in checks["problems"] if p["location"].startswith("layout")]
    assert layout
    assert {p["level"] for p in layout} == {"error"}
    assert checks["engine"]["run"] is False
    assert refused(app.build_workbook(str(project), "gis01", str(tmp_path))) == "has_errors"
    assert ok(app.preview_substation(str(project), "gis01"))["reason"]


def test_layout_warnings_show_and_do_not_block_build(
    app: api.Api, project: Path, substation: Path, tmp_path: Path
) -> None:
    psa1 = substation.parent / "panels" / "psa1.yaml"
    psa1.write_text(psa1.read_text() + "generated: true\n")  # psa2, psa3 stay hand-written

    checks = ok(app.run_checks(str(project), "gis01"))

    warnings = {p["location"] for p in checks["problems"] if p["level"] == "warning"}
    assert {"layout: psa2", "layout: psa3"} <= warnings
    assert checks["engine"]["run"] is True
    assert ok(app.build_workbook(str(project), "gis01", str(tmp_path)))["path"]


def test_hand_written_panels_are_built_as_they_are(app: api.Api, project: Path) -> None:
    target = ok(app.build_target(str(project), "gis01"))

    assert [s["name"] for s in target["sheets"]][:4] == ["1", "2", "3", "4"]
    assert target["problems"] == []
