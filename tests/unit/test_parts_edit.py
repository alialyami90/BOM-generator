"""Parts page writers (plan M23, ADR 0024)."""

import shutil
from pathlib import Path

import pytest

from bomgen.io import fields, parts_edit
from bomgen.io.edit import EditError
from bomgen.io.loader import load_project
from bomgen.models.substation import Equipment

EXAMPLES = Path(__file__).parents[2] / "examples"
GPS, L2, L1, GW = 6, 1, 2, 4  # the example's equipment rows


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "jfgp2")
    return tmp_path / "jfgp2" / "project.yaml"


def substation_yaml(project: Path) -> Path:
    return project.parent / "substations" / "gis01" / "substation.yaml"


def text(project: Path) -> str:
    """The substation file with runs of spaces closed up: a rewritten flow mapping moves
    its end-of-line comment's column, which changes nothing the file says."""
    return " ".join(substation_yaml(project).read_text(encoding="utf-8").split())


def equipment(project: Path) -> tuple[Equipment, ...]:
    (target,) = load_project(project).substations
    return tuple(target.substation.equipment)


def test_an_override_is_written_on_its_row(project: Path) -> None:
    assert parts_edit.set_override(project, "gis01", GPS, "unit_power_w", "60").written

    overrides = equipment(project)[GPS].overrides
    assert overrides is not None
    assert overrides.values() == {"unit_power_w": 60}


def test_an_override_equal_to_the_library_value_is_not_written(project: Path) -> None:
    before = text(project)

    parts_edit.set_override(project, "gis01", GPS, "unit_power_w", 50)  # SEL-2488 is 50 W

    assert text(project) == before


def test_typing_the_library_value_back_removes_the_override(project: Path) -> None:
    before = text(project)
    assert parts_edit.set_override(project, "gis01", GPS, "unit_power_w", 60).written

    assert parts_edit.set_override(project, "gis01", GPS, "unit_power_w", "50").written

    assert equipment(project)[GPS].overrides is None
    assert text(project) == before


def test_removing_the_last_override_removes_the_overrides_mapping(project: Path) -> None:
    before = text(project)
    parts_edit.set_override(project, "gis01", GPS, "unit_power_w", 60)
    parts_edit.set_override(project, "gis01", GPS, "height_u", 2)

    parts_edit.set_override(project, "gis01", GPS, "unit_power_w", None)
    assert equipment(project)[GPS].overrides.values() == {"height_u": 2}  # type: ignore[union-attr]
    parts_edit.set_override(project, "gis01", GPS, "height_u", None)

    assert equipment(project)[GPS].overrides is None
    assert text(project) == before


def test_an_override_on_a_sized_switch_without_a_part_is_refused(project: Path) -> None:
    assert fields.remove_field(project, ("equipment", L1, "part_id"), substation="gis01").written

    result = parts_edit.set_override(project, "gis01", L1, "unit_power_w", 30)

    assert not result.written
    assert any("pick the switch to override its data" in i.message for i in result.issues)


def test_an_override_that_breaks_a_library_rule_is_refused_with_its_sentence(
    project: Path,
) -> None:
    result = parts_edit.set_override(project, "gis01", GPS, "supply_type", "VAC")  # 2 supplies

    assert not result.written
    assert result.issues


def test_an_unknown_override_field_is_an_edit_error(project: Path) -> None:
    with pytest.raises(EditError):
        parts_edit.set_override(project, "gis01", GPS, "colour", "red")


def test_an_sfp_choice_replaces_the_automatic_pick_for_its_speed_and_media(
    project: Path,
) -> None:
    library = load_project(project).library
    sfp = next(
        d.part_id
        for d in library.devices
        if d.category == "sfp" and any(p.speed == "1G" and p.media == "MM" for p in d.ports)
    )

    assert parts_edit.set_sfp_choice(project, "gis01", L1, "1G", "MM", sfp).written

    choices = equipment(project)[L1].sfp
    assert [(c.speed.value, c.media.value, c.part_id) for c in choices] == [("1G", "MM", sfp)]


def test_clearing_the_last_sfp_choice_removes_sfp(project: Path) -> None:
    before = text(project)
    library = load_project(project).library
    sfp = next(d.part_id for d in library.devices if d.category == "sfp")
    parts_edit.set_sfp_choice(project, "gis01", L1, "1G", "MM", sfp)

    assert parts_edit.set_sfp_choice(project, "gis01", L1, "1G", "MM", None).written

    assert text(project) == before


def test_changing_the_part_clears_its_overrides_sfp_choices_and_part_number(
    project: Path,
) -> None:
    parts_edit.set_override(project, "gis01", GW, "unit_power_w", 99)
    fields.set_field(project, ("equipment", GW, "ordering_code"), "GW-1", substation="gis01")
    other = next(
        d.part_id
        for d in load_project(project).library.devices
        if d.category == "gateway" and d.part_id != "SEL-3555-GW"
    )

    result, cleared = parts_edit.set_equipment_part(project, "gis01", GW, other)

    assert result.written
    assert cleared == ("overrides", "ordering_code")
    row = equipment(project)[GW]
    assert (row.part_id, row.overrides, row.ordering_code) == (other, None, None)


def test_picking_the_same_part_writes_nothing(project: Path) -> None:
    result, cleared = parts_edit.set_equipment_part(project, "gis01", GW, "SEL-3555-GW")

    assert (result.written, cleared) == (False, ())


def test_moving_a_row_keeps_its_id(project: Path) -> None:
    assert fields.move_item(project, ("equipment",), GPS, 0, substation="gis01").written

    ids = [e.id for e in equipment(project)]
    assert ids[0] == "gps"
    assert len(ids) == 9


def empty(project: Path) -> None:
    assert fields.remove_field(project, ("equipment",), substation="gis01").written


def test_start_parts_writes_the_picked_rows_and_the_sized_l1_together(project: Path) -> None:
    empty(project)
    rows: list[dict[str, object]] = [
        {"role": "time_server", "part_id": "SEL-2488"},
        {"role": "l2_switch", "part_id": "RST2228-L2", "redundant": True},
        {"role": "operator_ws", "part_id": ""},  # not picked: dropped
    ]

    assert parts_edit.start_parts(project, "gis01", rows).written

    found = [(e.id, e.role.value, e.part_id) for e in equipment(project)]
    assert found == [
        ("gps", "time_server", "SEL-2488"),
        ("l2", "l2_switch", "RST2228-L2"),
        ("l1", "l1_switch", None),
    ]


def test_start_parts_without_an_l2_switch_is_refused(project: Path) -> None:
    empty(project)

    with pytest.raises(EditError, match="Pick the L2 switch first"):
        parts_edit.start_parts(project, "gis01", [{"role": "time_server", "part_id": "SEL-2488"}])


def test_start_parts_on_a_substation_with_equipment_is_refused(project: Path) -> None:
    with pytest.raises(EditError, match="already has equipment"):
        parts_edit.start_parts(project, "gis01", [{"role": "l2_switch", "part_id": "RST2228-L2"}])


def test_turning_the_cable_manager_off_writes_false(project: Path) -> None:
    assert parts_edit.set_cable_manager(project, "gis01", L2, False).written

    assert equipment(project)[L2].cable_manager is False


def test_turning_it_back_to_the_category_default_removes_the_key(project: Path) -> None:
    before = text(project)
    parts_edit.set_cable_manager(project, "gis01", L2, False)

    assert parts_edit.set_cable_manager(project, "gis01", L2, True).written

    assert equipment(project)[L2].cable_manager is None
    assert text(project) == before


def test_a_gateway_gets_a_cable_manager_only_when_asked(project: Path) -> None:
    before = text(project)
    parts_edit.set_cable_manager(project, "gis01", GW, False)  # its default: nothing to write
    assert text(project) == before

    assert parts_edit.set_cable_manager(project, "gis01", GW, True).written

    assert equipment(project)[GW].cable_manager is True


def test_a_sized_l1_without_a_part_takes_the_switch_default(project: Path) -> None:
    assert fields.remove_field(project, ("equipment", L1, "part_id"), substation="gis01").written

    assert parts_edit.set_cable_manager(project, "gis01", L1, False).written

    assert equipment(project)[L1].cable_manager is False


# M31 (design note 2026-10-31, ENG-3): a new row's L2 link and own SFPs, seeded by the
# library part's category so a fresh project gets its network accessories.

FW = 5  # the example's ext-fw row (FGR-60F, two 1G SFP slots)


def started(project: Path) -> dict[str, Equipment]:
    empty(project)
    rows: list[dict[str, object]] = [
        {"role": "l2_switch", "part_id": "RST2228-L2", "redundant": True},
        {"role": "other", "part_id": "SEL-3555-GW", "redundant": True},
        {"role": "firewall", "part_id": "FGR-60F", "redundant": True},
        {"role": "time_server", "part_id": "SEL-2488"},
        {"role": "other", "part_id": "SEL-3555-RTAC"},
        {"role": "da_server", "part_id": "SEL-3355"},
        {"role": "other", "part_id": "SEL-2240"},
    ]
    assert parts_edit.start_parts(project, "gis01", rows).written
    return {e.part_id or e.id: e for e in equipment(project)}


def link(row: Equipment) -> tuple[int, str]:
    return row.l2_ports, row.l2_speed.value


def test_start_parts_seeds_each_networked_rows_l2_link_by_category(project: Path) -> None:
    rows = started(project)
    assert link(rows["SEL-3555-GW"]) == (1, "1G")
    assert link(rows["FGR-60F"]) == (1, "1G")
    assert link(rows["SEL-2488"]) == (1, "100M")
    assert link(rows["SEL-3555-RTAC"]) == (2, "1G")
    assert link(rows["SEL-3355"]) == (1, "1G")


def test_rows_without_an_l2_link_are_not_seeded(project: Path) -> None:
    rows = started(project)
    assert rows["SEL-2240"].l2_ports == 0  # I/O chassis
    assert rows["RST2228-L2"].l2_ports == 0  # the switches are sized, not linked
    assert "l2_ports" not in text(project).split("SEL-2240")[1].split("}")[0]


def test_a_firewalls_own_sfps_follow_its_sfp_slots(project: Path) -> None:
    plan = started(project)["FGR-60F"].port_plan
    assert plan is not None
    assert [(a.count, a.speed.value, a.media.value) for a in plan.downlinks] == [(2, "1G", "MM")]


def test_the_rtac_com_ports_stay_for_the_engineer_to_enter(project: Path) -> None:
    assert started(project)["SEL-3555-RTAC"].port_plan is None


def test_a_new_part_reseeds_a_link_still_at_the_old_parts_defaults(project: Path) -> None:
    rows = started(project)
    index = list(rows).index("FGR-60F")
    parts_edit.set_equipment_part(project, "gis01", index, "FGR-60F.CISCO-LOW")  # RJ45 only
    row = equipment(project)[index]
    assert (link(row), row.port_plan) == ((1, "1G"), None)


def test_a_new_part_keeps_a_link_the_engineer_changed(project: Path) -> None:
    fields.set_field(project, ("equipment", GW, "l2_ports"), 3, substation="gis01")
    other = "SEL-3555-GW.SIEMENS-LOW"
    parts_edit.set_equipment_part(project, "gis01", GW, other)
    assert equipment(project)[GW].l2_ports == 3


def test_an_added_row_gets_the_defaults_for_the_fields_it_leaves_out() -> None:
    lib = load_project(EXAMPLES / "project.yaml").library
    row = {"id": "gw-2", "role": "other", "part_id": "SEL-3555-GW", "l2_speed": "100M"}
    assert parts_edit.with_link_defaults(row, lib) == {**row, "l2_ports": 1}


def test_a_firewall_with_many_sfp_slots_is_seeded_two_sfps() -> None:
    # A1, 2026-11-01: min(2, the part's SFP slots); FGR-60F.CISCO-HIGH has 10 slots.
    lib = load_project(EXAMPLES / "project.yaml").library
    seeded = parts_edit.link_defaults(lib.get("FGR-60F.CISCO-HIGH"), "firewall")
    assert seeded["port_plan"] == {"downlinks": [{"count": 2, "speed": "1G", "media": "MM"}]}
