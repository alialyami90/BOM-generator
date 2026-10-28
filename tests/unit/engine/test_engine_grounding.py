"""Group H grounding busbars (spec: How each panel BOM groups its materials, group H;
Data model and generation order, step 9)."""

import pytest
from engine_factories import library, panel

from bomgen.engine.errors import EngineError
from bomgen.engine.grounding import grounding
from bomgen.engine.items import flatten
from bomgen.models.bom import Group


def lines(**options: object) -> list[tuple[object, ...]]:
    p = panel([{"part_id": "LAMP"}], options=options)
    return [
        (x.group, x.tag, x.description, x.qty, x.make, x.model)
        for x in flatten(grounding(p, library()))
    ]


def test_default_busbars_are_ac_safety_and_instrument_ground() -> None:
    assert lines() == [
        (Group.H, "AC SAFETY POWER-GROUND", "AC", 1, None, None),
        (Group.H, "INSTRUMENT-GROUND", "INST", 1, None, None),
    ]


def test_panel_chooses_its_busbars() -> None:
    assert lines(grounding_busbars=["power_ground"]) == [
        (Group.H, "POWER-GROUND", "POWER", 1, None, None)
    ]


def test_unknown_busbar_is_an_error() -> None:
    with pytest.raises(EngineError, match="earth_bar"):
        lines(grounding_busbars=["earth_bar"])
