"""Panel layout: rules R5-R8 of the substations and auto-layout design (ADR 0013)."""

from bomgen.engine.layout import (
    Layout,
    LayoutRules,
    Unit,
    auto_layout,
    fill,
    fill_lines,
    used_u,
)
from bomgen.models.substation import DeviceMove, PairMove, Side, UnitRef

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


def test_r5_blank_plate_between_neighbours() -> None:
    assert used_u([1, 2, 1], 1) == 6
    assert used_u([1], 1) == 1
    assert used_u([], 1) == 0


def test_r5_din_rail_parts_cost_nothing() -> None:
    assert used_u([1, 0, 1], 1) == 3


def test_r5_cable_manager_sits_under_its_switch() -> None:
    layout = fill([u("sw", 1, A, cm=1), u("gw", 1, A, rank=1)], RULES)
    assert layout.panels[0].used_u(RULES) == 4  # switch 1 + manager 1, gap 1, device 1
    assert layout.panels[0].blank_plates() == 1


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


def test_r8_fill_lines_count_the_gaps() -> None:
    layout = fill([u("a", 1, A), u("b", 1, A, h=2, rank=1), u("c", 1, A, rank=2)], RULES)
    assert fill_lines(layout, RULES) == ["Panel 1: 6 U / 32 U"]
