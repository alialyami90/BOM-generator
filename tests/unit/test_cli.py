"""The ``bomgen`` command line: ``validate``, ``build`` and ``schema``."""

import io
import sys
from pathlib import Path

import pytest
from builders import SUBSTATION_DIR, default_p1, default_project, write_project
from typer.testing import CliRunner

from bomgen import __version__
from bomgen.cli import app, main

runner = CliRunner()


def test_version_prints_package_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"bomgen {__version__}"


def test_validate_ok_prints_summary(tmp_path: Path) -> None:
    project_file = write_project(tmp_path)
    result = runner.invoke(app, ["validate", "--project", str(project_file)])
    assert result.exit_code == 0
    assert result.stdout.strip() == (
        "OK: GIS 01: 1 substation(s); s1: 2 panels (p1, p2); 11 library parts"
    )


def test_validate_project_positional(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(write_project(tmp_path))])
    assert result.exit_code == 0
    assert result.stdout.startswith("OK: GIS 01: 1 substation(s)")


def test_validate_substation_file(tmp_path: Path) -> None:
    write_project(tmp_path)
    substation_file = tmp_path / SUBSTATION_DIR / "substation.yaml"
    result = runner.invoke(app, ["validate", str(substation_file)])
    assert result.exit_code == 0
    assert result.stdout.strip() == "OK: GIS 01 / s1: 2 panels (p1, p2), 11 library parts"


def test_validate_accepts_short_option(tmp_path: Path) -> None:
    project_file = write_project(tmp_path)
    result = runner.invoke(app, ["validate", "-p", str(project_file)])
    assert result.exit_code == 0
    assert result.stdout.startswith("OK: ")


def test_validate_reports_issues_and_exits_1(tmp_path: Path) -> None:
    p1 = default_p1()
    p1["devices"][1]["part_id"] = "NO-SUCH-PART"
    project_file = write_project(tmp_path, panels={"p1.yaml": p1})
    result = runner.invoke(app, ["validate", "-p", str(project_file)])
    assert result.exit_code == 1
    assert result.stdout == ""
    lines = result.stderr.strip().splitlines()
    assert lines[-1] == "1 problem(s) found."
    assert len(lines) == 2
    assert "p1.yaml:" in lines[0]
    assert "NO-SUCH-PART" in lines[0]


def test_validate_needs_exactly_one_file(tmp_path: Path) -> None:
    assert runner.invoke(app, ["validate"]).exit_code == 2
    project_file = str(write_project(tmp_path))
    assert runner.invoke(app, ["validate", project_file, "-p", project_file]).exit_code == 2


def test_schema_command_writes_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.invoke(app, ["schema", "--out", str(out_dir)])
    assert result.exit_code == 0
    names = [
        "library.schema.json",
        "panel.schema.json",
        "project.schema.json",
        "substation.schema.json",
    ]
    assert sorted(path.name for path in out_dir.iterdir()) == names
    for name in names:
        assert str(out_dir / name) in result.stdout


def test_no_arguments_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Substation SCADA BOM generator." in result.output
    assert "validate" in result.output
    assert "schema" in result.output


def test_validate_directory_path_reports_located_error_without_traceback(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", "-p", str(tmp_path)])
    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "Traceback" not in result.stderr
    lines = result.stderr.strip().splitlines()
    assert lines[0].startswith(f"{tmp_path.as_posix()}: cannot read file: ")
    assert lines[-1] == "1 problem(s) found."


def test_build_reports_input_issues_and_exits_1(tmp_path: Path) -> None:
    project = default_project()
    project["project"]["logo"] = "missing.png"
    result = runner.invoke(
        app, ["build", str(write_project(tmp_path, project=project)), "-o", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "project.logo: file not found" in result.stderr
    assert "1 problem(s) found." in result.stderr
    assert not list(tmp_path.glob("*.xlsx"))


def test_build_unknown_substation_is_a_usage_error(tmp_path: Path) -> None:
    project_file = write_project(tmp_path)
    result = runner.invoke(app, ["build", str(project_file), "--substation", "s9"])
    assert result.exit_code == 2
    assert "no substation 's9' (the project has: s1)" in result.output
    substation_file = tmp_path / SUBSTATION_DIR / "substation.yaml"
    result = runner.invoke(app, ["build", str(substation_file), "-s", "s9"])
    assert result.exit_code == 2
    assert "no substation 's9'" in result.output


def test_main_writes_utf8_to_a_cp1252_console(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The frozen bomgen.exe on Windows gets a cp1252 stdout; the check report has "ΣQ".
    raw = io.BytesIO()
    stdout = io.TextIOWrapper(raw, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    project = Path(__file__).resolve().parents[2] / "examples" / "project.yaml"
    monkeypatch.setattr(sys, "argv", ["bomgen", "build", str(project), "-o", str(tmp_path)])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 0
    sys.stdout.flush()
    assert "ΣQ" in raw.getvalue().decode("utf-8")
