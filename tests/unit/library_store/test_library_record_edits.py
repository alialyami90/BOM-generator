"""Editing device-database records and saving them in a local version (ADR 0018)."""

from pathlib import Path

import pytest

from bomgen.library_store.device_db import DeviceRecord, load_device_records, parse_device_records
from bomgen.library_store.edit import Insert, Remove, SetValue
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.local import save_edits
from bomgen.library_store.package import pack
from bomgen.library_store.records import apply_record_edits, check_record_field
from bomgen.library_store.store import LibraryStore

ROOT = Path(__file__).parents[3]
EXAMPLE_LIBRARY = ROOT / "examples" / "library.yaml"
DEVICE_DB = ROOT / "data" / "device-db"
SWITCH = "RST2228-L2"  # in device-db/network.yaml


def _records() -> dict[str, DeviceRecord]:
    files = {f"device-db/{p.name}": p.read_bytes() for p in DEVICE_DB.glob("*.yaml")}
    return parse_device_records(files)


def _new_record(part_id: str) -> dict[str, object]:
    return {
        "part_id": part_id,
        "kind": "device",
        "description": "Spare switch",
        "verified": "unverified",
        "datasheet": {"summary": "Not researched yet.", "mounting_kind": "rack", "height_u": 1},
        "alternatives": [],
        "sources": [],
    }


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    store = LibraryStore(tmp_path / "libraries")
    package = tmp_path / "psa-1.0.0.bomlib"
    pack(EXAMPLE_LIBRARY, package, name="psa", version="1.0.0", extra_dirs=[DEVICE_DB])
    store.import_package(package)
    return store


# -- applying -----------------------------------------------------------------------------


def test_a_record_field_edit_changes_only_that_field() -> None:
    records = _records()

    result = apply_record_edits(
        records, [SetValue(path=[SWITCH, "datasheet", "weight_kg"], value=3.2)]
    )

    assert result.problems == []
    assert result.records is not None
    assert result.records[SWITCH].datasheet.weight_kg == 3.2
    assert result.records[SWITCH].datasheet.summary == records[SWITCH].datasheet.summary
    assert {k: v for k, v in result.records.items() if k != SWITCH} == {
        k: v for k, v in records.items() if k != SWITCH
    }


def test_applying_record_edits_leaves_the_argument_unchanged() -> None:
    records = _records()
    before = records[SWITCH]

    apply_record_edits(records, [SetValue(path=[SWITCH, "verified"], value="partial")])

    assert records[SWITCH] is before
    assert records[SWITCH].verified == "confirmed"


def test_record_edits_reach_nested_lists_and_mappings() -> None:
    records = _records()

    result = apply_record_edits(
        records,
        [
            Insert(path=[SWITCH, "sources"], value="https://example.com/sheet.pdf", index=0),
            SetValue(path=[SWITCH, "datasheet", "operating_temp_c", "max"], value=60),
            SetValue(path=[SWITCH, "datasheet", "certifications"], value=["IEC 61850-3"]),
        ],
    )

    assert result.records is not None
    record = result.records[SWITCH]
    assert record.sources[0] == "https://example.com/sheet.pdf"
    assert record.datasheet.operating_temp_c is not None
    assert record.datasheet.operating_temp_c.max == 60
    assert record.datasheet.certifications == ["IEC 61850-3"]


def test_a_bad_record_value_is_a_problem_naming_the_part_and_field() -> None:
    result = apply_record_edits(
        _records(), [SetValue(path=[SWITCH, "datasheet", "weight_kg"], value="heavy")]
    )

    assert result.records is None
    assert [p.location for p in result.problems] == [f"{SWITCH}.datasheet.weight_kg"]


def test_a_record_edit_on_a_part_without_a_record_is_a_problem() -> None:
    result = apply_record_edits(_records(), [SetValue(path=["NOPE", "verified"], value="partial")])

    assert result.records is None
    assert result.problems[0].location == "NOPE.verified"
    assert "does not exist" in result.problems[0].message


def test_a_new_record_is_added_by_setting_its_part_id() -> None:
    result = apply_record_edits(
        _records(), [SetValue(path=["SW-NEW"], value=_new_record("SW-NEW"))]
    )

    assert result.records is not None
    assert result.records["SW-NEW"].description == "Spare switch"


def test_a_record_whose_part_id_differs_from_its_key_is_a_problem() -> None:
    result = apply_record_edits(_records(), [SetValue(path=[SWITCH, "part_id"], value="OTHER")])

    assert result.records is None
    assert result.problems[0].location == f"{SWITCH}.part_id"


def test_removing_a_record_deletes_it() -> None:
    result = apply_record_edits(_records(), [Remove(path=[SWITCH])])

    assert result.records is not None
    assert SWITCH not in result.records


# -- checking one field -------------------------------------------------------------------


def test_a_valid_record_field_has_no_message() -> None:
    assert check_record_field(_records(), [SWITCH, "datasheet", "weight_kg"], 2.5) is None


def test_an_invalid_record_field_gets_the_model_message() -> None:
    message = check_record_field(_records(), [SWITCH, "verified"], "maybe")

    assert message is not None
    assert "confirmed" in message


def test_a_record_field_on_a_missing_path_gets_a_message() -> None:
    message = check_record_field(_records(), ["NOPE", "verified"], "partial")

    assert message is not None
    assert "does not exist" in message


# -- saving -------------------------------------------------------------------------------


def test_record_edits_alone_save_a_local_version(store: LibraryStore) -> None:
    saved = save_edits(
        store,
        "psa",
        [],
        record_edits=[SetValue(path=[SWITCH, "datasheet", "weight_kg"], value=3.2)],
    )

    assert saved.manifest.version == "1.0.0+local.1"
    assert store.active_version("psa") == "1.0.0+local.1"
    assert load_device_records(store, "psa", "1.0.0+local.1")[SWITCH].datasheet.weight_kg == 3.2
    assert load_device_records(store, "psa", "1.0.0")[SWITCH].datasheet.weight_kg != 3.2


def test_a_changed_record_stays_in_its_file_and_other_files_are_untouched(
    store: LibraryStore,
) -> None:
    save_edits(
        store, "psa", [], record_edits=[SetValue(path=[SWITCH, "verified"], value="partial")]
    )

    base = store.root / "psa" / "1.0.0" / "device-db"
    local = store.root / "psa" / "1.0.0+local.1" / "device-db"
    assert sorted(p.name for p in local.iterdir()) == sorted(p.name for p in base.iterdir())
    assert (local / "network.yaml").read_bytes() != (base / "network.yaml").read_bytes()
    assert (local / "electrical.yaml").read_bytes() == (base / "electrical.yaml").read_bytes()
    assert SWITCH in parse_device_records(
        {"device-db/network.yaml": (local / "network.yaml").read_bytes()}
    )


def test_a_new_record_is_saved_in_the_local_records_file(store: LibraryStore) -> None:
    save_edits(
        store, "psa", [], record_edits=[SetValue(path=["SW-NEW"], value=_new_record("SW-NEW"))]
    )

    local = store.root / "psa" / "1.0.0+local.1" / "device-db" / "local.yaml"
    assert "SW-NEW" in parse_device_records({"device-db/local.yaml": local.read_bytes()})
    assert "SW-NEW" in load_device_records(store, "psa", store.active_version("psa") or "")


def test_a_library_without_records_gets_a_records_file_for_a_new_record(tmp_path: Path) -> None:
    store = LibraryStore(tmp_path / "libraries")
    package = tmp_path / "psa-1.0.0.bomlib"
    pack(EXAMPLE_LIBRARY, package, name="psa", version="1.0.0")
    store.import_package(package)

    save_edits(
        store, "psa", [], record_edits=[SetValue(path=["SW-NEW"], value=_new_record("SW-NEW"))]
    )

    assert list(load_device_records(store, "psa", store.active_version("psa") or "")) == ["SW-NEW"]


def test_library_and_record_edits_are_saved_together(store: LibraryStore) -> None:
    saved = save_edits(
        store,
        "psa",
        [SetValue(path=["devices", SWITCH, "make"], value="Acme")],
        record_edits=[SetValue(path=[SWITCH, "make"], value="Acme")],
    )

    assert saved.diff.changed == {SWITCH: ["make"]}
    assert saved.diff.files_changed == ["device-db/network.yaml"]
    assert (
        load_device_records(store, "psa", store.active_version("psa") or "")[SWITCH].make == "Acme"
    )


def test_the_release_notes_count_the_changed_records(store: LibraryStore) -> None:
    saved = save_edits(
        store,
        "psa",
        [],
        record_edits=[
            SetValue(path=[SWITCH, "verified"], value="partial"),
            SetValue(path=["SW-NEW"], value=_new_record("SW-NEW")),
        ],
    )

    assert saved.manifest.release_notes == "Local edit from 1.0.0: 2 device records changed."


def test_record_edits_with_problems_are_refused_and_write_nothing(store: LibraryStore) -> None:
    with pytest.raises(LibraryPackageError) as caught:
        save_edits(
            store, "psa", [], record_edits=[SetValue(path=[SWITCH, "verified"], value="maybe")]
        )

    assert caught.value.kind is RefusalKind.VALIDATION_FAILED
    assert f"{SWITCH}.verified" in str(caught.value)
    assert store.versions("psa") == ["1.0.0"]


def test_record_edits_that_change_nothing_are_refused(store: LibraryStore) -> None:
    unchanged = load_device_records(store, "psa", store.active_version("psa") or "")[
        SWITCH
    ].verified

    with pytest.raises(LibraryPackageError) as caught:
        save_edits(
            store, "psa", [], record_edits=[SetValue(path=[SWITCH, "verified"], value=unchanged)]
        )

    assert caught.value.kind is RefusalKind.NO_CHANGES


def test_record_editing_is_a_public_entry_point() -> None:
    import bomgen.library_store as library_store

    assert library_store.apply_record_edits is apply_record_edits
    assert library_store.check_record_field is check_record_field
