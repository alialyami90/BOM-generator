"""Group F DC distribution (spec: Derivation rules -> DC distribution (group F),
Breaker part numbers; Data model and generation order, step 7)."""

from typing import Any

import pytest
from engine_factories import device, library, loose, panel, powered, switch

from bomgen.engine.dc_dist import DcCircuits, dc_distribution, single_fed_loads
from bomgen.engine.errors import EngineError
from bomgen.engine.items import flatten
from bomgen.engine.units import expand_devices
from bomgen.models.bom import Group
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


def test_branch_rating_is_min_rating_or_current_with_margin() -> None:
    # 1.3 x 200 W / 125 V = 2.08 A -> 3 A -> next catalogue size 6 A (plan Q7).
    rows = table(build([{"part_id": "BIG"}]))
    assert rows[1][1] == "6A, 2P MCB For RTAC PS1"


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
