"""Exporting a project folder as a `.bomproj` file (ADR 0012, plan M8b)."""

import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from project_builders import FILES, PROJECT_YAML, make_project

import bomgen
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.project_store.export import export_project, read_project_identity

CREATED = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


def _members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def test_export_writes_every_project_file_and_a_manifest(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")

    result = export_project(project_file, tmp_path / "out.bomproj", created=CREATED)

    members = _members(result.path)
    assert sorted(members) == sorted(["manifest.json", "project.yaml", *FILES])
    assert members["project.yaml"].decode() == PROJECT_YAML
    assert members["substations/psa/panels/p1.yaml"] == b"id: p1\n"


def test_export_manifest_records_project_library_and_app_version(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")

    result = export_project(project_file, tmp_path / "out.bomproj", created=CREATED)

    manifest = json.loads(_members(result.path)["manifest.json"])
    assert manifest["format_version"] == 1
    assert manifest["project_id"] == "jfgp2"
    assert manifest["library_name"] == "psa-devices"
    assert manifest["library_version"] == "1.2.0"
    assert manifest["app_version"] == bomgen.__version__
    assert manifest["created"].startswith("2026-10-28T12:00:00")
    assert set(manifest["files"]) == {"project.yaml", *FILES}
    assert result.manifest.project_id == "jfgp2"


def test_export_excludes_out_backups_and_bomproj_files(tmp_path: Path) -> None:
    project_file = make_project(
        tmp_path / "jfgp2",
        **{
            "substations/psa/out/BOM.xlsx": "x",
            "out/report.txt": "x",
            "Backups/jfgp2-20260101-000000.bomproj": "x",
            "earlier.bomproj": "x",
            ".git/config": "x",
        },
    )

    result = export_project(project_file, tmp_path / "out.bomproj")

    assert sorted(_members(result.path)) == sorted(["manifest.json", "project.yaml", *FILES])


def test_export_keeps_a_nested_folder_named_backups(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2", **{"substations/psa/Backups/keep.yaml": "x"})

    result = export_project(project_file, tmp_path / "out.bomproj")

    assert "substations/psa/Backups/keep.yaml" in _members(result.path)


def test_export_does_not_follow_symlinks(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")
    secret = tmp_path / "secret.yaml"
    secret.write_text("secret")
    try:
        os.symlink(secret, project_file.parent / "linked.yaml")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")

    result = export_project(project_file, tmp_path / "out.bomproj")

    assert "linked.yaml" not in _members(result.path)


def test_export_defaults_to_the_project_id_in_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_file = make_project(tmp_path / "jfgp2")
    monkeypatch.chdir(tmp_path)

    result = export_project(project_file)

    assert result.path == tmp_path / "jfgp2.bomproj"
    assert result.path.is_file()


def test_export_into_the_project_folder_is_not_packed_next_time(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")
    inside = project_file.parent / "jfgp2.bomproj"
    export_project(project_file, inside)

    again = export_project(project_file, tmp_path / "again.bomproj")

    assert "jfgp2.bomproj" not in _members(again.path)


def test_export_is_deterministic(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")

    first = export_project(project_file, tmp_path / "a.bomproj", created=CREATED)
    second = export_project(project_file, tmp_path / "b.bomproj", created=CREATED)

    assert first.path.read_bytes() == second.path.read_bytes()


def test_export_without_a_library_records_none(tmp_path: Path) -> None:
    project_file = make_project(
        tmp_path / "jfgp2", project_yaml="project:\n  id: jfgp2\n  name: X\n"
    )

    result = export_project(project_file, tmp_path / "out.bomproj")

    assert result.manifest.library_name is None
    assert result.manifest.library_version is None


@pytest.mark.parametrize(
    "project_yaml",
    [
        "name: no project key\n",
        "project:\n  name: no id\n",
        "project:\n  id: 3\n",
        "project:\n  id: ../escape\n",
        "project:\n  id: con\n",
        "project:\n  id: with space\n",
        "project:\n  id: ok\nlibrary:\n  name: psa\n",
        "project:\n  id: ok\nlibrary:\n  name: psa\n  version: one\n",
        "- just\n- a list\n",
        "project: [unclosed\n",
    ],
)
def test_export_refuses_an_unusable_project_file(tmp_path: Path, project_yaml: str) -> None:
    project_file = make_project(tmp_path / "p", project_yaml=project_yaml)

    with pytest.raises(LibraryPackageError) as caught:
        export_project(project_file, tmp_path / "out.bomproj")

    assert caught.value.kind is RefusalKind.INVALID_PROJECT
    assert not (tmp_path / "out.bomproj").exists()


def test_export_refuses_a_missing_project_file(tmp_path: Path) -> None:
    with pytest.raises(LibraryPackageError) as caught:
        export_project(tmp_path / "nowhere" / "project.yaml", tmp_path / "out.bomproj")

    assert caught.value.kind is RefusalKind.INVALID_PROJECT


def test_read_project_identity_returns_id_and_library(tmp_path: Path) -> None:
    identity = read_project_identity(make_project(tmp_path / "p"))

    assert (identity.id, identity.library_name, identity.library_version) == (
        "jfgp2",
        "psa-devices",
        "1.2.0",
    )


@pytest.mark.parametrize("library_name", ["../../x", "Has Space", "con"])
def test_export_refuses_an_unsafe_library_name(tmp_path: Path, library_name: str) -> None:
    project_file = make_project(
        tmp_path / "p",
        project_yaml=(
            f"project:\n  id: ok\nlibrary:\n  name: {library_name!r}\n  version: 1.0.0\n"
        ),
    )

    with pytest.raises(LibraryPackageError) as caught:
        export_project(project_file, tmp_path / "out.bomproj")

    assert caught.value.kind is RefusalKind.INVALID_PROJECT


def test_identity_read_agrees_with_the_project_model_on_the_example_project() -> None:
    from bomgen.models.project import Project

    project_file = Path(__file__).parents[3] / "examples" / "project.yaml"
    model = Project.model_validate(yaml.safe_load(project_file.read_text(encoding="utf-8")))

    identity = read_project_identity(project_file)

    assert identity.id == model.project.id
    assert identity.library_name == model.library.name
    assert identity.library_version == model.library.version
