"""Library editing in the app: the pending set and the endpoints over it (M16, ADR 0018).

The edit operations and local versions are tested in the library store's own tests; these
cover what the app adds: keeping the set between sessions, describing it for review, and
the bridge replies.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.app.library_edit import Pending, PendingEdits, describe, merge
from bomgen.io.loader import load_library
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"
NAME = "psa-devices"
PART = "SEL-3555-RTAC"


def power(part: str, watts: float) -> dict[str, object]:
    return {"op": "set", "path": ["devices", part, "unit_power_w"], "value": watts}


# -- the pending set ------------------------------------------------------------------------


def test_pending_edits_survive_a_new_store_instance(tmp_path: Path) -> None:
    PendingEdits(tmp_path).save(NAME, Pending(base="1.0.0", edits=[power(PART, 80)]))
    again = PendingEdits(tmp_path).load(NAME)
    assert again == Pending(base="1.0.0", edits=[power(PART, 80)])


def test_no_pending_file_loads_as_none(tmp_path: Path) -> None:
    assert PendingEdits(tmp_path).load(NAME) is None


def test_a_damaged_pending_file_reports_a_problem_and_loads_empty(tmp_path: Path) -> None:
    store = PendingEdits(tmp_path)
    store.save(NAME, Pending(base="1.0.0", edits=[]))
    store.file(NAME).write_text("{not json", encoding="utf-8")
    loaded = store.load(NAME)
    assert loaded is not None
    assert loaded.edits == []
    assert loaded.base is None
    assert loaded.problem


def test_clear_removes_the_set(tmp_path: Path) -> None:
    store = PendingEdits(tmp_path)
    store.save(NAME, Pending(base="1.0.0", edits=[power(PART, 80)]))
    store.clear(NAME)
    assert store.load(NAME) is None


# -- merging and describing -----------------------------------------------------------------


def test_a_second_set_on_the_same_field_replaces_the_first() -> None:
    assert merge([power(PART, 80)], [power(PART, 90)], base={}) == [power(PART, 90)]


def test_setting_a_field_back_drops_its_entry() -> None:
    saved = {("devices", PART, "unit_power_w"): 25.0}
    assert merge([power(PART, 80)], [power(PART, 25.0)], base=saved) == []


def test_describe_lists_one_entry_per_changed_field_with_from_and_to() -> None:
    library = load_library(EXAMPLES / "library.yaml")
    data = library.model_dump(mode="json")
    device = next(d for d in data["devices"] if d["part_id"] == PART)
    assert device["unit_power_w"] == 62
    device["unit_power_w"] = 99.5
    device["ordering_code"] = None
    edited = type(library).model_validate(data)
    entries = describe(library, edited)
    by_field = {e["field"]: e for e in entries}
    assert by_field["unit_power_w"] == {
        "area": "Device",
        "label": PART,
        "kind": "changed",
        "field": "unit_power_w",
        "from": "62",
        "to": "99.5",
    }
    assert by_field["ordering_code"]["to"] == ""


def test_describe_lists_added_and_removed_devices() -> None:
    library = load_library(EXAMPLES / "library.yaml")
    data = library.model_dump(mode="json")
    gone = data["devices"].pop()
    clone = {**data["devices"][0], "part_id": "NEW-1"}
    data["devices"].append(clone)
    entries = describe(library, type(library).model_validate(data))
    kinds = {(e["label"], e["kind"]) for e in entries}
    assert ("NEW-1", "added") in kinds
    assert (gone["part_id"], "removed") in kinds


# -- the bridge -----------------------------------------------------------------------------


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
    package = tmp_path / "lib.bomlib"
    pack(EXAMPLES / "library.yaml", package, name=NAME, version="1.0.0")
    LibraryStore(tmp_path / "libraries").import_package(package)
    return api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
            "BOMGEN_APP_HOME": str(tmp_path / "app"),
        }
    )


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)
    return envelope["data"]


def refused(envelope: dict[str, object]) -> dict[str, str]:
    assert envelope["ok"] is False, envelope
    return envelope["error"]  # type: ignore[return-value]


def test_an_empty_pending_set_has_no_entries(app: api.Api) -> None:
    page = ok(app.library_pending())
    assert page["count"] == 0
    assert page["entries"] == []
    assert page["base"] == "1.0.0"
    assert page["next_version"] == "1.0.0+local.1"


def test_an_edited_device_is_saved_as_a_new_local_version(app: api.Api) -> None:
    page = ok(app.add_library_edits([power(PART, 99.5)]))
    assert page["count"] == 1
    assert ok(app.library_device(PART))["device"]["unit_power_w"] == 99.5
    applied = ok(app.apply_library_edits("Checked against the datasheet"))
    assert applied["version"] == "1.0.0+local.1"
    assert applied["previous"] == "1.0.0"
    assert ok(app.library_pending())["count"] == 0
    versions = ok(app.library_versions())["versions"]
    assert [v["version"] for v in versions if v["active"]] == ["1.0.0+local.1"]
    assert any(v["version"] == "1.0.0" for v in versions)


def test_check_field_reports_the_models_message(app: api.Api) -> None:
    assert ok(app.check_library_field(PART, "unit_power_w", 30)) is None
    message = ok(app.check_library_field(PART, "voltage_v", -5))
    assert message
    assert "greater than 0" in message


def test_an_edit_that_breaks_the_library_is_refused_and_not_kept(app: api.Api) -> None:
    error = refused(app.add_library_edits([power(PART, -1)]))
    assert error["kind"] == "invalid_edit"
    assert PART in error["message"]
    assert ok(app.library_pending())["count"] == 0


def test_an_emptied_optional_field_is_saved_as_a_remove(app: api.Api) -> None:
    ok(app.add_library_edits([{"op": "remove", "path": ["devices", PART, "ordering_code"]}]))
    assert ok(app.library_device(PART))["device"]["ordering_code"] is None
    entry = ok(app.library_pending())["entries"][0]
    assert entry["field"] == "ordering_code"
    assert entry["to"] == ""


def test_discard_returns_the_edits_for_undo(app: api.Api) -> None:
    ok(app.add_library_edits([power(PART, 99.5)]))
    reply = ok(app.discard_library_edits())
    assert reply["page"]["count"] == 0
    ok(app.add_library_edits(reply["discarded"]))
    assert ok(app.library_pending())["count"] == 1


def test_pending_keeps_its_base_when_another_version_is_activated(
    app: api.Api, tmp_path: Path
) -> None:
    ok(app.add_library_edits([power(PART, 99.5)]))
    second = tmp_path / "lib2.bomlib"
    pack(EXAMPLES / "library.yaml", second, name=NAME, version="1.1.0")
    LibraryStore(tmp_path / "libraries").import_package(second)
    page = ok(app.library_pending())
    assert page["base"] == "1.0.0"
    assert page["active"] == "1.1.0"
    assert page["count"] == 1
    assert ok(app.apply_library_edits(""))["previous"] == "1.0.0"


def test_a_pending_set_on_an_uninstalled_base_can_be_discarded(
    app: api.Api, tmp_path: Path
) -> None:
    PendingEdits(tmp_path / "app").save(NAME, Pending(base="9.9.9", edits=[power(PART, 1)]))
    page = ok(app.library_pending())
    assert page["problem"]
    assert "9.9.9" in page["problem"]
    assert ok(app.discard_library_edits())["page"]["count"] == 0


def test_an_unknown_device_is_refused(app: api.Api) -> None:
    assert refused(app.library_device("NOPE"))["kind"] == "not_found"


def test_library_device_shows_the_saved_value_beside_the_pending_one(app: api.Api) -> None:
    saved = ok(app.library_device(PART))["device"]["unit_power_w"]
    ok(app.add_library_edits([power(PART, 99.5)]))
    reply = ok(app.library_device(PART))
    assert reply["saved"]["unit_power_w"] == saved
    assert reply["pending_fields"] == ["unit_power_w"]


def test_library_device_lists_the_models_choices(app: api.Api) -> None:
    choices = ok(app.library_device(PART))["choices"]
    assert "rtac" in choices["category"]
    assert choices["supply_type"] == ["VDC", "VAC"]
    assert "CONTINUOUS" in choices["load_type"]
    assert "L2" in choices["purdue_level"]
