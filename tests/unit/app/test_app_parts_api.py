"""The Parts page of the desktop app (plan M23; docs/ui/screens.md, Parts)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.app.parts import parts_page
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


@pytest.fixture
def substation(project: Path) -> Path:
    return project.parent / "substations" / "gis01" / "substation.yaml"


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
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


def edit(file: Path, old: str, new: str) -> None:
    text = file.read_text(encoding="utf-8")
    assert old in text
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def parts(project: Path, store: LibraryStore) -> Any:
    found = parts_page(project, "gis01", store)["parts"]
    json.dumps(found)
    return found


def row(found: Any, entry_id: str) -> Any:
    return next(r for r in found["rows"] if r["id"] == entry_id)


def test_parts_rows_follow_the_equipment_order(project: Path, store: LibraryStore) -> None:
    ids = [r["id"] for r in parts(project, store)["rows"]]

    assert ids == ["fopp", "l2", "l1", "ext-esw", "gw", "ext-fw", "gps", "rtac", "hwio"]
    assert [r["index"] for r in parts(project, store)["rows"]] == list(range(9))


def test_a_row_is_named_by_its_role_or_else_by_its_part_category(
    project: Path, store: LibraryStore
) -> None:
    found = parts(project, store)

    assert row(found, "l2")["label"] == "L2 switch"
    assert row(found, "gps")["label"] == "Time server clock"  # role other, a gps_clock part
    assert row(found, "gw")["label"] == "Gateway"


def test_a_row_shows_the_library_values_of_its_base_part_not_the_derived_one(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(
        substation,
        "role: other, l2_ports: 1, l2_speed: 100M }",
        "role: other, l2_ports: 1, l2_speed: 100M, overrides: { unit_power_w: 99 } }",
    )

    gps = row(parts(project, store), "gps")

    assert gps["library"]["unit_power_w"] == 50
    assert gps["library"]["height_u"] == 1
    assert gps["overrides"] == {"unit_power_w": 99}


def test_a_sized_l1_row_without_a_part_has_no_library_values(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(substation, "{ id: l1, part_id: RST2228-L1-24MM, role:", "{ id: l1, role:")

    l1 = row(parts(project, store), "l1")

    assert l1["sized"] is True
    assert l1["part_id"] is None
    assert l1["library"] is None
    assert l1["sfp"] == []


def test_a_part_missing_from_the_library_is_unknown_and_the_page_still_loads(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(substation, "part_id: SEL-3555-RTAC", "part_id: SEL-3555-RTAC-OLD")

    rtac = row(parts(project, store), "rtac")

    assert rtac["known"] is False
    assert rtac["library"] is None
    assert rtac["part_id"] == "SEL-3555-RTAC-OLD"


def test_options_list_each_category_without_derived_parts(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(
        substation,
        "{ id: l2, part_id: RST2228-L2, role: l2_switch, redundant: true }",
        "{ id: l2, part_id: RST2228-L2, role: l2_switch, redundant: true, ordering_code: X1 }",
    )

    switches = [o["part_id"] for o in parts(project, store)["options"]["network_switch"]]

    assert "RST2228-L2" in switches
    assert not any("+" in p for p in switches)


def test_an_empty_category_has_an_empty_options_list(project: Path, store: LibraryStore) -> None:
    options = parts(project, store)["options"]

    assert options["kvm"] == []  # the shipped library has no KVM or console parts (Ali)
    assert options["console"] == []


def test_sfp_needs_are_the_speeds_and_media_the_switch_ports_use(
    project: Path, store: LibraryStore
) -> None:
    found = parts(project, store)
    l1 = row(found, "l1")["sfp"]

    assert [(s["speed"], s["media"]) for s in l1] == [("1G", "MM")]  # the L1 uplinks
    assert l1[0]["choice"] is None  # automatic
    assert l1[0]["candidates"]
    assert row(found, "gw")["sfp"] == []


def test_a_loose_item_of_a_time_accessory_part_is_listed_under_the_time_server_row(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(
        substation,
        "    - part_id: ZENON-V12  # row 51",
        "    - { part_id: SEL-C961-050, qty: 2 }\n    - part_id: ZENON-V12  # row 51",
    )

    accessories = row(parts(project, store), "gps")["accessories"]

    assert accessories["added"] == [
        {"index": 1, "part_id": "SEL-C961-050", "item": {"part_id": "SEL-C961-050", "qty": 2}}
    ]
    assert accessories["host_panel"] == "ws"
    assert {"part_id": "SEL-9524B", "qty": 1} in accessories["library"]
    assert "SEL-C961-050" in accessories["parts"]


def test_a_free_text_or_unrelated_loose_item_is_not_linked_to_the_time_server(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(
        substation,
        "    - part_id: ZENON-V12  # row 51",
        "    - { description: Spare cable }\n    - part_id: ZENON-V12  # row 51",
    )

    accessories = row(parts(project, store), "gps")["accessories"]

    assert accessories["added"] == []  # NAP-K55, ZENON-V12 and the free text are not its parts
    assert row(parts(project, store), "l2")["accessories"] is None


def test_parts_endpoints_return_the_refreshed_page(app: api.Api, project: Path) -> None:
    gps = row(ok(app.parts_page(str(project), "gis01"))["parts"], "gps")["index"]

    page = ok(app.set_part_override(str(project), "gis01", gps, "unit_power_w", 60))

    assert row(page["parts"], "gps")["overrides"] == {"unit_power_w": 60}
    page = ok(app.set_part_override(str(project), "gis01", gps, "unit_power_w", 50))
    assert row(page["parts"], "gps")["overrides"] == {}


def test_a_refused_override_comes_back_with_the_sentence(app: api.Api, project: Path) -> None:
    envelope = app.set_part_override(str(project), "gis01", 6, "supply_type", "VAC")

    assert envelope["ok"] is False
    assert envelope["error"]["kind"] == "invalid_edit"  # type: ignore[index]


def test_changing_a_part_says_what_was_cleared(app: api.Api, project: Path) -> None:
    ok(app.set_part_override(str(project), "gis01", 4, "unit_power_w", 99))
    other = next(
        o["part_id"]
        for o in ok(app.parts_page(str(project), "gis01"))["parts"]["options"]["gateway"]
        if o["part_id"] != "SEL-3555-GW"
    )

    data = ok(app.set_equipment_part(str(project), "gis01", 4, other))

    assert data["cleared"] == ["overrides"]
    assert row(data["page"]["parts"], "gw")["part_id"] == other


def test_moving_a_row_changes_the_order(app: api.Api, project: Path) -> None:
    page = ok(app.move_equipment(str(project), "gis01", 6, 0))

    assert page["parts"]["rows"][0]["id"] == "gps"
