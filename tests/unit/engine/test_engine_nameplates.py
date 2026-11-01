"""Device nameplates: one BOM row per panel and the plates' text (M26, ADR 0026)."""

from dataclasses import replace
from pathlib import Path

import engine_factories as f
import pytest

from bomgen.engine.nameplates import nameplate_item, nameplates
from bomgen.engine.pipeline import build
from bomgen.engine.units import expand_devices
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.bom import BomLine, BuildResult, Group

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


@pytest.fixture(scope="module")
def built(example: LoadedSubstation) -> BuildResult:
    return build(example)


def lines(result: BuildResult, panel_id: str) -> tuple[BomLine, ...]:
    return next(p for p in result.panels if p.panel_id == panel_id).lines


def plates(result: BuildResult, panel_id: str) -> list[str]:
    panel = next(p for p in result.nameplates if p.panel_id == panel_id)
    return [x.text for x in panel.plates]


def test_nameplate_qty_is_the_panels_tagged_units(built: BuildResult) -> None:
    counts = {p.panel_id: lines(built, p.panel_id)[-1].qty for p in built.panels}
    assert counts == {"psa1": 11, "psa2": 11, "psa3": 3, "ws": 3}


def test_nameplate_is_the_last_row_of_group_h(built: BuildResult) -> None:
    last = lines(built, "psa1")[-1]
    assert (last.group, last.tag, last.part_id, last.hwio) == (
        Group.H,
        None,
        "NAMEPLATE-0828805",
        0,
    )
    assert last.description == "Device nameplate, white PVC plate 60 x 30 mm, self-adhesive"
    assert lines(built, "psa1")[-2].group is Group.H  # after the busbars


def test_nameplate_text_is_the_mcb_short_tag(built: BuildResult) -> None:
    feed_1 = [
        b.load.removesuffix(" PS1") for b in built.branch_mcbs if b.tag.startswith("PSA1-Q1.")
    ]
    assert plates(built, "psa1")[1:] == feed_1  # FOPP_CCR_A01 is passive: no MCB
    assert plates(built, "psa1")[:3] == ["FOPP_CCR_A01", "L2_ESW_A01", "L1_ESW_A11"]


def test_din_rail_units_get_a_plate(built: BuildResult) -> None:
    assert "EXT_FW_A01" in plates(built, "psa1")  # the firewall sits on DIN rail


def test_kit_children_and_housekeeping_get_no_plate(built: BuildResult) -> None:
    # not the Axion modules, IL or TH
    assert plates(built, "psa3") == ["L2_GPS_A01", "L2_RTAC_A01", "HWIO"]
    assert plates(built, "ws") == ["L2_SRV/OAS/EAS_A01", "MONITOR", "Keyboard & Mouse"]


def test_each_plate_names_its_device(built: BuildResult) -> None:
    psa3 = next(p for p in built.nameplates if p.panel_id == "psa3")
    group_b = [x.description for x in lines(built, "psa3") if x.group is Group.B and x.tag]
    assert [x.device for x in psa3.plates] == group_b


def test_no_nameplate_role_means_no_row(example: LoadedSubstation, built: BuildResult) -> None:
    kit = example.library.catalogues.housekeeping.model_copy(update={"nameplate": None})
    catalogues = example.library.catalogues.model_copy(update={"housekeeping": kit})
    library = example.library.model_copy(update={"catalogues": catalogues})
    result = build(replace(example, library=library))
    assert result.nameplates == ()
    for panel in built.panels:
        assert lines(result, panel.panel_id) == lines(built, panel.panel_id)[:-1]


# Rules on their own, without the example (ADR 0026, item 1).

LIB = f.library(
    f.switch("L1", "L1"),
    f.powered("KB", "component", tag_type="KB"),
    f.powered("GW", "gateway", tag_type="GW", purdue_level="L2"),
    f.device("CABLE"),
)


def plate_texts(*devices: dict[str, object]) -> list[str]:
    p = f.panel(list(devices))
    return [x.text for x in nameplates(p, expand_devices(p, LIB)).plates]


def test_a_tag_override_is_printed_as_written() -> None:
    assert plate_texts({"part_id": "KB", "tag": "Keyboard & Mouse"}) == ["Keyboard & Mouse"]


def test_a_multi_quantity_row_gets_a_plate_per_unit() -> None:
    assert plate_texts({"part_id": "L1", "qty": 3}) == ["L1_ESW_A11", "L1_ESW_A12", "L1_ESW_A13"]


def test_a_panel_with_no_tagged_units_has_no_plates_and_no_row() -> None:
    p = f.panel([{"part_id": "CABLE", "qty": 2}])
    assert nameplates(p, expand_devices(p, LIB)).plates == ()
    assert nameplate_item(p, LIB, 0) is None


# Tag naming conventions: every unit has its own tag (ENG-15, ADR 0030).


def test_two_gateways_in_a_panel_get_different_plates() -> None:
    assert plate_texts({"part_id": "GW"}, {"part_id": "GW"}) == ["L2_GW_A01", "L2_GW_A02"]
