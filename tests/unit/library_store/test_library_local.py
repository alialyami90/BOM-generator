"""Saving an edited library as a local version, and the .bomlib backup of it (ADR 0018)."""

from pathlib import Path
from typing import Any

import pytest

from bomgen.bundle.container import MANIFEST_NAME, sha256
from bomgen.io.loader import load_library
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.local import dump_library, save_local_version
from bomgen.library_store.package import pack, read_package
from bomgen.library_store.store import LibraryStore
from bomgen.library_store.versions import Version
from bomgen.models.library import Library

ROOT = Path(__file__).parents[3]
EXAMPLE_LIBRARY = ROOT / "examples" / "library.yaml"
DEVICE_DB = ROOT / "data" / "device-db"


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    store = LibraryStore(tmp_path / "libraries")
    package = tmp_path / "psa-1.0.0.bomlib"
    pack(EXAMPLE_LIBRARY, package, name="psa", version="1.0.0", extra_dirs=[DEVICE_DB])
    store.import_package(package)
    return store


def _active(store: LibraryStore) -> Library:
    return load_library(store.library_file("psa"))


def _edited(library: Library, **changes: Any) -> Library:
    """The first device with `changes` applied, as a new library."""
    data = library.model_dump(mode="json")
    data["devices"][0].update(changes)
    return Library.model_validate(data)


def test_a_library_dumped_and_loaded_again_is_equal(tmp_path: Path) -> None:
    library = load_library(EXAMPLE_LIBRARY)
    file = tmp_path / "library.yaml"
    file.write_bytes(dump_library(library))

    assert load_library(file) == library


def test_the_dump_is_the_same_every_time() -> None:
    library = load_library(EXAMPLE_LIBRARY)

    assert dump_library(library) == dump_library(library)


def test_a_saved_edit_becomes_the_active_local_version_and_the_old_one_stays(
    store: LibraryStore,
) -> None:
    library = _active(store)
    edited = _edited(library, make="Acme")

    saved = save_local_version(store, "psa", edited)

    assert saved.manifest.version == "1.0.0+local.1"
    assert saved.previous == "1.0.0"
    assert store.active_version("psa") == "1.0.0+local.1"
    assert store.versions("psa") == ["1.0.0", "1.0.0+local.1"]
    assert _active(store).devices[0].make == "Acme"
    assert load_library(store.library_file("psa", "1.0.0")).devices[0].make != "Acme"


def test_the_saved_version_lists_what_changed(store: LibraryStore) -> None:
    library = _active(store)
    first = library.devices[0].part_id

    saved = save_local_version(store, "psa", _edited(library, make="Acme"), note="Ali's change")

    assert saved.diff.changed == {first: ["make"]}
    notes = saved.manifest.release_notes
    assert notes.startswith("Local edit from 1.0.0: 1 part changed")
    assert "Ali's change" in notes


def test_the_other_files_of_the_base_version_are_carried_over(store: LibraryStore) -> None:
    save_local_version(store, "psa", _edited(_active(store), make="Acme"))

    base = store.root / "psa" / "1.0.0"
    local = store.root / "psa" / "1.0.0+local.1"
    names = sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())
    assert sorted(p.relative_to(local).as_posix() for p in local.rglob("*") if p.is_file()) == names
    assert (local / "device-db" / "network.yaml").read_bytes() == (
        base / "device-db" / "network.yaml"
    ).read_bytes()


def test_the_manifest_checksums_match_the_files(store: LibraryStore) -> None:
    saved = save_local_version(store, "psa", _edited(_active(store), make="Acme"))

    folder = store.root / "psa" / "1.0.0+local.1"
    assert set(saved.manifest.files) == {
        p.relative_to(folder).as_posix()
        for p in folder.rglob("*")
        if p.is_file() and p.name != MANIFEST_NAME
    }
    for name, digest in saved.manifest.files.items():
        assert sha256((folder / name).read_bytes()) == digest


def test_the_manifest_keeps_the_schema_and_app_requirements_of_the_base(
    store: LibraryStore,
) -> None:
    base = store.manifest("psa", "1.0.0")

    saved = save_local_version(store, "psa", _edited(_active(store), make="Acme"))

    assert saved.manifest.name == "psa"
    assert saved.manifest.schema_version == base.schema_version
    assert saved.manifest.min_app_version == base.min_app_version


def test_the_next_edit_takes_the_next_local_number(store: LibraryStore) -> None:
    first = save_local_version(store, "psa", _edited(_active(store), make="One"))
    second = save_local_version(store, "psa", _edited(_active(store), make="Two"))

    assert (first.manifest.version, second.manifest.version) == (
        "1.0.0+local.1",
        "1.0.0+local.2",
    )
    assert second.previous == "1.0.0+local.1"


def test_an_edit_starting_from_the_release_takes_a_number_that_is_not_in_use(
    store: LibraryStore,
) -> None:
    save_local_version(store, "psa", _edited(_active(store), make="One"))

    again = save_local_version(store, "psa", _edited(_active(store), make="Two"), base="1.0.0")

    assert again.manifest.version == "1.0.0+local.2"
    assert again.previous == "1.0.0"


def test_a_version_orders_between_its_base_and_the_next_release(store: LibraryStore) -> None:
    saved = save_local_version(store, "psa", _edited(_active(store), make="One"))

    assert Version.parse("1.0.0") < Version.parse(saved.manifest.version) < Version.parse("1.0.1")


def test_saving_without_a_change_is_refused_and_writes_nothing(store: LibraryStore) -> None:
    with pytest.raises(LibraryPackageError) as caught:
        save_local_version(store, "psa", _active(store))

    assert caught.value.kind is RefusalKind.NO_CHANGES
    assert store.versions("psa") == ["1.0.0"]


def test_a_library_that_fails_the_loader_checks_is_refused_and_writes_nothing(
    store: LibraryStore,
) -> None:
    library = _active(store)
    data = library.model_dump(mode="json")
    data["devices"][0]["children"] = [{"part_id": "NO-SUCH-PART", "qty": 1}]
    broken = Library.model_validate(data)

    with pytest.raises(LibraryPackageError) as caught:
        save_local_version(store, "psa", broken)

    assert caught.value.kind is RefusalKind.VALIDATION_FAILED
    assert "NO-SUCH-PART" in str(caught.value)
    assert store.versions("psa") == ["1.0.0"]
    assert store.active_version("psa") == "1.0.0"


def test_saving_into_a_library_that_is_not_installed_is_refused(store: LibraryStore) -> None:
    with pytest.raises(LibraryPackageError) as caught:
        save_local_version(store, "other", _active(store))

    assert caught.value.kind is RefusalKind.NOT_INSTALLED
    with pytest.raises(LibraryPackageError) as caught:
        save_local_version(store, "psa", _active(store), base="9.9.9")
    assert caught.value.kind is RefusalKind.NOT_INSTALLED


def test_a_base_with_a_damaged_file_is_refused(store: LibraryStore) -> None:
    (store.root / "psa" / "1.0.0" / "device-db" / "network.yaml").write_text("changed")

    with pytest.raises(LibraryPackageError) as caught:
        save_local_version(store, "psa", _edited(_active(store), make="Acme"))

    assert caught.value.kind is RefusalKind.STORE_DAMAGED
    assert store.versions("psa") == ["1.0.0"]


def test_the_backup_of_an_edited_library_is_a_package_that_imports_elsewhere(
    tmp_path: Path, store: LibraryStore
) -> None:
    edited = _edited(_active(store), make="Acme")
    save_local_version(store, "psa", edited)
    backup = tmp_path / "backup.bomlib"

    store.export_package("psa", "1.0.0+local.1", backup)

    contents = read_package(backup)
    assert contents.manifest.version == "1.0.0+local.1"
    other = LibraryStore(tmp_path / "other")
    other.import_package(backup)
    assert other.active_version("psa") == "1.0.0+local.1"
    assert load_library(other.library_file("psa")) == edited
    assert (other.root / "psa" / "1.0.0+local.1" / "device-db" / "network.yaml").is_file()


def test_the_backup_is_the_same_bytes_every_time(tmp_path: Path, store: LibraryStore) -> None:
    store.export_package("psa", "1.0.0", tmp_path / "a.bomlib")
    store.export_package("psa", "1.0.0", tmp_path / "b.bomlib")

    assert (tmp_path / "a.bomlib").read_bytes() == (tmp_path / "b.bomlib").read_bytes()


def test_the_backup_of_a_missing_version_is_refused(tmp_path: Path, store: LibraryStore) -> None:
    with pytest.raises(LibraryPackageError) as caught:
        store.export_package("psa", "2.0.0", tmp_path / "x.bomlib")

    assert caught.value.kind is RefusalKind.NOT_INSTALLED


def test_the_backup_of_a_tampered_version_is_refused(tmp_path: Path, store: LibraryStore) -> None:
    (store.root / "psa" / "1.0.0" / "library.yaml").write_text("devices: []\n")

    with pytest.raises(LibraryPackageError) as caught:
        store.export_package("psa", "1.0.0", tmp_path / "x.bomlib")

    assert caught.value.kind is RefusalKind.STORE_DAMAGED
    assert not (tmp_path / "x.bomlib").exists()
