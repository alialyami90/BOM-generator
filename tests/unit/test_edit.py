"""Substation writers for the app's editors (plan M17, ADR 0021)."""

import shutil
from pathlib import Path

import pytest

from bomgen.io import edit
from bomgen.io.edit import EditError
from bomgen.io.loader import LoadedSubstation, load_project

EXAMPLES = Path(__file__).parents[2] / "examples"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "jfgp2")
    return tmp_path / "jfgp2" / "project.yaml"


def substation_text(project: Path) -> str:
    return (project.parent / "substations" / "gis01" / "substation.yaml").read_text("utf-8")


def loaded(project: Path) -> LoadedSubstation:
    (target,) = load_project(project).substations
    return target


def test_writer_changes_only_the_edited_lines(project: Path) -> None:
    before = substation_text(project)
    result = edit.set_option(project, "gis01", "inter_panel_terminals", 44)
    assert result.written
    assert result.issues == ()
    after = substation_text(project)
    changed = [
        (old, new)
        for old, new in zip(before.splitlines(), after.splitlines(), strict=True)
        if old != new
    ]
    assert changed == [("    inter_panel_terminals: 40", "    inter_panel_terminals: 44")]


def test_writer_returns_the_new_layout_preview(project: Path) -> None:
    result = edit.set_option(project, "gis01", "aux_socket_a", 16, panel=1)
    assert result.preview is not None
    psa1 = next(p for p in result.preview.panels if p.id == "psa1")
    assert psa1.options.aux_socket_a == 16


def test_an_invalid_value_is_not_written_and_says_why(project: Path) -> None:
    before = substation_text(project)
    result = edit.set_option(project, "gis01", "ac_spare_branches", -1)
    assert not result.written
    assert [i.location for i in result.issues] == [
        "generated_panels.options.ac_spare_branches",
        "generated_panels.options_by_panel[2].ac_spare_branches",  # merged into panel 2's
    ]
    assert substation_text(project) == before


def test_a_document_must_be_in_the_register(project: Path) -> None:
    result = edit.set_generated_document(project, "gis01", "nope-bom")
    assert not result.written
    assert any("nope-bom" in i.message for i in result.issues)
    assert edit.set_generated_document(project, "gis01", "gis01-power").written
    assert loaded(project).substation.generated_panels.document == "gis01-power"  # type: ignore[union-attr]


def test_enclosure_is_set_for_every_generated_panel(project: Path) -> None:
    enclosure = loaded(project).substation.generated_panels.enclosure  # type: ignore[union-attr]
    new = enclosure.model_dump(mode="json", exclude_none=True) | {"h_mm": 2200}
    result = edit.set_enclosure(project, "gis01", new)
    assert result.written
    assert result.preview is not None
    assert {p.enclosure.h_mm for p in result.preview.panels} == {2200}
    assert "  enclosure:  # as psa1\n" in substation_text(project)


def test_panel_option_is_set_and_removed_again(project: Path) -> None:
    assert edit.set_option(project, "gis01", "smoke_detector", False, panel=3).written
    options = {o.key: o for o in edit.panel_options(loaded(project), 3)}
    assert (options["smoke_detector"].value, options["smoke_detector"].own) == (False, True)
    assert options["smoke_detector"].shared is True
    assert options["inter_panel_terminals"].own is False
    assert options["inter_panel_terminals"].value == 40

    assert edit.remove_option(project, "gis01", "smoke_detector", panel=3).written
    by_panel = loaded(project).substation.generated_panels.options_by_panel  # type: ignore[union-attr]
    assert 3 not in by_panel
    assert by_panel[2] == {"aux_socket_a": 10}


def test_removing_the_last_panel_option_removes_options_by_panel(project: Path) -> None:
    assert edit.remove_option(project, "gis01", "aux_socket_a", panel=2).written
    assert "options_by_panel" not in substation_text(project)


def test_removing_a_shared_option_restores_its_default(project: Path) -> None:
    assert edit.remove_option(project, "gis01", "main_mcb_override_a").written
    options = {o.key: o for o in edit.panel_options(loaded(project), 1)}
    assert options["main_mcb_override_a"].value is None


def test_unknown_option_is_refused(project: Path) -> None:
    with pytest.raises(EditError, match="unknown panel option 'colour'"):
        edit.set_option(project, "gis01", "colour", "red")


def test_port_plan_is_set_and_removed(project: Path) -> None:
    plan = {"uplinks": [{"count": 2, "speed": "1G", "media": "SM"}], "serial_ports": 2}
    assert edit.set_port_plan(project, "gis01", "gw", plan).written
    gw = next(e for e in loaded(project).substation.equipment if e.id == "gw")
    assert gw.port_plan is not None
    assert gw.port_plan.serial_ports == 2
    assert edit.set_port_plan(project, "gis01", "gw", None).written
    gw = next(e for e in loaded(project).substation.equipment if e.id == "gw")
    assert gw.port_plan is None
    with pytest.raises(EditError, match="no equipment row 'xx'"):
        edit.set_port_plan(project, "gis01", "xx", None)


def test_layout_overrides_are_written_one_per_line(project: Path) -> None:
    moves = [{"device": "gps", "panel": 2, "side": None, "unit": None}]
    result = edit.set_layout_overrides(project, "gis01", moves)
    assert result.written
    assert "  overrides:\n    - { device: gps, panel: 2 }\n" in substation_text(project)
    assert result.preview is not None
    (gps_panel,) = {p.number for p in result.preview.fills for x in p.units if x.device == "gps"}
    assert gps_panel == 2
    assert edit.set_layout_overrides(project, "gis01", []).written
    assert "  overrides: []\n" in substation_text(project)


def test_layout_removed_is_checked_against_the_equipment(project: Path) -> None:
    result = edit.set_layout_removed(project, "gis01", [{"device": "nope"}])
    assert not result.written
    assert result.issues
    assert edit.set_layout_removed(project, "gis01", [{"device": "gps"}]).written
    assert loaded(project).substation.layout.removed[0].device == "gps"


def test_unknown_substation(project: Path) -> None:
    with pytest.raises(EditError, match="no substation 'gis99'"):
        edit.set_option(project, "gis99", "smoke_detector", True)


def test_an_edit_does_not_block_on_problems_it_did_not_cause(project: Path) -> None:
    register = project.read_text("utf-8")
    project.write_text(register.replace("issue_date: 2026-10-28  # ASSUMED", "issue_date: x", 1))
    result = edit.set_option(project, "gis01", "inter_panel_terminals", 44)
    assert result.written
    assert result.issues  # the project's own problem is still reported
    assert result.preview is None
