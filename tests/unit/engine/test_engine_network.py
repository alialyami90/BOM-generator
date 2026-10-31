"""Group C network and IO accessories (spec: Derivation rules -> Network accessories
(group C); Data model and generation order, step 3)."""

from typing import Any

import pytest
from engine_factories import device, library, panel, powered, sfp, switch

from bomgen.engine.errors import EngineError
from bomgen.engine.items import BomItem
from bomgen.engine.network import accessories
from bomgen.engine.units import expand_devices
from bomgen.models.bom import Group, QtySum
from bomgen.models.library import SfpChoice

PARTS = (
    switch("L2", "L2"),
    switch("L1", "L1"),
    powered("FW", "firewall", make="Fortigate", tag_type="FW", purdue_level="EXT"),
    device("FOPP", "patch_panel", tag_type="FOPP", tag_pattern="{prefix}-FOPP-CCR-{lan}01"),
    powered("RTAC", "rtac", tag_type="RTAC", tag_pattern="{prefix}-RTAC"),
    sfp("SFP-LX", "1G", "SM"),
    sfp("SFP-SX", "1G", "MM"),
    sfp("SFP-FX", "100M", "MM"),
    sfp("FR-SX", "1G", "MM", make="Fortigate"),
    device("CM", "cable_manager", tag_pattern="Cable Manager"),
    device("C607", "serial_cable", tag_pattern="COM-CABLE"),
)


def build(devices: list[dict[str, Any]], plans: dict[str, Any], **fields: Any) -> list[BomItem]:
    lib = library(*PARTS)
    p = panel(devices, port_plans=plans, **fields)
    return accessories(p, expand_devices(p, lib), lib)


def summary(items: list[BomItem]) -> list[tuple[str | None, Any, str | None]]:
    return [(i.line.tag, i.line.qty, i.line.part_id) for i in items]


def test_l2_switch_gets_sm_sfps_for_l3_uplinks() -> None:
    plans = {
        "L2": {
            "uplinks_l3": [{"count": 2, "speed": "1G", "media": "SM"}],
            "downlinks": [
                {"count": 15, "speed": "1G", "media": "MM"},
                {"count": 2, "speed": "100M", "media": "MM"},
            ],
        }
    }
    items = build([{"part_id": "L2"}], plans)
    assert summary(items) == [
        ("L2-ESW-A01 SFP (SM)", 2, "SFP-LX"),
        ("L2-ESW-A01 SFP (MM)", 15, "SFP-SX"),
        ("L2-ESW-A01 SFP (MM)", 2, "SFP-FX"),
        ("Cable Manager", 1, "CM"),
    ]
    assert all(i.line.group is Group.C for i in items)


def test_spare_ports_give_formula_quantity() -> None:
    plans = {"L1": {"uplinks": [{"count": 24, "speed": "1G", "media": "MM", "spare": 3}]}}
    (sfps, _managers) = build([{"part_id": "L1", "qty": 6}], plans)
    assert sfps.line.tag == "L1-ESW-A11 to A16 SFP (MM)"
    assert sfps.line.qty == QtySum(parts=(24, 3))


def test_sfp_choice_prefers_host_make() -> None:
    plans = {"FW": {"downlinks": [{"count": 2, "speed": "1G", "media": "MM"}]}}
    items = build([{"part_id": "FW"}], plans)
    assert summary(items) == [("EXT-FW-A SFP (MM)", 2, "FR-SX")]


def test_sfp_falls_back_to_library_order() -> None:
    plans = {"RTAC": {"downlinks": [{"count": 1, "speed": "1G", "media": "MM"}]}}
    (item,) = build([{"part_id": "RTAC"}], plans)
    assert item.line.part_id == "SFP-SX"


def test_one_host_with_one_part_twice_gets_one_row() -> None:
    plans = {
        "L2": {
            "uplinks": [{"count": 6, "speed": "1G", "media": "MM"}],
            "downlinks": [{"count": 2, "speed": "1G", "media": "MM"}],
        }
    }
    (item, _manager) = build([{"part_id": "L2"}], plans)
    assert item.line.qty == QtySum(parts=(6, 2))


def test_port_plan_by_tag_wins_over_part_id() -> None:
    plans = {
        "L2": {"downlinks": [{"count": 1, "speed": "1G", "media": "MM"}]},
        "PSA1-L2-ESW-A01": {"downlinks": [{"count": 4, "speed": "1G", "media": "MM"}]},
    }
    (item, _manager) = build([{"part_id": "L2"}], plans)
    assert item.line.qty == 4


def test_copper_ports_need_no_sfp() -> None:
    plans = {"L2": {"downlinks": [{"count": 4, "speed": "1G", "media": "RJ45"}]}}
    assert summary(build([{"part_id": "L2"}], plans)) == [("Cable Manager", 1, "CM")]


def test_missing_sfp_is_an_error() -> None:
    plans = {"L2": {"downlinks": [{"count": 1, "speed": "10G", "media": "SM"}]}}
    with pytest.raises(EngineError, match=r"PSA1-L2-ESW-A01.*10G SM"):
        build([{"part_id": "L2"}], plans)


def test_cable_managers_one_per_switch_and_patch_panel() -> None:
    # 001: FOPP + L2 + 6 x L1 = 8 here, plus the firewall, which gets none.
    devices: list[dict[str, Any]] = [
        {"part_id": "FOPP"},
        {"part_id": "L2"},
        {"part_id": "L1", "qty": 6},
        {"part_id": "FW"},
    ]
    (item,) = build(devices, {})
    assert (item.line.tag, item.line.qty, item.line.description) == ("Cable Manager", 8, "CM")


def test_no_cable_managers_without_switches() -> None:
    assert build([{"part_id": "RTAC"}], {}) == []


def test_serial_cables_one_per_used_rtac_port() -> None:
    (item,) = build([{"part_id": "RTAC"}], {"RTAC": {"serial_ports": 6}}, lan=None)
    assert (item.line.tag, item.line.qty, item.line.part_id) == ("COM-CABLE", 6, "C607")


def test_sfps_come_before_cable_managers_and_serial_cables() -> None:
    plans = {
        "RTAC": {"serial_ports": 2, "downlinks": [{"count": 1, "speed": "100M", "media": "MM"}]}
    }
    items = build([{"part_id": "L2"}, {"part_id": "RTAC"}], plans)
    assert [i.line.part_id for i in items] == ["SFP-FX", "CM", "C607"]


def test_one_sfp_part_serving_two_media_gets_one_row_per_media() -> None:
    # Review on #22: the SM uplinks must not disappear into an "SFP (MM)" row.
    combo = device(
        "SFP-COMBO",
        "sfp",
        make="Ruggedcom",
        ports=[
            {"count": 1, "speed": "1G", "media": "SM", "kind": "fixed"},
            {"count": 1, "speed": "1G", "media": "MM", "kind": "fixed"},
        ],
    )
    lib = library(switch("L2", "L2"), combo, device("CM", "cable_manager"))
    plans = {
        "L2": {
            "uplinks_l3": [{"count": 2, "speed": "1G", "media": "SM"}],
            "downlinks": [{"count": 15, "speed": "1G", "media": "MM"}],
        }
    }
    p = panel([{"part_id": "L2"}], port_plans=plans)
    items = accessories(p, expand_devices(p, lib), lib)
    assert summary(items)[:2] == [
        ("L2-ESW-A01 SFP (SM)", 2, "SFP-COMBO"),
        ("L2-ESW-A01 SFP (MM)", 15, "SFP-COMBO"),
    ]


def build_with_choice(choice: list[dict[str, str]], plans: dict[str, Any]) -> list[BomItem]:
    """As ``build`` with the L2 switch carrying an SFP choice, as a derived part does."""
    lib = library(*PARTS)
    devices = [
        d.model_copy(update={"sfp_choice": [SfpChoice.model_validate(c) for c in choice]})
        if d.part_id == "L2"
        else d
        for d in lib.devices
    ]
    lib = lib.model_copy(update={"devices": devices})
    p = panel([{"part_id": "L2"}], port_plans=plans)
    return accessories(p, expand_devices(p, lib), lib)


MM_DOWNLINKS = {
    "L2": {
        "downlinks": [
            {"count": 4, "speed": "1G", "media": "MM"},
            {"count": 2, "speed": "1G", "media": "SM"},
        ]
    }
}


def test_sfp_choice_replaces_the_automatic_pick() -> None:
    items = build_with_choice([{"speed": "1G", "media": "MM", "part_id": "FR-SX"}], MM_DOWNLINKS)
    assert summary(items)[:2] == [
        ("L2-ESW-A01 SFP (MM)", 4, "FR-SX"),
        ("L2-ESW-A01 SFP (SM)", 2, "SFP-LX"),
    ]


def test_sfp_choice_for_another_media_keeps_the_automatic_pick() -> None:
    items = build_with_choice([{"speed": "100M", "media": "MM", "part_id": "SFP-FX"}], MM_DOWNLINKS)
    assert [part for _tag, _qty, part in summary(items)[:2]] == ["SFP-SX", "SFP-LX"]


def test_an_sfp_choice_that_does_not_fit_the_ports_is_an_engine_error() -> None:
    choice = [{"speed": "1G", "media": "MM", "part_id": "SFP-FX"}]
    with pytest.raises(EngineError, match=r"^PSA1-L2-ESW-A01: SFP SFP-FX is not 1G MM$"):
        build_with_choice(choice, MM_DOWNLINKS)


def test_a_switch_without_a_cable_manager_adds_no_manager_row() -> None:
    devices: list[dict[str, Any]] = [
        {"part_id": "L2", "cable_manager": False},
        {"part_id": "L1", "qty": 2},
    ]
    (item,) = build(devices, {})
    assert item.line.qty == 2


def test_a_firewall_with_a_cable_manager_adds_a_manager_row() -> None:
    (item,) = build([{"part_id": "FW", "cable_manager": True}], {})
    assert (item.line.tag, item.line.qty) == ("Cable Manager", 1)
