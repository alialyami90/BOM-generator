"""Field-level writers and checks for the app's forms (plan M17c, ADR 0021)."""

import shutil
from pathlib import Path

import pytest

from bomgen.io import fields
from bomgen.io.edit import EditError
from bomgen.io.errors import format_location
from bomgen.io.loader import LoadedSubstation, load_project

EXAMPLES = Path(__file__).parents[2] / "examples"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "jfgp2")
    return tmp_path / "jfgp2" / "project.yaml"


def gis01(project: Path) -> LoadedSubstation:
    (target,) = load_project(project).substations
    return target


def substation_yaml(project: Path) -> Path:
    return project.parent / "substations" / "gis01" / "substation.yaml"


def test_set_a_project_default(project: Path) -> None:
    result = fields.set_field(project, ("defaults", "spares", "port_fraction"), 0.25)
    assert result.written
    assert gis01(project).spares.port_fraction == 0.25
    assert "    port_fraction: 0.25" in project.read_text("utf-8")


def test_set_a_substation_override_and_remove_it_again(project: Path) -> None:
    path = ("constants", "t_max_c")
    assert fields.set_field(project, path, 40, substation="gis01").written
    assert gis01(project).constants.t_max_c == 40
    assert fields.remove_field(project, path, substation="gis01").written
    assert gis01(project).constants.t_max_c == 35
    assert "\nconstants:" not in substation_yaml(project).read_text("utf-8")  # emptied, gone


def test_validate_field_returns_the_engines_message(project: Path) -> None:
    before = project.read_text("utf-8")
    message = fields.validate_field(project, ("defaults", "spares", "port_fraction"), 1.5)
    assert message == "Input should be less than 1"
    assert fields.validate_field(project, ("defaults", "spares", "port_fraction"), 0.3) is None
    assert project.read_text("utf-8") == before


def test_validate_field_reports_a_rule_over_several_keys(project: Path) -> None:
    message = fields.validate_field(project, ("constants", "t_max_c"), 20, substation="gis01")
    assert message == "t_max_c must be greater than t_int_c"


def test_validate_field_checks_against_the_other_files(project: Path) -> None:
    message = fields.validate_field(project, ("document",), "nope", substation="gis01")
    assert message is not None
    assert "nope" in message


def test_equipment_rows_are_added_moved_and_removed(project: Path) -> None:
    row = {"id": "gps2", "part_id": "SEL-2488", "role": "other", "l2_ports": 1}
    assert fields.insert_item(project, ("equipment",), None, row, substation="gis01").written
    ids = [e.id for e in gis01(project).substation.equipment]
    assert ids[-1] == "gps2"
    assert fields.move_item(project, ("equipment",), len(ids) - 1, 0, substation="gis01").written
    assert gis01(project).substation.equipment[0].id == "gps2"
    assert fields.remove_item(project, ("equipment",), 0, substation="gis01").written
    assert [e.id for e in gis01(project).substation.equipment] == ids[:-1]
    assert "  - id: fopp\n    part_id: FOPP-96SM\n" in substation_yaml(project).read_text("utf-8")


def test_a_hand_written_panel_device_is_updated(project: Path) -> None:
    path = ("devices", 0, "purpose")
    result = fields.set_field(project, path, "Interface", substation="gis01", panel="psa1")
    assert result.written
    psa1 = next(p for p in gis01(project).panels if p.id == "psa1")
    assert psa1.devices[0].purpose == "Interface"


def test_bad_paths_are_refused(project: Path) -> None:
    with pytest.raises(EditError, match=r"no item 99 at equipment\[99\]\.qty"):
        fields.set_field(project, ("equipment", 99, "qty"), 2, substation="gis01")
    with pytest.raises(EditError, match="not a list"):
        fields.insert_item(project, ("document",), None, "x", substation="gis01")
    with pytest.raises(EditError, match="within its substation"):
        fields.set_field(project, ("x",), 1, panel="psa1")


def test_document_users_name_every_sheet_and_panel(project: Path) -> None:
    loaded = load_project(project)
    assert fields.document_users(loaded, "gis01-heat") == [
        "gis01: heat dissipation sheet",
        "gis01: heat calculations sheet",
    ]
    users = fields.document_users(loaded, "gis01-bom")
    assert users[:2] == ["gis01: workbook", "gis01: generated panels"]
    assert "gis01: panel ws" in users
    assert fields.document_users(loaded, "nope") == []


def test_assumed_values_are_listed_and_confirmed(project: Path) -> None:
    assert fields.assumed_fields(project) == [
        ("documents", 0, "issue_date"),
        ("documents", 1, "issue_date"),
        ("documents", 2, "issue_date"),
    ]
    assert fields.confirm_field(project, ("documents", 0, "issue_date")).written
    assert fields.assumed_fields(project)[0] == ("documents", 1, "issue_date")
    text = project.read_text("utf-8")
    assert "    issue_date: 2026-10-28\n  - key: gis01-power" in text
    assert ("equipment", 4, "l2_ports") in fields.assumed_fields(substation_yaml(project))
    with pytest.raises(EditError, match="not marked ASSUMED"):
        fields.confirm_field(project, ("documents", 0, "issue_date"))


def test_fingerprint_changes_with_the_file(project: Path) -> None:
    before = fields.file_fingerprint(project)
    assert fields.file_fingerprint(project) == before
    fields.set_field(project, ("project", "client"), "SEC")
    assert fields.file_fingerprint(project) != before


def uses(target: LoadedSubstation, part_id: str) -> list[tuple[str, str, str, str]]:
    return [
        (use.where, use.file.name if use.file else "", format_location(use.path), use.name)
        for use in fields.part_users(target, part_id)
    ]


def test_part_users_list_equipment_rows_and_hand_written_panel_rows(project: Path) -> None:
    target = gis01(project)
    gps = [row.id for row in target.substation.equipment].index("gps")
    assert uses(target, "SEL-2488") == [
        ("equipment", "substation.yaml", f"equipment[{gps}]", "gps"),
        ("panel", "psa3.yaml", "devices[0]", "psa3: SEL-2488"),
    ]


def test_part_users_skip_a_mirror_whose_rows_come_from_its_source(project: Path) -> None:
    panels = [use for use in uses(gis01(project), "FOPP-96SM") if use[0] == "panel"]
    assert panels == [("panel", "psa1.yaml", "devices[0]", "psa1: FOPP-96SM")]


def test_part_users_name_a_tagged_panel_row_by_its_tag(project: Path) -> None:
    (use,) = uses(gis01(project), "SEL-3355")
    assert use[:3] == ("panel", "ws.yaml", "devices[0]")


def test_part_users_list_loose_items_and_what_they_bring(project: Path) -> None:
    assert uses(gis01(project), "NAP-K55") == [
        (
            "loose material",
            "substation.yaml",
            "loose_material.items[0]",
            '55" LCD Alarm Annunciator',
        )
    ]
    assert uses(gis01(project), "LPA37-696") == [
        (
            "loose material",
            "substation.yaml",
            "loose_material.items[0].children[0]",
            '55" LCD Alarm Annunciator',
        )
    ]


def test_part_users_list_library_parts_that_bring_the_part(project: Path) -> None:
    first, *_alternatives = uses(gis01(project), "FOPP-SPOOL")
    assert first == ("library", "", "devices[0].children[0]", "FOPP-96SM")


def test_part_users_of_an_unused_part_is_empty(project: Path) -> None:
    assert uses(gis01(project), "NOPE-1") == []
