"""Group D cabinet housekeeping (spec: Derivation rules -> Housekeeping kit (group D);
How each panel BOM groups its materials; Data model and generation order, step 5)."""

from typing import Any

import pytest
from engine_factories import device, library, loose, panel, powered

from bomgen.engine.errors import EngineError
from bomgen.engine.housekeeping import housekeeping, needs_change_over
from bomgen.engine.items import flatten
from bomgen.models.bom import Group
from bomgen.models.panel import Ventilation

SWITCH = powered("SW", "network_switch", tag_type="ESW", purdue_level="L2")
MONITOR = powered("MON", "monitor", power_supplies=1)
ANNUNCIATOR = powered("ANN", "annunciator", power_supplies=1)


def rows(
    ventilation: Ventilation, change_over: bool = False, **options: Any
) -> list[tuple[Any, ...]]:
    lib = library(SWITCH)
    p = panel([{"part_id": "SW"}], options=options)
    items = housekeeping(p, lib, ventilation, change_over)
    lines = flatten(items)
    assert all(line.group is Group.D for line in lines)
    return [(line.tag, line.qty, line.part_id) for line in lines]


def test_forced_ventilation_gives_two_fans_and_three_thermostats() -> None:
    assert rows(Ventilation.FORCED) == [
        ("PSA1-IL", 1, "LAMP"),
        ("PSA1-FAN-1,2", 2, "FAN"),
        ("PSA1-TH-1,2,3", 3, "TH"),
        ("PSA1-IPR", 1, "IPR"),
        (None, 1, "IPR-BASE"),
        (None, 1, "IPR-SUPP"),
        (None, 1, "IPR-BRKT"),
    ]


def test_natural_ventilation_gives_filters_and_one_thermostat() -> None:
    assert rows(Ventilation.NATURAL)[1:3] == [("PSA1-FILTER", 2, "FILTER"), ("PSA1-TH-1", 1, "TH")]


def test_ipr_kit_has_relay_base_suppression_bracket() -> None:
    lib = library(SWITCH)
    items = housekeeping(panel([{"part_id": "SW"}]), lib, Ventilation.FORCED, False)
    ipr = items[-1]
    assert ipr.line.tag == "PSA1-IPR"
    assert [c.part_id for c in ipr.children] == ["IPR-BASE", "IPR-SUPP", "IPR-BRKT"]


def test_door_switch_follows_the_lamp_when_catalogued() -> None:
    lib = library(SWITCH, device("DS", "door_switch"), door_switch={"part_id": "DS"})
    items = housekeeping(panel([{"part_id": "SW"}]), lib, Ventilation.FORCED, False)
    assert [i.line.part_id for i in items[:2]] == ["LAMP", "DS"]


def test_change_over_diodes_after_the_ipr_kit() -> None:
    assert rows(Ventilation.FORCED, change_over=True)[-2:] == [
        ("PSA1-COD-1", 1, "COD-NEG"),
        ("PSA1-COD-2", 1, "COD-POS"),
    ]


def test_socket_only_when_aux_socket_set() -> None:
    assert "SOCKET" not in [part for _tag, _qty, part in rows(Ventilation.FORCED)]
    assert rows(Ventilation.FORCED, True, aux_socket_a=10)[-1] == ("PSA1-AUX PS", 1, "SOCKET")


def test_socket_rating_must_match_catalogue() -> None:
    with pytest.raises(EngineError, match="16 A"):
        rows(Ventilation.FORCED, aux_socket_a=16)


def test_change_over_diodes_auto_follow_single_fed_loads() -> None:
    lib = library(SWITCH, MONITOR)
    assert needs_change_over(panel([{"part_id": "MON"}]), lib, [])
    assert not needs_change_over(panel([{"part_id": "SW"}]), lib, [])


def test_loose_load_fed_from_panel_needs_change_over() -> None:
    lib = library(SWITCH, ANNUNCIATOR)
    p = panel([{"part_id": "SW"}])
    assert needs_change_over(p, lib, [loose("ANN", fed_from="psa1")])
    assert not needs_change_over(p, lib, [loose("ANN", fed_from="psa3")])


@pytest.mark.parametrize("value", [True, False])
def test_change_over_option_overrides_auto(value: bool) -> None:
    lib = library(SWITCH, MONITOR)
    p = panel([{"part_id": "MON"}], options={"change_over_diodes": value})
    assert needs_change_over(p, lib, []) is value


HEATER = device(
    "HEATER", tag_type="HTR", supply_type="VAC", unit_power_w=400, load_type="CONTINUOUS"
)
HYGRO = device("HYGRO", tag_type="HYG")
SMOKE = device("SMOKE", tag_type="SD")


def kit_rows(ventilation: Ventilation, **options: Any) -> list[tuple[Any, ...]]:
    lib = library(
        SWITCH,
        HEATER,
        HYGRO,
        SMOKE,
        heater={"part_id": "HEATER"},
        hygrostat={"part_id": "HYGRO"},
        smoke_detector={"part_id": "SMOKE"},
    )
    p = panel([{"part_id": "SW"}], options=options)
    return [(line.part_id, line.qty) for line in flatten(housekeeping(p, lib, ventilation, False))]


def test_defaults_give_two_fans_three_thermostats() -> None:
    """ADR 0032: unset counts are the spec's kit."""
    assert ("FAN", 2) in kit_rows(Ventilation.FORCED)
    assert ("TH", 3) in kit_rows(Ventilation.FORCED)
    assert ("FILTER", 2) in kit_rows(Ventilation.NATURAL)


def test_counts_come_from_the_panel_options() -> None:
    kit = {"fans": 3, "thermostats_forced": 4, "lamps": 2, "filters": 4}
    forced = kit_rows(Ventilation.FORCED, housekeeping=kit)
    assert [r for r in forced if r[0] in {"LAMP", "FAN", "TH", "FILTER"}] == [
        ("LAMP", 2),
        ("FAN", 3),
        ("TH", 4),
    ]
    assert ("FILTER", 4) in kit_rows(Ventilation.NATURAL, housekeeping=kit)


def test_heater_adds_row_and_ac_branch() -> None:
    """The heater row follows the thermostats; its C branch is ac_dist's (see there)."""
    parts = [r[0] for r in kit_rows(Ventilation.FORCED, housekeeping={"heater": True})]
    assert parts[parts.index("TH") + 1] == "HEATER"


def test_hygrostat_and_supplied_smoke_detector_add_rows() -> None:
    rows_ = kit_rows(
        Ventilation.NATURAL, housekeeping={"hygrostat": True}, smoke_detector="supplied"
    )
    assert ("HYGRO", 1) in rows_
    assert ("SMOKE", 1) in rows_
    assert "SMOKE" not in [r[0] for r in kit_rows(Ventilation.NATURAL)]


def test_heater_without_a_library_role_is_an_error() -> None:
    p = panel([{"part_id": "SW"}], options={"housekeeping": {"heater": True}})
    with pytest.raises(EngineError, match="no heater part"):
        housekeeping(p, library(SWITCH), Ventilation.FORCED, False)
