"""Substation model: documents, panels, equipment, network, spares, layout (ADR 0012/0013)."""

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.models.project import ConstantOverrides, DesignConstants, merge_defaults
from bomgen.models.substation import (
    DeviceMove,
    Equipment,
    GeneratedPanels,
    Network,
    PairMove,
    PartOverrides,
    Substation,
)

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
            {"id": "l2", "part_id": "RST2228-L2", "role": "l2_switch", "redundant": True},
            {"id": "l1", "part_id": "RST2228-L1-24MM", "role": "l1_switch", "redundant": True},
            {
                "id": "ext-fw",
                "part_id": "FGR-60F",
                "role": "firewall",
                "redundant": True,
                "l2_ports": 1,
            },
            {
                "id": "gps",
                "part_id": "SEL-2488",
                "role": "other",
                "l2_ports": 1,
                "l2_speed": "100M",
            },
        ],
        "network": {"ied_count": 40, "topology": "star"},
        "spares": {"port_fraction": 0.2},
        "layout": {
            "blank_plate_u": 1,
            "overrides": [
                {"device": "l1", "unit": 3, "side": "a", "panel": 3},
                {"pair": "l1", "unit": 2, "panel": [3, 4]},
                {"pair": "ext-fw", "panel": [3, 4]},
            ],
            "removed": [{"device": "gps"}, {"device": "ext-fw", "side": "a"}],
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
    assert s.layout.overrides[1].unit == 2
    assert [(r.device, r.unit, r.side) for r in s.layout.removed] == [
        ("gps", None, None),
        ("ext-fw", None, "a"),
    ]
    assert s.spares is not None
    assert s.spares.model_fields_set == {"port_fraction"}
    assert s.constants is None
    assert s.generated_panels is not None
    assert s.generated_panels.cabinet_number.format(n=2) == "861-GIS01-PSA-0002"
    assert s.generated_panels.options_by_panel == {2: {"aux_socket_a": 10}}


def test_redundant_equipment_cannot_name_a_side() -> None:
    with pytest.raises(ValidationError, match="leave side out"):
        Equipment.model_validate(
            {"id": "fw", "part_id": "X", "role": "firewall", "redundant": True, "side": "a"}
        )
    other = {"id": "x", "part_id": "X", "role": "other", "side": "b"}
    assert Equipment.model_validate(other).side == "b"


def test_l1_switch_model_is_picked_by_the_tool_unless_pinned() -> None:
    picked = Equipment.model_validate({"id": "l1", "role": "l1_switch", "redundant": True})
    assert picked.part_id is None
    with pytest.raises(ValidationError, match="part_id is needed for a firewall"):
        Equipment.model_validate({"id": "fw", "role": "firewall"})


def test_equipment_carries_purpose_and_hwio_onto_its_rows() -> None:
    fopp = Equipment.model_validate(
        {"id": "fopp", "part_id": "X", "role": "fopp", "purpose": "L2-L3 Interface"}
    )
    assert fopp.purpose == "L2-L3 Interface"
    assert fopp.hwio_points is None
    l1 = Equipment.model_validate({"id": "l1", "role": "l1_switch", "hwio_points": 10})
    assert l1.hwio_points == 10
    with pytest.raises(ValidationError, match="hwio_points"):
        Equipment.model_validate({"id": "l1", "role": "l1_switch", "hwio_points": -1})


def test_equipment_port_plan_is_per_unit_and_not_on_sized_switches() -> None:
    plan = {"downlinks": [{"count": 2, "speed": "1G", "media": "MM"}]}
    firewall = Equipment.model_validate(
        {"id": "fw", "part_id": "X", "role": "firewall", "port_plan": plan}
    )
    assert firewall.port_plan is not None
    assert firewall.port_plan.downlinks[0].count == 2
    for role in ("l1_switch", "l2_switch"):
        with pytest.raises(ValidationError, match="computed by the switch sizing"):
            Equipment.model_validate(
                {"id": "s", "part_id": "X", "role": role, "redundant": True, "port_plan": plan}
            )


def test_l1_switch_count_is_not_an_input() -> None:
    with pytest.raises(ValidationError, match="leave qty out"):
        Equipment.model_validate({"id": "l1", "part_id": "X", "role": "l1_switch", "qty": 2})
    fopp = {"id": "fopp", "part_id": "X", "role": "fopp", "qty": 2}
    assert Equipment.model_validate(fopp).qty == 2


@pytest.mark.parametrize("role", ["l1_switch", "l2_switch"])
def test_equipment_needs_one_l1_and_one_l2_switch(role: str) -> None:
    data = substation_dict()
    data["layout"] = {}
    data["equipment"] = [e for e in data["equipment"] if e["role"] != role]
    with pytest.raises(ValidationError, match=f"exactly one redundant {role}"):
        Substation.model_validate(data)
    data = substation_dict()
    data["equipment"].append({"id": "y", "part_id": "Y", "role": role, "redundant": True})
    with pytest.raises(ValidationError, match=f"exactly one redundant {role}"):
        Substation.model_validate(data)


def test_equipment_needs_generated_panels() -> None:
    data = substation_dict()
    del data["generated_panels"]
    with pytest.raises(ValidationError, match="generated_panels"):
        Substation.model_validate(data)
    data["equipment"] = []
    data["layout"] = {}
    assert Substation.model_validate(data).generated_panels is None


@pytest.mark.parametrize("bad", ["PSA", "PSA{n}{n}", "PSA{m}", "PSA{n:q}", "PSA{n!r}x{n}"])
def test_generated_panel_templates_need_one_number(bad: str) -> None:
    data = copy.deepcopy(substation_dict()["generated_panels"])
    data["tag_prefix"] = bad
    with pytest.raises(ValidationError, match="tag_prefix"):
        GeneratedPanels.model_validate(data)


def test_pair_move_needs_two_different_panels() -> None:
    with pytest.raises(ValidationError, match="two different panels"):
        PairMove.model_validate({"pair": "ext-fw", "panel": [3, 3]})


def test_panel_file_cannot_be_both_generated_and_manual() -> None:
    data = substation_dict()
    data["manual_panels"] = ["panels/psa1.yaml"]
    with pytest.raises(ValidationError, match=r"both panels and manual_panels: panels/psa1\.yaml"):
        Substation.model_validate(data)


def test_a_new_substation_may_have_no_panel_files_yet() -> None:
    # ADR 0021 (M17d): the app creates a blank substation; the build says it has no panels
    data = substation_dict()
    data["panels"], data["manual_panels"] = [], []
    assert Substation.model_validate(data).panels == []


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


@pytest.mark.parametrize(
    ("field", "bad"), [("id", "PSA {n}"), ("tag_prefix", "psa{n}"), ("sheet_name", "a:{n}")]
)
def test_generated_panel_templates_render_valid_values(field: str, bad: str) -> None:
    data = copy.deepcopy(substation_dict()["generated_panels"])
    data[field] = bad
    with pytest.raises(ValidationError, match=field):
        GeneratedPanels.model_validate(data)


def test_loose_material_title_defaults_to_the_workbook_text() -> None:
    data = substation_dict()
    data["loose_material"] = {"host_panel": "ws"}
    s = Substation.model_validate(data)
    assert s.loose_material is not None
    assert s.loose_material.title == "PSA Panels Loose Material and Auxiliary Equipment"


def test_override_position_is_optional_and_one_based() -> None:
    assert DeviceMove.model_validate({"device": "gps", "panel": 1}).position is None
    move = PairMove.model_validate({"pair": "ext-fw", "panel": [3, 4], "position": 2})
    assert move.position == 2
    with pytest.raises(ValidationError):
        DeviceMove.model_validate({"device": "gps", "panel": 1, "position": 0})


def test_top_u_and_position_are_exclusive() -> None:
    assert DeviceMove.model_validate({"device": "gps", "panel": 1, "top_u": 30}).top_u == 30
    assert PairMove.model_validate({"pair": "l2", "panel": [1, 2], "top_u": 28}).top_u == 28
    with pytest.raises(ValidationError, match="give position or top_u, not both"):
        DeviceMove.model_validate({"device": "gps", "panel": 1, "position": 1, "top_u": 30})
    with pytest.raises(ValidationError, match="give position or top_u, not both"):
        PairMove.model_validate({"pair": "l2", "panel": [1, 2], "position": 1, "top_u": 30})


def test_overrides_need_a_part_id_on_a_sized_switch() -> None:
    with pytest.raises(ValidationError, match="pick the switch to override its data"):
        Equipment(id="l1", role="l1_switch", redundant=True, overrides={"height_u": 2})


def test_a_part_number_needs_a_part_id_on_a_sized_switch() -> None:
    with pytest.raises(ValidationError, match="pick the switch to override its data"):
        Equipment(id="l1", role="l1_switch", redundant=True, ordering_code="X-1")


def test_sfp_choice_is_for_l1_and_l2_switches_only() -> None:
    sfp = [{"speed": "1G", "media": "MM", "part_id": "SFP-1"}]
    with pytest.raises(ValidationError, match="sfp is for L1 and L2 switches"):
        Equipment(id="gw", part_id="X", role="other", sfp=sfp)
    assert Equipment(id="l2", part_id="X", role="l2_switch", redundant=True, sfp=sfp).sfp


def test_partoverrides_values_lists_only_what_was_set() -> None:
    assert PartOverrides(height_u=2).values() == {"height_u": 2}


@pytest.mark.parametrize(
    "role",
    [
        "time_server",
        "operator_ws",
        "engineering_ws",
        "da_server",
        "kvm",
        "console",
        "annunciator",
        "time_accessory",
    ],
)
def test_parts_page_roles_parse(role: str) -> None:
    assert Equipment(id="x", part_id="X", role=role).role.value == role


@pytest.mark.parametrize("speed", ["2.5G", "5G", "25G"])
def test_new_port_speeds_are_not_sized_as_l2_links(speed: str) -> None:
    data = substation_dict()
    data["equipment"][3]["l2_speed"] = speed

    with pytest.raises(ValidationError, match="not sized for SFPs"):
        Substation.model_validate(data)


def test_generated_panels_may_set_enclosure_and_kind_per_panel() -> None:
    # Plan M50: a generated panel may have its own enclosure and kind; unset, the shared ones.
    data = substation_dict()
    narrow = ENCLOSURE | {"w_mm": 600, "cable_entry": "bottom"}
    data["generated_panels"] |= {"enclosure_by_panel": {3: narrow}, "kind_by_panel": {3: "control"}}
    generated = Substation.model_validate(data).generated_panels
    assert generated is not None
    assert generated.enclosure_by_panel[3].w_mm == 600
    assert generated.enclosure_by_panel[3].cable_entry == "bottom"
    assert generated.kind_by_panel == {3: "control"}
    plain = Substation.model_validate(substation_dict()).generated_panels
    assert plain is not None
    assert (plain.enclosure_by_panel, plain.kind_by_panel) == ({}, {})


# --- design basis (ADR 0031, plan M52) ---


def test_design_basis_defaults_match_today() -> None:
    from bomgen.engine.tags import FIRST_NUMBER
    from bomgen.models.substation import DesignBasis

    basis = DesignBasis()
    assert basis.dc_voltage_v is None
    assert basis.ac_voltage_v is None
    assert basis.redundancy == "duplicated_lan"
    assert basis.tagging.side_letters == ("A", "B")
    assert basis.tagging.first_numbers == FIRST_NUMBER
    assert basis.spares_policy is None
    data = substation_dict()
    assert Substation.model_validate(data).design_basis is None


@pytest.mark.parametrize("scheme", ["prp", "hsr"])
def test_prp_and_hsr_are_refused_until_a_rule_exists(scheme: str) -> None:
    from bomgen.models.substation import DesignBasis

    with pytest.raises(ValidationError, match="not supported yet"):
        DesignBasis.model_validate({"redundancy": scheme})


def test_tagging_side_letters_are_two_different_capitals() -> None:
    from bomgen.models.substation import Tagging

    with pytest.raises(ValidationError):
        Tagging.model_validate({"side_letters": ["A", "A"]})
    with pytest.raises(ValidationError):
        Tagging.model_validate({"side_letters": ["a", "b"]})
    assert Tagging.model_validate({"side_letters": ["X", "Y"]}).side_letters == ("X", "Y")


def test_ied_count_refused_with_schedule() -> None:
    row = {"bay": "E01", "name": "SEL-411L", "qty": 2}
    with pytest.raises(ValidationError, match="ied_count or ied_schedule"):
        Network.model_validate({"ied_count": 40, "ied_schedule": [row]})


def test_ied_row_defaults_to_one_dual_100m_mm_port_landing_on_l1() -> None:
    network = Network.model_validate({"ied_schedule": [{"bay": "E01", "name": "SEL-411L"}]})
    (row,) = network.ied_schedule
    assert (row.qty, row.attachment, row.lands_on) == (1, "dual", "l1")
    assert [(p.count, p.speed, p.media) for p in row.ports] == [(1, "100M", "MM")]


def test_ied_row_needs_a_port() -> None:
    with pytest.raises(ValidationError, match="at least 1"):
        Network.model_validate({"ied_schedule": [{"bay": "E01", "name": "X", "ports": []}]})


# -- Recorded issues and accepted warnings (ADR 0036, plan M66) --

SHA = "a" * 64


def issue(rev: str = "00", **extra: Any) -> dict[str, Any]:
    return {
        "rev": rev,
        "date": "2026-11-03",
        "file": "out/GIS01_Rev00.xlsx",
        "sha256": SHA,
        "description": "Issued for review",
    } | extra


def test_a_substation_has_no_issues_until_one_is_recorded() -> None:
    model = Substation.model_validate(substation_dict())
    assert model.issues == []
    assert model.checks is None


def test_issue_record_keeps_names_and_accepted_warnings() -> None:
    accepted = {
        "check": "dc_float",
        "subject": "Acti9",
        "reason": "Vendor letter",
        "date": "2026-11-03",
    }
    data = substation_dict() | {
        "issues": [
            issue(prepared="A. Engineer", checked="B. Checker", accepted_warnings=[accepted])
        ]
    }
    record = Substation.model_validate(data).issues[0]
    assert (record.prepared, record.checked, record.approved) == ("A. Engineer", "B. Checker", None)
    assert record.accepted_warnings[0].reason == "Vendor letter"


def test_recorded_revs_are_unique() -> None:
    with pytest.raises(ValidationError, match="rev '00' is recorded twice"):
        Substation.model_validate(substation_dict() | {"issues": [issue(), issue()]})


@pytest.mark.parametrize("bad", ["abc", "A" * 64, "a" * 63])
def test_issue_hash_is_a_sha256_hex_digest(bad: str) -> None:
    with pytest.raises(ValidationError):
        Substation.model_validate(substation_dict() | {"issues": [issue(sha256=bad)]})


def test_an_accepted_warning_needs_a_reason() -> None:
    accepted = {"check": "dc_float", "reason": " ", "date": "2026-11-03"}
    with pytest.raises(ValidationError):
        Substation.model_validate(substation_dict() | {"checks": {"accepted": [accepted]}})


def test_external_link_defaults_to_a_redundant_1g_sm_link_on_l2() -> None:
    network = Network.model_validate({"external_links": [{"name": "CCR"}]})
    (link,) = network.external_links
    assert (link.count, link.speed, link.media, link.lands_on) == (1, "1G", "SM", "l2")
    assert (link.redundant, link.through_firewall, link.cable_length_m) == (True, False, None)


def test_external_link_speed_must_be_sized() -> None:
    with pytest.raises(ValidationError):
        Network.model_validate({"external_links": [{"name": "CCR", "speed": "25G"}]})
