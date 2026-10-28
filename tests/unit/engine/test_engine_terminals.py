"""Group G terminal strips (spec: Derivation rules -> Terminal block quantities (group G);
Tag naming conventions, circuit and strip codes; Data model and generation order, step 8)."""

from typing import Any

import pytest
from engine_factories import library, panel, powered

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
