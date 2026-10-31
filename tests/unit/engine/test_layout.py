"""Panel layout: rules R5-R8 of the substations and auto-layout design (ADR 0013)."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from bomgen.engine.layout import (
    Layout,
    LayoutResult,
    LayoutRules,
    PanelFill,
    Unit,
    auto_layout,
    blank_plates,
    fill,
    fill_lines,
    l1_candidates,
    layout_preview,
    layout_substation,
    reconcile_panels_list,
    render_panel_yaml,
    used_u,
    waist_u,
    with_layout,
)
from bomgen.io.derived import derive_parts
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.library import Category, PurdueLevel
from bomgen.models.panel import Panel, PortAllocation
from bomgen.models.project import LayoutDefaults
from bomgen.models.substation import (
    DeviceMove,
    EquipmentRole,
    PairMove,
    Side,
    UnitRef,
)
from bomgen.models.substation import Layout as LayoutInputs

RULES = LayoutRules(capacity_u=32, blank_plate_u=1)
A, B, NONE = Side.A, Side.B, Side.NONE


def u(device: str, n: int, side: Side, h: int = 1, rank: int = 0, cm: int = 0) -> Unit:
    return Unit(device, n, side, part_id=device.upper(), rank=rank, height_u=h, cable_manager_u=cm)


def pair(device: str, n: int, h: int = 1, rank: int = 0, cm: int = 0) -> list[Unit]:
    return [u(device, n, A, h, rank, cm), u(device, n, B, h, rank, cm)]


def where(layout: Layout) -> dict[str, int]:
    """``device#n/side`` -> panel number."""
    return {f"{x.key}/{x.side.value}": p.number for p in layout.panels for x in p.units}


def kinds(layout: Layout) -> list[str]:
    return [issue.kind for issue in layout.issues]


def _stack(*blocks: tuple[int, int]) -> list[Unit]:
    """Units top to bottom from ``(height_u, cable_manager_u)`` pairs."""
    return [u(f"d{i}", 1, A, h, rank=i, cm=cm) for i, (h, cm) in enumerate(blocks)]


def test_r5_blank_plate_between_neighbours() -> None:
    assert used_u(_stack((1, 0), (2, 0), (1, 0)), 1) == 6
    assert used_u(_stack((1, 0)), 1) == 1
    assert used_u([], 1) == 0


def test_r5_din_rail_parts_cost_nothing() -> None:
    assert used_u(_stack((1, 0), (0, 0), (1, 0)), 1) == 3


def test_r5_cable_manager_needs_no_blank_plate_below_it() -> None:
    # switch + manager, then a device: the passive manager may touch it (Ali, M12)
    layout = fill([u("sw", 1, A, cm=1), u("gw", 1, A, rank=1)], RULES)
    assert layout.panels[0].used_u(RULES) == 3
    assert layout.panels[0].blank_plates() == 0


def test_r5_active_device_above_a_managed_switch_still_needs_a_plate() -> None:
    # gw over switch + manager: the switch's top touches the active gateway
    stack = _stack((1, 0), (1, 1))
    assert used_u(stack, 1) == 4
    assert blank_plates(stack) == 1


def test_r5_managed_blocks_stack_without_plates() -> None:
    # FOPP + manager, L2 + manager, L1 + manager, then a firewall: no plates at all
    stack = _stack((1, 1), (1, 1), (1, 1), (1, 0))
    assert used_u(stack, 1) == 7
    assert blank_plates(stack) == 0


def test_r5_din_rail_part_does_not_break_the_rule() -> None:
    # a DIN-rail part between two rack devices is not a rack neighbour
    assert blank_plates(_stack((1, 1), (0, 0), (1, 0))) == 0
    assert blank_plates(_stack((1, 0), (0, 0), (1, 0))) == 1


def test_r5_fill_stops_at_32u_and_opens_a_new_panel() -> None:
    units = [x for n in range(1, 18) for x in pair("sw", n)]  # 17 + 16 gaps = 33 > 32
    layout = fill(units, RULES)
    assert [len(p.units) for p in layout.panels] == [16, 16, 1, 1]
    assert [p.used_u(RULES) for p in layout.panels] == [31, 31, 1, 1]


def test_r5_exact_fit_stays_in_the_panel() -> None:
    units = [x for n in range(1, 12) for x in pair("io", n, h=2)]  # 22 + 10 = 32
    layout = fill(units, RULES)
    assert [p.used_u(RULES) for p in layout.panels] == [32, 32]


def test_r5_device_taller_than_capacity_is_reported() -> None:
    layout = fill([*pair("sw", 1), *pair("big", 1, h=40, rank=1), *pair("fw", 1, rank=2)], RULES)
    assert kinds(layout) == ["device-too-tall", "device-too-tall"]
    assert where(layout)["big#1/a"] == 3
    assert where(layout)["big#1/b"] == 4
    assert where(layout)["fw#1/a"] == 5  # the tall panel is full; the next unit opens a pair


def test_r6_a_units_odd_panels_b_units_even() -> None:
    units = [x for n in range(1, 21) for x in pair("sw", n)]
    layout = fill(units, RULES)
    for panel in layout.panels:
        expected = A if panel.number % 2 else B
        assert {x.side for x in panel.units} == {expected}
    for odd, even in zip(layout.panels[::2], layout.panels[1::2], strict=True):
        assert [x.key for x in odd.units] == [x.key for x in even.units]


def test_r6_lock_step_survives_a_one_sided_removal() -> None:
    units = [x for n in range(1, 17) for x in pair("sw", n)] + pair("gw", 1, rank=1)
    layout = auto_layout(units, RULES, removed=[UnitRef(device="sw", unit=3, side="b")])
    # Panel 2 has room for gw#1/b, but its partner gw#1/a does not fit in panel 1.
    assert where(layout)["gw#1/a"] == 3
    assert where(layout)["gw#1/b"] == 4


def test_r6_units_follow_group_order() -> None:
    units = [*pair("fw", 1, rank=3), *pair("l2", 1, rank=0), *pair("l1", 2, rank=1)]
    units += pair("l1", 1, rank=1)
    layout = fill(units, RULES)
    assert [x.key for x in layout.panels[0].units] == ["l2#1", "l1#1", "l1#2", "fw#1"]


def _thirteen_u_pair() -> list[Unit]:
    return [x for n in range(1, 8) for x in pair("sw", n)]  # 7 + 6 gaps = 13U each side


def test_r6_common_devices_go_to_most_free_panel() -> None:
    commons = [u("gps", 1, NONE, rank=1), u("rtac", 1, NONE, h=2, rank=2), u("io", 1, NONE, rank=3)]
    layout = fill([*_thirteen_u_pair(), *commons], RULES)
    assert where(layout)["gps#1/none"] == 1  # 19 free each: tie goes to panel 1
    assert where(layout)["rtac#1/none"] == 2  # 19 free vs 17
    assert where(layout)["io#1/none"] == 1  # 17 free vs 16


def test_r6_common_device_that_fits_nowhere_opens_a_new_pair() -> None:
    units = [x for n in range(1, 17) for x in pair("sw", n)]  # 31U each side
    layout = fill([*units, u("rtac", 1, NONE, h=2, rank=1)], RULES)
    assert where(layout)["rtac#1/none"] == 3
    assert [p.number for p in layout.panels] == [1, 2, 3]


def test_r6_only_common_devices_opens_one_pair_and_drops_empty_b() -> None:
    layout = fill([u("gps", 1, NONE)], RULES)
    assert [p.number for p in layout.panels] == [1]
    assert layout.issues == []
    spread = fill([u("gps", 1, NONE), u("io", 1, NONE, rank=1)], RULES)
    assert where(spread) == {"gps#1/none": 1, "io#1/none": 2}  # most free U


def test_r7_removed_unit_is_dropped_before_the_fill() -> None:
    commons = [u("gps", 1, NONE, rank=1), u("io", 1, NONE, rank=2)]
    kept = auto_layout([*_thirteen_u_pair(), *commons], RULES)
    assert where(kept)["io#1/none"] == 2
    dropped = auto_layout([*_thirteen_u_pair(), *commons], RULES, removed=[UnitRef(device="gps")])
    assert "gps#1/none" not in where(dropped)
    assert where(dropped)["io#1/none"] == 1


def test_r7_removal_by_side_keeps_the_partner() -> None:
    layout = auto_layout(pair("gw", 1), RULES, removed=[UnitRef(device="gw", side="a")])
    assert where(layout) == {"gw#1/b": 2}
    assert kinds(layout) == ["panel-empty"]


def test_r7_move_one_unit_to_another_panel() -> None:
    units = [*_thirteen_u_pair(), *pair("fw", 1, rank=1)]
    layout = auto_layout(units, RULES, moves=[DeviceMove(device="fw", side="a", panel=2)])
    assert where(layout)["fw#1/a"] == 2
    assert where(layout)["fw#1/b"] == 2
    assert layout.issues == []


def test_r7_move_a_pair_moves_both_sides() -> None:
    units = [*_thirteen_u_pair(), *pair("fw", 1, rank=1)]
    layout = auto_layout(units, RULES, moves=[PairMove(pair="fw", unit=1, panel=(3, 4))])
    assert (where(layout)["fw#1/a"], where(layout)["fw#1/b"]) == (3, 4)
    assert [p.number for p in layout.panels] == [1, 2, 3, 4]


def test_r7_move_without_unit_moves_every_unit() -> None:
    units = [*_thirteen_u_pair(), *pair("l1", 1, rank=1), *pair("l1", 2, rank=1)]
    layout = auto_layout(units, RULES, moves=[PairMove(pair="l1", panel=(4, 3))])
    assert {where(layout)[f"l1#{n}/a"] for n in (1, 2)} == {4}
    assert {where(layout)[f"l1#{n}/b"] for n in (1, 2)} == {3}


def test_r7_move_that_does_not_fit_is_reported_not_reflowed() -> None:
    full = [x for n in range(1, 17) for x in pair("sw", n)]  # 31U each side
    units = [*full, *pair("rtac", 1, h=2, rank=1)]
    before = where(fill(units, RULES))
    layout = auto_layout(units, RULES, moves=[DeviceMove(device="rtac", side="b", panel=2)])
    after = where(layout)
    assert after["rtac#1/b"] == 2
    assert kinds(layout) == ["move-does-not-fit"]  # panel 4 is left empty and dropped
    assert layout.issues[0].subject == "panel 2"
    assert {k: v for k, v in after.items() if not k.startswith("rtac")} == {
        k: v for k, v in before.items() if not k.startswith("rtac")
    }


def test_r7_stale_override_is_reported_and_ignored() -> None:
    units = [*pair("l1", 1), *pair("l1", 2)]
    layout = auto_layout(
        units,
        RULES,
        moves=[DeviceMove(device="l1", unit=3, side="a", panel=2)],
        removed=[UnitRef(device="gw")],
    )
    assert kinds(layout) == ["stale-removal", "stale-override"]
    assert all(not issue.is_error for issue in layout.issues)
    assert where(layout) == where(fill(units, RULES))


def test_r7_pair_move_of_a_single_entry_is_stale() -> None:
    units = [*pair("fw", 1), u("gps", 1, NONE, rank=1)]
    layout = auto_layout(units, RULES, moves=[PairMove(pair="gps", panel=(1, 2))])
    assert kinds(layout) == ["stale-override"]
    assert where(layout) == where(fill(units, RULES))


def test_r7_move_to_unknown_panel_is_reported() -> None:
    layout = auto_layout(pair("fw", 1), RULES, moves=[DeviceMove(device="fw", side="a", panel=9)])
    assert kinds(layout) == ["unknown-panel"]
    assert where(layout)["fw#1/a"] == 1


def test_r7_move_that_empties_a_panel_is_reported() -> None:
    units = [x for n in range(1, 17) for x in pair("sw", n)] + pair("fw", 1, rank=1)
    middle = auto_layout(
        [*units, *pair("gw", 1, rank=2)],
        RULES,
        moves=[PairMove(pair="fw", panel=(5, 6)), PairMove(pair="gw", panel=(5, 6))],
    )
    assert kinds(middle) == ["panel-empty", "panel-empty"]
    last = auto_layout(units, RULES, moves=[PairMove(pair="fw", panel=(1, 2))])
    assert [p.number for p in last.panels] == [1, 2]
    assert kinds(last) == ["move-does-not-fit", "move-does-not-fit"]


def test_r7_overrides_survive_a_rerun() -> None:
    units = [*_thirteen_u_pair(), *pair("fw", 1, rank=1), u("gps", 1, NONE, rank=2)]
    moves = [PairMove(pair="fw", panel=(3, 4))]
    assert auto_layout(units, RULES, moves=moves) == auto_layout(units, RULES, moves=moves)


def stack(layout: Layout, number: int) -> list[str]:
    """``device/side`` top to bottom in a panel."""
    return [f"{x.device}/{x.side.value}" for x in layout.panels[number - 1].units]


def _abc() -> list[Unit]:
    return [*pair("a", 1), *pair("b", 1, rank=1), *pair("c", 1, rank=2)]


def test_r7_position_orders_a_unit_within_its_panel() -> None:
    move = DeviceMove(device="c", side="a", panel=1, position=1)
    layout = auto_layout(_abc(), RULES, moves=[move])
    assert stack(layout, 1) == ["c/a", "a/a", "b/a"]
    assert stack(layout, 2) == ["a/b", "b/b", "c/b"]  # the B unit keeps the automatic order


def test_r7_pair_move_with_position_orders_both_sides() -> None:
    layout = auto_layout(_abc(), RULES, moves=[PairMove(pair="a", panel=(1, 2), position=2)])
    assert stack(layout, 1) == ["b/a", "a/a", "c/a"]
    assert stack(layout, 2) == ["b/b", "a/b", "c/b"]


def test_r7_position_counts_rack_devices_only() -> None:
    units = [*pair("a", 1), *pair("rail", 1, h=0, rank=1), *pair("b", 1, rank=2)]
    units += pair("c", 1, rank=3)
    move = DeviceMove(device="c", side="a", panel=1, position=2)
    rack = [x for x in stack(auto_layout(units, RULES, moves=[move]), 1) if x != "rail/a"]
    assert rack == ["a/a", "c/a", "b/a"]  # the DIN-rail part between a and b does not count


def test_r7_position_past_the_bottom_puts_it_last() -> None:
    move = DeviceMove(device="a", side="a", panel=1, position=9)
    layout = auto_layout(_abc(), RULES, moves=[move])
    assert stack(layout, 1) == ["b/a", "c/a", "a/a"]
    assert layout.issues == []


def test_r7_position_moves_a_unit_into_another_panel() -> None:
    units = [x for n in range(1, 17) for x in pair("sw", n)]  # 31U: panels 1 and 2
    units += [*pair("fw", 1, rank=1), *pair("gw", 1, rank=2)]  # panels 3 and 4
    move = DeviceMove(device="sw", unit=1, side="a", panel=3, position=1)
    layout = auto_layout(units, RULES, moves=[move])
    assert stack(layout, 3) == ["sw/a", "fw/a", "gw/a"]
    assert layout.panels[2].position(units[0]) == 1
    assert layout.panels[2].position(units[-2]) == 3


def test_r5_blank_plates_follow_the_pinned_order() -> None:
    # a switch with its manager above a firewall needs no plate; the other way round does
    units = [u("sw", 1, A, cm=1), u("fw", 1, A, rank=1)]
    assert fill(units, RULES).panels[0].used_u(RULES) == 3
    layout = auto_layout(units, RULES, moves=[DeviceMove(device="fw", panel=1, position=1)])
    assert stack(layout, 1) == ["fw/a", "sw/a"]
    assert layout.panels[0].used_u(RULES) == 4
    assert layout.panels[0].blank_plates() == 1


def test_r7_pin_to_the_automatic_place_stays_a_pin() -> None:
    units = [*pair("fw", 1), u("gps", 1, NONE, rank=1)]
    assert where(fill(units, RULES))["gps#1/none"] == 1  # the tie goes to panel 1
    pin = DeviceMove(device="gps", panel=1)
    layout = auto_layout(units, RULES, moves=[pin])
    assert where(layout) == where(fill(units, RULES))
    gps = units[-1]
    assert layout.panels[0].is_pinned(gps)
    assert not layout.panels[0].is_pinned(units[0])
    # A heavier A side would now send the GPS to panel 2; the pin holds it in panel 1.
    heavier = [*units, u("io", 1, A, h=5, rank=2)]
    assert where(fill(heavier, RULES))["gps#1/none"] == 2
    assert where(auto_layout(heavier, RULES, moves=[pin]))["gps#1/none"] == 1


def test_r7_a_later_move_without_position_drops_the_earlier_position() -> None:
    moves = [
        DeviceMove(device="c", side="a", panel=1, position=1),
        DeviceMove(device="c", side="a", panel=1),
    ]
    layout = auto_layout(_abc(), RULES, moves=moves)
    assert stack(layout, 1) == ["a/a", "b/a", "c/a"]
    assert layout.panels[0].is_pinned(_abc()[4])


def test_r8_fill_lines_count_the_gaps() -> None:
    layout = fill([u("a", 1, A), u("b", 1, A, h=2, rank=1), u("c", 1, A, rank=2)], RULES)
    assert fill_lines(layout, RULES) == ["Panel 1: 6 U / 32 U"]


# --- The substation adapter (R3, R4, R9) on the example substation ---------------------

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def with_changes(loaded: LoadedSubstation, **changes: Any) -> LoadedSubstation:
    """The loaded substation with top-level ``Substation`` fields replaced."""
    return replace(loaded, substation=loaded.substation.model_copy(update=changes))


def rows(panel: Panel) -> list[tuple[str, int, str | None, int | None]]:
    return [(d.part_id, d.qty, d.lan, d.first_nn) for d in panel.devices]


def test_r9_b_panels_are_written_in_full(example: LoadedSubstation) -> None:
    result = layout_substation(example)
    assert [p.id for p in result.panels] == ["psa1", "psa2"]
    first, second = result.panels
    assert all(p.generated for p in result.panels)
    assert (first.lan, second.lan) == ("A", "B")
    assert {d.lan for d in second.devices} <= {"B", None}
    assert [r[:2] for r in rows(first) if r[2]] == [r[:2] for r in rows(second) if r[2]]
    assert second.options.aux_socket_a == 10  # options_by_panel
    assert first.cabinet_number == "861-GIS01-PSA-0001"


def test_r9_l1_numbering_continues_across_panels(example: LoadedSubstation) -> None:
    many = with_changes(
        example, network=example.substation.network.model_copy(update={"ied_count": 19 * 14})
    )  # 14 L1 switches per side: they cannot all fit in panels 1 and 2
    result = layout_substation(many)
    l1 = [
        (p.number, r)
        for p in result.fills
        for r in rows(_panel_of(result, p.number))
        if r[0] == "RST2228-L1-24MM"
    ]
    in_first = next(r[1] for n, r in l1 if n == 1)
    later = next(r for n, r in l1 if n == 3)
    assert later[3] == 11 + in_first
    assert in_first + later[1] == 14


def _panel_of(result: LayoutResult, number: int) -> Panel:
    return result.panels[number - 1]


def test_r3_port_plans_sit_with_their_switches(example: LoadedSubstation) -> None:
    first, second = layout_substation(example).panels
    for panel in (first, second):
        l1 = panel.port_plans["RST2228-L1-24MM"]
        assert l1.uplinks == [PortAllocation(count=6, speed="1G", media="MM", spare=3)]
        l2 = panel.port_plans["RST2228-L2"]
        assert l2.uplinks_l3 == [PortAllocation(count=2, speed="1G", media="SM")]
        # 3 L1 links + ext-fw 1 + gw 1 + rtac 2 as 1G MM; the GPS on 100M MM
        assert l2.downlinks == [
            PortAllocation(count=7, speed="1G", media="MM"),
            PortAllocation(count=1, speed="100M", media="MM"),
        ]


def test_r4_generated_files_never_mention_ieds(example: LoadedSubstation) -> None:
    odd = with_changes(
        example, network=example.substation.network.model_copy(update={"ied_count": 37})
    )
    result = layout_substation(odd)
    for panel in result.panels:
        text = render_panel_yaml(panel).lower()
        assert "37" not in text
        assert "ied" not in text
    assert result.report.lines()[0] == "IED count: 37"


def test_r9_rendered_yaml_loads_back_as_the_same_panel(example: LoadedSubstation) -> None:
    for panel in layout_substation(example).panels:
        assert Panel.model_validate(yaml.safe_load(render_panel_yaml(panel))) == panel


def test_r7_manual_panels_are_left_alone(example: LoadedSubstation) -> None:
    result = layout_substation(example)
    assert "ws" not in {p.id for p in result.panels}
    assert "ws" in example.manual_panel_ids


def test_r7_pinned_position_survives_a_rebuild(example: LoadedSubstation) -> None:
    pin = LayoutInputs(overrides=[DeviceMove(device="gps", panel=1, position=1)])
    first = layout_preview(example, pin)
    assert first.fills[0].units[0].device == "gps"
    # More IEDs give more L1 switches; the GPS stays on top of panel 1.
    network = example.substation.network.model_copy(update={"ied_count": 60})
    bigger = with_changes(example, network=network)
    again = layout_preview(bigger, pin)
    assert again.plan.l1_per_side > first.plan.l1_per_side
    assert again.fills[0].units[0].device == "gps"
    assert again.fills[0].is_pinned(again.fills[0].units[0])


def test_r7_preview_overrides_replace_the_files_overrides(example: LoadedSubstation) -> None:
    inputs = LayoutInputs(overrides=[PairMove(pair="gw", panel=(3, 4))])
    result = layout_preview(example, inputs)
    assert [p.id for p in result.panels] == ["psa1", "psa2", "psa3", "psa4"]
    assert rows(result.panels[2]) == [("SEL-3555-GW", 1, "A", None)]
    assert example.substation.layout.overrides == []


def _l2_downlinks(result: LayoutResult, number: int) -> list[PortAllocation]:
    return _panel_of(result, number).port_plans["RST2228-L2"].downlinks


def test_r7_removed_units_free_their_l2_ports(example: LoadedSubstation) -> None:
    result = layout_preview(example, LayoutInputs(removed=[UnitRef(device="gw")]))
    assert result.plan.l2_demand_per_side == 7
    for number in (1, 2):  # 3 L1 links + ext-fw 1 + rtac 2; no gateway SFP
        assert _l2_downlinks(result, number)[0] == PortAllocation(count=6, speed="1G", media="MM")
    assert "7 of 16 usable ports" in result.report.port_lines[1]


def test_r7_removed_l1_switch_is_a_port_capacity_error(example: LoadedSubstation) -> None:
    removed = [UnitRef(device="l1", unit=3, side="a")]
    result = layout_preview(example, LayoutInputs(removed=removed))
    assert [(i.kind, i.subject) for i in result.report.issues if i.is_error][:1] == [
        ("port-capacity", "side A L1")
    ]
    assert _l2_downlinks(result, 1)[0].count == 6  # side A: 2 L1 links + 4
    assert _l2_downlinks(result, 2)[0].count == 7  # side B keeps its 3 L1 switches


def test_r7_removed_l2_switch_is_a_port_capacity_error(example: LoadedSubstation) -> None:
    removed = [UnitRef(device="l2", side="b")]
    result = layout_preview(example, LayoutInputs(removed=removed))
    issue = next(i for i in result.report.issues if i.kind == "port-capacity")
    assert issue.subject == "side B L2"
    assert issue.is_error


def test_r1_tool_picks_the_l1_model_unless_pinned(example: LoadedSubstation) -> None:
    equipment = [
        e.model_copy(update={"part_id": None}) if e.role is EquipmentRole.L1_SWITCH else e
        for e in example.substation.equipment
    ]
    result = layout_substation(with_changes(example, equipment=equipment))
    assert result.plan.l1_part_id == "RST2228-L1-24MM"
    l1_switches = [
        d.part_id
        for d in example.library.devices
        if d.category is Category.NETWORK_SWITCH and d.purdue_level is PurdueLevel.L1
    ]
    candidates = [c.ports.part_id for c in result.l1_candidates]
    assert candidates[0] == "RST2228-L1-24MM"
    assert sorted(candidates) == sorted(l1_switches)


def test_r5_missing_height_is_reported(example: LoadedSubstation) -> None:
    devices = [
        d.model_copy(update={"height_u": None}) if d.part_id == "SEL-2488" else d
        for d in example.library.devices
    ]
    library = example.library.model_copy(update={"devices": devices})
    result = layout_substation(replace(example, library=library))
    issue = next(i for i in result.report.issues if i.kind == "missing-height")
    assert "SEL-2488" in issue.message
    assert result.report.has_errors


def test_r9_build_keeps_hand_written_panels(example: LoadedSubstation) -> None:
    assert with_layout(example) == (example, None)


def test_r9_build_lays_out_generated_panels_again(example: LoadedSubstation) -> None:
    owned = replace(
        example,
        panels=tuple(
            p.model_copy(update={"generated": True}) if p.id == "psa1" else p
            for p in example.panels
        ),
    )
    rebuilt, report = with_layout(owned)
    assert [p.id for p in rebuilt.panels] == ["psa1", "psa2", "ws"]
    assert report is not None
    assert report.lines()[0] == "IED count: 40"
    # psa2 and psa3 are hand-written but listed in panels: the layout says it replaced them
    replaced = [(i.subject, i.is_error) for i in report.issues if i.kind == "replaced-panel"]
    assert replaced == [("psa2", False), ("psa3", False)]


SUBSTATION_YAML = """\
substation:
  id: s1
panels:  # the layout rewrites these
  - panels/psa1.yaml  # first
  - panels/old.yaml

manual_panels:
  - panels/ws.yaml
"""


def test_r9_panels_list_is_rewritten_with_its_comments() -> None:
    text = reconcile_panels_list(SUBSTATION_YAML, ["panels/psa1.yaml", "panels/psa2.yaml"])
    assert text == SUBSTATION_YAML.replace(
        "  - panels/psa1.yaml  # first\n  - panels/old.yaml\n",
        "  - panels/psa1.yaml\n  - panels/psa2.yaml\n",
    )


def test_r9_panels_flow_list_and_missing_list_become_block_lists() -> None:
    flow = "substation: {id: s1}\npanels: [a.yaml]\nlayout: {}\n"
    assert reconcile_panels_list(flow, ["b.yaml"]) == (
        "substation: {id: s1}\npanels:\n  - b.yaml\nlayout: {}\n"
    )
    flush = "panels:\n- a.yaml\n- c.yaml\nlayout: {}\n"
    assert reconcile_panels_list(flush, ["b.yaml"]) == "panels:\n- b.yaml\nlayout: {}\n"
    assert reconcile_panels_list("substation: {id: s1}", ["b.yaml"]) == (
        "substation: {id: s1}\npanels:\n  - b.yaml\n"
    )


def test_r9_loose_material_on_a_panel_the_layout_drops_is_reported(
    example: LoadedSubstation,
) -> None:
    result = layout_substation(example)  # the example feeds the annunciator from psa3
    issue = next(i for i in result.report.issues if i.kind == "missing-panel")
    assert issue.subject == "loose_material.items[0].fed_from"
    assert "'psa3'" in issue.message
    assert issue.is_error


def with_entry(loaded: LoadedSubstation, device: str, **fields: Any) -> LoadedSubstation:
    """The example with equipment ``device`` changed and its derived part in the library."""
    equipment = [
        e.model_validate({**e.model_dump(exclude_unset=True), **fields}) if e.id == device else e
        for e in loaded.substation.equipment
    ]
    substation = loaded.substation.model_copy(update={"equipment": equipment})
    library, problems = derive_parts(loaded.library, substation)
    assert problems == []
    return replace(loaded, substation=substation, library=library)


def test_override_height_moves_the_layout(example: LoadedSubstation) -> None:
    result = layout_preview(with_entry(example, "gw", overrides={"height_u": 10}))
    gw = [x for fill in result.fills for x in fill.units if x.device == "gw"]
    assert {x.height_u for x in gw} == {10}
    gw_rows = [d for p in result.panels for d in p.devices if d.part_id.startswith("SEL-3555-GW")]
    assert {d.part_id for d in gw_rows} == {"SEL-3555-GW+gw"}


def test_l1_ranking_ignores_derived_parts(example: LoadedSubstation) -> None:
    candidates = l1_candidates(with_entry(example, "l1", ordering_code="L1-CODE"))
    assert candidates
    assert not [c for c in candidates if "+" in c.ports.part_id]


def test_an_l1_override_applies_to_the_sized_switch(example: LoadedSubstation) -> None:
    result = layout_preview(with_entry(example, "l1", overrides={"unit_power_w": 50}))
    l1_rows = [d.part_id for p in result.panels for d in p.devices if "L1" in d.part_id]
    assert l1_rows
    assert set(l1_rows) == {"RST2228-L1-24MM+l1"}
    assert result.plan.l1_part_id == "RST2228-L1-24MM+l1"


def test_time_server_stacks_above_network_in_a_panel() -> None:
    gw = replace(u("gw", 1, NONE, rank=0), priority=2)
    gps = replace(u("gps", 1, NONE, rank=1), priority=1)
    assert [x.device for x in PanelFill(1, [gw, gps]).stack()] == ["gps", "gw"]


def test_priority_ties_keep_equipment_order() -> None:
    late = replace(u("late", 1, NONE, rank=1), priority=2)
    early = replace(u("early", 1, NONE, rank=0), priority=2)
    assert [x.device for x in PanelFill(1, [late, early]).stack()] == ["early", "late"]


def test_priority_does_not_choose_the_panel() -> None:
    units = [*pair("sw", 1, h=20, rank=0), *pair("gps", 1, h=20, rank=1)]
    ranked = [replace(x, priority=1) if x.device == "gps" else x for x in units]
    assert where(fill(ranked, RULES)) == where(fill(units, RULES))


def test_units_carry_priority_and_waist_from_the_category(example: LoadedSubstation) -> None:
    units = {x.device: x for f in layout_preview(example).fills for x in f.units}
    assert (units["gps"].priority, units["rtac"].priority, units["l2"].priority) == (1, 4, 2)
    assert not any(x.waist for x in units.values())


WAIST_RULES = LayoutRules(capacity_u=32, blank_plate_u=1, waist_u=18)


def kvm(rank: int, device: str = "kvm", h: int = 1) -> Unit:
    return replace(u(device, 1, NONE, h=h, rank=rank), waist=True)


def tops(panel: PanelFill, rules: LayoutRules = WAIST_RULES) -> dict[str, int] | None:
    placed = panel.place(rules)
    return None if placed is None else {x.device: top for x, top in placed.items()}


def test_waist_u_from_the_project_heights() -> None:
    assert waist_u(LayoutDefaults()) == 18
    assert waist_u(LayoutDefaults(waist_height_mm=1100, rack_start_mm=100)) == 22


def test_units_stack_from_the_top_without_a_kvm() -> None:
    panel = PanelFill(1, [u("a", 1, NONE, rank=0), u("b", 1, NONE, h=2, rank=1)])
    assert tops(panel) == {"a": 32, "b": 30}


def test_kvm_bottom_sits_at_waist_height() -> None:
    panel = PanelFill(1, [replace(u("sw", 1, NONE, h=2, rank=0), priority=2), kvm(rank=1)])
    assert tops(panel) == {"sw": 32, "kvm": 18}
    assert panel.top_u(panel.units[1], WAIST_RULES) == 18


def test_units_that_do_not_fit_above_the_kvm_go_below_it() -> None:
    panel = PanelFill(1, [*(u(f"d{i:02}", 1, NONE, rank=i) for i in range(13)), kvm(rank=13)])
    assert tops(panel) == {
        **{f"d{i:02}": 32 - 2 * i for i in range(7)},
        "kvm": 18,
        **{f"d{i:02}": 16 - 2 * (i - 7) for i in range(7, 13)},
    }


def test_a_console_stacks_above_the_kvm_at_waist_height() -> None:
    panel = PanelFill(1, [kvm(rank=0), kvm(rank=1, device="console")])
    assert tops(panel) == {"kvm": 18, "console": 20}


def test_a_panel_that_overflows_below_the_kvm_does_not_fit() -> None:
    tall = [u(f"t{i}", 1, NONE, h=10, rank=i) for i in range(3)]
    panel = PanelFill(1, [*tall[:2], kvm(rank=3)])
    assert tops(panel) == {"t0": 32, "kvm": 18, "t1": 16}
    assert not panel.fits(tall[2], WAIST_RULES)
    assert PanelFill(1, [*tall, kvm(rank=3)]).place(WAIST_RULES) is None


def test_a_pinned_kvm_ignores_waist_height() -> None:
    unit = kvm(rank=1)
    panel = PanelFill(1, [u("a", 1, NONE, rank=0), unit], pins={unit: 1})
    assert tops(panel) == {"kvm": 32, "a": 30}
