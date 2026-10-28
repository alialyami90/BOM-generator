"""The restore dry-run: restore_backup's two refusals as checks, then the normal preview."""

from datetime import datetime
from pathlib import Path

import pytest
from project_builders import make_project

from bomgen.bundle.checks import CheckStatus
from bomgen.bundle.errors import RefusalKind
from bomgen.library_store.store import LibraryStore
from bomgen.project_store import preview_backup_restore
from bomgen.project_store.backup import backup_project

FIRST = datetime(2026, 10, 28, 9, 0, 0)
IDS = [
    "location",
    "folder",
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
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


def _statuses(preview: object) -> dict[str, CheckStatus]:
    return {c.id: c.status for c in preview.checks}  # type: ignore[attr-defined]


def test_a_backup_in_its_own_project_passes_every_check_and_replaces_it(
    tmp_path: Path, store: LibraryStore
) -> None:
    project_file = make_project(tmp_path / "ws" / "jfgp2")
    saved = backup_project(project_file, now=FIRST)

    preview = preview_backup_restore(saved, store=store)

    assert [c.id for c in preview.checks] == IDS
    statuses = _statuses(preview)
    assert statuses["location"] is CheckStatus.OK
    assert statuses["folder"] is CheckStatus.OK
    assert statuses["name"] is CheckStatus.WARNING  # restoring replaces the current project
    assert preview.can_import
    assert preview.project_id == "jfgp2"
    assert preview.target_dir == tmp_path / "ws" / "jfgp2"
    assert preview.exists


def test_a_file_outside_a_backups_folder_fails_the_first_check_and_skips_the_rest(
    tmp_path: Path, store: LibraryStore
) -> None:
    project_file = make_project(tmp_path / "ws" / "jfgp2")
    saved = backup_project(project_file, now=FIRST)
    elsewhere = tmp_path / "elsewhere.bomproj"
    elsewhere.write_bytes(saved.read_bytes())

    preview = preview_backup_restore(elsewhere, store=store)

    first = preview.checks[0]
    assert (first.id, first.status, first.kind) == (
        "location",
        CheckStatus.FAILED,
        RefusalKind.INVALID_PROJECT,
    )
    assert "Backups" in first.detail
    assert [c.status for c in preview.checks[1:]] == [CheckStatus.SKIPPED] * (len(IDS) - 1)
    assert not preview.can_import
    assert preview.files == []


def test_a_backup_of_another_project_fails_the_folder_check_and_skips_the_rest(
    tmp_path: Path, store: LibraryStore
) -> None:
    saved = backup_project(make_project(tmp_path / "ws" / "jfgp2"), now=FIRST)
    other = make_project(tmp_path / "ws" / "other")
    foreign = other.parent / "Backups" / saved.name
    foreign.parent.mkdir()
    foreign.write_bytes(saved.read_bytes())

    preview = preview_backup_restore(foreign, store=store)

    statuses = _statuses(preview)
    assert statuses["location"] is CheckStatus.OK
    assert statuses["folder"] is CheckStatus.FAILED
    folder = preview.checks[1]
    assert folder.kind is RefusalKind.INVALID_PROJECT
    assert "'other'" in folder.detail
    assert all(statuses[i] is CheckStatus.SKIPPED for i in IDS[2:])
    assert preview.project_id == "jfgp2"
    assert not preview.can_import


def test_a_damaged_backup_fails_its_own_check_and_skips_the_folder_check(
    tmp_path: Path, store: LibraryStore
) -> None:
    project_file = make_project(tmp_path / "ws" / "jfgp2")
    damaged = project_file.parent / "Backups" / "jfgp2-20261028-090000.bomproj"
    damaged.parent.mkdir()
    damaged.write_text("not a zip")

    preview = preview_backup_restore(damaged, store=store)

    statuses = _statuses(preview)
    assert statuses["location"] is CheckStatus.OK
    assert statuses["folder"] is CheckStatus.SKIPPED
    assert statuses["package"] is CheckStatus.FAILED
    assert not preview.can_import


def test_a_relative_path_is_resolved_like_restore_backup(
    tmp_path: Path, store: LibraryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = backup_project(make_project(tmp_path / "ws" / "jfgp2"), now=FIRST)
    monkeypatch.chdir(saved.parent)

    preview = preview_backup_restore(Path(saved.name), store=store)

    assert preview.can_import
    assert preview.target_dir == tmp_path / "ws" / "jfgp2"


def test_the_preview_writes_nothing(tmp_path: Path, store: LibraryStore) -> None:
    saved = backup_project(make_project(tmp_path / "ws" / "jfgp2"), now=FIRST)
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

    preview_backup_restore(saved, store=store)

    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == before
