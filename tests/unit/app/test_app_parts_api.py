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
    # M86: it shows the SFP rows of the switch the sizing picked (was none before M86)
    assert [(s["speed"], s["media"]) for s in l1["sfp"]] == [("1G", "MM")]


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
        "tags": [],  # the example library tags no part (plan M81)
        "supply_type": "VDC",
        "unit_power_w": 77,
        "data_quality": None,  # a library file has no device records
        "on_list": True,  # no vendor list (plan M53)
        "tier": None,  # an original (plan M83)
        "level": "L2 switch",  # a switch says its level
        "replaces": None,
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


def test_parts_page_sfp_counts_carry_rule(laid_out: Path, store: LibraryStore) -> None:
    """M49: each SFP sub-row gives the links, spare, extra and total of each BOM row."""
    (sfp,) = row(parts(laid_out, store), "l1")["sfp"]

    assert (sfp["used"], sfp["extra"], sfp["total"]) == (6, 0, 9)
    assert sfp["spare"] == {
        "value": 3,
        "rule": "3: the project's spare SFPs per L1 row",
        "override": None,
        "unit": None,
        "source": "engine",
    }
    assert sfp["rule"] == "6 links + 3 spare"


def test_sfp_spare_and_extra_are_set_from_the_parts_page(app: api.Api, laid_out: Path) -> None:
    project = laid_out
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


# --- The IED schedule (plan M60, ADR 0034) ---------------------------------------------


def test_ied_rows_are_added_set_and_removed_from_the_parts_page(
    app: api.Api, project: Path
) -> None:
    page = ok(app.add_ied_row(str(project), "gis01", {"bay": "E01", "name": "SEL-411L", "qty": 40}))
    assert page["network"]["ied_count"] == 0
    (first,) = page["parts"]["ieds"]
    assert first["ports_text"] == "1x100M MM"
    page = ok(app.set_ied_field(str(project), "gis01", 0, "ports", "2x100M MM"))
    assert page["parts"]["ieds"][0]["ports_text"] == "2x100M MM"
    data = ok(app.remove_ied_row(str(project), "gis01", 0))
    assert data["row"]["bay"] == "E01"
    assert data["page"]["parts"]["ieds"] == []


def test_ied_field_with_unreadable_ports_is_refused(app: api.Api, project: Path) -> None:
    ok(app.add_ied_row(str(project), "gis01", {"bay": "E01", "name": "P"}))
    envelope: Any = app.set_ied_field(str(project), "gis01", 0, "ports", "fast")
    assert envelope["ok"] is False
    assert "fast" in envelope["error"]["message"]


def test_ied_csv_import_is_reviewed_before_it_replaces_the_schedule(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    csv = tmp_path / "ieds.csv"
    csv.write_text(
        "bay,name,qty,ports,attachment,lands_on\n"
        "E01,SEL-411L,40,1x100M MM,dual,l1\n"
        "E02,Meter,x,,dual,l1\n",
        encoding="utf-8",
    )
    review = ok(app.import_ied_csv(str(project), "gis01", str(csv), True))
    assert (len(review["rows"]), review["replaces"], review["can_import"]) == (1, 0, True)
    assert [(p["row"], p["column"]) for p in review["problems"]] == [(3, "qty")]
    assert ok(app.parts_page(str(project), "gis01"))["parts"]["ieds"] == []
    page = ok(app.import_ied_csv(str(project), "gis01", str(csv), False))
    assert [r["bay"] for r in page["parts"]["ieds"]] == ["E01"]


def test_layout_page_gives_the_schedules_ports_per_side(app: api.Api, project: Path) -> None:
    rows = [
        {"bay": "E01", "name": "P", "qty": 30},
        {"bay": "E02", "name": "M", "qty": 4, "attachment": "single_a"},
    ]
    for r in rows:
        ok(app.add_ied_row(str(project), "gis01", r))
    plan = ok(app.substation_layout(str(project), "gis01"))["plan"]
    assert plan["ied_count"] == 34
    assert plan["ied_ports"] == [
        {"speed": "100M", "media": "MM", "lands_on": "l1", "a": 34, "b": 30}
    ]


def test_undo_puts_a_removed_ied_row_back_in_its_place(app: api.Api, project: Path) -> None:
    for bay in ("E01", "E02", "E03"):
        ok(app.add_ied_row(str(project), "gis01", {"bay": bay, "name": "P"}))
    data = ok(app.remove_ied_row(str(project), "gis01", 1))
    page = ok(app.add_ied_row(str(project), "gis01", data["row"], 1))
    assert [r["bay"] for r in page["parts"]["ieds"]] == ["E01", "E02", "E03"]


# --- External links (plan M61) --------------------------------------------------------


def test_external_links_are_edited_on_parts_and_counted_on_the_result_card(
    app: api.Api, project: Path
) -> None:
    page = ok(app.add_external_link(str(project), "gis01", {"name": "CCR", "count": 2}, None))
    (link,) = page["parts"]["links"]
    assert (link["name"], link["speed"], link["media"], link["lands_on"]) == (
        "CCR",
        "1G",
        "SM",
        "l2",
    )
    page = ok(app.set_external_link_field(str(project), "gis01", 0, "redundant", False))
    assert page["parts"]["links"][0]["redundant"] is False
    plan = ok(app.substation_layout(str(project), "gis01"))["plan"]
    assert plan["external_links"] == [
        {"name": "CCR", "count": 2, "speed": "1G", "media": "SM", "lands_on": "l2", "a": 2, "b": 0}
    ]
    data = ok(app.remove_external_link(str(project), "gis01", 0))
    assert data["row"]["name"] == "CCR"
    assert data["page"]["parts"]["links"] == []


def test_a_common_row_offers_a_panel_hint(project: Path, store: LibraryStore) -> None:
    """M74: a common row may be steered to a panel; a redundant row may not."""
    found = parts(project, store)
    gps = row(found, "gps")["placement"]
    assert (gps["panel_hint"], gps["steerable"]) == (None, True)
    assert row(found, "l2")["placement"]["steerable"] is False


def test_a_panel_hint_on_a_redundant_row_is_refused(app: api.Api, project: Path) -> None:
    l2 = 1  # the example's redundant L2 switch row
    problem = ok(
        app.check_substation_field(str(project), "gis01", ["equipment", l2, "panel_hint"], 2)
    )
    assert "panel_hint steers a common device" in problem


def test_a_row_shows_its_rack_priority_and_its_categorys(
    project: Path, store: LibraryStore
) -> None:
    """M76: the category's stack priority, and the row's own when set."""
    found = parts(project, store)
    rtac = row(found, "rtac")["placement"]
    assert (rtac["priority"], rtac["default_priority"]) == (None, 4)
    assert row(found, "gps")["placement"]["default_priority"] == 1


# plan M86 (Ali's v0.5.0 point 2): SFP rows on every switch row

UNPIN_L1 = ("{ id: l1, part_id: RST2228-L1-24MM, role:", "{ id: l1, role:")


def counts(sfps: list[Any]) -> list[tuple[Any, ...]]:
    return [(s["speed"], s["media"], s["used"], s["spare"]["value"], s["total"]) for s in sfps]


@pytest.mark.usefixtures("laid_out")  # M87: hand-written panels have no pin (below)
def test_m49_a_sized_l1_row_shows_the_sfp_rows_of_the_switch_the_sizing_picked(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    pinned = row(parts(project, store), "l1")
    edit(substation, *UNPIN_L1)

    l1 = row(parts(project, store), "l1")

    assert l1["part_id"] is None
    # the sizing picks the example's own switch, so the numbers are the pinned row's
    assert l1["pin"]["part_id"] == "RST2228-L1-24MM"
    assert (l1["pin"]["make"], l1["pin"]["model"]) == ("Ruggedcom", "RST-2228")
    assert counts(l1["sfp"]) == counts(pinned["sfp"]) == [("1G", "MM", 6, 3, 9)]
    assert l1["sfp"][0]["rule"] == pinned["sfp"][0]["rule"]
    assert l1["sfp"][0]["choice"] is None
    assert pinned["pin"] is None  # a row with a part is edited, not pinned


@pytest.mark.usefixtures("laid_out")
def test_m49_pinning_the_sized_l1_keeps_its_sfp_rows_and_makes_them_editable(
    app: api.Api, project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(substation, *UNPIN_L1)
    sized = row(parts(project, store), "l1")

    done = ok(
        app.set_equipment_part(str(project), "gis01", sized["index"], sized["pin"]["part_id"])
    )

    l1 = row(done["page"]["parts"], "l1")
    assert l1["part_id"] == "RST2228-L1-24MM"
    assert l1["pin"] is None
    assert counts(l1["sfp"]) == counts(sized["sfp"])
    written = next(e for e in read_yaml(substation).data["equipment"] if e["id"] == "l1")
    assert written["part_id"] == "RST2228-L1-24MM"
    page = ok(app.set_sfp_count(str(project), "gis01", l1["index"], "1G", "MM", "spare", 1))
    assert row(page["parts"], "l1")["sfp"][0]["total"] == 7


@pytest.mark.parametrize(
    ("old", "new", "said"),
    [
        # the layout fails: the sizing refuses the count
        (
            "  l3_uplinks_per_l2: 2\n",
            "  l3_uplinks_per_l2: 2\n  l1_per_side: 1\n",
            "fewer than the 3 the sizing needs",
        ),
        # the project does not load
        ("part_id: SEL-3555-RTAC", "part_id: SEL-3555-RTAC-OLD", "problems listed at the top"),
    ],
)
def test_m49_switch_rows_say_why_their_sfp_rows_are_missing(
    project: Path, substation: Path, store: LibraryStore, old: str, new: str, said: str
) -> None:
    assert row(parts(project, store), "l1")["sfp_reason"] is None
    edit(substation, old, new)

    found = parts(project, store)

    for entry in ("l1", "l2"):
        switch = row(found, entry)
        assert switch["sfp"] == []
        assert said in switch["sfp_reason"]
    assert row(found, "gw")["sfp_reason"] is None  # only the switch rows have SFP rows


def test_m49_an_sfp_row_names_the_automatic_part(project: Path, store: LibraryStore) -> None:
    """The engine's pick with no choice: the switch's make first (engine/network.py)."""
    found = parts(project, store)
    sfps = {(s["speed"], s["media"]): s for s in row(found, "l2")["sfp"]}
    names = {o["part_id"]: (o["make"], o["model"]) for o in found["options"]["sfp"]}

    mm = sfps[("1G", "MM")]
    assert mm["auto"] == "SFP-1G-SX-MM"  # the Ruggedcom switch takes the Ruggedcom SFP
    assert names[mm["auto"]] == ("Ruggedcom", "6GK6000-8FG51-0AA0")
    # the other parts are named the same way, by make and model
    assert [names[c] for c in mm["candidates"]] == [
        ("Ruggedcom", "6GK6000-8FG51-0AA0"),
        ("Fortigate", "FR-TRAN-SX"),
    ]
    assert {s["auto"] for s in sfps.values()} <= set(names)


# plan M87, Q77 (a): the quantity on each BOM row is the value the engineer types; it is
# stored as the spare it implies. The example laid out has 6 1G MM links per L1 row.
def sfp_of(page: Any, entry_id: str = "l1") -> Any:
    (sfp,) = row(page["parts"], entry_id)["sfp"]
    return sfp


def written_sfp(substation: Path) -> Any:
    return next(e for e in read_yaml(substation).data["equipment"] if e["id"] == "l1").get("sfp")


@pytest.mark.usefixtures("laid_out")
def test_m49_a_typed_total_is_stored_as_the_spare_it_implies(
    app: api.Api, project: Path, substation: Path
) -> None:
    l1 = row(ok(app.parts_page(str(project), "gis01"))["parts"], "l1")["index"]

    page = ok(app.set_sfp_total(str(project), "gis01", l1, "1G", "MM", 20))

    assert written_sfp(substation) == [{"speed": "1G", "media": "MM", "spare": 14}]
    sfp = sfp_of(page)
    assert (sfp["used"], sfp["spare"]["override"], sfp["total"]) == (6, 14, 20)
    assert sfp["quantity"] == {
        "value": 9,
        "rule": "6 links + 3 spare (the project's spare SFPs per L1 row)",
        "override": 20,
        "unit": None,
        "source": "override",
    }
    assert sfp["rule"] == "6 links + 14 spare"


@pytest.mark.usefixtures("laid_out")
def test_m49_a_total_below_the_links_is_refused_naming_the_links(
    app: api.Api, project: Path, substation: Path
) -> None:
    l1 = row(ok(app.parts_page(str(project), "gis01"))["parts"], "l1")["index"]
    before = substation.read_text(encoding="utf-8")
    said = "Enter at least 6: the switch has 6 1G MM links on each BOM row"

    refused = app.set_sfp_total(str(project), "gis01", l1, "1G", "MM", 5)

    assert refused["ok"] is False
    assert said in str(refused["error"])
    assert substation.read_text(encoding="utf-8") == before
    # the draft form asks the same question before Save
    assert said in ok(app.check_sfp_total(str(project), "gis01", l1, "1G", "MM", 5))
    assert ok(app.check_sfp_total(str(project), "gis01", l1, "1G", "MM", 6)) is None
    page = ok(app.set_sfp_total(str(project), "gis01", l1, "1G", "MM", 6))  # one per link
    assert (sfp_of(page)["spare"]["override"], sfp_of(page)["total"]) == (0, 6)


@pytest.mark.usefixtures("laid_out")
def test_m49_resetting_the_total_returns_the_automatic_spare(
    app: api.Api, project: Path, substation: Path
) -> None:
    l1 = row(ok(app.parts_page(str(project), "gis01"))["parts"], "l1")["index"]
    ok(app.set_sfp_total(str(project), "gis01", l1, "1G", "MM", 20))

    page = ok(app.set_sfp_total(str(project), "gis01", l1, "1G", "MM", None))

    assert written_sfp(substation) is None
    sfp = sfp_of(page)
    assert (sfp["quantity"]["override"], sfp["quantity"]["source"]) == (None, "engine")
    assert (sfp["spare"]["override"], sfp["total"]) == (None, 9)


@pytest.mark.usefixtures("laid_out")
def test_m49_a_typed_total_keeps_the_extra(app: api.Api, project: Path, substation: Path) -> None:
    l1 = row(ok(app.parts_page(str(project), "gis01"))["parts"], "l1")["index"]
    ok(app.set_sfp_count(str(project), "gis01", l1, "1G", "MM", "extra", 2))

    page = ok(app.set_sfp_total(str(project), "gis01", l1, "1G", "MM", 20))

    assert written_sfp(substation) == [{"speed": "1G", "media": "MM", "extra": 2, "spare": 12}]
    sfp = sfp_of(page)
    assert (sfp["extra"], sfp["total"], sfp["rule"]) == (2, 20, "6 links + 12 spare + 2 extra")
    # the extra comes on top of the links: a total that leaves no room for it is refused
    said = ok(app.check_sfp_total(str(project), "gis01", l1, "1G", "MM", 7))
    assert said.startswith("Enter at least 8: the switch has 6 1G MM links")
    assert "the 2 extra SFPs" in said


@pytest.mark.usefixtures("laid_out")
def test_m49_a_typed_total_uses_the_extra_the_same_save_writes(
    app: api.Api, project: Path, substation: Path
) -> None:
    """Save writes the drafted total and extra in the order they were typed; each BOM row
    carries the total the engineer typed in either order."""
    l1 = row(ok(app.parts_page(str(project), "gis01"))["parts"], "l1")["index"]

    ok(app.set_sfp_total(str(project), "gis01", l1, "1G", "MM", 20, 4))
    page = ok(app.set_sfp_count(str(project), "gis01", l1, "1G", "MM", "extra", 4))

    assert sfp_of(page)["total"] == 20
    assert ok(app.check_sfp_total(str(project), "gis01", l1, "1G", "MM", 9, 4)) is not None


@pytest.mark.usefixtures("laid_out")
def test_m49_the_l2_total_can_go_above_its_links(app: api.Api, project: Path) -> None:
    """Ali's point 2: an L2 switch's automatic spare is 0; its total is typed like an L1's."""

    def mm(page: Any) -> Any:
        found = row(page["parts"], "l2")["sfp"]
        return next(s for s in found if (s["speed"], s["media"]) == ("1G", "MM"))

    before = mm(ok(app.parts_page(str(project), "gis01")))
    assert before["quantity"]["rule"].endswith("(the project sets spare SFPs on L1 rows only)")
    l2 = row(ok(app.parts_page(str(project), "gis01"))["parts"], "l2")["index"]

    page = ok(app.set_sfp_total(str(project), "gis01", l2, "1G", "MM", before["used"] + 2))

    assert (mm(page)["spare"]["override"], mm(page)["total"]) == (2, before["used"] + 2)


@pytest.fixture
def laid_out(app: api.Api, project: Path, substation: Path) -> Path:
    """The example laid out: generated panels, whose SFPs the Parts page edits (on its own
    hand-written panels they are read-only, plan M87). 6 links per L1 row."""
    text = substation.read_text("utf-8")
    substation.write_text(text[: text.index("\nloose_material:") + 1], "utf-8")
    ok(app.generate_panels(str(project), "gis01"))
    return project


def test_m49_the_sfp_quantity_cell_still_reads_links_plus_spare(
    app: api.Api, laid_out: Path, substation: Path
) -> None:
    from bomgen.engine.layout import with_layout
    from bomgen.engine.pipeline import build
    from bomgen.io.loader import load_substation
    from bomgen.models.bom import Group, QtySum

    found = ok(app.parts_page(str(laid_out), "gis01"))
    links, l1 = sfp_of(found)["used"], row(found["parts"], "l1")["index"]
    ok(app.set_sfp_total(str(laid_out), "gis01", l1, "1G", "MM", links + 10))

    result = build(with_layout(load_substation(substation))[0])

    cells = [
        line.qty
        for panel in result.panels
        for line in panel.lines
        if line.group is Group.C and line.tag is not None and line.tag.startswith("L1-")
    ]
    # one L1 row per cabinet, as on the page: its cell is still links + spare
    assert cells == [QtySum(parts=(links, 10))] * 2


@pytest.fixture
def split(app: api.Api, project: Path, substation: Path) -> Path:
    """The example laid out for 300 IEDs: each side's L1 switches fill one cabinet and spill
    into the next of their side (psa1 and psa3 on A), so one entry's BOM rows differ."""
    text = substation.read_text("utf-8")
    text = text[: text.index("\nloose_material:") + 1].replace("ied_count: 40", "ied_count: 300")
    substation.write_text(text, "utf-8")
    ws = substation.parent / "panels" / "ws.yaml"  # its sheet "4" is the fourth cabinet's
    ws.write_text(ws.read_text("utf-8").replace('sheet_name: "4"', 'sheet_name: "WS"'), "utf-8")
    ok(app.generate_panels(str(project), "gis01"))
    return project


Cell = tuple[str, str, str, str]  # cabinet, switch level, media, SFP part


def bom_sfps(substation: Path) -> dict[Cell, int]:
    """The SFP quantity the build prints on each switch's BOM rows, by cabinet."""
    from bomgen.engine.layout import with_layout
    from bomgen.engine.pipeline import build
    from bomgen.io.loader import load_substation
    from bomgen.models.bom import Group, QtySum

    built = with_layout(load_substation(substation))[0]
    names = {p.id: p.cabinet_name for p in built.panels}
    return {
        (names[panel.panel_id], line.tag[:2], line.tag[-3:-1], str(line.part_id)): (
            line.qty.value if isinstance(line.qty, QtySum) else int(str(line.qty))
        )
        for panel in build(built).panels
        for line in panel.lines
        if line.group is Group.C and line.tag and line.tag[:2] in ("L1", "L2") and "SFP" in line.tag
    }


def page_sfps(found: Any) -> dict[Cell, int]:
    """The quantity the page gives each switch's SFP rows on each BOM row, keyed as
    ``bom_sfps``."""
    return {
        (x["cabinet"], r["role"][:2].upper(), f["media"], f["choice"] or f["auto"]): x["quantity"]
        for r in found["parts"]["rows"]
        if r["role"] in ("l1_switch", "l2_switch")
        for f in r["sfp"]
        for x in f["rows"]
    }


def l1_cells(cells: dict[Cell, int]) -> list[int]:
    return [n for (_cab, level, _media, _part), n in sorted(cells.items()) if level == "L1"]


@pytest.mark.parametrize("panels", ["hand-written", "generated", "split"])
def test_m49_the_total_on_the_page_is_the_quantity_in_the_bom(
    app: api.Api, project: Path, substation: Path, panels: str, request: pytest.FixtureRequest
) -> None:
    """plan M87: the page counts the SFPs from the panels the build uses, on every BOM row of
    the entry, so each quantity it shows is the one the BOM prints there, before and after a
    typed total."""
    if panels != "hand-written":
        request.getfixturevalue("laid_out" if panels == "generated" else "split")
    found = ok(app.parts_page(str(project), "gis01"))
    assert page_sfps(found) == bom_sfps(substation)

    l1 = row(found["parts"], "l1")
    total = 30 if panels == "generated" else 100
    typed = app.set_sfp_total(str(project), "gis01", l1["index"], "1G", "MM", total)

    if panels == "generated":  # psa1 and psa2, one side each, 6 links per row
        assert typed["ok"] is True
        assert page_sfps(typed["data"]) == bom_sfps(substation)
        assert l1_cells(bom_sfps(substation)) == [30, 30]
        assert all(f["agree"] for r in found["parts"]["rows"] for f in r["sfp"])
    elif panels == "split":  # psa1 to psa4: 26 and 6 links per side, 3 spare
        assert l1_cells(page_sfps(found)) == [29, 29, 9, 9]
        # the total is typed on the row with the most links, the first of equals
        assert (l1["sfp"][0]["agree"], l1["sfp"][0]["on"]) == (False, "PSA Cabinet - 001")
        assert l1["sfp"][0]["quantity"]["value"] == 29
        assert typed["ok"] is True
        assert page_sfps(typed["data"]) == bom_sfps(substation)
        assert l1_cells(bom_sfps(substation)) == [100, 100, 80, 80]
    else:
        # the hand-written files name the library part, which no SFP choice reaches (ADR
        # 0024): the BOM keeps the files' port plans, so the page refuses a total
        assert typed["ok"] is False
        assert "hand-written" in str(typed["error"])
        assert page_sfps(ok(app.parts_page(str(project), "gis01"))) == bom_sfps(substation)


def test_m87_hand_written_panels_give_their_files_sfps_read_only(
    app: api.Api, project: Path, substation: Path, store: LibraryStore
) -> None:
    """The example's own panels are hand-written: its switch rows show the files' port plans
    (the spec's =24+3), read-only, and a choice in the file changes neither them nor the BOM."""
    from bomgen.app.parts import HAND_WRITTEN

    found = parts(project, store)
    l1, l2 = row(found, "l1"), row(found, "l2")
    assert counts(l1["sfp"]) == [("1G", "MM", 24, 3, 27)]
    assert counts(l2["sfp"]) == [
        ("100M", "MM", 2, 0, 2),
        ("1G", "MM", 15, 0, 15),
        ("1G", "SM", 2, 0, 2),
    ]
    assert l1["sfp_hand"] == l2["sfp_hand"] == HAND_WRITTEN
    assert (l1["pin"], l1["sfp_reason"], row(found, "gw")["sfp_hand"]) == (None, None, None)
    said = ok(app.check_sfp_total(str(project), "gis01", l1["index"], "1G", "MM", 30))
    assert said == HAND_WRITTEN

    ok(app.set_sfp_count(str(project), "gis01", l1["index"], "1G", "MM", "spare", 1))

    assert counts(row(parts(project, store), "l1")["sfp"]) == [("1G", "MM", 24, 3, 27)]
    assert l1_cells(bom_sfps(substation)) == [27, 27]


def test_m87_an_unpinned_l1_on_hand_written_panels_shows_the_files_sfps_without_a_pin(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    """M86's sized L1 rows on hand-written panels: the files' numbers, and no Pin, which
    would change nothing the BOM prints."""
    from bomgen.app.parts import HAND_WRITTEN

    edit(substation, *UNPIN_L1)

    l1 = row(parts(project, store), "l1")

    assert l1["part_id"] is None
    assert counts(l1["sfp"]) == [("1G", "MM", 24, 3, 27)]
    assert (l1["pin"], l1["sfp_hand"]) == (None, HAND_WRITTEN)


def test_m87_a_switch_the_hand_written_files_do_not_place_says_so(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    from bomgen.app.parts import NOT_PLACED

    edit(substation, *UNPIN_L1)
    for name in ("psa1", "psa2"):
        panel = substation.parent / "panels" / f"{name}.yaml"
        text = panel.read_text(encoding="utf-8").replace(
            "RST2228-L1-24MM", "RST2228-L1-24MM.CISCO-MID"
        )
        panel.write_text(text, encoding="utf-8")

    l1 = row(parts(project, store), "l1")

    assert l1["pin"] is None
    assert (l1["sfp"], l1["sfp_reason"], l1["sfp_hand"]) == ([], NOT_PLACED, None)
