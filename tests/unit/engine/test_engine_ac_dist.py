"""Group E AC distribution (spec: Derivation rules -> AC distribution (group E),
Breaker part numbers; Data model and generation order, step 6)."""

from typing import Any

from engine_factories import library, panel, powered

from bomgen.engine.ac_dist import ac_distribution
from bomgen.engine.items import flatten
from bomgen.models.bom import Group
from bomgen.models.panel import Ventilation

SWITCH = powered("SW", "network_switch", tag_type="ESW", purdue_level="L2")


def build(ventilation: Ventilation = Ventilation.FORCED, **options: Any) -> list[tuple[Any, ...]]:
    p = panel([{"part_id": "SW"}], options=options)
    circuits = ac_distribution(p, library(SWITCH), ventilation)
    lines = flatten(circuits.items)
    assert all(line.group is Group.E for line in lines)
    return [(line.tag, line.description, line.qty, line.model, line.hwio) for line in lines]


def test_branches_in_load_order_with_one_spare() -> None:
    assert build() == [
        ("PSA1-CINC", "6A, 2P MCB For Main Auxiliary AC Supply", 1, "A9F74206", 0),
        ("PSA1-C1", "1A, 2P MCB For Illumination Lamp", 1, "A9F74201", 0),
        ("PSA1-C2", "2A, 2P MCB For Fan-1 and TH-1", 1, "A9F74202", 0),
        ("PSA1-C3", "2A, 2P MCB For Fan-2 and TH-2", 1, "A9F74202", 0),
        ("PSA1-C4", "1A, 2P MCB For TH-3", 1, "A9F74201", 0),
        ("PSA1-C5", "2A, 2P MCB For SPARE", 1, "A9F74202", 0),
        (None, "AC Auxiliary Contacts (for MCB CINC, C2, C3)", 3, "A9A26924", 3),
    ]


def test_breaker_rows_carry_catalogue_make_and_code() -> None:
    p = panel([{"part_id": "SW"}])
    cinc = ac_distribution(p, library(SWITCH), Ventilation.FORCED).items[0].line
    assert (cinc.make, cinc.model, cinc.ordering_code) == ("Schneider", "A9F74206", "A9F74206")


def test_cinc_is_16a_with_a_10a_socket() -> None:
    rows = build(aux_socket_a=10)
    assert rows[0][1:4] == ("16A, 2P MCB For Main Auxiliary AC Supply", 1, "A9F74216")
    assert rows[5][:2] == ("PSA1-C5", "10A, 2P MCB For Aux PS")
    assert rows[6][:2] == ("PSA1-C6", "2A, 2P MCB For SPARE")


def test_console_without_fans_has_lamp_thermostat_spare_all_1a() -> None:
    p = panel([{"part_id": "SW"}], kind="console", tag_prefix="WS", lan=None)
    lines = flatten(ac_distribution(p, library(SWITCH), Ventilation.NATURAL).items)
    assert [(x.tag, x.description, x.qty, x.hwio) for x in lines] == [
        ("WS-CINC", "6A, 2P MCB For Main Auxiliary AC Supply", 1, 0),
        ("WS-C1", "1A, 2P MCB For Illumination Lamp", 1, 0),
        ("WS-C2", "1A, 2P MCB For TH-1", 1, 0),
        ("WS-C3", "1A, 2P MCB For SPARE", 1, 0),
        (None, "AC Auxiliary Contacts (for MCB CINC)", 1, 0),
    ]


def test_spare_count_is_a_panel_input() -> None:
    rows = build(ac_spare_branches=2)
    assert [r[0] for r in rows[5:7]] == ["PSA1-C5", "PSA1-C6"]


def test_mcb_count_includes_cinc() -> None:
    p = panel([{"part_id": "SW"}], options={"aux_socket_a": 10})
    assert ac_distribution(p, library(SWITCH), Ventilation.FORCED).mcbs == 7
