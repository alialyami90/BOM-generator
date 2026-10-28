"""`bomgen project export | import | backup` (ADR 0012, plan M8b)."""

import zipfile
from pathlib import Path

import pytest
from project_builders import make_project
from typer.testing import CliRunner

from bomgen.cli import app


@pytest.fixture
def runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.setenv("BOMGEN_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv("BOMGEN_LIBRARY_HOME", str(tmp_path / "libraries"))
    return CliRunner()


def test_project_group_is_part_of_the_bomgen_app(runner: CliRunner) -> None:
    result = runner.invoke(app, ["project", "--help"])

    assert result.exit_code == 0
    for command in ("export", "import", "backup"):
        assert command in result.output


def test_export_import_and_backup_round_trip(runner: CliRunner, tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "source" / "jfgp2")
    package = tmp_path / "jfgp2.bomproj"

    exported = runner.invoke(app, ["project", "export", str(project_file), "-o", str(package)])
    assert exported.exit_code == 0, exported.output
    assert f"Wrote {package} (jfgp2, 3 files)" in exported.output

    imported = runner.invoke(app, ["project", "import", str(package)])
    assert imported.exit_code == 0, imported.output
    project_dir = tmp_path / "workspace" / "jfgp2"
    assert f"Imported project jfgp2 into {project_dir}" in imported.output
    assert (project_dir / "project.yaml").is_file()

    saved = runner.invoke(app, ["project", "backup", str(project_dir / "project.yaml")])
    assert saved.exit_code == 0, saved.output
    assert "Backup saved to" in saved.output
    assert len(list((project_dir / "Backups").glob("jfgp2-*.bomproj"))) == 1


def test_import_tells_which_bomlib_to_install(runner: CliRunner, tmp_path: Path) -> None:
    package = tmp_path / "p.bomproj"
    runner.invoke(
        app, ["project", "export", str(make_project(tmp_path / "s" / "jfgp2")), "-o", str(package)]
    )

    result = runner.invoke(app, ["project", "import", str(package)])

    assert result.exit_code == 0, result.output
    assert "note: " in result.output
    assert "bomgen library import psa-devices-1.2.0.bomlib" in result.output


def test_import_refuses_an_existing_project_with_exit_1(runner: CliRunner, tmp_path: Path) -> None:
    package = tmp_path / "p.bomproj"
    runner.invoke(
        app, ["project", "export", str(make_project(tmp_path / "s" / "jfgp2")), "-o", str(package)]
    )
    runner.invoke(app, ["project", "import", str(package)])

    result = runner.invoke(app, ["project", "import", str(package)])

    assert result.exit_code == 1
    assert "error: project 'jfgp2' already exists" in result.output
    assert "--force" in result.output


def test_import_force_replaces_and_reports_the_backup(runner: CliRunner, tmp_path: Path) -> None:
    package = tmp_path / "p.bomproj"
    runner.invoke(
        app, ["project", "export", str(make_project(tmp_path / "s" / "jfgp2")), "-o", str(package)]
    )
    runner.invoke(app, ["project", "import", str(package)])

    result = runner.invoke(app, ["project", "import", str(package), "--force"])

    assert result.exit_code == 0, result.output
    assert "Replaced the existing project; its backup is" in result.output
    assert list((tmp_path / "workspace" / "jfgp2" / "Backups").glob("*.bomproj"))


def test_import_into_a_chosen_workspace(runner: CliRunner, tmp_path: Path) -> None:
    package = tmp_path / "p.bomproj"
    runner.invoke(
        app, ["project", "export", str(make_project(tmp_path / "s" / "jfgp2")), "-o", str(package)]
    )
    chosen = tmp_path / "chosen"

    result = runner.invoke(app, ["project", "import", str(package), "--workspace", str(chosen)])

    assert result.exit_code == 0, result.output
    assert (chosen / "jfgp2" / "project.yaml").is_file()


def test_export_of_an_unusable_project_fails_in_one_line(runner: CliRunner, tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "p", project_yaml="name: nothing\n")

    result = runner.invoke(app, ["project", "export", str(project_file), "-o", str(tmp_path / "x")])

    assert result.exit_code == 1
    assert result.output.startswith("error: ")
    assert "Traceback" not in result.output


def test_import_of_a_tampered_package_exits_1(runner: CliRunner, tmp_path: Path) -> None:
    package = tmp_path / "p.bomproj"
    runner.invoke(
        app, ["project", "export", str(make_project(tmp_path / "s" / "jfgp2")), "-o", str(package)]
    )
    tampered = tmp_path / "t.bomproj"
    with zipfile.ZipFile(package) as old, zipfile.ZipFile(tampered, "w") as new:
        for name in old.namelist():
            data = old.read(name)
            new.writestr(name, data + b"#" if name == "project.yaml" else data)

    result = runner.invoke(app, ["project", "import", str(tampered)])

    assert result.exit_code == 1
    assert "error: checksum mismatch: project.yaml" in result.output
    assert not (tmp_path / "workspace").exists()


def test_import_with_rename_to_keeps_both_projects(runner: CliRunner, tmp_path: Path) -> None:
    package = tmp_path / "jfgp2.bomproj"
    runner.invoke(
        app, ["project", "export", str(make_project(tmp_path / "s" / "jfgp2")), "-o", str(package)]
    )
    runner.invoke(app, ["project", "import", str(package)])

    clash = runner.invoke(app, ["project", "import", str(package)])
    kept = runner.invoke(app, ["project", "import", str(package), "--rename-to", "jfgp2-2"])

    assert clash.exit_code == 1
    assert "--rename-to" in clash.output
    assert kept.exit_code == 0, kept.output
    assert "Imported project jfgp2-2" in kept.output
    assert (tmp_path / "workspace" / "jfgp2-2" / "project.yaml").is_file()
    assert (tmp_path / "workspace" / "jfgp2" / "project.yaml").is_file()
