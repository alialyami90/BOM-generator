"""Substation model: documents, panels, equipment, network, spares, layout (ADR 0012/0013)."""

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.models.project import ConstantOverrides, DesignConstants, merge_defaults
from bomgen.models.substation import Equipment, GeneratedPanels, Network, PairMove, Substation

ENCLOSURE = {
    "make": "Rawabi",
    "model": "Fixed Frame",
    "h_mm": 2100,
    "d_mm": 1000,
    "w_mm": 800,
    "cable_entry": "top",
}


def substation_dict() -> dict[str, Any]:
    """The design's substation file (section 3.2), trimmed."""
    calc = {"document": "s1-power", "scope": "861-GIS01-PSA-001/002"}
    return {
        "substation": {"id": "s1", "name": "GIS Substation"},
        "document": "s1-bom",
        "calculations": {
            "power_consumption": calc,
            "heat_dissipation": calc,
            "heat_calculations": calc,
        },
        "panels": ["panels/psa1.yaml", "panels/psa2.yaml"],
        "manual_panels": ["panels/ws.yaml"],
        "equipment": [
            {"part_id": "RST2228-L2", "role": "l2_switch", "redundant": True},
            {"part_id": "RST2228-L1-24MM", "role": "l1_switch", "redundant": True},
            {"part_id": "FGR-60F", "role": "firewall", "redundant": True, "l2_ports": 1},
            {"part_id": "SEL-2488", "role": "other", "l2_ports": 1, "l2_speed": "100M"},
        ],
        "network": {"ied_count": 40, "topology": "star"},
        "spares": {"port_fraction": 0.2},
        "layout": {
            "blank_plate_u": 1,
            "overrides": [
                {"device": "PSA1-L1-ESW-A13", "panel": 3},
                {"pair": "EXT-FW", "panel": [3, 4]},
            ],
            "removed": ["PSA1-DHPCC-GW-1"],
        },
        "generated_panels": {
            "id": "psa{n}",
            "cabinet_number": "861-GIS01-PSA-{n:04d}",
            "cabinet_name": "PSA Cabinet - {n:03d}",
            "tag_prefix": "PSA{n}",
            "sheet_name": "{n}",
            "enclosure": ENCLOSURE,
            "document": "s1-bom",
            "options_by_panel": {2: {"aux_socket_a": 10}},
        },
    }


def test_substation_from_design_example_validates() -> None:
    s = Substation.model_validate(substation_dict())
    assert s.substation.id == "s1"
    assert s.equipment[3].l2_speed == "100M"
    assert s.equipment[3].l2_media == "MM"
    assert s.equipment[3].side == "none"
    assert isinstance(s.layout.overrides[1], PairMove)
    assert s.spares is not None
    assert s.spares.model_fields_set == {"port_fraction"}
    assert s.constants is None
    assert s.generated_panels is not None
    assert s.generated_panels.cabinet_number.format(n=2) == "861-GIS01-PSA-0002"
    assert s.generated_panels.options_by_panel == {2: {"aux_socket_a": 10}}


def test_redundant_equipment_cannot_name_a_side() -> None:
    with pytest.raises(ValidationError, match="leave side out"):
        Equipment.model_validate(
            {"part_id": "X", "role": "firewall", "redundant": True, "side": "a"}
        )
    assert Equipment.model_validate({"part_id": "X", "role": "other", "side": "b"}).side == "b"


def test_l1_switch_count_is_not_an_input() -> None:
    with pytest.raises(ValidationError, match="leave qty out"):
        Equipment.model_validate({"part_id": "X", "role": "l1_switch", "qty": 2})
    assert Equipment.model_validate({"part_id": "X", "role": "fopp", "qty": 2}).qty == 2


@pytest.mark.parametrize("role", ["l1_switch", "l2_switch"])
def test_equipment_needs_one_l1_and_one_l2_switch(role: str) -> None:
    data = substation_dict()
    data["equipment"] = [e for e in data["equipment"] if e["role"] != role]
    with pytest.raises(ValidationError, match=f"exactly one redundant {role}"):
        Substation.model_validate(data)
    data = substation_dict()
    data["equipment"].append({"part_id": "Y", "role": role, "redundant": True})
    with pytest.raises(ValidationError, match=f"exactly one redundant {role}"):
        Substation.model_validate(data)


def test_equipment_needs_generated_panels() -> None:
    data = substation_dict()
    del data["generated_panels"]
    with pytest.raises(ValidationError, match="generated_panels"):
        Substation.model_validate(data)
    data["equipment"] = []
    assert Substation.model_validate(data).generated_panels is None


@pytest.mark.parametrize("bad", ["PSA", "PSA{n}{n}", "PSA{m}", "PSA{n:q}", "PSA{n!r}x{n}"])
def test_generated_panel_templates_need_one_number(bad: str) -> None:
    data = copy.deepcopy(substation_dict()["generated_panels"])
    data["tag_prefix"] = bad
    with pytest.raises(ValidationError, match="tag_prefix"):
        GeneratedPanels.model_validate(data)


def test_pair_move_needs_two_different_panels() -> None:
    with pytest.raises(ValidationError, match="two different panels"):
        PairMove.model_validate({"pair": "EXT-FW", "panel": [3, 3]})


def test_panel_file_cannot_be_both_generated_and_manual() -> None:
    data = substation_dict()
    data["manual_panels"] = ["panels/psa1.yaml"]
    with pytest.raises(ValidationError, match=r"both panels and manual_panels: panels/psa1\.yaml"):
        Substation.model_validate(data)


def test_substation_needs_a_panel_file() -> None:
    data = substation_dict()
    data["panels"], data["manual_panels"] = [], []
    with pytest.raises(ValidationError, match="at least one file"):
        Substation.model_validate(data)


def test_network_defaults_are_design_values() -> None:
    network = Network()
    assert network.ied_count == 0
    assert network.topology == "star"
    assert network.ring_max_switches == 6
    assert network.l1_uplinks_per_switch == 1
    assert network.l1_interlink is True
    assert network.l3_uplinks_per_l2 == 2


def test_panel_capacity_is_not_an_input() -> None:
    data = substation_dict()
    data["layout"]["panel_capacity_u"] = 32
    with pytest.raises(ValidationError, match="panel_capacity_u"):
        Substation.model_validate(data)


def test_merged_constants_recheck_t_max_above_t_int() -> None:
    data = substation_dict()
    data["constants"] = {"t_int_c": 40}
    s = Substation.model_validate(data)  # alone, an override is not checked
    assert s.constants == ConstantOverrides.model_validate({"t_int_c": 40})
    with pytest.raises(ValidationError, match="t_max_c must be greater than t_int_c"):
        merge_defaults(DesignConstants(t_max_c=35), s.constants)


def test_loose_material_belongs_to_the_substation() -> None:
    data = substation_dict()
    data["loose_material"] = {
        "host_panel": "ws",
        "items": [{"part_id": "CABLE-1", "qty": 2, "children": ["LUG-1"], "fed_from": "psa1"}],
    }
    s = Substation.model_validate(data)
    assert s.loose_material is not None
    assert s.loose_material.items[0].children == ["LUG-1"]
