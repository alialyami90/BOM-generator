"""Pipeline for groups A-D and the loose-material table (spec: Data model and
generation order, steps 1-5; How each panel BOM groups its materials -> Loose material)."""

from pathlib import Path
from typing import Any

from engine_factories import device, library, loose, panel, powered, switch

from bomgen.engine.kits import loose_table
from bomgen.engine.pipeline import build
from bomgen.engine.units import expand_devices
from bomgen.io.loader import LoadedSubstation
from bomgen.io.mirror import mirror_panel
from bomgen.models.bom import Group
from bomgen.models.panel import PanelMirror
from bomgen.models.project import DesignConstants, LooseMaterial, Project, Spares
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


def loaded(loose_material: dict[str, Any] | None = None) -> LoadedSubstation:
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
    lib = library(switch("L2", "L2"), device("CM", "cable_manager", tag_pattern="Cable Manager"))
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
        panels=(p1, p2),
        panel_files={},
        manual_panel_ids=frozenset(),
    )


def test_groups_a_to_d_in_order_with_cabinet_title() -> None:
    result = build(loaded())
    p1 = result.panels[0]
    assert (p1.panel_id, p1.sheet_name) == ("p1", "1")
    assert p1.title == ("CAB-001", "Dhahran - Cabinet 1")
    groups = [line.group for line in p1.lines]
    assert groups == sorted(groups)
    assert {Group.A, Group.B, Group.C, Group.D} <= set(groups)
    assert p1.lines[0].tag == "PANEL"


def test_mirrored_panel_takes_lan_b_tags() -> None:
    result = build(loaded())
    assert [p.panel_id for p in result.panels] == ["p1", "p2"]
    assert result.panels[1].lines[1].tag == "PSA2-L2-ESW-B01"


def test_no_loose_table_without_loose_material() -> None:
    assert build(loaded()).loose is None


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
