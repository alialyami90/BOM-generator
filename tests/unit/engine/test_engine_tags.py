"""Tag naming (spec: Tag naming conventions; Data model and generation order, step 1)."""

from typing import Any

import pytest
from engine_factories import device, library, panel, powered, switch

from bomgen.engine.errors import EngineError
from bomgen.engine.units import DeviceRow, describe, expand_devices


def rows(
    *instances: dict[str, Any], lib_devices: tuple[dict[str, Any], ...] = (), **fields: Any
) -> tuple[DeviceRow, ...]:
    lib = library(*lib_devices)
    return expand_devices(panel(list(instances), **fields), lib)


SWITCHES = (
    switch("L2", "L2"),
    switch("L1", "L1"),
    switch("EXT", "EXT"),
    powered("FW", "firewall", tag_type="FW", purdue_level="EXT"),
    device("FOPP", "patch_panel", tag_type="FOPP", tag_pattern="{prefix}-FOPP-CCR-{lan}01"),
    powered("GW", "gateway", tag_type="GW", tag_pattern="{prefix}-DHPCC-GW-{lan_index}"),
)


def test_l2_switch_is_lan_letter_plus_01() -> None:
    (row,) = rows({"part_id": "L2"}, lib_devices=SWITCHES)
    assert row.tag == "PSA1-L2-ESW-A01"
    assert row.unit_tags == ("PSA1-L2-ESW-A01",)


def test_l1_switches_number_from_11_as_one_range_row() -> None:
    (row,) = rows({"part_id": "L1", "qty": 6}, lib_devices=SWITCHES)
    assert row.tag == "PSA1-L1-ESW-A11 to A16"
    assert row.unit_tags == tuple(f"PSA1-L1-ESW-A{n}" for n in range(11, 17))


def test_numbering_continues_across_rows_of_the_same_level() -> None:
    first, second = rows({"part_id": "L1", "qty": 2}, {"part_id": "L1"}, lib_devices=SWITCHES)
    assert first.tag == "PSA1-L1-ESW-A11 to A12"
    assert second.tag == "PSA1-L1-ESW-A13"


def test_first_nn_continues_a_range_from_another_panel() -> None:
    first, second = rows(
        {"part_id": "L1", "qty": 2, "first_nn": 13}, {"part_id": "L1"}, lib_devices=SWITCHES
    )
    assert first.tag == "PSA1-L1-ESW-A13 to A14"
    assert second.tag == "PSA1-L1-ESW-A15"


def test_first_nn_below_the_levels_first_number_is_an_error() -> None:
    with pytest.raises(EngineError, match="first_nn 5 is below 11"):
        rows({"part_id": "L1", "first_nn": 5}, lib_devices=SWITCHES)


def test_first_nn_below_the_running_count_is_an_error() -> None:
    with pytest.raises(EngineError, match="first_nn 12"):
        rows({"part_id": "L1", "qty": 2}, {"part_id": "L1", "first_nn": 12}, lib_devices=SWITCHES)


def test_ext_switch_and_firewall_take_lan_letter_only() -> None:
    ext, fw = rows({"part_id": "EXT"}, {"part_id": "FW"}, lib_devices=SWITCHES)
    assert ext.tag == "PSA1-EXT-ESW-A"
    assert fw.tag == "PSA1-EXT-FW-A"


def test_fopp_tag_pattern() -> None:
    (row,) = rows({"part_id": "FOPP"}, lib_devices=SWITCHES)
    assert row.tag == "PSA1-FOPP-CCR-A01"


def test_gateway_numbers_by_lan_index() -> None:
    (row_a,) = rows({"part_id": "GW"}, lib_devices=SWITCHES)
    (row_b,) = rows({"part_id": "GW"}, lib_devices=SWITCHES, lan="B", tag_prefix="PSA2")
    assert row_a.tag == "PSA1-DHPCC-GW-1"
    assert row_b.tag == "PSA2-DHPCC-GW-2"


def test_lan_b_swaps_letter_and_prefix() -> None:
    l2, l1 = rows(
        {"part_id": "L2"},
        {"part_id": "L1", "qty": 6},
        lib_devices=SWITCHES,
        lan="B",
        tag_prefix="PSA2",
    )
    assert l2.tag == "PSA2-L2-ESW-B01"
    assert l1.tag == "PSA2-L1-ESW-B11 to B16"


def test_fans_and_thermostats_number_units() -> None:
    fan, th = rows({"part_id": "FAN", "qty": 2}, {"part_id": "TH", "qty": 3})
    (th_ws,) = rows({"part_id": "TH"}, tag_prefix="WS")
    assert fan.tag == "PSA1-FAN-1,2"
    assert fan.unit_tags == ("PSA1-FAN-1", "PSA1-FAN-2")
    assert th.tag == "PSA1-TH-1,2,3"
    assert th_ws.tag == "WS-TH-1"


def test_type_code_without_level_is_prefix_and_type() -> None:
    (row,) = rows({"part_id": "GPS"}, lib_devices=(powered("GPS", "gps_clock", tag_type="GPS"),))
    assert row.tag == "PSA1-GPS"


def test_panel_tag_override_wins() -> None:
    (row,) = rows({"part_id": "L2", "tag": "PSA1-CORE-1"}, lib_devices=SWITCHES)
    assert row.tag == "PSA1-CORE-1"
    assert row.unit_tags == ("PSA1-CORE-1",)


def test_part_without_tag_type_has_no_tag() -> None:
    (row,) = rows({"part_id": "SPOOL"}, lib_devices=(device("SPOOL"),))
    assert row.tag is None
    assert row.unit_tags == (None,)


def test_literal_tag_pattern_is_used_as_is() -> None:
    (row,) = rows(
        {"part_id": "KBM"},
        lib_devices=(device("KBM", "peripheral", tag_pattern="Keyboard & Mouse"),),
    )
    assert row.tag == "Keyboard & Mouse"


def test_instance_lan_overrides_panel_lan() -> None:
    (row,) = rows({"part_id": "L2", "lan": "B"}, lib_devices=SWITCHES)
    assert row.tag == "PSA1-L2-ESW-B01"
    assert row.lan == "B"


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("LAN-{lan} switch ({level})", "LAN-A switch (L1)"),
        ("Protocol Gateway {purpose}", "Protocol Gateway for PCC"),
        ("Plain text", "Plain text"),
    ],
)
def test_description_fills_lan_level_purpose(template: str, expected: str) -> None:
    lib = library(switch("L1", "L1", description_template=template))
    l1 = lib.get("L1")
    assert l1 is not None
    assert describe(l1, "A", "for PCC") == expected


def test_ext_device_in_a_panel_without_lan_has_no_dangling_hyphen() -> None:
    (row,) = rows({"part_id": "EXT"}, lib_devices=SWITCHES, lan=None, tag_prefix="PSA3")
    assert row.tag == "PSA3-EXT-ESW"


def test_numbered_device_in_a_panel_without_lan_keeps_its_number() -> None:
    (row,) = rows({"part_id": "L2"}, lib_devices=SWITCHES, lan=None, tag_prefix="PSA3")
    assert row.tag == "PSA3-L2-ESW-01"
