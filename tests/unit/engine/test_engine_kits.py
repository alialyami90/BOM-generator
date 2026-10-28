"""Groups A and B with kit children (spec: How each panel BOM groups its materials;
Columns of a panel BOM; Data model and generation order, steps 1-2)."""

from engine_factories import device, library, panel, powered, switch

from bomgen.engine.enclosure import enclosure_item
from bomgen.engine.items import BomItem, flatten
from bomgen.engine.kits import main_equipment
from bomgen.engine.units import expand_devices
from bomgen.models.bom import BomLine, Group
from bomgen.models.panel import CableEntry

FOPP = device(
    "FOPP",
    "patch_panel",
    make="Hubbell",
    tag_type="FOPP",
    tag_pattern="{prefix}-FOPP-CCR-{lan}01",
    description_template="LC, 96 core SM FOPP for {purpose}",
    cores=96,
    children=[
        {"part_id": "SPOOL", "qty": 1},
        {"part_id": "PIGTAIL", "qty": "cores"},
    ],
)
KIT = (FOPP, device("SPOOL", model=None, ordering_code=None), device("PIGTAIL"))


def test_enclosure_row_states_size_base_frame_and_entry() -> None:
    item = enclosure_item(panel([{"part_id": "LAMP"}]))
    assert item.line == BomLine(
        group=Group.A,
        tag="PANEL",
        description=(
            "Cabinet : H2100 x D1000 x W800 mm\n"
            "Base Frame: H100 x D950 x W750 mm\n"
            "Cable Entry: Top Entry"
        ),
        qty=1,
        make="Rawabi",
        model="Fixed Frame",
        ordering_code="Fixed Frame",
    )


def test_enclosure_without_base_frame_skips_that_line() -> None:
    p = panel([{"part_id": "LAMP"}])
    enclosure = p.enclosure.model_copy(update={"base_frame": None, "cable_entry": CableEntry.SIDE})
    item = enclosure_item(p.model_copy(update={"enclosure": enclosure}))
    assert item.line.description == "Cabinet : H2100 x D1000 x W800 mm\nCable Entry: Side Entry"


def test_children_follow_parent_with_blank_designation() -> None:
    lib = library(*KIT)
    p = panel([{"part_id": "FOPP", "purpose": "L2-L3 Interface"}])
    (item,) = main_equipment(expand_devices(p, lib), lib)
    assert item.line.tag == "PSA1-FOPP-CCR-A01"
    assert item.line.description == "LC, 96 core SM FOPP for L2-L3 Interface"
    assert item.line.group is Group.B
    assert item.line.merge_fg
    assert [(c.tag, c.description, c.qty, c.model) for c in item.children] == [
        (None, "SPOOL", 1, None),
        (None, "PIGTAIL", 96, "PIGTAIL"),
    ]


def test_pigtails_equal_cores_times_parent_qty() -> None:
    lib = library(*KIT)
    (item,) = main_equipment(expand_devices(panel([{"part_id": "FOPP", "qty": 2}]), lib), lib)
    assert [c.qty for c in item.children] == [2, 192]


def test_part_without_children_does_not_merge() -> None:
    lib = library(switch("L2", "L2"))
    (item,) = main_equipment(expand_devices(panel([{"part_id": "L2"}]), lib), lib)
    assert item.children == ()
    assert not item.line.merge_fg


def test_row_hwio_override_wins_over_library() -> None:
    # Columns of a panel BOM, HWIO; plan Q5: the L1 row of cabinet 001 carries 10.
    lib = library(switch("L1", "L1", hwio_points=1), switch("L2", "L2", hwio_points=1))
    p = panel([{"part_id": "L2"}, {"part_id": "L1", "qty": 6, "hwio_points": 10}])
    l2, l1 = main_equipment(expand_devices(p, lib), lib)
    assert l2.line.hwio == 1
    assert l1.line.hwio == 10


def test_hwio_is_points_per_unit_times_qty() -> None:
    lib = library(switch("L1", "L1", hwio_points=1))
    (item,) = main_equipment(expand_devices(panel([{"part_id": "L1", "qty": 3}]), lib), lib)
    assert item.line.hwio == 3


def test_ordering_code_stays_blank_when_the_library_has_none() -> None:
    lib = library(powered("AXION", "io_chassis", ordering_code=None, model="SEL-2240"))
    (item,) = main_equipment(expand_devices(panel([{"part_id": "AXION"}]), lib), lib)
    assert item.line.model == "SEL-2240"
    assert item.line.ordering_code is None


def test_flatten_sets_absolute_parent_indices() -> None:
    a = BomLine(group=Group.A, description="a", qty=1)
    p = BomLine(group=Group.B, description="p", qty=1)
    c = BomLine(group=Group.B, description="c", qty=1)
    lines = flatten([BomItem(a), BomItem(p, (c, c))])
    assert [line.parent for line in lines] == [None, None, 1, 1]
