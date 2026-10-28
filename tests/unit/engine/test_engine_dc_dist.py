"""Group F DC distribution (spec: Derivation rules -> DC distribution (group F),
Breaker part numbers; Data model and generation order, step 7)."""

from typing import Any

import pytest
from engine_factories import device, get, library, loose, panel, powered, switch

from bomgen.engine.dc_dist import (
    DcCircuits,
    branch_sizing,
    dc_distribution,
    single_fed_loads,
)
from bomgen.engine.errors import EngineError
from bomgen.engine.items import flatten
from bomgen.engine.units import expand_devices
from bomgen.models.bom import Group
from bomgen.models.calc import BranchSizing
from bomgen.models.project import DesignConstants

PARTS = (
    switch("L2", "L2", unit_power_w=77),
    switch("L1", "L1", unit_power_w=77),
    powered("FW", "firewall", tag_type="FW", purdue_level="EXT", alarm_on_branch_mcb=True),
    powered("BIG", "rtac", tag_type="RTAC", unit_power_w=200, min_branch_mcb_a=1),
    powered("MON", "monitor", tag_type="MONITOR", tag_pattern="{prefix}-MONITOR", power_supplies=1),
    powered("ANN", "annunciator", power_supplies=1, unit_power_w=100),
    device("FOPP", "patch_panel"),
)


def build(devices: list[dict[str, Any]], change_over: bool = False, **fields: Any) -> DcCircuits:
    lib = library(*PARTS)
    p = panel(devices, **fields)
    rows = expand_devices(p, lib)
    fed = single_fed_loads(p, rows, lib, [])
    return dc_distribution(p, lib, DesignConstants(), rows, fed, change_over)


def table(circuits: DcCircuits) -> list[tuple[Any, ...]]:
    lines = flatten(circuits.items)
    assert all(line.group is Group.F for line in lines)
    return [(line.tag, line.description, line.qty, line.hwio) for line in lines]


def test_one_branch_per_supply_on_each_feed_same_n() -> None:
    circuits = build([{"part_id": "L2"}, {"part_id": "FOPP"}, {"part_id": "L1", "qty": 2}])
    assert table(circuits) == [
        ("PSA1-Q1", "6A, 2P MCB For Main DC supply-1", 1, 0),
        ("PSA1-Q1.1", "2A, 2P MCB For L2_ESW_A01 PS1", 1, 0),
        ("PSA1-Q1.2", "2A, 2P MCB For L1_ESW_A11 PS1", 1, 0),
        ("PSA1-Q1.3", "2A, 2P MCB For L1_ESW_A12 PS1", 1, 0),
        ("PSA1-Q1.4", "2A, 2P MCB For SPARE", 1, 0),
        ("PSA1-Q2", "6A, 2P MCB For Main DC supply-2", 1, 0),
        ("PSA1-Q2.1", "2A, 2P MCB For L2_ESW_A01 PS2", 1, 0),
        ("PSA1-Q2.2", "2A, 2P MCB For L1_ESW_A11 PS2", 1, 0),
        ("PSA1-Q2.3", "2A, 2P MCB For L1_ESW_A12 PS2", 1, 0),
        ("PSA1-Q2.4", "2A, 2P MCB For SPARE", 1, 0),
        (None, "DC Auxiliary Contacts (For MCB Q1, Q2)", 2, 2),
    ]
    assert circuits.branches_per_feed == 4


def test_spare_branches_per_feed_is_a_panel_input() -> None:
    circuits = build([{"part_id": "L2"}], options={"dc_spare_branches_per_feed": 3})
    tags = [row[0] for row in table(circuits)]
    assert tags[:5] == ["PSA1-Q1", "PSA1-Q1.1", "PSA1-Q1.2", "PSA1-Q1.3", "PSA1-Q1.4"]
    assert circuits.branches_per_feed == 4


def test_branch_mcb_carries_1_3_times_the_running_current() -> None:
    # Q35 (a): 1.3 x 200 W / 125 V = 2.08 A -> next catalogue size 6 A.
    rows = table(build([{"part_id": "BIG"}]))
    assert rows[1][1] == "6A, 2P MCB For RTAC PS1"


def sized(mcb: dict[str, Any] | None = None, **fields: Any) -> BranchSizing:
    part = powered("DEV", "rtac", **fields)
    return branch_sizing(
        get(library(part, mcb=mcb), "DEV"), library(part, mcb=mcb), DesignConstants()
    )


C_CURVE = {"trip_curve": "C", "magnetic_trip_multiple": 5}


def test_branch_mcb_clears_inrush_on_c_curve() -> None:
    # Q35 (b): 12 A inrush / 5 = 2.4 A -> 6 A, though 10 W needs only 0.1 A.
    sizing = sized(C_CURVE, inrush_a=12)
    assert (sizing.rating_a, sizing.set_by) == (6, ("inrush",))
    assert sizing.inrush_need_a == pytest.approx(2.4)


def test_inrush_divides_by_the_catalogues_trip_multiple() -> None:
    # A D-curve set (10 x In) clears the same 12 A inrush at 2 A.
    sizing = sized({"trip_curve": "D", "magnetic_trip_multiple": 10}, inrush_a=12)
    assert sizing.rating_a == 2


def test_trip_multiple_defaults_to_the_curves_lower_bound() -> None:
    # A C-curve set without an explicit multiple trips from 5 x In.
    assert sized({"trip_curve": "C"}, inrush_a=12).trip_multiple == 5


def test_dc_trip_multiple_is_not_used() -> None:
    # Ali's rule divides by the set's (AC) multiple, C = 5, even on 125 V DC (ADR 0019).
    sizing = sized(C_CURVE | {"magnetic_trip_multiple_dc": 7}, inrush_a=12)
    assert (sizing.trip_multiple, sizing.rating_a) == (5, 6)


def test_inrush_without_a_trip_curve_is_not_sized_for() -> None:
    # The catalogue gives no magnetic threshold, so (b) cannot apply; the check warns.
    sizing = sized(None, inrush_a=12)
    assert (sizing.rating_a, sizing.trip_multiple, sizing.inrush_need_a) == (2, None, None)


def test_branch_mcb_floor_is_2a() -> None:
    # Q35 (c): 10 W needs 0.1 A and the catalogue has 1 A, but the floor is 2 A.
    sizing = sized(C_CURVE, min_branch_mcb_a=None)
    assert (sizing.rating_a, sizing.set_by, sizing.floor_a) == (2, ("floor",), 2)


def test_floor_is_a_design_constant() -> None:
    part = powered("DEV", "rtac")
    lib = library(part)
    sizing = branch_sizing(get(lib, "DEV"), lib, DesignConstants(min_branch_mcb_a=6))
    assert (sizing.rating_a, sizing.floor_a) == (6, 6)


def test_library_min_branch_mcb_a_no_longer_sets_the_rating() -> None:
    # The hand-typed floor is deprecated (Q35): read, reported, not used.
    sizing = sized(C_CURVE, min_branch_mcb_a=6)
    assert (sizing.rating_a, sizing.library_min_a) == (2, 6)


def test_every_condition_that_gives_the_rating_is_named() -> None:
    # 1.3 x 150 W / 125 V = 1.56 A, 8 A / 5 = 1.6 A and the 2 A floor all give 2 A.
    sizing = sized(C_CURVE, unit_power_w=150, inrush_a=8)
    assert (sizing.rating_a, sizing.set_by) == (2, ("running", "inrush", "floor"))
    assert sizing.running_a == pytest.approx(1.56)


def test_qcod_takes_the_same_rule() -> None:
    lib = library(*PARTS, powered("SF", "monitor", power_supplies=1, inrush_a=12), mcb=C_CURVE)
    p = panel([{"part_id": "L2"}, {"part_id": "SF"}])
    rows = expand_devices(p, lib)
    circuits = dc_distribution(
        p, lib, DesignConstants(), rows, single_fed_loads(p, rows, lib, []), True
    )
    assert [line.description for line in flatten(circuits.items) if "QCOD" in (line.tag or "")] == [
        "6A, 2P MCB For Monitor",
        "6A, 2P MCB For SPARE",
    ]


def test_branch_sizings_name_each_branch_mcb() -> None:
    circuits = build([{"part_id": "L2"}, {"part_id": "BIG"}], change_over=True)
    assert [(b.tag, b.rating_a, b.set_by) for b in circuits.branch_mcbs] == [
        ("PSA1-Q1.1", 2, ("floor",)),
        ("PSA1-Q1.2", 6, ("running",)),
        ("PSA1-Q2.1", 2, ("floor",)),
        ("PSA1-Q2.2", 6, ("running",)),
    ]


def test_main_mcb_is_next_size_above_design_current_minimum_6a() -> None:
    # 7 x 77 W x 1.3 / 125 V = 5.6 A -> 6 A; 9 x 77 W -> 7.2 A -> 10 A.
    assert build([{"part_id": "L1", "qty": 7}]).main_a == 6
    nine = build([{"part_id": "L1", "qty": 9}])
    assert nine.main_a == 10
    assert nine.design_current_a == pytest.approx(9 * 77 * 1.3 / 125)


def test_main_mcb_override_wins() -> None:
    circuits = build([{"part_id": "L2"}], options={"main_mcb_override_a": 16})
    assert table(circuits)[0][1] == "16A, 2P MCB For Main DC supply-1"
    assert (circuits.main_a, circuits.rule_main_a) == (16, 6)  # the check report flags it


def test_alarmed_branches_add_aux_contacts() -> None:
    rows = table(build([{"part_id": "L2"}, {"part_id": "FW"}]))
    assert rows[-1] == (None, "DC Auxiliary Contacts (For MCB Q1, Q2, Q1.2, Q2.2)", 4, 2)


def test_single_fed_load_goes_through_qcod_with_a_spare() -> None:
    rows = table(build([{"part_id": "L2"}, {"part_id": "MON"}], change_over=True))
    assert rows[-3:] == [
        ("PSA1-QCOD-1", "2A, 2P MCB For Monitor", 1, 0),
        ("PSA1-QCOD-2", "2A, 2P MCB For SPARE", 1, 0),
        (None, "DC Auxiliary Contacts (For MCB Q1, Q2)", 2, 2),
    ]
    assert "MONITOR" not in " ".join(r[1] for r in rows[:-3])


def test_loose_load_fed_from_the_panel_gets_a_qcod() -> None:
    lib = library(*PARTS)
    p = panel([{"part_id": "L2"}], id="psa3")
    rows = expand_devices(p, lib)
    fed = single_fed_loads(p, rows, lib, [loose("ANN", fed_from="psa3"), loose("ANN")])
    assert [f.name for f in fed] == ["Annunciator"]
    circuits = dc_distribution(p, lib, DesignConstants(), rows, fed, True)
    assert circuits.qcods == 2


def test_design_current_is_the_cabinets_own_dc_loads() -> None:
    # Power Consumption sheet: the loose annunciator is "External Equipment", so
    # cabinet 003's sum Q is ~1.5 A (DC distribution). Single-fed rows count.
    lib = library(*PARTS)
    p = panel([{"part_id": "L2"}, {"part_id": "MON"}], id="psa3")
    rows = expand_devices(p, lib)
    fed = single_fed_loads(p, rows, lib, [loose("ANN", fed_from="psa3")])
    circuits = dc_distribution(p, lib, DesignConstants(), rows, fed, True)
    assert circuits.design_current_a == pytest.approx((77 + 10) * 1.3 / 125)


def test_single_fed_load_without_change_over_is_an_error() -> None:
    with pytest.raises(EngineError, match="change-over"):
        build([{"part_id": "MON"}], change_over=False)


def test_console_aux_contacts_carry_no_hwio() -> None:
    rows = table(build([{"part_id": "L2"}], kind="console"))
    assert rows[-1][3] == 0


def test_no_dc_loads_no_group_f() -> None:
    assert build([{"part_id": "FOPP"}]).items == []
