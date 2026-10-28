"""Groups A-D and the loose-material table built from ``examples/`` (plan M2).

Expected rows live in ``expected_groups_a_d.py``; spec-stated values are asserted here
with the section they come from.
"""

from pathlib import Path

import pytest
from expected_groups_a_d import LOOSE, PSA1_A_TO_D, PSA2_A_TO_D, PSA3_A_TO_D, WS_A_TO_D, Row

from bomgen.engine.pipeline import build
from bomgen.io.loader import load_project
from bomgen.models.bom import BomLine, BomTable, BuildResult, Group, PanelBom, QtySum

pytestmark = pytest.mark.golden

PROJECT_FILE = Path(__file__).resolve().parents[2] / "examples" / "project.yaml"
GROUPS_A_TO_D = {Group.A, Group.B, Group.C, Group.D}


@pytest.fixture(scope="module")
def result() -> BuildResult:
    return build(load_project(PROJECT_FILE))


def panel(result: BuildResult, panel_id: str) -> PanelBom:
    return next(p for p in result.panels if p.panel_id == panel_id)


def row(line: BomLine) -> Row:
    return (
        line.tag,
        line.description,
        line.qty,
        line.make,
        line.model,
        line.ordering_code,
        line.hwio,
    )


def rows(table: BomTable) -> list[Row]:
    return [row(line) for line in table.lines if line.group in GROUPS_A_TO_D]


@pytest.mark.parametrize(
    ("panel_id", "expected"),
    [("psa1", PSA1_A_TO_D), ("psa2", PSA2_A_TO_D), ("psa3", PSA3_A_TO_D), ("ws", WS_A_TO_D)],
)
def test_groups_a_to_d_match_the_example_workbook(
    result: BuildResult, panel_id: str, expected: list[Row]
) -> None:
    assert rows(panel(result, panel_id)) == expected


def test_loose_material_table(result: BuildResult) -> None:
    # How each panel BOM groups its materials -> Loose material: a second table on
    # sheet 4, under the console.
    assert result.loose is not None
    assert result.loose.host_panel == "ws"
    assert result.loose.title == (
        "GIS Substation",
        "PSA Panels Loose Material and Auxiliary Equipment",
    )
    assert rows(result.loose) == LOOSE


def test_cabinet_titles(result: BuildResult) -> None:
    # Columns of a panel BOM: title line 1 the cabinet number, line 2 "<Substation> -
    # <Cabinet name>"; plan Q22: cabinet 003's title reads 003.
    assert [p.title for p in result.panels] == [
        ("861-GIS01-PSA-0001", "GIS Substation - PSA Cabinet - 001"),
        ("861-GIS01-PSA-0002", "GIS Substation - PSA Cabinet - 002"),
        ("861-GIS01-PSA-0003", "GIS Substation - PSA Cabinet - 003"),
        ("861-GIS01-PSA-0010", "GIS Substation - WS Console"),
    ]


def test_spec_tags(result: BuildResult) -> None:
    # Tag naming conventions (plan section 5, "Tags").
    tags = {p.panel_id: {line.tag for line in p.lines} for p in result.panels}
    assert {
        "PSA1-L2-ESW-A01",
        "PSA1-L1-ESW-A11 to A16",
        "PSA1-EXT-ESW-A",
        "PSA1-EXT-FW-A",
        "PSA1-FOPP-CCR-A01",
        "PSA1-DHPCC-GW-1",
    } <= tags["psa1"]
    assert {"PSA2-L2-ESW-B01", "PSA2-L1-ESW-B11 to B16", "PSA2-DHPCC-GW-2"} <= tags["psa2"]


def test_fopp_children_and_pigtails_equal_cores(result: BuildResult) -> None:
    # Derivation rules -> Network accessories: spool (1), splice holder (1), LC SM
    # pigtails (qty = cores, 96); Formatting -> Merges: B4:B7, F4:F6, G4:G6.
    lines = panel(result, "psa1").lines
    fopp = lines[1]
    assert fopp.merge_fg
    assert [(c.qty, c.parent) for c in lines[2:5]] == [(1, 1), (1, 1), (96, 1)]


def test_l1_sfps_entered_as_24_plus_3(result: BuildResult) -> None:
    # Derivation rules -> Network accessories: 27 x 1000BASE-SX MM, entered as =24+3.
    for panel_id, host in (("psa1", "L1-ESW-A11 to A16"), ("psa2", "L1-ESW-B11 to B16")):
        (line,) = [x for x in panel(result, panel_id).lines if x.tag == f"{host} SFP (MM)"]
        assert line.qty == QtySum(parts=(24, 3))


def test_nine_cable_managers_per_network_cabinet(result: BuildResult) -> None:
    # Derivation rules -> Network accessories: 9 per network cabinet.
    for panel_id in ("psa1", "psa2"):
        (line,) = [x for x in panel(result, panel_id).lines if x.tag == "Cable Manager"]
        assert line.qty == 9


def test_six_rtac_serial_cables(result: BuildResult) -> None:
    # Derivation rules -> Network accessories: one SEL-C607 per used COM port (6).
    (line,) = [x for x in panel(result, "psa3").lines if x.tag == "COM-CABLE"]
    assert (line.qty, line.model) == (6, "SEL-C607")


def test_ventilation_parts(result: BuildResult) -> None:
    # How each panel BOM groups its materials -> What changes by panel type; Derivation
    # rules -> Housekeeping kit: fans + 3 thermostats, or filters + 1 thermostat (WS).
    def tags(panel_id: str) -> list[str | None]:
        return [x.tag for x in panel(result, panel_id).lines if x.group is Group.D]

    for panel_id, prefix in (("psa1", "PSA1"), ("psa2", "PSA2"), ("psa3", "PSA3")):
        assert {f"{prefix}-FAN-1,2", f"{prefix}-TH-1,2,3", f"{prefix}-IPR"} <= set(tags(panel_id))
    assert {"WS-FILTER", "WS-TH-1", "WS-IPR"} <= set(tags("ws"))
    assert not any(t and "FAN" in t for t in tags("ws"))


def test_change_over_diodes_and_socket(result: BuildResult) -> None:
    # What changes by panel type: 003 adds change-over diodes; 002 adds the aux socket.
    # The WS console's single-fed monitor needs them too (Derivation rules -> DC).
    def tags(panel_id: str) -> set[str | None]:
        return {x.tag for x in panel(result, panel_id).lines}

    assert {"PSA3-COD-1", "PSA3-COD-2"} <= tags("psa3")
    assert {"WS-COD-1", "WS-COD-2"} <= tags("ws")
    assert not {"PSA1-COD-1", "PSA2-COD-1"} & (tags("psa1") | tags("psa2"))
    assert "PSA2-AUX PS" in tags("psa2")
    assert "PSA1-AUX PS" not in tags("psa1")


def test_hwio_from_group_b(result: BuildResult) -> None:
    # Columns of a panel BOM, HWIO: 1 per L2/EXT switch, the L1 row's 10 (plan Q5),
    # 1 for the GPS clock. Aux contacts follow in M3.
    assert [sum(x.hwio for x in p.lines) for p in result.panels] == [12, 12, 1, 0]
