"""Panel model: enclosure, devices, port plans, options, document info and mirrors."""

import copy
from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.models.panel import (
    BaseFrame,
    DeviceInstance,
    DocumentInfo,
    Panel,
    PanelMirror,
    PanelOptions,
    Ventilation,
)


def psa1_dict() -> dict[str, Any]:
    """The plan's section 3.3 example, trimmed to two devices."""
    return {
        "id": "psa1",
        "cabinet_number": "861-GIS01-PSA-0001",
        "cabinet_name": "PSA Cabinet - 001",
        "tag_prefix": "PSA1",
        "lan": "A",
        "sheet_name": "1",
        "kind": "network",
        "enclosure": {
            "make": "Rawabi",
            "model": "ENC-2100",
            "ordering_code": "RW-2100-1000-800",
            "h_mm": 2100,
            "d_mm": 1000,
            "w_mm": 800,
            "base_frame": {"h_mm": 100, "d_mm": 950, "w_mm": 750},
            "cable_entry": "top",
        },
        "devices": [
            {"part_id": "FOPP-96SM", "qty": 1, "purpose": "L2-L3 uplink to CCR"},
            {"part_id": "RST2228-L2", "qty": 1},
        ],
        "port_plans": {
            "RST2228-L2": {
                "uplinks_l3": [{"count": 2, "speed": "1G", "media": "SM"}],
                "downlinks": [
                    {"count": 6, "speed": "1G", "media": "MM"},
                    {"count": 1, "speed": "100M", "media": "MM"},
                ],
            },
        },
        "options": {
            "aux_socket_a": None,
            "smoke_detector": True,
            "change_over_diodes": "auto",
            "ventilation": "auto",
            "dc_spare_branches_per_feed": 3,
            "ac_spare_branches": 1,
            "main_mcb_override_a": None,
            "inter_panel_terminals": 40,
            "terminal_overrides": {},
            "grounding_busbars": ["ac_safety_ground", "instrument_ground"],
        },
        "document": "psa1-bom",
        "revision": {"highlight": [{"tag": "PSA1-Q1.3", "columns": ["D"]}]},
    }


def mirror_dict() -> dict[str, Any]:
    return {
        "id": "psa2",
        "mirror_of": "psa1",
        "cabinet_number": "861-GIS01-PSA-0002",
        "cabinet_name": "PSA Cabinet - 002",
        "tag_prefix": "PSA2",
        "lan": "B",
        "sheet_name": "2",
        "options": {"aux_socket_a": 10},
        "document": "psa2-bom",
    }


def test_panel_from_plan_example_validates() -> None:
    panel = Panel.model_validate(psa1_dict())
    assert panel.id == "psa1"
    assert panel.enclosure.cable_entry.value == "top"
    assert panel.devices[0].qty == 1
    assert panel.port_plans["RST2228-L2"].downlinks[1].count == 1
    assert panel.options.inter_panel_terminals == 40
    assert panel.revision.highlight[0].columns == ["D"]


def test_panel_options_defaults() -> None:
    options = PanelOptions()
    assert options.smoke_detector is True
    assert options.change_over_diodes == "auto"
    assert options.ventilation is Ventilation.AUTO
    assert options.dc_spare_branches_per_feed == 1
    assert options.ac_spare_branches == 1
    assert options.grounding_busbars == ["ac_safety_ground", "instrument_ground"]
    assert options.terminal_overrides == {}
    assert options.aux_socket_a is None


def test_panel_omitted_optional_sections_use_defaults() -> None:
    data = psa1_dict()
    for key in ("options", "port_plans", "revision"):
        del data[key]
    panel = Panel.model_validate(data)
    assert panel.options == PanelOptions()
    assert panel.port_plans == {}
    assert panel.revision.highlight == []


@pytest.mark.parametrize("rev", [0, "0"])
@pytest.mark.parametrize("issue_date", [date(2026, 10, 28), "2026-10-28"])
def test_rev_and_issue_date_accept_unquoted_yaml_scalars(rev: object, issue_date: object) -> None:
    info = DocumentInfo.model_validate({"doc_no": "D", "rev": rev, "issue_date": issue_date})
    assert info.rev == "0"
    assert info.issue_date == date(2026, 10, 28)


def test_enclosure_base_frame_dimensions() -> None:
    panel = Panel.model_validate(psa1_dict())
    assert panel.enclosure.base_frame == BaseFrame(h_mm=100, d_mm=950, w_mm=750)
    data = psa1_dict()
    del data["enclosure"]["base_frame"]
    assert Panel.model_validate(data).enclosure.base_frame is None


def test_enclosure_rejects_the_old_base_frame_mm_key() -> None:
    data = psa1_dict()
    data["enclosure"]["base_frame_mm"] = 100
    with pytest.raises(ValidationError, match="base_frame_mm"):
        Panel.model_validate(data)


def test_base_frame_needs_all_three_positive_dimensions() -> None:
    for bad in ({"h_mm": 100, "d_mm": 950}, {"h_mm": 0, "d_mm": 950, "w_mm": 750}):
        with pytest.raises(ValidationError):
            BaseFrame.model_validate(bad)


def test_device_instance_hwio_override() -> None:
    assert DeviceInstance(part_id="RST2228-L1-24MM", qty=6, hwio_points=10).hwio_points == 10
    assert DeviceInstance(part_id="RST2228-L1-24MM", hwio_points=0).hwio_points == 0
    assert DeviceInstance(part_id="RST2228-L1-24MM").hwio_points is None
    with pytest.raises(ValidationError):
        DeviceInstance(part_id="RST2228-L1-24MM", hwio_points=-1)


def test_panel_requires_at_least_one_device() -> None:
    data = psa1_dict()
    data["devices"] = []
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


@pytest.mark.parametrize("prefix", ["psa1", "1PSA", "PSA-1", ""])
def test_tag_prefix_must_be_upper_case_code(prefix: str) -> None:
    data = psa1_dict()
    data["tag_prefix"] = prefix
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


@pytest.mark.parametrize("panel_id", ["PSA1", "-psa1", "psa 1", ""])
def test_panel_id_must_be_lower_case_slug(panel_id: str) -> None:
    data = psa1_dict()
    data["id"] = panel_id
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


@pytest.mark.parametrize("lan", ["C", "a", ""])
def test_lan_must_be_a_or_b(lan: str) -> None:
    data = psa1_dict()
    data["lan"] = lan
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


def test_lan_may_be_null() -> None:
    data = psa1_dict()
    data["lan"] = None
    assert Panel.model_validate(data).lan is None


@pytest.mark.parametrize("value", [True, False, "auto"])
def test_change_over_diodes_accepts_true_false_auto(value: object) -> None:
    assert PanelOptions.model_validate({"change_over_diodes": value}).change_over_diodes == value


def test_change_over_diodes_rejects_other_strings() -> None:
    with pytest.raises(ValidationError):
        PanelOptions.model_validate({"change_over_diodes": "yes"})


def test_panel_rejects_unknown_option_key() -> None:
    data = psa1_dict()
    data["options"]["smoke_detectors"] = True
    with pytest.raises(ValidationError, match="smoke_detectors"):
        Panel.model_validate(data)


def test_revision_mark_needs_at_least_one_valid_column() -> None:
    data = copy.deepcopy(psa1_dict())
    data["revision"]["highlight"][0]["columns"] = []
    with pytest.raises(ValidationError):
        Panel.model_validate(data)
    data["revision"]["highlight"][0]["columns"] = ["I"]
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


def test_port_allocation_count_must_be_positive() -> None:
    data = psa1_dict()
    data["port_plans"]["RST2228-L2"]["downlinks"][0]["count"] = 0
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


def test_port_allocation_rejects_unknown_media() -> None:
    data = psa1_dict()
    data["port_plans"]["RST2228-L2"]["downlinks"][0]["media"] = "copper"
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


def test_enclosure_dimensions_must_be_positive() -> None:
    data = psa1_dict()
    data["enclosure"]["h_mm"] = 0
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


def test_default_option_lists_are_not_shared_between_instances() -> None:
    first = Panel.model_validate({**psa1_dict(), "options": {}})
    second = Panel.model_validate({**psa1_dict(), "options": {}})
    assert first.options.grounding_busbars is not second.options.grounding_busbars


def test_mirror_from_plan_example_validates() -> None:
    mirror = PanelMirror.model_validate(mirror_dict())
    assert mirror.mirror_of == "psa1"
    assert mirror.options == {"aux_socket_a": 10}


def test_mirror_cannot_mirror_itself() -> None:
    data = mirror_dict()
    data["mirror_of"] = data["id"]
    with pytest.raises(ValidationError, match="mirror"):
        PanelMirror.model_validate(data)


def test_mirror_shares_panel_id_and_prefix_patterns() -> None:
    data = mirror_dict()
    data["tag_prefix"] = "psa2"
    with pytest.raises(ValidationError):
        PanelMirror.model_validate(data)
    data = mirror_dict()
    data["mirror_of"] = "PSA1"
    with pytest.raises(ValidationError):
        PanelMirror.model_validate(data)


def test_panel_document_is_a_register_key() -> None:
    assert Panel.model_validate(psa1_dict()).document == "psa1-bom"
    data = psa1_dict()
    data["document"] = {"doc_no": "DOC-1", "rev": "0", "issue_date": "2026-10-28"}
    with pytest.raises(ValidationError, match="document"):
        Panel.model_validate(data)
    data["document"] = "PSA1 BOM"
    with pytest.raises(ValidationError, match="document"):
        Panel.model_validate(data)


def test_panel_generated_defaults_false() -> None:
    assert Panel.model_validate(psa1_dict()).generated is False
    assert Panel.model_validate({**psa1_dict(), "generated": True}).generated is True


def test_device_first_nn_defaults_to_none_and_must_be_positive() -> None:
    assert DeviceInstance.model_validate({"part_id": "X"}).first_nn is None
    assert DeviceInstance.model_validate({"part_id": "X", "first_nn": 15}).first_nn == 15
    with pytest.raises(ValidationError, match="first_nn"):
        DeviceInstance.model_validate({"part_id": "X", "first_nn": 0})
