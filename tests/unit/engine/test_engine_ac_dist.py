"""Group E AC distribution (spec: Derivation rules -> AC distribution (group E),
Breaker part numbers; Data model and generation order, step 6)."""

from typing import Any

from engine_factories import library, panel, powered

from bomgen.engine.ac_dist import AcCircuits, ac_distribution
from bomgen.engine.items import flatten
from bomgen.engine.units import expand_devices
from bomgen.models.bom import Group
from bomgen.models.library import CatalogueChoice, Library, resolve_catalogues
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.project import DesignConstants

SWITCH = powered("SW", "network_switch", tag_type="ESW", purdue_level="L2")
SERVER = powered(
    "SRV",
    "workstation",
    tag_type="SRV",
    purdue_level="L2",
    supply_type="VAC",
    voltage_v=None,
    power_supplies=0,
    unit_power_w=250,
)


def ac(p: Panel, lib: Library, ventilation: Ventilation) -> AcCircuits:
    return ac_distribution(p, lib, ventilation, expand_devices(p, lib), DesignConstants())


def build(ventilation: Ventilation = Ventilation.FORCED, **options: Any) -> list[tuple[Any, ...]]:
    p = panel([{"part_id": "SW"}], options=options)
    circuits = ac(p, library(SWITCH), ventilation)
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
    cinc = ac(p, library(SWITCH), Ventilation.FORCED).items[0].line
    assert (cinc.make, cinc.model, cinc.ordering_code) == ("Schneider", "A9F74206", "A9F74206")


def test_cinc_is_16a_with_a_10a_socket() -> None:
    rows = build(aux_socket_a=10)
    assert rows[0][1:4] == ("16A, 2P MCB For Main Auxiliary AC Supply", 1, "A9F74216")
    assert rows[5][:2] == ("PSA1-C5", "10A, 2P MCB For Aux PS")
    assert rows[6][:2] == ("PSA1-C6", "2A, 2P MCB For SPARE")


def test_console_without_fans_has_lamp_thermostat_spare_all_1a() -> None:
    p = panel([{"part_id": "SW"}], kind="console", tag_prefix="WS", lan=None)
    lines = flatten(ac(p, library(SWITCH), Ventilation.NATURAL).items)
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
    assert ac(p, library(SWITCH), Ventilation.FORCED).mcbs == 7


def test_ac_branches_use_the_ac_mcb_choice_not_mcb_dc() -> None:
    # ADR 0023: mcb sizes the AC branches and CINC; mcb_dc only the DC ones.
    dc_set = {
        "id": "dc-only",
        "family": "C60H-DC 2P",
        "make": "Other",
        "ratings_a": [1, 2, 6, 10, 16],
        "code_pattern": "DC{rating:03d}",
        "dc_rating_v": 250,
        "ac_rated": False,
    }
    lib = resolve_catalogues(
        library(SWITCH, mcb_brands=[dc_set]), CatalogueChoice(mcb_dc="dc-only")
    )
    circuits = ac(panel([{"part_id": "SW"}]), lib, Ventilation.FORCED)
    breakers = [line for line in flatten(circuits.items) if line.tag]
    assert {line.make for line in breakers} == {"Schneider"}
    assert breakers[0].model == "A9F74206"


def with_server(qty: int = 1, part: dict[str, Any] | None = None, **options: Any) -> AcCircuits:
    p = panel([{"part_id": "SW"}, {"part_id": "SRV", "qty": qty}], options=options)
    return ac(p, library(SWITCH, SERVER | (part or {})), Ventilation.FORCED)


def server_table(circuits: AcCircuits) -> list[tuple[Any, ...]]:
    return [(x.tag, x.description, x.qty, x.hwio) for x in flatten(circuits.items)]


def test_each_vac_unit_gets_a_branch_after_the_socket() -> None:
    circuits = with_server(aux_socket_a=10)
    assert server_table(circuits) == [
        ("PSA1-CINC", "16A, 2P MCB For Main Auxiliary AC Supply", 1, 0),
        ("PSA1-C1", "1A, 2P MCB For Illumination Lamp", 1, 0),
        ("PSA1-C2", "2A, 2P MCB For Fan-1 and TH-1", 1, 0),
        ("PSA1-C3", "2A, 2P MCB For Fan-2 and TH-2", 1, 0),
        ("PSA1-C4", "1A, 2P MCB For TH-3", 1, 0),
        ("PSA1-C5", "10A, 2P MCB For Aux PS", 1, 0),
        ("PSA1-C6", "2A, 2P MCB For L2_SRV_A01", 1, 0),
        ("PSA1-C7", "2A, 2P MCB For SPARE", 1, 0),
        (None, "AC Auxiliary Contacts (for MCB CINC, C2, C3)", 3, 3),
    ]
    [record] = circuits.branch_mcbs
    assert (record.tag, record.unit_tag, record.feed, record.load) == (
        "PSA1-C6",
        "PSA1-L2-SRV-A01",
        None,
        "L2_SRV_A01",
    )
    assert record.set_by == ("running", "floor")


def test_each_unit_of_a_vac_row_gets_its_own_branch() -> None:
    rows = server_table(with_server(2))
    assert rows[5:8] == [
        ("PSA1-C5", "2A, 2P MCB For L2_SRV_A01", 1, 0),
        ("PSA1-C6", "2A, 2P MCB For L2_SRV_A02", 1, 0),
        ("PSA1-C7", "2A, 2P MCB For SPARE", 1, 0),
    ]


def test_the_spare_stays_the_largest_housekeeping_branch() -> None:
    rows = server_table(with_server(part={"unit_power_w": 1500}))
    assert rows[5:7] == [
        ("PSA1-C5", "10A, 2P MCB For L2_SRV_A01", 1, 0),
        ("PSA1-C6", "2A, 2P MCB For SPARE", 1, 0),
    ]


def test_a_vac_unit_raises_cinc_above_its_branch() -> None:
    # 1.3 x 1500 W / 230 V = 8.48 A -> 10 A branch -> CINC 16 A, above it.
    rows = server_table(with_server(part={"unit_power_w": 1500}))
    assert rows[0][1] == "16A, 2P MCB For Main Auxiliary AC Supply"


def test_cinc_carries_the_ac_design_current() -> None:
    # Three 600 W units: 6 A branches (3.39 A each), so above the branch is 10 A, but
    # the panel's AC design current 3 x 3.39 = 10.2 A needs 16 A.
    rows = server_table(with_server(3, part={"unit_power_w": 600}))
    assert rows[0][1] == "16A, 2P MCB For Main Auxiliary AC Supply"


def test_a_vac_unit_with_alarm_adds_an_ac_aux_contact() -> None:
    rows = server_table(with_server(part={"alarm_on_branch_mcb": True}))
    assert rows[-1] == (None, "AC Auxiliary Contacts (for MCB CINC, C2, C3, C5)", 4, 4)


def test_x3_ac_counts_the_vac_branches() -> None:
    # CINC, lamp, two fan circuits, TH-3, the unit and the spare: X3-AC is 2 x 7.
    assert with_server().mcbs == 7


def test_a_vac_unit_excluded_from_power_gets_no_branch() -> None:
    circuits = with_server(part={"excluded_from_power": True})
    assert circuits.mcbs == 6
    assert circuits.branch_mcbs == []


def test_spare_rating_override() -> None:
    # Plan M58: the panel may set the AC spare's rating; unset, the largest housekeeping branch.
    rows = build(ac_spare_rating_a=6)
    assert rows[5] == ("PSA1-C5", "6A, 2P MCB For SPARE", 1, "A9F74206", 0)
    assert ac(panel([{"part_id": "SW"}]), library(SWITCH), Ventilation.FORCED).rule_spare_a == 2


def test_alarm_toggle_on_an_ac_unit_overrides_the_library() -> None:
    p = panel([{"part_id": "SW"}, {"part_id": "SRV", "alarm_on_branch_mcb": True}])
    rows = server_table(ac(p, library(SWITCH, SERVER), Ventilation.FORCED))
    assert rows[-1] == (None, "AC Auxiliary Contacts (for MCB CINC, C2, C3, C5)", 4, 4)
    off = panel([{"part_id": "SW"}, {"part_id": "SRV", "alarm_on_branch_mcb": False}])
    alarmed = SERVER | {"alarm_on_branch_mcb": True}
    rows = server_table(ac(off, library(SWITCH, alarmed), Ventilation.FORCED))
    assert rows[-1] == (None, "AC Auxiliary Contacts (for MCB CINC, C2, C3)", 3, 3)


def kit_branches(lib: Library, **options: Any) -> list[tuple[Any, ...]]:
    p = panel([{"part_id": "SW"}], options=options)
    return [
        (b.tag, b.load, b.rating_a, b.rule_rating_a)
        for b in ac(p, lib, Ventilation.FORCED).housekeeping
    ]


def test_fixed_rating_when_part_has_no_watts() -> None:
    """ADR 0032 item 4; the lamp keeps 1 A below the 2 A branch floor."""
    branches = kit_branches(library(SWITCH))
    assert branches == [
        ("PSA1-C1", "Illumination Lamp", 1, 1),
        ("PSA1-C2", "Fan-1 and TH-1", 2, 2),
        ("PSA1-C3", "Fan-2 and TH-2", 2, 2),
        ("PSA1-C4", "TH-3", 1, 1),
    ]
    p = panel([{"part_id": "SW"}])
    (lamp, *_rest) = ac(p, library(SWITCH), Ventilation.FORCED).housekeeping
    assert lamp.rule == "1 A: the spec's lamp rating"


def test_branch_rating_from_part_watts_when_given() -> None:
    hot = {"supply_type": "VAC", "voltage_v": None, "power_supplies": 0, "unit_power_w": 900}
    lib = library(
        SWITCH, powered("BIGFAN", "fan", **hot), fan={"part_id": "BIGFAN", "airflow_m3h": 358}
    )
    p = panel([{"part_id": "SW"}])
    fan_branch = ac(p, lib, Ventilation.FORCED).housekeeping[1]
    assert fan_branch.rating_a > 2
    assert "from the part's watts" in fan_branch.rule


def test_heater_branch_follows_the_thermostats_and_is_sized_from_its_watts() -> None:
    heater = powered(
        "HEATER", "component", supply_type="VAC", voltage_v=None, power_supplies=0, unit_power_w=400
    )
    lib = library(SWITCH, heater, heater={"part_id": "HEATER"})
    branches = kit_branches(lib, housekeeping={"heater": True})
    assert branches[-1][:2] == ("PSA1-C5", "Heater")
    assert branches[-1][2] >= 2


def test_branch_ratings_option_wins_and_keeps_the_rule() -> None:
    branches = kit_branches(library(SWITCH), housekeeping={"branch_ratings": {"fan": 6}})
    assert branches[1] == ("PSA1-C2", "Fan-1 and TH-1", 6, 2)
    rows = build(housekeeping={"branch_ratings": {"fan": 6}})
    assert rows[2][1] == "6A, 2P MCB For Fan-1 and TH-1"
