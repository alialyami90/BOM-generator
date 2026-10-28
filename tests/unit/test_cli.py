"""The ``bomgen`` command line: ``validate`` and ``schema``."""

from pathlib import Path

from builders import default_p1, write_project
from typer.testing import CliRunner

from bomgen.cli import app

runner = CliRunner()


def test_validate_ok_prints_summary(tmp_path: Path) -> None:
    project_file = write_project(tmp_path)
    result = runner.invoke(app, ["validate", "--project", str(project_file)])
    assert result.exit_code == 0
    assert result.stdout.strip() == "OK: GIS 01: 2 panels (p1, p2), 10 library parts"


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


def test_validate_requires_project_option() -> None:
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 2


def test_schema_command_writes_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.invoke(app, ["schema", "--out", str(out_dir)])
    assert result.exit_code == 0
    names = ["library.schema.json", "panel.schema.json", "project.schema.json"]
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
