"""The Parts page of the desktop app (plan M23; docs/ui/screens.md, Parts)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.app.parts import parts_page
from bomgen.io import lifecycle
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.package import pack
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


def test_a_new_blank_substation_opens_its_parts_page(project: Path, store: LibraryStore) -> None:
    """Settings and Parts both load this page; a blank substation has no switches to size."""
    lifecycle.create_substation(project, "b", "b", store=store)

    found = parts_page(project, "b", store)["parts"]

    assert found["rows"] == []
    assert found["default_rows"]


def test_starting_a_blank_substations_parts_lays_out_its_panels(
    app: api.Api, project: Path, store: LibraryStore
) -> None:
    """Panels follow the equipment with no manual step (Ali, 2026-10-28; audit ALI-3)."""
    lifecycle.create_substation(project, "b", "b", store=store)
    rows: list[dict[str, Any]] = [
        {"role": "time_server", "part_id": "SEL-2488"},
        {"role": "l2_switch", "part_id": "RST2228-L2", "redundant": True},
    ]

    ok(app.start_parts(str(project), "b", rows))

    listed = read_yaml(project.parent / "substations" / "b" / "substation.yaml").data["panels"]
    assert listed == ["panels/psa1.yaml", "panels/psa2.yaml"]
    assert ok(app.build_target(str(project), "b"))["problems"] == []


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


def test_a_network_row_shows_its_cable_manager_and_the_category_default(
    project: Path, store: LibraryStore
) -> None:
    found = parts(project, store)

    assert row(found, "l2")["cable_manager"] == {"on": True, "default": True}
    assert row(found, "ext-fw")["cable_manager"] == {"on": True, "default": True}
    assert row(found, "gw")["cable_manager"] == {"on": False, "default": False}
    assert row(found, "rtac")["cable_manager"] is None  # not a network device


def test_a_cable_manager_choice_is_shown_over_the_default(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(
        substation,
        "{ id: l2, part_id: RST2228-L2,",
        "{ id: l2, cable_manager: false, part_id: RST2228-L2,",
    )

    assert row(parts(project, store), "l2")["cable_manager"] == {"on": False, "default": True}


def test_the_cable_manager_endpoint_returns_the_page(app: api.Api, project: Path) -> None:
    page = ok(app.set_cable_manager(str(project), "gis01", 4, True))  # the gateway

    assert row(page["parts"], "gw")["cable_manager"] == {"on": True, "default": False}


def test_options_carry_what_the_device_picker_shows(project: Path, store: LibraryStore) -> None:
    switches = parts(project, store)["options"]["network_switch"]

    l2 = next(o for o in switches if o["part_id"] == "RST2228-L2")
    assert l2 == {
        "part_id": "RST2228-L2",
        "make": "Ruggedcom",
        "model": "RST-2228",
        "supply_type": "VDC",
        "unit_power_w": 77,
        "data_quality": None,  # a library file has no device records
        "on_list": True,  # no vendor list (plan M53)
    }


def test_options_carry_the_data_quality_of_the_installed_library(
    project: Path, store: LibraryStore, tmp_path: Path
) -> None:
    package = tmp_path / "lib.bomlib"
    db = Path(__file__).parents[3] / "data" / "device-db"
    library = read_yaml(project).data["library"]  # the version the example asks for
    pack(
        EXAMPLES / "library.yaml",
        package,
        name=library["name"],
        version=library["version"],
        extra_dirs=[db],
    )
    store.import_package(package)
    edit(project, "  file: library.yaml\n", "")

    rtacs = parts(project, store)["options"]["rtac"]

    assert next(o for o in rtacs if o["part_id"] == "SEL-3555-RTAC")["data_quality"] == "partial"


def test_rows_give_the_l2_link_and_com_ports_the_inputs_edit(
    project: Path, store: LibraryStore
) -> None:
    """M31: the link to the L2 switch on every row that has one, COM ports on an RTAC."""
    found = parts(project, store)

    gps = row(found, "gps")
    assert gps["link"] == {"l2_ports": 1, "l2_speed": "100M", "l2_media": "MM", "no_sfp": False}
    assert gps["serial_ports"] is None  # not an RTAC
    assert row(found, "rtac")["serial_ports"] == 6
    assert row(found, "rtac")["link"]["l2_ports"] == 2
    for switch in ("l1", "l2", "fopp"):
        assert row(found, switch)["link"] is None  # sized or patched, not linked by hand


def test_a_link_no_library_sfp_serves_is_marked_on_its_row(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    """M46: the row says so before Checks does; an RJ45 link needs no SFP."""
    text = substation.read_text(encoding="utf-8")
    old = "l2_ports: 1, l2_speed: 100M }"
    assert old in text
    substation.write_text(text.replace(old, "l2_ports: 1, l2_speed: 10G, l2_media: SM }"), "utf-8")
    assert row(parts(project, store), "gps")["link"]["no_sfp"] is True
    substation.write_text(
        text.replace(old, "l2_ports: 1, l2_speed: 10G, l2_media: RJ45 }"), "utf-8"
    )
    assert row(parts(project, store), "gps")["link"]["no_sfp"] is False


def test_the_l2_link_and_com_ports_are_written_as_equipment_fields(
    app: api.Api, project: Path, store: LibraryStore
) -> None:
    ok(app.set_substation_field(str(project), "gis01", ["equipment", 4, "l2_ports"], 2))
    ok(app.set_substation_field(str(project), "gis01", ["equipment", 4, "l2_speed"], "10G"))
    path: list[str | int] = ["equipment", 7, "port_plan", "serial_ports"]
    ok(app.set_substation_field(str(project), "gis01", path, 4))

    found = parts(project, store)
    link = {"l2_ports": 2, "l2_speed": "10G", "l2_media": "MM", "no_sfp": True}  # no 10G SFP
    assert row(found, "gw")["link"] == link
    assert row(found, "rtac")["serial_ports"] == 4


def test_add_a_device_offers_monitors_and_peripherals(project: Path, store: LibraryStore) -> None:
    """APP-23: the console's monitor and keyboard can be added as equipment rows."""
    found = parts(project, store)
    added = {c["category"]: c["label"] for c in found["add_categories"]}
    assert added["monitor"] == "Monitor"
    assert added["peripheral"] == "Keyboard and mouse"
    assert "NAP-F23" in [o["part_id"] for o in found["options"]["monitor"]]
    assert "KEYTEK-KBM" in [o["part_id"] for o in found["options"]["peripheral"]]


def test_a_monitor_row_is_named_by_its_category(
    app: api.Api, project: Path, store: LibraryStore
) -> None:
    row_in = {"id": "mon", "part_id": "NAP-F23", "role": "other"}
    ok(app.add_equipment(str(project), "gis01", row_in, None, True))
    assert row(parts(project, store), "mon")["label"] == "Monitor"


def test_parts_page_sfp_counts_carry_rule(project: Path, store: LibraryStore) -> None:
    """M49: each SFP sub-row gives the links, spare, extra and total of each BOM row."""
    (sfp,) = row(parts(project, store), "l1")["sfp"]

    assert (sfp["used"], sfp["extra"], sfp["total"]) == (6, 0, 9)
    assert sfp["spare"] == {
        "value": 3,
        "rule": "3: the project's spare SFPs per L1 row",
        "override": None,
        "unit": None,
        "source": "engine",
    }
    assert sfp["rule"] == "6 links + 3 spare"


def test_sfp_spare_and_extra_are_set_from_the_parts_page(app: api.Api, project: Path) -> None:
    l1 = row(ok(app.parts_page(str(project), "gis01"))["parts"], "l1")["index"]

    ok(app.set_sfp_count(str(project), "gis01", l1, "1G", "MM", "spare", 1))
    page = ok(app.set_sfp_count(str(project), "gis01", l1, "1G", "MM", "extra", 2))

    (sfp,) = row(page["parts"], "l1")["sfp"]
    assert (sfp["spare"]["override"], sfp["extra"], sfp["total"]) == (1, 2, 9)
    assert sfp["rule"] == "6 links + 1 spare + 2 extra"


def test_the_panel_cap_is_set_on_parts_and_reported_on_the_board(
    app: api.Api, project: Path
) -> None:
    """M62: Parts writes layout.max_panels; the page and the layout preview give it back."""
    page = ok(app.parts_page(str(project), "gis01"))
    assert page["max_panels"] is None

    page = ok(app.set_substation_field(str(project), "gis01", ["layout", "max_panels"], 1))

    assert page["max_panels"] == 1
    issues = ok(app.substation_layout(str(project), "gis01"))["issues"]
    assert any("does not fit in 1 panel" in i["message"] for i in issues)


def test_parts_page_gives_generated_tag_as_placeholder(app: api.Api, project: Path) -> None:
    """M59: each row carries the tags the layout generates, one per panel row, which the
    BOM text fields show as placeholders; a typed tag does not replace them."""
    page = ok(app.parts_page(str(project), "gis01"))["parts"]
    assert row(page, "l1")["tags"] == ["PSA1-L1-ESW-A11 to A13", "PSA2-L1-ESW-B11 to B13"]
    gw = row(page, "gw")

    ok(app.set_substation_field(str(project), "gis01", ["equipment", gw["index"], "tag"], "X"))

    page = ok(app.parts_page(str(project), "gis01"))["parts"]
    assert row(page, "gw")["tags"] == gw["tags"]
    assert row(page, "gw")["bom_text"]["tag"] == "X"


def test_a_typed_tag_another_unit_has_is_marked_on_its_row(app: api.Api, project: Path) -> None:
    """M59: the duplicate-tag check's sentence shows on the row before Checks runs."""
    page = ok(app.parts_page(str(project), "gis01"))["parts"]
    gps = row(page, "gps")
    assert gps["duplicate"] is None
    path = ["equipment", gps["index"], "tag"]

    ok(app.set_substation_field(str(project), "gis01", path, "PSA1-L2-ESW-A01"))

    duplicate = row(ok(app.parts_page(str(project), "gis01"))["parts"], "gps")["duplicate"]
    assert duplicate == "PSA1-L2-ESW-A01: 2 device units share this tag (psa1): each needs its own"


def test_a_row_with_branch_mcbs_shows_its_alarm_and_the_library_default(
    project: Path, store: LibraryStore, substation: Path
) -> None:
    """Plan M58: "Alarm on branch MCB trip" with the library's value as the default."""
    found = parts(project, store)
    assert row(found, "ext-fw")["alarm"] == {"on": True, "default": True}
    assert row(found, "fopp")["alarm"] is None  # no supply, no branch MCB

    text = substation.read_text("utf-8")
    substation.write_text(
        text.replace("  - id: ext-fw\n", "  - id: ext-fw\n    alarm_on_branch_mcb: false\n"),
        "utf-8",
    )
    assert row(parts(project, store), "ext-fw")["alarm"] == {"on": False, "default": True}


def test_a_row_names_the_figures_its_part_assumes(project: Path, store: LibraryStore) -> None:
    # ADR 0037 (M67c): Parts shows a chip for an assumed power or inrush.
    library = project.parent / "library.yaml"
    edit(
        library,
        "  - part_id: SEL-3555-RTAC  # 'Panel 3' row 5: PSA3-RTAC\n",
        "  - part_id: SEL-3555-RTAC  # 'Panel 3' row 5: PSA3-RTAC\n"
        '    sources: { unit_power_w: { kind: assumed, ref: "the example workbook" } }\n',
    )

    found = parts(project, store)

    assert row(found, "rtac")["assumed"] == [
        {"field": "unit_power_w", "ref": "the example workbook"}
    ]
    assert row(found, "gps")["assumed"] == []


def test_picker_groups_vendor_list_parts_first(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(
        project,
        "substations:",
        "vendor_lists:\n  - { key: avl, name: Client AVL, makes: [Siemens] }\nsubstations:",
    )
    with substation.open("a", encoding="utf-8") as f:
        f.write("design_basis:\n  vendor_list: avl\n")
    found = parts(project, store)

    switches = found["options"]["network_switch"]
    on = [o["on_list"] for o in switches]
    assert on == sorted(on, reverse=True)  # the list's parts first
    assert {o["make"] for o in switches if o["on_list"]} == {"Siemens"}
    assert not row(found, "l1")["on_list"]  # Ruggedcom: the warning chip
    assert found["vendor_list"] == "Client AVL"


def test_without_a_vendor_list_every_part_is_on_it(project: Path, store: LibraryStore) -> None:
    found = parts(project, store)
    assert found["vendor_list"] is None
    assert all(o["on_list"] for o in found["options"]["network_switch"])
    assert row(found, "l1")["on_list"]
