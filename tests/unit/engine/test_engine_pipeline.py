"""Pipeline for groups A-D and the loose-material table (spec: Data model and
generation order, steps 1-5; How each panel BOM groups its materials -> Loose material)."""

from pathlib import Path

from builders import default_library, write_project
from engine_factories import device, library, loose, panel, powered

from bomgen.engine.kits import loose_table
from bomgen.engine.pipeline import build
from bomgen.engine.units import expand_devices
from bomgen.io.loader import load_project
from bomgen.models.bom import Group
from bomgen.models.project import LooseMaterial

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


def project_file(tmp_path: Path) -> Path:
    lib = default_library()
    lib["devices"].append(device("CM", "cable_manager", tag_pattern="Cable Manager"))
    return write_project(tmp_path, library=lib)


def test_groups_a_to_d_in_order_with_cabinet_title(tmp_path: Path) -> None:
    result = build(load_project(project_file(tmp_path)))
    p1 = result.panels[0]
    assert (p1.panel_id, p1.sheet_name) == ("p1", "1")
    assert p1.title == ("CAB-001", "Dhahran - Cabinet 1")
    groups = [line.group for line in p1.lines]
    assert groups == sorted(groups)
    assert {Group.A, Group.B, Group.D} <= set(groups)
    assert p1.lines[0].tag == "PANEL"


def test_mirrored_panel_takes_lan_b_tags(tmp_path: Path) -> None:
    result = build(load_project(project_file(tmp_path)))
    assert [p.panel_id for p in result.panels] == ["p1", "p2"]
    assert result.panels[1].lines[1].tag == "P2-L2-ESW-B01"


def test_no_loose_table_without_loose_material(tmp_path: Path) -> None:
    assert build(load_project(project_file(tmp_path))).loose is None


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
