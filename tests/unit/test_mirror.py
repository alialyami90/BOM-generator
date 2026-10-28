"""Panel mirroring: tag rewriting and merging a mirror file over its original panel."""

from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.io.mirror import lan_index, mirror_panel, mirror_tag
from bomgen.models.panel import Panel, PanelMirror


def base_dict() -> dict[str, Any]:
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
            "h_mm": 2100,
            "d_mm": 1000,
            "w_mm": 800,
            "cable_entry": "top",
        },
        "devices": [
            {"part_id": "RST2228-L2", "tag": "PSA1-L2-ESW-A01", "lan": "A"},
            {"part_id": "SFP-1G-SM", "qty": 2},
            {"part_id": "OTHER", "tag": "RST2228-L2"},
        ],
        "port_plans": {
            "PSA1-L2-ESW-A01": {"uplinks": [{"count": 2, "speed": "1G", "media": "SM"}]},
            "SFP-1G-SM": {"serial_ports": 1},
        },
        "options": {"dc_spare_branches_per_feed": 3},
        "document": {"doc_no": "DOC-1", "rev": "0", "issue_date": "2026-10-28"},
        "revision": {"highlight": [{"tag": "PSA1-L2-ESW-A01", "columns": ["D"]}]},
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
        "document": {"doc_no": "DOC-2", "rev": "1", "issue_date": "2026-11-01"},
    }


def base_panel() -> Panel:
    return Panel.model_validate(base_dict())


def mirror() -> PanelMirror:
    return PanelMirror.model_validate(mirror_dict())


def test_lan_index() -> None:
    assert lan_index("A") == 1
    assert lan_index("B") == 2


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("PSA1-L2-ESW-A01", "PSA2-L2-ESW-B01"),
        ("PSA1-L1-ESW-A11 to A16", "PSA2-L1-ESW-B11 to B16"),
        ("PSA1-EXT-FW-A", "PSA2-EXT-FW-B"),
        ("PSA1-DHPCC-GW-1", "PSA2-DHPCC-GW-2"),
        ("PSA1-FOPP-CCR-A01", "PSA2-FOPP-CCR-B01"),
        ("RST2228-L2", "RST2228-L2"),
    ],
)
def test_mirror_swaps_lan_letter_and_prefix_in_tags(tag: str, expected: str) -> None:
    assert mirror_tag(tag, base_panel(), mirror()) == expected


def test_mirror_tag_changes_only_the_last_segment_for_the_lan() -> None:
    assert mirror_tag("PSA1-A-ESW-A01", base_panel(), mirror()) == "PSA2-A-ESW-B01"


def test_mirror_tag_keeps_lan_when_a_panel_has_none() -> None:
    no_lan = Panel.model_validate({**base_dict(), "lan": None})
    assert mirror_tag("PSA1-L2-ESW-A01", no_lan, mirror()) == "PSA2-L2-ESW-A01"


def test_mirror_panel_copies_devices_and_port_plans() -> None:
    result = mirror_panel(base_panel(), mirror())
    assert result.kind == base_panel().kind
    assert result.enclosure == base_panel().enclosure
    assert [(d.part_id, d.qty, d.tag, d.lan) for d in result.devices] == [
        ("RST2228-L2", 1, "PSA2-L2-ESW-B01", "B"),
        ("SFP-1G-SM", 2, None, None),
        ("OTHER", 1, "RST2228-L2", None),
    ]
    assert list(result.port_plans) == ["PSA2-L2-ESW-B01", "SFP-1G-SM"]
    assert result.port_plans["PSA2-L2-ESW-B01"] == base_panel().port_plans["PSA1-L2-ESW-A01"]


def test_mirror_panel_takes_identity_and_document_from_mirror() -> None:
    result = mirror_panel(base_panel(), mirror())
    assert result.id == "psa2"
    assert result.cabinet_number == "861-GIS01-PSA-0002"
    assert result.cabinet_name == "PSA Cabinet - 002"
    assert result.tag_prefix == "PSA2"
    assert result.lan == "B"
    assert result.sheet_name == "2"
    assert result.document == mirror().document
    assert result.revision == mirror().revision
    assert result.revision.highlight == []


def test_mirror_options_merge_over_base() -> None:
    result = mirror_panel(base_panel(), mirror())
    assert result.options.dc_spare_branches_per_feed == 3
    assert result.options.aux_socket_a == 10


def test_mirror_bad_option_raises_validation_error() -> None:
    bad = PanelMirror.model_validate({**mirror_dict(), "options": {"ac_spare_branches": -1}})
    with pytest.raises(ValidationError, match="ac_spare_branches"):
        mirror_panel(base_panel(), bad)
