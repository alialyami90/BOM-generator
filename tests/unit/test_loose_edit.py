"""Loose-material writers (plan M18, ADR 0022)."""

import shutil
from pathlib import Path

import pytest

from bomgen.io import fields, loose_edit
from bomgen.io.edit import EditError
from bomgen.io.loader import load_project
from bomgen.models.project import LooseMaterial

EXAMPLES = Path(__file__).parents[2] / "examples"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "jfgp2")
    return tmp_path / "jfgp2" / "project.yaml"


def material(project: Path) -> LooseMaterial:
    (target,) = load_project(project).substations
    assert target.substation.loose_material is not None
    return target.substation.loose_material


def substation_yaml(project: Path) -> Path:
    return project.parent / "substations" / "gis01" / "substation.yaml"


def drop_loose_material(project: Path) -> None:
    assert fields.remove_field(project, ("loose_material",), substation="gis01").written


def test_add_a_free_text_item_at_the_end(project: Path) -> None:
    count = len(material(project).items)
    item = {"description": "Cable tray, 300 mm", "qty": "1 Lot", "tag": "Tray"}
    result = loose_edit.add_loose_item(project, "gis01", item)
    assert result.written
    added = material(project).items[-1]
    assert (added.part_id, added.description, added.qty) == (None, "Cable tray, 300 mm", "1 Lot")
    assert len(material(project).items) == count + 1
    assert "# row 49" in substation_yaml(project).read_text("utf-8")  # comments kept


def test_add_a_library_item_at_a_position(project: Path) -> None:
    item = {"part_id": "ZENON-V12", "tag": "HMI", "qty": 2}
    assert loose_edit.add_loose_item(project, "gis01", item, index=0).written
    first = material(project).items[0]
    assert (first.part_id, first.tag, first.qty) == ("ZENON-V12", "HMI", 2)
    assert material(project).items[1].part_id == "NAP-K55"


def test_the_first_item_starts_loose_material_under_a_host_panel(project: Path) -> None:
    drop_loose_material(project)
    item = {"description": "Spare keys"}
    with pytest.raises(EditError, match="host_panel"):
        loose_edit.add_loose_item(project, "gis01", item)
    assert loose_edit.add_loose_item(project, "gis01", item, host_panel="ws").written
    assert material(project).host_panel == "ws"
    assert [i.description for i in material(project).items] == ["Spare keys"]


def test_an_unknown_part_is_refused_and_nothing_is_written(project: Path) -> None:
    before = substation_yaml(project).read_text("utf-8")
    result = loose_edit.add_loose_item(project, "gis01", {"part_id": "GHOST"})
    assert not result.written
    assert any("unknown part_id 'GHOST'" in issue.message for issue in result.issues)
    assert substation_yaml(project).read_text("utf-8") == before


def test_switch_a_library_item_to_free_text(project: Path) -> None:
    item = {"description": "Alarm annunciator, by others", "tag": "Annunciator"}
    assert loose_edit.set_loose_item(project, "gis01", 0, item).written
    first = material(project).items[0]
    assert (first.part_id, first.description, first.children, first.fed_from) == (
        None,
        "Alarm annunciator, by others",
        [],
        None,
    )


def test_remove_and_move_items(project: Path) -> None:
    ids = [i.part_id for i in material(project).items]
    assert loose_edit.move_loose_item(project, "gis01", 0, 1).written
    assert [i.part_id for i in material(project).items][:2] == [ids[1], ids[0]]
    assert loose_edit.remove_loose_item(project, "gis01", 0).written
    assert [i.part_id for i in material(project).items] == [ids[0], *ids[2:]]


def test_removing_the_last_item_keeps_the_host_panel(project: Path) -> None:
    for _ in material(project).items:
        assert loose_edit.remove_loose_item(project, "gis01", 0).written
    assert material(project).items == []
    assert material(project).host_panel == "ws"
    (target,) = load_project(project).substations
    assert target.substation.loose_material is not None


def test_set_host_panel_checks_the_panel_exists(project: Path) -> None:
    assert not loose_edit.set_host_panel(project, "gis01", "nope").written
    assert loose_edit.set_host_panel(project, "gis01", "psa1").written
    assert material(project).host_panel == "psa1"


def test_validate_loose_item_reports_by_field(project: Path) -> None:
    before = substation_yaml(project).read_text("utf-8")
    bad = {"part_id": "GHOST", "fed_from": "zz"}
    messages = loose_edit.validate_loose_item(project, "gis01", 0, bad)
    assert messages == {
        "part_id": "unknown part_id 'GHOST' (not in library.yaml)",
        "fed_from": "fed_from 'zz' is not a panel id in this substation",
    }
    assert loose_edit.validate_loose_item(project, "gis01", None, {"description": "x"}) == {}
    whole = loose_edit.validate_loose_item(project, "gis01", None, {"qty": 2})
    assert list(whole) == [""]
    assert "part_id or a description" in whole[""]
    assert substation_yaml(project).read_text("utf-8") == before


def test_a_missing_item_index_is_an_edit_error(project: Path) -> None:
    with pytest.raises(EditError, match="no loose item 99"):
        loose_edit.set_loose_item(project, "gis01", 99, {"description": "x"})
    with pytest.raises(EditError, match="no loose item 99"):
        loose_edit.validate_loose_item(project, "gis01", 99, {"description": "x"})
