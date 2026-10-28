"""Backups: an export into the project's own `Backups/` folder."""

import zipfile
from datetime import datetime
from pathlib import Path

import pytest
from project_builders import FILES, make_project

from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.project_store.backup import backup_project

NOW = datetime(2026, 10, 28, 13, 5, 9)


def test_backup_writes_a_timestamped_file_in_the_backups_folder(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")

    path = backup_project(project_file, now=NOW)

    assert path == tmp_path / "jfgp2" / "Backups" / "jfgp2-20261028-130509.bomproj"
    with zipfile.ZipFile(path) as zf:
        assert sorted(zf.namelist()) == sorted(["manifest.json", "project.yaml", *FILES])


def test_two_backups_in_one_second_do_not_collide(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")

    first = backup_project(project_file, now=NOW)
    second = backup_project(project_file, now=NOW)
    third = backup_project(project_file, now=NOW)

    assert len({first, second, third}) == 3
    assert second.name == "jfgp2-20261028-130509-2.bomproj"
    assert third.name == "jfgp2-20261028-130509-3.bomproj"


def test_a_backup_does_not_contain_earlier_backups(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "jfgp2")
    backup_project(project_file, now=NOW)

    second = backup_project(project_file, now=datetime(2026, 10, 28, 14, 0, 0))

    with zipfile.ZipFile(second) as zf:
        assert not [n for n in zf.namelist() if n.startswith("Backups")]


def test_backup_of_an_unusable_project_is_refused(tmp_path: Path) -> None:
    project_file = make_project(tmp_path / "p", project_yaml="name: nothing\n")

    with pytest.raises(LibraryPackageError) as caught:
        backup_project(project_file, now=NOW)

    assert caught.value.kind is RefusalKind.INVALID_PROJECT
    assert not (tmp_path / "p" / "Backups").exists()
