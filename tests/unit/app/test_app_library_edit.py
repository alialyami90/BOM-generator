"""Library editing in the app: the pending set and the endpoints over it (M16, ADR 0018).

The edit operations and local versions are tested in the library store's own tests; these
cover what the app adds: keeping the set between sessions, describing it for review, and
the bridge replies.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.app.library_edit import Pending, PendingEdits, describe, merge
from bomgen.io.loader import load_library
from bomgen.io.yaml_source import read_yaml
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


# -- lists, new devices and deletes (PR a2) ---------------------------------------------------


def test_removing_a_device_added_in_the_set_drops_its_insert_and_its_edits() -> None:
    insert = {"op": "insert", "path": ["devices"], "value": {"part_id": "NEW-1"}}
    edit = power("NEW-1", 5)
    remove = {"op": "remove", "path": ["devices", "NEW-1"]}
    assert merge([insert, edit, power(PART, 80)], [remove], base={}) == [power(PART, 80)]


def test_describe_shows_a_changed_list_as_readable_text() -> None:
    library = load_library(EXAMPLES / "library.yaml")
    data = library.model_dump(mode="json")
    device = next(d for d in data["devices"] if d["part_id"] == "RST2228-L2")
    device["ports"] = [{"count": 4, "speed": "1G", "media": None, "kind": "sfp_slot"}]
    entry = next(
        e for e in describe(library, type(library).model_validate(data)) if e["field"] == "ports"
    )
    assert entry["to"] == "4 x 1G sfp_slot any"
    assert "{" not in entry["from"]


def test_library_device_lists_the_part_ids_and_the_list_choices(app: api.Api) -> None:
    reply = ok(app.library_device(PART))
    assert PART in reply["part_ids"]
    assert reply["choices"]["speed"] == ["10M", "100M", "1G", "10G"]
    assert reply["choices"]["per"] == ["unit", "serial_port"]
    assert "sfp_slot" in reply["choices"]["kind"]


def test_a_whole_port_list_is_set_and_checked(app: api.Api) -> None:
    ports = [{"count": 8, "speed": "1G", "kind": "sfp_slot", "usable_for": "uplink"}]
    edit = {"op": "set", "path": ["devices", "RST2228-L2", "ports"], "value": ports}
    assert ok(app.check_library_field("RST2228-L2", "ports", ports)) is None
    ok(app.add_library_edits([edit]))
    assert ok(app.library_device("RST2228-L2"))["device"]["ports"][0]["count"] == 8
    bad = [{"count": 0, "speed": "1G", "kind": "sfp_slot"}]
    assert ok(app.check_library_field("RST2228-L2", "ports", bad))


def test_a_new_device_copies_the_electrical_data_ports_and_parts(app: api.Api) -> None:
    page = ok(app.add_library_device("SEL-3555-RTAC-B", "rtac", "SEL", "SEL-3555 B", PART))
    assert [(e["label"], e["kind"]) for e in page["entries"]] == [("SEL-3555-RTAC-B", "added")]
    new = ok(app.library_device("SEL-3555-RTAC-B"))
    source = ok(app.library_device(PART))["device"]
    assert new["saved"] is None
    assert new["device"]["unit_power_w"] == source["unit_power_w"]
    assert new["device"]["ports"] == source["ports"]
    assert new["device"]["model"] == "SEL-3555 B"
    assert new["device"]["alt_group"] is None


def test_a_blank_device_needs_only_its_identity(app: api.Api) -> None:
    ok(app.add_library_device("SITE-CABLE", "component", "Local", "Cable", None))
    device = ok(app.library_device("SITE-CABLE"))["device"]
    assert device["description_template"] == "Local Cable"
    assert device["excluded_from_power"] is True


def test_a_new_device_with_a_part_id_in_use_is_refused(app: api.Api) -> None:
    error = refused(app.add_library_device(PART, "rtac", "SEL", "x", None))
    assert error["kind"] == "invalid_edit"
    assert ok(app.library_pending())["count"] == 0


def test_a_deleted_device_is_listed_as_removed(app: api.Api) -> None:
    ok(app.add_library_edits([{"op": "remove", "path": ["devices", "SEL-2488"]}]))
    entries = ok(app.library_pending())["entries"]
    assert ("SEL-2488", "removed") in {(e["label"], e["kind"]) for e in entries}


# -- who uses a part (the In use banner and the delete warning) --------------------------------


def test_part_users_lists_the_open_substations_rows(app: api.Api, tmp_path: Path) -> None:
    project = Path(shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3"))
    reply = ok(app.library_part_users(PART, str(project / "project.yaml"), "gis01"))
    assert reply["substation"]
    wheres = {u["where"] for u in reply["uses"]}
    assert "equipment" in wheres
    assert all(set(u) == {"where", "name", "panel", "index"} for u in reply["uses"])


def test_an_equipment_use_gives_its_row_for_use_this_instead(app: api.Api, tmp_path: Path) -> None:
    project = Path(shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3"))
    uses = ok(app.library_part_users(PART, str(project / "project.yaml"), "gis01"))["uses"]
    row = next(u for u in uses if u["where"] == "equipment")
    ids = [
        e["id"]
        for e in read_yaml(project / "substations" / "gis01" / "substation.yaml").data["equipment"]
    ]
    assert ids[row["index"]] == row["name"]
    assert all(u["index"] is None for u in uses if u["where"] != "equipment")


def test_a_panel_row_names_its_panel_apart(app: api.Api, tmp_path: Path) -> None:
    project = Path(shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3"))
    uses = ok(app.library_part_users(PART, str(project / "project.yaml"), "gis01"))["uses"]
    panel = next(u for u in uses if u["where"] == "panel")
    assert panel["panel"] == "psa3"
    assert ":" not in panel["name"]
    assert all(u["panel"] is None for u in uses if u["where"] != "panel")


def test_an_unused_part_has_no_users(app: api.Api, tmp_path: Path) -> None:
    project = Path(shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3"))
    assert (
        ok(app.library_part_users("NOPE-1", str(project / "project.yaml"), "gis01"))["uses"] == []
    )


# -- datasheet records (device-db, B5's record edits) -----------------------------------------


@pytest.fixture
def app_db(tmp_path: Path) -> api.Api:
    package = tmp_path / "lib.bomlib"
    db = Path(__file__).parents[3] / "data" / "device-db"
    pack(EXAMPLES / "library.yaml", package, name=NAME, version="1.0.0", extra_dirs=[db])
    LibraryStore(tmp_path / "libraries").import_package(package)
    return api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
            "BOMGEN_APP_HOME": str(tmp_path / "app"),
        }
    )


def test_library_device_carries_its_datasheet_record(app_db: api.Api) -> None:
    reply = ok(app_db.library_device(PART))
    assert reply["record"]["datasheet"]["weight_kg"] == 9.07
    assert reply["saved_record"]["verified"] == "partial"


def test_a_datasheet_field_is_checked_with_the_records_message(app_db: api.Api) -> None:
    assert ok(app_db.check_library_record(PART, "datasheet.weight_kg", 10)) is None
    assert ok(app_db.check_library_record(PART, "verified", "maybe"))


def test_datasheet_fields_are_saved_as_a_local_version(app_db: api.Api) -> None:
    fields = {
        "datasheet.weight_kg": 10.5,
        "datasheet.power.typical_w": 60,
        "datasheet.dimensions_mm.h": 133,
        "verified": "confirmed",
    }
    page = ok(app_db.set_library_record_fields(PART, fields))
    labels = {e["field"] for e in page["entries"] if e["area"] == "Datasheet"}
    assert {"datasheet.weight_kg", "datasheet.power.typical_w", "verified"} <= labels
    assert "datasheet.dimensions_mm.h" in labels
    record = ok(app_db.library_device(PART))["record"]
    assert record["datasheet"]["dimensions_mm"]["h"] == 133
    applied = ok(app_db.apply_library_edits("datasheet"))
    assert applied["version"] == "1.0.0+local.1"
    assert ok(app_db.library_device(PART))["saved_record"]["datasheet"]["weight_kg"] == 10.5


def test_an_emptied_datasheet_field_is_removed_and_set_back_drops_it(app_db: api.Api) -> None:
    ok(app_db.set_library_record_fields(PART, {"datasheet.weight_kg": None}))
    assert ok(app_db.library_device(PART))["record"]["datasheet"]["weight_kg"] is None
    page = ok(app_db.set_library_record_fields(PART, {"datasheet.weight_kg": 9.07}))
    assert page["count"] == 0


def test_a_record_field_the_model_refuses_is_not_kept(app_db: api.Api) -> None:
    error = refused(app_db.set_library_record_fields(PART, {"verified": "maybe"}))
    assert error["kind"] == "invalid_edit"
    assert ok(app_db.library_pending())["count"] == 0


def test_a_device_without_a_record_has_none(app: api.Api) -> None:
    reply = ok(app.library_device(PART))
    assert reply["record"] is None
    assert reply["saved_record"] is None


def test_discarded_datasheet_edits_come_back_on_undo(app_db: api.Api) -> None:
    ok(app_db.set_library_record_fields(PART, {"datasheet.weight_kg": 10.5}))
    gone = ok(app_db.discard_library_edits())
    assert ok(app_db.library_pending())["count"] == 0
    page = ok(app_db.add_library_edits(gone["discarded"], gone["discarded_records"]))
    assert page["count"] == 1


def test_the_record_choices_come_from_the_model(app_db: api.Api) -> None:
    choices = ok(app_db.library_device(PART))["choices"]
    assert choices["verified"] == ["confirmed", "partial", "unverified"]
    assert "din_rail" in choices["mounting_kind"]


def test_a_record_message_reads_as_the_rule(app_db: api.Api) -> None:
    message = ok(app_db.check_library_record(PART, "datasheet.mounting_kind", "din_rail"))
    assert message.startswith("height_u is above 0")


def test_a_list_of_words_is_reviewed_as_words(app_db: api.Api) -> None:
    fields = {"datasheet.certifications": ["IEC 61850-3", "IEEE 1613"]}
    entries = ok(app_db.set_library_record_fields(PART, fields))["entries"]
    assert entries[0]["to"] == "IEC 61850-3, IEEE 1613"


# -- alternatives (ADR 0017) -------------------------------------------------------------------

SWITCH = "RST2228-L2"


def test_alternatives_list_the_device_first_with_deltas(app: api.Api) -> None:
    rows = ok(app.library_alternatives(SWITCH))["rows"]
    assert rows[0]["part_id"] == SWITCH
    assert rows[0]["is_self"] is True
    assert {r["tier"] for r in rows[1:]} == {"low", "mid", "high"}
    assert all("power_delta_w" in r for r in rows)


def test_alternatives_follow_pending_edits(app: api.Api) -> None:
    ok(app.add_library_edits([power(f"{SWITCH}.MOXA-LOW", 999)]))
    rows = ok(app.library_alternatives(SWITCH))["rows"]
    moxa = next(r for r in rows if r["part_id"] == f"{SWITCH}.MOXA-LOW")
    assert moxa["unit_power_w"] == 999


def test_a_device_without_a_group_has_only_itself(app: api.Api) -> None:
    ok(app.add_library_edits([{"op": "remove", "path": ["devices", PART, "alt_group"]}]))
    reply = ok(app.library_alternatives(PART))
    assert reply["group"] is None
    assert [r["part_id"] for r in reply["rows"]] == [PART]


def test_an_added_alternative_joins_the_group_as_a_copy(app: api.Api) -> None:
    ok(app.add_library_device("RST-NEW", "network_switch", "X", "Y", SWITCH, SWITCH))
    device = ok(app.library_device("RST-NEW"))["device"]
    assert device["alt_group"] == SWITCH
    assert "RST-NEW" in [r["part_id"] for r in ok(app.library_alternatives(SWITCH))["rows"]]


def test_tier_choices_come_from_the_model(app: api.Api) -> None:
    assert ok(app.library_device(SWITCH))["choices"]["tier"] == ["low", "mid", "high"]


def test_deleting_a_device_added_in_the_set_leaves_no_pending_change(app: api.Api) -> None:
    ok(app.add_library_device("SITE-CABLE", "component", "Local", "Cable", None))
    ok(app.add_library_edits([{"op": "remove", "path": ["devices", "SITE-CABLE"]}]))
    assert ok(app.library_pending())["count"] == 0


def test_library_device_names_each_part_by_make_and_model(app: api.Api) -> None:
    ok(app.add_library_device("SITE-CABLE", "component", "Local", "Cable", None))
    ok(app.add_library_device("SITE-BARE", "component", "", "", None))
    names = ok(app.library_device(PART))["part_names"]
    assert names["SITE-CABLE"] == "Local Cable"
    assert names["SITE-BARE"] == ""
    assert set(names) == set(ok(app.library_device(PART))["part_ids"])
