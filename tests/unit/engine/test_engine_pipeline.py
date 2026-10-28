"""Pipeline for groups A-H and the loose-material table (spec: Data model and
generation order, steps 1-11; How each panel BOM groups its materials -> Loose material)."""

from pathlib import Path
from typing import Any

import pytest
from engine_factories import device, library, loose, panel, powered, switch

from bomgen.engine.kits import loose_table
from bomgen.engine.pipeline import build
from bomgen.engine.units import expand_devices
from bomgen.io.loader import LoadedSubstation
from bomgen.io.mirror import mirror_panel
from bomgen.models.bom import Group
from bomgen.models.library import Library
from bomgen.models.panel import Panel, PanelMirror, Ventilation
from bomgen.models.project import DesignConstants, LooseExtra, LooseMaterial, Project, Spares
from bomgen.models.substation import Substation

GPS = powered(
    "GPS",
    "gps_clock",
    tag_type="GPS",
    loose_items=[
        {"part_id": "ANT", "tag": "Time Server Accessories"},
        {"part_id": "CABLE", "qty": 2},
    ],
)
LOOSE_PARTS = (
    GPS,
    device("ANT", ordering_code="Included with GPS"),
    device("CABLE", ordering_code=None),
    device("ANN", "annunciator", description_template="Annunciator"),
    device("MOUNT", "accessory"),
    device("FO", "cable", make=None, model=None, ordering_code=None),
)


def loaded(
    loose_material: dict[str, Any] | None = None,
    lib: Library | None = None,
    panels: tuple[Panel, ...] | None = None,
) -> LoadedSubstation:
    project = Project.model_validate(
        {
            "project": {"id": "gis", "name": "GIS 01"},
            "library": {"name": "lib", "version": "1.0.0"},
            "substations": ["substations/s1/substation.yaml"],
        }
    )
    calc = {"document": "calc", "scope": "All"}
    substation = Substation.model_validate(
        {
            "substation": {"id": "s1", "name": "Dhahran"},
            "document": "bom",
            "calculations": {
                k: calc for k in ("power_consumption", "heat_dissipation", "heat_calculations")
            },
            "panels": ["p1.yaml", "p2.yaml"],
            "loose_material": loose_material,
        }
    )
    lib = lib or library(
        switch("L2", "L2"), device("CM", "cable_manager", tag_pattern="Cable Manager")
    )
    p1 = panel([{"part_id": "L2"}], id="p1", cabinet_number="CAB-001", cabinet_name="Cabinet 1")
    p2 = mirror_panel(
        p1,
        PanelMirror.model_validate(
            {
                "id": "p2",
                "mirror_of": "p1",
                "cabinet_number": "CAB-002",
                "cabinet_name": "Cabinet 2",
                "tag_prefix": "PSA2",
                "lan": "B",
                "sheet_name": "2",
                "document": "p2-bom",
            }
        ),
    )
    return LoadedSubstation(
        file=Path("substation.yaml"),
        substation=substation,
        project=project,
        library=lib,
        documents={},
        constants=DesignConstants(),
        spares=Spares(),
        panels=panels or (p1, p2),
        panel_files={},
        manual_panel_ids=frozenset(),
    )


def test_groups_a_to_h_in_order_with_cabinet_title() -> None:
    result = build(loaded())
    p1 = result.panels[0]
    assert (p1.panel_id, p1.sheet_name) == ("p1", "1")
    assert p1.title == ("CAB-001", "Dhahran - Cabinet 1")
    groups = [line.group for line in p1.lines]
    assert groups == sorted(groups)
    assert set(groups) == set(Group)
    assert p1.lines[0].tag == "PANEL"
    assert [p1.lines[i].group for i in p1.separators_before()] == [
        Group.E,
        Group.F,
        Group.G,
        Group.H,
    ]


def test_mirrored_panel_takes_lan_b_tags() -> None:
    result = build(loaded())
    assert [p.panel_id for p in result.panels] == ["p1", "p2"]
    assert result.panels[1].lines[1].tag == "PSA2-L2-ESW-B01"


def test_no_loose_table_without_loose_material() -> None:
    assert build(loaded()).loose is None


def test_no_loose_lines_no_loose_table() -> None:
    # The Loose Material sheet is written only while it has rows (ADR 0020, 0022).
    lib = library(*LOOSE_PARTS)
    material = LooseMaterial(host_panel="ws", items=[])
    assert loose_table(material, "GIS Substation", [], lib) is None


def test_device_loose_items_fill_the_table_without_project_items() -> None:
    lib = library(*LOOSE_PARTS)
    p = panel([{"part_id": "GPS"}], id="psa3", lan=None, tag_prefix="PSA3")
    material = LooseMaterial(host_panel="ws", items=[])
    table = loose_table(material, "GIS Substation", [(p, expand_devices(p, lib))], lib)
    assert table is not None
    assert [line.part_id for line in table.lines] == ["ANT", "CABLE"]


def test_loose_table_lists_project_items_then_device_loose_items() -> None:
    lib = library(*LOOSE_PARTS)
    p = panel([{"part_id": "GPS"}], id="psa3", lan=None, tag_prefix="PSA3")
    material = LooseMaterial(
        host_panel="ws",
        items=[
            loose("ANN", tag='55" Annunciator', children=["MOUNT"], fed_from="psa3"),
            loose("FO", tag="FO", qty="1 Lot"),
        ],
    )
    table = loose_table(material, "GIS Substation", [(p, expand_devices(p, lib))], lib)
    assert table is not None
    assert table.host_panel == "ws"
    assert table.title == ("GIS Substation", "PSA Panels Loose Material and Auxiliary Equipment")
    assert [(line.tag, line.part_id, line.qty, line.parent) for line in table.lines] == [
        ('55" Annunciator', "ANN", 1, None),
        (None, "MOUNT", 1, 0),
        ("FO", "FO", "1 Lot", None),
        ("Time Server Accessories", "ANT", 1, None),
        (None, "CABLE", 2, 3),
    ]
    assert [line.merge_fg for line in table.lines] == [True, False, False, True, False]
    assert table.lines[3].ordering_code == "Included with GPS"


def test_free_text_loose_item_prints_its_description_without_make_model_or_code() -> None:
    lib = library(*LOOSE_PARTS)
    item = LooseExtra(description="Cable tray, 300 mm", qty="1 Lot", tag="Tray")
    table = loose_table(LooseMaterial(host_panel="ws", items=[item]), "GIS", [], lib)
    assert table is not None
    line = table.lines[0]
    assert (line.tag, line.description, line.qty) == ("Tray", "Cable tray, 300 mm", "1 Lot")
    assert (line.make, line.model, line.ordering_code, line.part_id) == (None, None, None, None)
    assert (line.hwio, line.merge_fg) == (0, False)


def test_loose_table_title_comes_from_the_loose_material() -> None:
    lib = library(*LOOSE_PARTS)
    material = LooseMaterial(host_panel="ws", title="Loose Items", items=[loose("FO")])
    table = loose_table(material, "GIS Substation", [], lib)
    assert table is not None
    assert table.title == ("GIS Substation", "Loose Items")


AXION = (
    powered(
        "AXION",
        "io_chassis",
        tag_type="HWIO",
        tag_pattern="{prefix}-HWIO",
        children=[{"part_id": "DI", "qty": 2}],
    ),
    device(
        "DI",
        terminals=[{"strip": "XDIP{slot}", "block": "UT-2.5-MT", "count": 58, "first_slot": "D"}],
    ),
)


def test_xdin_defaults_to_the_hwio_total_of_every_panel() -> None:
    cable_manager = device("CM", "cable_manager", tag_pattern="Cable Manager")
    lib = library(switch("L2", "L2", hwio_points=1), cable_manager, *AXION)
    forced = {"ventilation": "forced"}
    p1 = panel([{"part_id": "L2"}], id="p1", options=forced)
    p3 = panel(
        [{"part_id": "AXION"}], id="p3", kind="control", tag_prefix="PSA3", lan=None, options=forced
    )
    result = build(loaded(lib=lib, panels=(p1, p3)))
    total = sum(line.hwio for p in result.panels for line in p.lines)
    xdin = [line.qty for line in result.panels[1].lines if line.tag == "PSA3-XDIN"]
    assert total == 1 + 2 * (3 + 2)  # L2 switch, AC and DC aux contacts of both panels
    assert xdin == [total]


def test_revision_marks_reach_lines_of_every_group() -> None:
    p1 = panel(
        [{"part_id": "L2"}],
        id="p1",
        revision={
            "highlight": [
                {"tag": "PSA1-L2-ESW-A01", "columns": ["D"]},
                {"tag": "PSA1-X-AC", "columns": ["D", "F"]},
            ]
        },
    )
    lines = build(loaded(panels=(p1,))).panels[0].lines
    revised = {line.tag: line.revised for line in lines if line.revised}
    assert revised == {"PSA1-L2-ESW-A01": {"D"}, "PSA1-X-AC": {"D", "F"}}


def auto_panel(unit_power_w: float) -> LoadedSubstation:
    cable_manager = device("CM", "cable_manager", tag_pattern="Cable Manager")
    lib = library(switch("L2", "L2", unit_power_w=unit_power_w), cable_manager)
    p1 = panel([{"part_id": "L2"}], id="p1", options={"ventilation": "auto"})
    return loaded(lib=lib, panels=(p1,))


def test_auto_ventilation_picks_filters_for_a_cool_cabinet() -> None:
    # Heat Calculations, "Rule for the tool": dT <= TMax - TInt -> filters + 1 thermostat,
    # which feeds groups D, E and G.
    result = build(auto_panel(10))
    tags = {line.tag for line in result.panels[0].lines}
    assert {"PSA1-FILTER", "PSA1-TH-1"} <= tags
    assert not any(tag and "FAN" in tag for tag in tags)
    (thf,) = [line.qty for line in result.panels[0].lines if line.tag == "PSA1-THF"]
    assert thf == 5
    assert result.heat is not None
    assert result.heat.cabinets[0].ventilation is Ventilation.NATURAL
    assert result.heat.line_up is None


def test_auto_ventilation_picks_fans_for_a_hot_cabinet() -> None:
    # 800 W / (7.92 m2 x 5.5) = 18 C > 10 C -> fans, thermostats and their AC branches.
    result = build(auto_panel(800))
    tags = {line.tag for line in result.panels[0].lines}
    assert {"PSA1-FAN-1,2", "PSA1-TH-1,2,3", "PSA1-C2", "PSA1-C3"} <= tags
    assert result.heat is not None
    (cabinet,) = result.heat.cabinets
    assert cabinet.ventilation is Ventilation.FORCED
    assert cabinet.forced.fan_m3h == 716
    assert result.heat.line_up is not None


def test_build_result_carries_the_dc_mains_per_panel() -> None:
    (main, _p2) = build(loaded()).mains
    assert (main.panel_id, main.rating_a, main.rule_rating_a) == ("p1", 6, 6)
    assert main.design_current_a == pytest.approx(10 * 1.3 / 125)


def test_build_result_carries_each_branch_mcbs_sizing() -> None:
    result = build(loaded())
    assert [(b.panel_id, b.tag, b.rating_a) for b in result.branch_mcbs][:2] == [
        ("p1", "PSA1-Q1.1", 2),
        ("p1", "PSA1-Q2.1", 2),
    ]


def test_build_result_carries_power_and_heat_per_cabinet() -> None:
    result = build(loaded())
    assert result.power is not None
    assert result.heat is not None
    assert [c.panel_id for c in result.power.cabinets] == ["p1", "p2"]
    assert [c.panel_id for c in result.heat.cabinets] == ["p1", "p2"]
    dc = result.power.cabinets[0].dc
    assert dc is not None
    assert dc.lines[0].source.line == 1  # the L2 switch row of p1
