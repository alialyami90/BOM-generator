"""The import dry-run: every check listed, nothing written."""

import json
import zipfile
from pathlib import Path

import pytest
from project_builders import FILES, make_project

from bomgen.bundle.checks import CheckStatus
from bomgen.bundle.errors import RefusalKind
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore
from bomgen.project_store.export import export_project
from bomgen.project_store.importer import import_project
from bomgen.project_store.preview import preview_project_import

IDS = [
    "package",
    "paths",
    "size",
    "manifest",
    "files",
    "checksums",
    "identity",
    "contents",
    "name",
    "library",
]


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


def _statuses(preview: object) -> dict[str, CheckStatus]:
    return {c.id: c.status for c in preview.checks}  # type: ignore[attr-defined]


def _install_library(store: LibraryStore, tmp_path: Path, version: str) -> None:
    source = tmp_path / f"lib-{version}.yaml"
    source.write_text("devices: []\n")
    bomlib = tmp_path / f"psa-devices-{version}.bomlib"
    pack(source, bomlib, name="psa-devices", version=version)
    store.import_package(bomlib, force=True)


def test_preview_lists_every_check_and_the_contents(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    preview = preview_project_import(package, workspace=workspace, store=store)

    assert [c.id for c in preview.checks] == IDS
    assert preview.project_id == "jfgp2"
    assert preview.target_dir == workspace / "jfgp2"
    assert not preview.exists
    assert sorted(f.name for f in preview.files) == sorted(["project.yaml", *FILES])
    assert all(f.size > 0 for f in preview.files)
    assert preview.manifest is not None
    assert preview.manifest.library_name == "psa-devices"


def test_a_good_package_for_a_new_project_can_be_imported(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    _install_library(store, tmp_path, "1.2.0")

    preview = preview_project_import(package, workspace=workspace, store=store)

    assert preview.can_import
    assert set(_statuses(preview).values()) == {CheckStatus.OK}
    assert preview.library_note is None


def test_preview_writes_nothing(workspace: Path, package: Path, store: LibraryStore) -> None:
    preview_project_import(package, workspace=workspace, store=store)

    assert not workspace.exists()


def test_an_existing_project_is_a_warning_not_a_failure(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    import_project(package, workspace=workspace, store=store)

    preview = preview_project_import(package, workspace=workspace, store=store)

    assert preview.exists
    assert preview.can_import
    name = next(c for c in preview.checks if c.id == "name")
    assert name.status is CheckStatus.WARNING
    assert "jfgp2" in name.detail
    assert "backed up" in name.detail


def test_a_library_that_differs_is_a_warning_with_the_remedy(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    preview = preview_project_import(package, workspace=workspace, store=store)

    library = next(c for c in preview.checks if c.id == "library")
    assert library.status is CheckStatus.WARNING
    assert "bomgen library import psa-devices-1.2.0.bomlib" in library.detail
    assert preview.library_note == library.detail
    assert preview.can_import


def test_a_project_without_a_library_passes_the_library_check(
    tmp_path: Path, workspace: Path, store: LibraryStore
) -> None:
    project_file = make_project(tmp_path / "bare", project_yaml="project:\n  id: bare\n  name: B\n")
    package = export_project(project_file, tmp_path / "bare.bomproj").path

    preview = preview_project_import(package, workspace=workspace, store=store)

    assert next(c for c in preview.checks if c.id == "library").status is CheckStatus.OK


def test_a_tampered_package_fails_the_checksum_check(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    tampered = tmp_path / "tampered.bomproj"
    with zipfile.ZipFile(package) as old, zipfile.ZipFile(tampered, "w") as new:
        for name in old.namelist():
            data = old.read(name)
            new.writestr(name, data + b"#" if name == "project.yaml" else data)

    preview = preview_project_import(tampered, workspace=workspace, store=store)

    statuses = _statuses(preview)
    assert statuses["checksums"] is CheckStatus.FAILED
    assert statuses["identity"] is CheckStatus.SKIPPED
    assert statuses["name"] is CheckStatus.SKIPPED
    assert not preview.can_import
    assert preview.project_id == "jfgp2"  # the manifest was readable
    assert preview.files == []


def test_a_hostile_project_id_fails_the_manifest_check(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    hostile = tmp_path / "hostile.bomproj"
    with zipfile.ZipFile(package) as old, zipfile.ZipFile(hostile, "w") as new:
        for name in old.namelist():
            data = old.read(name)
            if name == "manifest.json":
                data = json.dumps({**json.loads(data), "project_id": "../escape"}).encode()
            new.writestr(name, data)

    preview = preview_project_import(hostile, workspace=workspace, store=store)

    assert _statuses(preview)["manifest"] is CheckStatus.FAILED
    assert preview.project_id is None
    assert preview.target_dir is None
    assert not preview.can_import


def test_a_newer_format_is_reported_as_incompatible(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    newer = tmp_path / "newer.bomproj"
    with zipfile.ZipFile(package) as old, zipfile.ZipFile(newer, "w") as new:
        for name in old.namelist():
            data = old.read(name)
            if name == "manifest.json":
                data = json.dumps({**json.loads(data), "format_version": 2}).encode()
            new.writestr(name, data)

    preview = preview_project_import(newer, workspace=workspace, store=store)

    manifest = next(c for c in preview.checks if c.id == "manifest")
    assert manifest.kind is RefusalKind.INCOMPATIBLE


def test_a_file_that_is_not_a_package_fails_the_first_check(
    tmp_path: Path, workspace: Path, store: LibraryStore
) -> None:
    junk = tmp_path / "junk.bomproj"
    junk.write_text("nope")

    preview = preview_project_import(junk, workspace=workspace, store=store)

    assert _statuses(preview)["package"] is CheckStatus.FAILED
    assert not preview.can_import
    assert preview.manifest is None
