"""Group G terminal strips (spec: Derivation rules -> Terminal block quantities (group G);
Tag naming conventions, circuit and strip codes; Data model and generation order, step 8)."""

from typing import Any

import pytest
from engine_factories import device, library, panel, powered

from bomgen.engine.errors import EngineError
from bomgen.engine.items import flatten
from bomgen.engine.terminals import StripInputs, terminal_strips
from bomgen.engine.units import expand_devices
from bomgen.models.bom import Group
from bomgen.models.library import Library
from bomgen.models.panel import Ventilation

SWITCH = powered("SW", "network_switch", tag_type="ESW", purdue_level="L2")


def lib() -> Library:
    return library(SWITCH)


def inputs(**fields: Any) -> StripInputs:
    values: dict[str, Any] = {
        "ventilation": Ventilation.FORCED,
        "ac_mcbs": 6,
        "dc_branches_per_feed": 13,
        "change_over": False,
        "annunciator_feeds": 0,
        "xdin_default": 0,
    }
    return StripInputs(**(values | fields))


def strips(strip_inputs: StripInputs, **fields: Any) -> dict[str, object]:
    p = panel([{"part_id": "SW"}], **fields)
    library_ = lib()
    lines = flatten(terminal_strips(p, library_, expand_devices(p, library_), strip_inputs))
    assert all(line.group is Group.G for line in lines)
    return {str(line.tag).removeprefix(f"{p.tag_prefix}-"): line.qty for line in lines}


def test_network_cabinet_001() -> None:
    assert strips(inputs(), options={"inter_panel_terminals": 40}) == {
        "X-AC": 6,
        "X3-AC": 12,
        "TBL": 4,
        "THF": 12,
        "XSD": 4,
        "X-DC1": 6,
        "X-DC2": 6,
        "X4-DC1": 32,
        "X4-DC2": 32,
        "XIP": 40,
    }


def test_x3_ac_is_two_per_ac_mcb_including_cinc() -> None:
    assert strips(inputs(ac_mcbs=7))["X3-AC"] == 14


def test_x4_dc_is_two_per_branch_plus_one_rounded_in_network_cabinets() -> None:
    assert strips(inputs(dc_branches_per_feed=4))["X4-DC1"] == 16
    control = strips(inputs(dc_branches_per_feed=4), kind="control")
    assert (control["X4-DC1"], control["X4-DC2"]) == (10, 10)


def test_socket_adds_xps() -> None:
    assert strips(inputs(), options={"aux_socket_a": 10})["XPS"] == 4


def test_no_smoke_detector_no_xsd() -> None:
    assert "XSD" not in strips(inputs(), options={"smoke_detector": False})


def test_change_over_and_annunciator_strips() -> None:
    result = strips(inputs(change_over=True, annunciator_feeds=1), kind="control")
    assert (result["X4-COD"], result["X-ANN"]) == (8, 4)


def test_console_fixed_strips_and_xip_block() -> None:
    p = panel(
        [{"part_id": "SW"}], kind="console", tag_prefix="WS", options={"inter_panel_terminals": 12}
    )
    library_ = lib()
    strip_inputs = inputs(
        ventilation=Ventilation.NATURAL, ac_mcbs=4, dc_branches_per_feed=2, change_over=True
    )
    lines = flatten(terminal_strips(p, library_, expand_devices(p, library_), strip_inputs))
    assert {(x.tag, x.qty, x.model) for x in lines} >= {
        ("WS-X-AC", 4, "UT-16"),
        ("WS-X3-AC", 8, "UT-2.5-MTD"),
        ("WS-X-DC1", 4, "UT-16"),
        ("WS-X4-DC1", 6, "UT-2.5-MTD"),
        ("WS-THF", 5, "UT-2.5-MTD"),
        ("WS-X4-COD", 6, "UT-2.5-MTD"),
        ("WS-XIP", 12, "UT-2.5-MTD"),
    }


def test_strip_rows_carry_block_make_model_and_code() -> None:
    p = panel([{"part_id": "SW"}])
    library_ = lib()
    first = terminal_strips(p, library_, expand_devices(p, library_), inputs())[0].line
    assert (first.tag, first.description, first.make, first.model, first.ordering_code) == (
        "PSA1-X-AC",
        "Terminal Blocks For AC Input Circuits",
        "Phoenix",
        "UT-16",
        "3044199",
    )


def test_terminal_override_wins() -> None:
    assert strips(inputs(), options={"terminal_overrides": {"THF": 10}})["THF"] == 10


def test_override_of_a_missing_strip_is_an_error() -> None:
    with pytest.raises(EngineError, match="XYZ"):
        strips(inputs(), options={"terminal_overrides": {"XYZ": 1}})


RTAC = powered(
    "RTAC",
    "rtac",
    tag_type="RTAC",
    tag_pattern="{prefix}-RTAC",
    terminals=[
        {
            "strip": "XRTAC-C{n}",
            "block": "UT-2.5-MT",
            "count": 5,
            "per": "serial_port",
            "description": "Terminal Blocks for RTAC COM Port",
        }
    ],
)
DI_MODULE = device(
    "DI",
    terminals=[
        {
            "strip": "XDIP{slot}",
            "block": "UT-2.5-MT",
            "count": 58,
            "first_slot": "D",
            "description": 'Knife Disconnect Terminal Blocks For Axion "{slot} Slot" (DI)',
        }
    ],
)
CHASSIS = powered(
    "AXION",
    "io_chassis",
    tag_type="HWIO",
    tag_pattern="{prefix}-HWIO",
    children=[{"part_id": "DI", "qty": 4}],
)


def device_strips(xdin_default: int = 40, **options: Any) -> list[tuple[object, ...]]:
    p = panel(
        [{"part_id": "RTAC"}, {"part_id": "AXION"}],
        kind="control",
        tag_prefix="PSA3",
        port_plans={"RTAC": {"serial_ports": 6}},
        options=options,
    )
    library_ = library(RTAC, DI_MODULE, CHASSIS)
    rows = expand_devices(p, library_)
    lines = flatten(terminal_strips(p, library_, rows, inputs(xdin_default=xdin_default)))
    return [(x.tag, x.description, x.qty, x.model) for x in lines]


def test_di_module_adds_one_58_way_strip_per_slot_from_first_slot() -> None:
    di = [x for x in device_strips() if str(x[0]).startswith("PSA3-XDIP")]
    assert di == [
        (
            f"PSA3-XDIP{slot}",
            f'Knife Disconnect Terminal Blocks For Axion "{slot} Slot" (DI)',
            58,
            "UT-2.5-MT",
        )
        for slot in "DEFG"
    ]


def test_xdin_defaults_to_the_project_hwio_total() -> None:
    xdin = [x for x in device_strips(xdin_default=40) if x[0] == "PSA3-XDIN"]
    assert xdin == [
        ("PSA3-XDIN", "Knife Disconnect Terminal Blocks For DI Negative", 40, "UT-2.5-MT")
    ]


def test_xdin_override_wins() -> None:
    xdin = [x[2] for x in device_strips(terminal_overrides={"XDIN": 36}) if x[0] == "PSA3-XDIN"]
    assert xdin == [36]


def test_no_di_module_no_xdin() -> None:
    assert "XDIN" not in strips(inputs(xdin_default=40))


def test_rtac_adds_five_terminals_per_used_serial_port() -> None:
    rtac = [x for x in device_strips() if str(x[0]).startswith("PSA3-XRTAC")]
    assert rtac == [
        (f"PSA3-XRTAC-C{n}", "Terminal Blocks for RTAC COM Port", 5, "UT-2.5-MT")
        for n in range(1, 7)
    ]


def test_device_strips_follow_x_ann_di_then_xdin_then_rtac_before_xip() -> None:
    tags = [str(x[0]).removeprefix("PSA3-") for x in device_strips(inter_panel_terminals=8)]
    assert tags[-12:] == [
        "XDIPD",
        "XDIPE",
        "XDIPF",
        "XDIPG",
        "XDIN",
        *(f"XRTAC-C{n}" for n in range(1, 7)),
        "XIP",
    ]


def test_strip_without_placeholder_sums_its_units() -> None:
    relay = device("RLY", terminals=[{"strip": "XRLY", "block": "UT-2.5-MT", "count": 3}])
    p = panel([{"part_id": "RLY", "qty": 2}])
    library_ = library(relay)
    lines = flatten(terminal_strips(p, library_, expand_devices(p, library_), inputs()))
    assert [(x.tag, x.description, x.qty) for x in lines if x.tag == "PSA1-XRLY"] == [
        ("PSA1-XRLY", "Terminal Blocks For XRLY", 6)
    ]
