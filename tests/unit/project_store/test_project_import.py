"""Importing a `.bomproj` into the workspace (ADR 0012, plan M8b)."""

import json
import os
import zipfile
from datetime import datetime
from pathlib import Path

import pytest
from project_builders import FILES, PROJECT_YAML, make_project

from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore
from bomgen.project_store.export import export_project
from bomgen.project_store.importer import import_project

NOW = datetime(2026, 10, 28, 15, 0, 0)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


@pytest.fixture
def package(tmp_path: Path) -> Path:
    project_file = make_project(tmp_path / "source" / "jfgp2")
    return export_project(project_file, tmp_path / "jfgp2.bomproj").path


def _install_library(store: LibraryStore, tmp_path: Path, version: str) -> None:
    source = tmp_path / f"lib-{version}.yaml"
    source.write_text("devices: []\n")
    bomlib = tmp_path / f"psa-devices-{version}.bomlib"
    pack(source, bomlib, name="psa-devices", version=version)
    store.import_package(bomlib, force=True)


def _tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes().decode("utf-8", "replace")
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _rewrite(source: Path, target: Path, **manifest_changes: object) -> Path:
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w") as new:
        for name in old.namelist():
            data = old.read(name)
            if name == "manifest.json":
                manifest = json.loads(data)
                manifest.update(manifest_changes)
                data = json.dumps(manifest).encode()
            new.writestr(name, data)
    return target


def test_import_creates_the_project_in_the_workspace(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    result = import_project(package, workspace=workspace, store=store)

    project_dir = workspace / "jfgp2"
    assert result.project_dir == project_dir
    assert result.manifest.project_id == "jfgp2"
    assert not result.replaced
    assert result.backup is None
    assert _tree(project_dir) == {"project.yaml": PROJECT_YAML, **FILES}


def test_import_defaults_to_the_workspace_from_the_environment(
    tmp_path: Path, package: Path, store: LibraryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BOMGEN_WORKSPACE", str(tmp_path / "from-env"))

    result = import_project(package, store=store)

    assert result.project_dir == tmp_path / "from-env" / "jfgp2"


def test_import_refuses_an_existing_project_unless_forced(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    import_project(package, workspace=workspace, store=store)
    (workspace / "jfgp2" / "project.yaml").write_text("edited locally\n")

    with pytest.raises(LibraryPackageError) as caught:
        import_project(package, workspace=workspace, store=store)

    assert caught.value.kind is RefusalKind.PROJECT_EXISTS
    assert "jfgp2" in str(caught.value)
    assert (workspace / "jfgp2" / "project.yaml").read_text() == "edited locally\n"


def test_forced_import_backs_up_then_overwrites(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    import_project(package, workspace=workspace, store=store)
    project_dir = workspace / "jfgp2"
    (project_dir / "substations/psa/substation.yaml").write_text("edited locally\n")

    result = import_project(package, workspace=workspace, force=True, store=store, now=NOW)

    assert result.replaced
    assert result.backup == project_dir / "Backups" / "jfgp2-20261028-150000.bomproj"
    assert (project_dir / "substations/psa/substation.yaml").read_text() == "name: PSA\n"
    with zipfile.ZipFile(result.backup) as zf:
        assert zf.read("substations/psa/substation.yaml") == b"edited locally\n"


def test_forced_import_keeps_backups_and_out_folders(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    import_project(package, workspace=workspace, store=store)
    project_dir = workspace / "jfgp2"
    (project_dir / "Backups").mkdir()
    (project_dir / "Backups" / "older.bomproj").write_text("old backup")
    (project_dir / "substations/psa/out").mkdir()
    (project_dir / "substations/psa/out/BOM.xlsx").write_text("workbook")

    import_project(package, workspace=workspace, force=True, store=store, now=NOW)

    assert (project_dir / "Backups" / "older.bomproj").read_text() == "old backup"
    assert (project_dir / "substations/psa/out/BOM.xlsx").read_text() == "workbook"


def test_forced_import_removes_files_the_package_dropped(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    import_project(package, workspace=workspace, store=store)
    stale = workspace / "jfgp2" / "substations/psa/panels/old.yaml"
    stale.write_text("stale")

    import_project(package, workspace=workspace, force=True, store=store, now=NOW)

    assert not stale.exists()


def test_failed_forced_import_keeps_the_existing_project(
    workspace: Path, package: Path, store: LibraryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    import_project(package, workspace=workspace, store=store)
    project_dir = workspace / "jfgp2"
    (project_dir / "project.yaml").write_text("edited locally\n")
    before = _tree(workspace)
    real_replace = os.replace

    def locked(src: str | Path, dst: str | Path) -> None:
        if Path(src).name.startswith(".incoming-"):
            raise PermissionError("locked by antivirus")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", locked)
    with pytest.raises(PermissionError):
        import_project(package, workspace=workspace, force=True, store=store, now=NOW)
    monkeypatch.undo()

    after = _tree(workspace)
    after.pop("jfgp2/Backups/jfgp2-20261028-150000.bomproj", None)  # the safety backup may remain
    assert after == before
    assert not [p for p in workspace.iterdir() if p.name.startswith(".")]


def test_import_rejects_a_tampered_package(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    tampered = tmp_path / "tampered.bomproj"
    with zipfile.ZipFile(package) as old, zipfile.ZipFile(tampered, "w") as new:
        for name in old.namelist():
            data = old.read(name)
            new.writestr(name, data + b"#" if name == "project.yaml" else data)

    with pytest.raises(LibraryPackageError, match=r"checksum mismatch: project\.yaml"):
        import_project(tampered, workspace=workspace, store=store)

    assert not workspace.exists()


@pytest.mark.parametrize("project_id", ["../escape", "con", "a/b", "", "x" * 65])
def test_import_rejects_a_hostile_project_id(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore, project_id: str
) -> None:
    hostile = _rewrite(package, tmp_path / "hostile.bomproj", project_id=project_id)

    with pytest.raises(LibraryPackageError):
        import_project(hostile, workspace=workspace, store=store)

    assert not workspace.exists()
    assert not (tmp_path / "escape").exists()


def test_import_rejects_a_manifest_that_disagrees_with_project_yaml(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    other = _rewrite(package, tmp_path / "other.bomproj", project_id="someone-else")

    with pytest.raises(LibraryPackageError, match=r"someone-else.*jfgp2"):
        import_project(other, workspace=workspace, store=store)


def test_import_rejects_a_newer_format(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    newer = _rewrite(package, tmp_path / "newer.bomproj", format_version=2)

    with pytest.raises(LibraryPackageError) as caught:
        import_project(newer, workspace=workspace, store=store)

    assert caught.value.kind is RefusalKind.INCOMPATIBLE


def test_a_bomlib_given_to_project_import_is_explained(
    tmp_path: Path, workspace: Path, store: LibraryStore
) -> None:
    source = tmp_path / "library.yaml"
    source.write_text("devices: []\n")
    bomlib = tmp_path / "psa-1.0.0.bomlib"
    pack(source, bomlib, name="psa", version="1.0.0")

    with pytest.raises(LibraryPackageError, match=r"\.bomlib library.*bomgen library import"):
        import_project(bomlib, workspace=workspace, store=store)


def test_import_names_the_bomlib_to_install_when_the_library_is_missing(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    result = import_project(package, workspace=workspace, store=store)

    assert result.library_note is not None
    assert "psa-devices 1.2.0" in result.library_note
    assert "bomgen library import psa-devices-1.2.0.bomlib" in result.library_note


def test_import_names_the_bomlib_to_install_when_the_active_version_differs(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    _install_library(store, tmp_path, "1.1.0")

    result = import_project(package, workspace=workspace, store=store)

    assert result.library_note is not None
    assert "the active version is 1.1.0" in result.library_note
    assert "bomgen library import psa-devices-1.2.0.bomlib" in result.library_note


def test_import_names_rollback_when_the_version_is_installed_but_inactive(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    _install_library(store, tmp_path, "1.2.0")
    _install_library(store, tmp_path, "1.3.0")

    result = import_project(package, workspace=workspace, store=store)

    assert result.library_note is not None
    assert "bomgen library rollback psa-devices --to 1.2.0" in result.library_note


def test_no_library_note_when_the_versions_match(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    _install_library(store, tmp_path, "1.2.0")

    assert import_project(package, workspace=workspace, store=store).library_note is None


def test_no_library_note_for_a_project_without_a_library(
    tmp_path: Path, workspace: Path, store: LibraryStore
) -> None:
    project_file = make_project(tmp_path / "bare", project_yaml="project:\n  id: bare\n  name: B\n")
    package = export_project(project_file, tmp_path / "bare.bomproj").path

    assert import_project(package, workspace=workspace, store=store).library_note is None
