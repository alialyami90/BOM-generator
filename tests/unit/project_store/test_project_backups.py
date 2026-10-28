"""Listing and restoring the backups in a project's `Backups/` folder."""

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from project_builders import make_project

from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.store import LibraryStore
from bomgen.project_store.backup import backup_project, list_backups, restore_backup

FIRST = datetime(2026, 10, 28, 9, 0, 0)
SECOND = datetime(2026, 10, 28, 10, 30, 0)


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


def test_no_backups_folder_lists_nothing(tmp_path: Path) -> None:
    assert list_backups(make_project(tmp_path / "jfgp2")) == []


def test_backups_are_listed_newest_first_with_their_details(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")
    older = backup_project(project_file, now=FIRST)
    newer = backup_project(project_file, now=SECOND)

    backups = list_backups(project_file)

    assert [b.path for b in backups] == [newer, older]
    latest = backups[0]
    assert latest.project_id == "jfgp2"
    assert (latest.library_name, latest.library_version) == ("psa-devices", "1.2.0")
    assert latest.file_count == 3
    assert latest.size == newer.stat().st_size
    assert latest.problem is None
    assert latest.saved == SECOND.astimezone(UTC)


def test_a_damaged_backup_is_listed_with_a_problem(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")
    good = backup_project(project_file, now=FIRST)
    bad = good.with_name("jfgp2-20261028-100000.bomproj")
    bad.write_text("not a zip")
    os.utime(bad, (SECOND.timestamp(), SECOND.timestamp()))

    backups = list_backups(project_file)

    assert [b.path for b in backups] == [bad, good]
    assert backups[0].problem is not None
    assert backups[0].project_id is None
    assert backups[0].size == len("not a zip")
    assert backups[1].problem is None


def test_other_files_in_the_backups_folder_are_ignored(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")
    backup_project(project_file, now=FIRST)
    (tmp_path / "jfgp2" / "Backups" / "notes.txt").write_text("hi")

    assert len(list_backups(project_file)) == 1


def test_restore_brings_back_the_saved_project_and_backs_up_the_current_one(
    tmp_path: Path, store: LibraryStore
) -> None:
    project_file = make_project(tmp_path / "ws" / "jfgp2")
    saved = backup_project(project_file, now=FIRST)
    (tmp_path / "ws" / "jfgp2" / "substations/psa/substation.yaml").write_text("edited\n")

    result = restore_backup(saved, store=store, now=SECOND)

    assert result.replaced
    assert result.project_dir == tmp_path / "ws" / "jfgp2"
    assert (result.project_dir / "substations/psa/substation.yaml").read_text() == "name: PSA\n"
    assert len(list_backups(project_file)) == 3 - 1  # the original and the safety backup


def test_restore_refuses_a_file_outside_a_backups_folder(
    tmp_path: Path, store: LibraryStore
) -> None:
    project_file = make_project(tmp_path / "ws" / "jfgp2")
    saved = backup_project(project_file, now=FIRST)
    elsewhere = tmp_path / "elsewhere.bomproj"
    elsewhere.write_bytes(saved.read_bytes())

    with pytest.raises(LibraryPackageError) as caught:
        restore_backup(elsewhere, store=store)

    assert caught.value.kind is RefusalKind.INVALID_PROJECT


def test_restore_accepts_a_path_relative_to_the_project_folder(
    tmp_path: Path, store: LibraryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_file = make_project(tmp_path / "ws" / "jfgp2")
    saved = backup_project(project_file, now=FIRST)
    monkeypatch.chdir(tmp_path / "ws" / "jfgp2")

    result = restore_backup(Path("Backups") / saved.name, store=store, now=SECOND)

    assert result.project_dir == tmp_path / "ws" / "jfgp2"


def test_restore_accepts_a_bare_file_name_from_inside_backups(
    tmp_path: Path, store: LibraryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_file = make_project(tmp_path / "ws" / "jfgp2")
    saved = backup_project(project_file, now=FIRST)
    monkeypatch.chdir(saved.parent)

    result = restore_backup(Path(saved.name), store=store, now=SECOND)

    assert result.project_dir == tmp_path / "ws" / "jfgp2"


def test_restore_refuses_a_backup_of_another_project(tmp_path: Path, store: LibraryStore) -> None:
    project_file = make_project(tmp_path / "ws" / "jfgp2")
    saved = backup_project(project_file, now=FIRST)
    other = make_project(tmp_path / "ws" / "other")
    (other.parent / "Backups").mkdir()
    foreign = other.parent / "Backups" / saved.name
    foreign.write_bytes(saved.read_bytes())

    with pytest.raises(LibraryPackageError, match="not to the folder 'other'") as caught:
        restore_backup(foreign, store=store)

    assert caught.value.kind is RefusalKind.INVALID_PROJECT
    assert (other.parent / "project.yaml").read_text() == project_file.read_text()


def test_backups_made_in_the_same_second_list_newest_first(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")
    made = [backup_project(project_file, now=FIRST) for _ in range(11)]

    listed = [b.path for b in list_backups(project_file)]

    assert listed == list(reversed(made))  # -11 before -10 before ... before the first
