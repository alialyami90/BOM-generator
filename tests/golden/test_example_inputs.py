"""The example project in ``examples/`` loads and carries the spec's example values.

Expected values cite the spec section they come from, or the example workbook cell
they were transcribed from (ADR 0010 item 10).
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bomgen.cli import app
from bomgen.io.loader import LoadedSubstation, load_project, load_substation
from bomgen.models.library import DeviceType
from bomgen.models.panel import Panel

pytestmark = pytest.mark.golden

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
PROJECT_FILE = EXAMPLES / "project.yaml"
SUBSTATION_FILE = EXAMPLES / "substations" / "gis01" / "substation.yaml"


@pytest.fixture(scope="module")
def loaded() -> LoadedSubstation:
    return load_substation(SUBSTATION_FILE)


def panel(loaded: LoadedSubstation, panel_id: str) -> Panel:
    return next(p for p in loaded.panels if p.id == panel_id)


def part(loaded: LoadedSubstation, part_id: str) -> DeviceType:
    device = loaded.library.get(part_id)
    assert device is not None, part_id
    return device


def test_example_project_loads(loaded: LoadedSubstation) -> None:
    # Overview (4 cabinets in this order); Output requirements OUT-3 (one sheet per
    # cabinet in panel order); example workbook, sheets '1'-'4'.
    assert [p.id for p in loaded.panels] == ["psa1", "psa2", "psa3", "ws"]
    assert [p.sheet_name for p in loaded.panels] == ["1", "2", "3", "4"]


def test_cabinet_numbers_and_names(loaded: LoadedSubstation) -> None:
    # Overview (cabinet numbers); names from example workbook, '1'!A1, '2'!A1, '3'!A1, '4'!A1.
    assert [(p.cabinet_number, p.cabinet_name, p.tag_prefix) for p in loaded.panels] == [
        ("861-GIS01-PSA-0001", "PSA Cabinet - 001", "PSA1"),
        ("861-GIS01-PSA-0002", "PSA Cabinet - 002", "PSA2"),
        ("861-GIS01-PSA-0003", "PSA Cabinet - 003", "PSA3"),
        ("861-GIS01-PSA-0010", "WS Console", "WS"),
    ]
    # Overview: Cabinet 001 is LAN-A, 002 is LAN-B, 003 and the console have no LAN.
    assert [p.lan for p in loaded.panels] == ["A", "B", None, None]


def test_unit_wattages_match_power_consumption_sheet(loaded: LoadedSubstation) -> None:
    # Example workbook, 'Power Consumption'!I7:I11, I49:I51, I68:I69, I84 (DC) and
    # I17:I20 (AC). These unit watts are what make the spec's "Power Consumption sheet"
    # totals come out at 2,177.5 W DC and 1,090.3 W AC.
    dc_watts: dict[str, float] = {
        "RST2228-L2": 77,  # I7
        "RST2228-L1-24MM": 77,  # I8
        "SEL-2730M-EXT": 45,  # I9
        "SEL-3555-GW": 73,  # I10
        "FGR-60F": 21,  # I11
        "SEL-2488": 50,  # I49
        "SEL-3555-RTAC": 62,  # I50
        "SEL-2240": 31,  # I51
        "SEL-3355": 91,  # I68
        "NAP-F23": 52,  # I69
        "NAP-K55": 100,  # I84
    }
    ac_watts: dict[str, float] = {
        "SZ2500-LAMP": 11,  # I17
        "SK3243-FAN": 87,  # I18
        "SK3110-TH": 30,  # I19
        "IPR-2903685": 1.56,  # I20
    }
    for part_id, watts in dc_watts.items():
        device = part(loaded, part_id)
        assert (device.unit_power_w, device.supply_type, device.voltage_v) == (
            watts,
            "VDC",
            125,
        ), part_id
    for part_id, watts in ac_watts.items():
        device = part(loaded, part_id)
        assert (device.unit_power_w, device.supply_type, device.voltage_v) == (
            watts,
            "VAC",
            230,
        ), part_id


def test_l1_row_hwio_override(loaded: LoadedSubstation) -> None:
    # Example workbook, 'Panel 1'!H9 (the six-L1-switch row carries 10); plan Q5.
    l1_row = next(d for d in panel(loaded, "psa1").devices if d.part_id == "RST2228-L1-24MM")
    assert l1_row.qty == 6
    assert l1_row.hwio_points == 10


def test_psa2_mirrors_psa1_with_lan_b_and_socket(loaded: LoadedSubstation) -> None:
    # How each panel BOM groups its materials -> "What changes by panel type":
    # 002 is the LAN-B mirror of 001 plus an auxiliary power socket.
    psa1, psa2 = panel(loaded, "psa1"), panel(loaded, "psa2")
    assert (psa2.lan, psa2.tag_prefix) == ("B", "PSA2")
    assert psa2.devices == psa1.devices
    assert psa2.port_plans == psa1.port_plans
    assert psa2.enclosure == psa1.enclosure
    assert psa1.options.aux_socket_a is None
    # Derivation rules -> AC distribution: the 10 A socket of Cabinet 002.
    assert psa2.options.aux_socket_a == 10
    assert psa2.options.model_copy(update={"aux_socket_a": None}) == psa1.options


def test_dc_spare_branches_per_panel(loaded: LoadedSubstation) -> None:
    # Derivation rules -> DC distribution: 3 spares per feed in 001/002, 1 in 003 and WS.
    assert [p.options.dc_spare_branches_per_feed for p in loaded.panels] == [3, 3, 1, 1]


def test_l1_switch_matches_library_example(loaded: LoadedSubstation) -> None:
    # Inputs the tool needs -> 1. Device library, example column (L1 switch).
    l1 = part(loaded, "RST2228-L1-24MM")
    assert l1.category == "network_switch"
    assert (l1.make, l1.model) == ("Ruggedcom", "RST-2228")
    assert l1.ordering_code == "6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05"
    assert l1.description_template == (
        "LAN-{lan} Industrial Ethernet switch (Level-1) (24 MM FO Ports)"
    )
    assert (l1.tag_type, l1.purdue_level, l1.tag_pattern) == ("ESW", "L1", None)
    assert (l1.supply_type, l1.voltage_v, l1.unit_power_w) == ("VDC", 125, 77)
    assert (l1.load_type, l1.power_supplies, l1.min_branch_mcb_a) == ("CONTINUOUS", 2, 2)
    assert (l1.alarm_on_branch_mcb, l1.hwio_points) == (False, 1)
    ports = [(g.count, g.speed, g.media, g.kind) for g in l1.ports]
    assert ports == [(24, "100M", "MM", "fixed"), (4, "1G", None, "sfp_slot")]
    assert (l1.children, l1.terminals, l1.loose_items) == ([], [], [])
    assert l1.excluded_from_power is False


def test_breaker_codes(loaded: LoadedSubstation) -> None:
    # Derivation rules -> "Breaker part numbers".
    mcb = loaded.library.catalogues.mcb
    assert (mcb.make, mcb.poles) == ("Schneider", 2)
    assert [mcb.code_for(rating) for rating in mcb.ratings_a] == [
        "A9F74201",
        "A9F74202",
        "A9F74206",
        "A9F74210",
        "A9F74216",
    ]
    assert loaded.library.catalogues.aux_contact.ordering_code == "A9A26924"


def test_terminal_block_codes(loaded: LoadedSubstation) -> None:
    # Derivation rules -> "Terminal block quantities (group G)", Type / code column.
    blocks = loaded.library.catalogues.terminal_blocks
    assert {name: block.ordering_code for name, block in blocks.items()} == {
        "UT-16": "3044199",
        "UT-2.5-MTD": "3064085",
        "UT-2.5-MT": "3046362",
    }


def test_ws_console_dimensions(loaded: LoadedSubstation) -> None:
    # Heat Dissipation and Heat Calculations sheets -> natural convection (WS console):
    # H = 1.6 m, W = 0.8 m, D = 0.636 m.
    enclosure = panel(loaded, "ws").enclosure
    assert (enclosure.h_mm, enclosure.w_mm, enclosure.d_mm) == (1600, 800, 636)


def test_design_constants_are_spec_values(loaded: LoadedSubstation) -> None:
    # Inputs the tool needs -> 3. Project settings, design constants.
    constants = loaded.constants
    assert constants.dc_voltage_v == 125
    assert constants.ac_voltage_v == 230
    assert constants.power_margin == 0.25
    assert constants.current_factor == 1.3
    assert constants.btu_per_w == 3.41
    assert constants.t_max_c == 35
    assert constants.t_int_c == 25
    assert constants.air_constant_m3k_per_wh == 4.1
    assert constants.steel_coefficient_w_per_m2c == 5.5
    assert constants.min_main_mcb_a == 6


def test_example_validates_from_the_cli() -> None:
    # Plan M1/M1b: `bomgen validate` accepts the example project and its substation.
    for args in (["-p", str(PROJECT_FILE)], [str(PROJECT_FILE)], [str(SUBSTATION_FILE)]):
        result = CliRunner().invoke(app, ["validate", *args])
        assert result.exit_code == 0, result.output
        assert result.stdout.startswith("OK: JAFURAH JFGP2 PKG.3")


def test_example_project_has_one_substation() -> None:
    # ADR 0012: today's example becomes one project with one substation; the register
    # carries the workbook's three document numbers (page footers).
    project = load_project(PROJECT_FILE)
    assert [s.substation.substation.id for s in project.substations] == ["gis01"]
    (gis01,) = project.substations
    assert {k: (e.doc_no, e.rev) for k, e in gis01.documents.items()} == {
        "gis01-bom": ("VD-EL0009-861GISPSA-001", "02"),
        "gis01-power": ("VD-EL0009-861GISPSA-002", "00"),
        "gis01-heat": ("VD-EL0009-861GISPSA-003", "00"),
    }
    assert {p.document for p in gis01.panels} == {"gis01-bom"}
    assert gis01.manual_panel_ids == frozenset({"ws"})


def test_example_substation_layout_inputs(loaded: LoadedSubstation) -> None:
    # Design (substations and auto layout) 3.2 and R1, R10: 40 IEDs in a star, 32U usable
    # of a 42U panel, today's "=24+3" as sfp_per_l1.
    network = loaded.substation.network
    assert (network.ied_count, network.topology) == (40, "star")
    assert loaded.panel_capacity_u == 32
    assert loaded.spares.sfp_per_l1 == 3
    assert loaded.spares.port_fraction == 0.20
    assert loaded.substation.layout.blank_plate_u == 1
    roles = {e.role.value: e.part_id for e in loaded.substation.equipment}
    assert roles["l1_switch"] == "RST2228-L1-24MM"
    assert roles["l2_switch"] == "RST2228-L2"
    # R1 example: the RST2228 has 28 ports (24 for IEDs, 4 uplink slots).
    l1 = part(loaded, "RST2228-L1-24MM")
    assert sum(g.count for g in l1.ports) == 28
    assert [g.usable_for for g in l1.ports] == ["ied", "uplink"]
    for equipment in loaded.substation.equipment:
        assert part(loaded, equipment.part_id).height_u is not None, equipment.part_id


def test_terminal_strip_descriptions_and_busbar_tags(loaded: LoadedSubstation) -> None:
    # Example workbook, 'Panel 3'!C55:C61 (strip descriptions) and 'Panel 1'!B76:B77,
    # 'Aux'!B45 (grounding row labels).
    rtac = part(loaded, "SEL-3555-RTAC").terminals[0]
    assert rtac.description == "Terminal Blocks for RTAC COM Port"
    di = part(loaded, "SEL-2244-2").terminals[0]
    assert di.description is not None
    assert di.description.format(slot="E") == (
        'Knife Disconnect Terminal Blocks For Axion "E Slot" (DI)'
    )
    tags = {key: bar.tag for key, bar in loaded.library.catalogues.busbars.items()}
    assert tags == {
        "ac_safety_ground": "AC SAFETY POWER-GROUND",
        "instrument_ground": "INSTRUMENT-GROUND",
        "power_ground": "POWER-GROUND",
    }
