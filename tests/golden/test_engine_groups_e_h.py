"""Groups E-H built from ``examples/`` (plan M3).

Expected rows live in ``expected_groups_e_h.py``; spec-stated values are asserted here
with the section they come from.
"""

from pathlib import Path

import pytest
from expected_groups_a_d import Row
from expected_groups_e_h import PSA1_E_TO_H, PSA2_E_TO_H, PSA3_E_TO_H, WS_E_TO_H

from bomgen.engine.pipeline import build
from bomgen.io.loader import load_substation
from bomgen.models.bom import BomLine, BuildResult, Group, PanelBom

pytestmark = pytest.mark.golden

SUBSTATION_FILE = (
    Path(__file__).resolve().parents[2] / "examples" / "substations" / "gis01" / "substation.yaml"
)
GROUPS_E_TO_H = {Group.E, Group.F, Group.G, Group.H}
PREFIXES = {"psa1": "PSA1", "psa2": "PSA2", "psa3": "PSA3", "ws": "WS"}


@pytest.fixture(scope="module")
def result() -> BuildResult:
    return build(load_substation(SUBSTATION_FILE))


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


def qty(result: BuildResult, panel_id: str, tag: str) -> object:
    (line,) = [x for x in panel(result, panel_id).lines if x.tag == tag]
    return line.qty


def model(result: BuildResult, panel_id: str, tag: str) -> str | None:
    (line,) = [x for x in panel(result, panel_id).lines if x.tag == tag]
    return line.model


@pytest.mark.parametrize(
    ("panel_id", "expected"),
    [("psa1", PSA1_E_TO_H), ("psa2", PSA2_E_TO_H), ("psa3", PSA3_E_TO_H), ("ws", WS_E_TO_H)],
)
def test_groups_e_to_h_match_the_example_workbook(
    result: BuildResult, panel_id: str, expected: list[Row]
) -> None:
    lines = panel(result, panel_id).lines
    assert [row(x) for x in lines if x.group in GROUPS_E_TO_H] == expected


def test_groups_in_order_with_separators_before_e_to_h(result: BuildResult) -> None:
    # Data model and generation order, step 11: rows A->H, a separator row before groups
    # E, F, G and H.
    for p in result.panels:
        groups = [x.group for x in p.lines]
        assert groups == sorted(groups)
        assert [p.lines[i].group for i in p.separators_before()] == [
            Group.E,
            Group.F,
            Group.G,
            Group.H,
        ]


def test_cabinet_001_numbers_71_rows(result: BuildResult) -> None:
    # Plan M3: SR.NO 1...71 on cabinet 001 (one SR.NO per line; separators carry none).
    assert len(panel(result, "psa1").lines) == 71


def test_dc_branches_of_cabinet_001(result: BuildResult) -> None:
    # Derivation rules -> DC distribution: Q1.1-Q1.10 in group B order (6 L1 switches
    # -> Q1.2-Q1.7), 3 spares per feed, the same n on both feeds.
    lines = panel(result, "psa1").lines
    for feed in (1, 2):
        branches = [x for x in lines if x.tag and x.tag.startswith(f"PSA1-Q{feed}.")]
        assert [x.tag for x in branches] == [f"PSA1-Q{feed}.{n}" for n in range(1, 14)]
        assert [x.description.split(" For ")[1] for x in branches[1:7]] == [
            f"L1_ESW_A{n} PS{feed}" for n in range(11, 17)
        ]
        assert all(x.model == "A9F74202" for x in branches)


@pytest.mark.parametrize(
    ("panel_id", "cinc", "main"),
    [("psa1", 6, 16), ("psa2", 16, 16), ("psa3", 6, 6), ("ws", 6, 6)],
)
def test_incoming_and_main_ratings(
    result: BuildResult, panel_id: str, cinc: int, main: int
) -> None:
    # Derivation rules -> AC distribution: CINC 6A, 16A with the 10A socket (002);
    # DC distribution: Q1/Q2 16A where sum Q ~ 7.1 A, 6A where ~ 1.5 A.
    prefix = PREFIXES[panel_id]
    assert model(result, panel_id, f"{prefix}-CINC") == f"A9F742{cinc:02d}"
    for feed in (1, 2):
        assert model(result, panel_id, f"{prefix}-Q{feed}") == f"A9F742{main:02d}"


@pytest.mark.parametrize(
    ("panel_id", "ac", "dc"), [("psa1", 3, 4), ("psa2", 3, 4), ("psa3", 3, 2), ("ws", 1, 2)]
)
def test_aux_contact_quantities(result: BuildResult, panel_id: str, ac: int, dc: int) -> None:
    # Derivation rules -> AC distribution: 3, WS console 1; DC distribution: 4 in
    # 001/002, 2 elsewhere.
    lines = panel(result, panel_id).lines
    (ac_line,) = [x for x in lines if x.description.startswith("AC Auxiliary Contacts")]
    (dc_line,) = [x for x in lines if x.description.startswith("DC Auxiliary Contacts")]
    assert (ac_line.qty, dc_line.qty) == (ac, dc)


# Derivation rules -> Terminal block quantities (group G), columns 001, 002, 003, WS.
TERMINAL_TABLE = {
    "X-AC": (6, 6, 6, 4),
    "X3-AC": (12, 14, 12, 8),
    "X-DC1": (6, 6, 6, 4),
    "X-DC2": (6, 6, 6, 4),
    "X4-DC1": (32, 32, 10, 6),
    "X4-DC2": (32, 32, 10, 6),
    "TBL": (4, 4, 4, 4),
    "THF": (12, 12, 12, 5),
    "XSD": (4, 4, 4, 4),
    "XPS": (None, 4, None, None),
    "X4-COD": (None, None, 8, 6),
    "X-ANN": (None, None, 4, None),
    "XDIPD": (None, None, 58, None),
    "XDIPE": (None, None, 58, None),
    "XDIPF": (None, None, 58, None),
    "XDIPG": (None, None, 58, None),
    "XDIN": (None, None, 40, None),
    **{f"XRTAC-C{n}": (None, None, 5, None) for n in range(1, 7)},
    "XIP": (40, 40, None, 12),
}


def test_terminal_block_quantities(result: BuildResult) -> None:
    for column, (panel_id, prefix) in enumerate(PREFIXES.items()):
        strips = {
            (x.tag or "").removeprefix(f"{prefix}-"): x.qty
            for x in panel(result, panel_id).lines
            if x.group is Group.G
        }
        expected = {k: v[column] for k, v in TERMINAL_TABLE.items() if v[column] is not None}
        assert strips == expected, panel_id


def test_xip_on_the_console_is_mtd(result: BuildResult) -> None:
    # Terminal table: XIP UT-2.5-MT (UT-2.5-MTD on WS).
    assert model(result, "psa1", "PSA1-XIP") == "UT-2.5-MT"
    assert model(result, "ws", "WS-XIP") == "UT-2.5-MTD"


def test_hwio_panel_totals_cover_xdin(result: BuildResult) -> None:
    # HWIO points: panel totals 17, 17 and 6; summed, the DI count the Axion modules
    # in cabinet 003 cover (XDIN 40). psa3.yaml also sets XDIN: 40 as an override, so
    # this checks the two agree; the default itself is covered in test_engine_pipeline.
    totals = [sum(x.hwio for x in p.lines) for p in result.panels]
    assert totals == [17, 17, 6, 0]
    assert qty(result, "psa3", "PSA3-XDIN") == sum(totals)


def test_grounding_rows(result: BuildResult) -> None:
    # How each panel BOM groups its materials, group H: description only, no make/model.
    for p in result.panels:
        h = [x for x in p.lines if x.group is Group.H]
        assert h
        assert all((x.make, x.model, x.ordering_code, x.qty) == (None, None, None, 1) for x in h)
