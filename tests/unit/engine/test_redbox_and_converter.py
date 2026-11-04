"""RedBox and media converter roles (ADR 0038, plan M73): a mixed network is drawn with the
right names, tags, MCBs, power and L2 ports. psa-devices ships neither, so a test part covers it."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from bomgen.app.parts import ADD_CATEGORIES, CATEGORY_LABEL, ROLE_LABEL
from bomgen.checks import TAGGED_CATEGORIES
from bomgen.engine.layout import CABLE_MANAGED, PRIORITY, layout_preview, with_layout
from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.io.parts_edit import link_defaults
from bomgen.io.references import NETWORK_DEVICES
from bomgen.models.library import Category, DeviceType
from bomgen.models.substation import Equipment, EquipmentRole

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"
ROLES = {
    Category.REDBOX: EquipmentRole.REDBOX,
    Category.MEDIA_CONVERTER: EquipmentRole.MEDIA_CONVERTER,
}


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def part(loaded: LoadedSubstation, category: Category, tag: str, power: float = 6.0) -> DeviceType:
    """A test part: the example's firewall record (DC, two supplies) as ``category``."""
    base = loaded.library.get("FGR-60F")
    assert base is not None
    return base.model_copy(
        update={"part_id": f"{tag}-1", "category": category, "tag_type": tag, "unit_power_w": power}
    )


def with_row(loaded: LoadedSubstation, device: DeviceType, **row: Any) -> LoadedSubstation:
    """The example with ``device`` in its library, one row of it and generated panels."""
    library = loaded.library.model_copy(update={"devices": [*loaded.library.devices, device]})
    entry = Equipment.model_validate({"id": "x", "part_id": device.part_id, **row})
    substation = loaded.substation.model_copy(
        update={"equipment": [*loaded.substation.equipment, entry]}
    )
    panels = tuple(p.model_copy(update={"generated": True}) for p in loaded.panels)
    return replace(loaded, library=library, substation=substation, panels=panels)


def test_redbox_and_media_converter_are_named_tagged_network_devices() -> None:
    for category, role in ROLES.items():
        assert PRIORITY[category] == 2  # with the network devices
        assert category in TAGGED_CATEGORIES
        assert category in NETWORK_DEVICES  # a cable manager is allowed
        assert category not in CABLE_MANAGED  # and off by default
        assert category in ADD_CATEGORIES
        assert ROLE_LABEL[role] == CATEGORY_LABEL[category]
    assert ROLE_LABEL[EquipmentRole.REDBOX] == "RedBox"
    assert ROLE_LABEL[EquipmentRole.MEDIA_CONVERTER] == "Media converter"


def test_their_l2_link_defaults_are_one_port(example: LoadedSubstation) -> None:
    rbx, mc = part(example, Category.REDBOX, "RBX"), part(example, Category.MEDIA_CONVERTER, "MC")
    assert link_defaults(rbx, "redbox") == {"l2_ports": 1, "l2_speed": "100M"}
    assert link_defaults(mc, "media_converter") == {"l2_ports": 1, "l2_speed": "1G"}


@pytest.mark.parametrize(
    ("category", "tag"), [(Category.REDBOX, "RBX"), (Category.MEDIA_CONVERTER, "MC")]
)
def test_a_row_builds_with_its_tag_mcbs_and_power(
    example: LoadedSubstation, category: Category, tag: str
) -> None:
    role = ROLES[category].value
    built = build(with_layout(with_row(example, part(example, category, tag), role=role))[0])
    unpowered = part(example, category, tag, power=0.0)
    base = build(with_layout(with_row(example, unpowered, role=role))[0])
    (line,) = [x for p in built.panels for x in p.lines if x.part_id == f"{tag}-1"]
    assert line.tag is not None
    assert f"-{tag}" in line.tag
    assert [m for m in built.branch_mcbs if m.unit_tag == line.tag]
    assert built.power is not None
    assert base.power is not None
    margin = 1 + example.constants.power_margin
    assert built.power.dc_total_w == pytest.approx(base.power.dc_total_w + 6.0 * margin)


def test_a_common_redbox_takes_an_l2_port_on_each_side(example: LoadedSubstation) -> None:
    rbx = part(example, Category.REDBOX, "RBX")
    before = layout_preview(with_row(example, rbx, role="redbox"))
    after = layout_preview(with_row(example, rbx, role="redbox", l2_ports=1))
    assert after.plan.l2_demand_per_side == before.plan.l2_demand_per_side + 1
