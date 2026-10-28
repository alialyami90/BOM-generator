"""Writers for hand-written panel files (plan M17b, ADR 0021)."""

import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.io.edit import EditError
from bomgen.io.loader import load_project
from bomgen.io.panel_edit import create_panel, delete_panel, write_panel
from bomgen.io.yaml_source import read_yaml

EXAMPLES = Path(__file__).parents[2] / "examples"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "jfgp2")
    return tmp_path / "jfgp2" / "project.yaml"


def folder(project: Path) -> Path:
    return project.parent / "substations" / "gis01"


def panel_data(project: Path, name: str) -> dict[str, Any]:
    return read_yaml(folder(project) / "panels" / name).data


def test_write_changes_only_the_edited_line(project: Path) -> None:
    file = folder(project) / "panels" / "ws.yaml"
    before = file.read_text("utf-8")
    data = panel_data(project, "ws.yaml") | {"cabinet_name": "WS Console 2"}
    result = write_panel(project, "gis01", "ws", data)
    assert result.written
    changed = [
        (a, b)
        for a, b in zip(before.splitlines(), file.read_text("utf-8").splitlines(), strict=True)
        if a != b
    ]
    assert changed == [
        (
            'cabinet_name: "WS Console"  # \'Aux\'!A1 prints it as "WS CONSOLE"',
            'cabinet_name: "WS Console 2"  # \'Aux\'!A1 prints it as "WS CONSOLE"',
        )
    ]


def test_an_invalid_panel_is_not_written(project: Path) -> None:
    file = folder(project) / "panels" / "ws.yaml"
    before = file.read_text("utf-8")
    result = write_panel(project, "gis01", "ws", panel_data(project, "ws.yaml") | {"devices": []})
    assert not result.written
    assert [i.location for i in result.issues] == ["devices"]
    assert file.read_text("utf-8") == before


def test_create_lists_the_panel_in_manual_panels(project: Path) -> None:
    new = panel_data(project, "ws.yaml") | {
        "id": "ws2",
        "cabinet_number": "861-GIS01-PSA-0011",
        "tag_prefix": "WS2",
        "sheet_name": "5",
    }
    result = create_panel(project, "gis01", new)
    assert result.written, result.issues
    (target,) = load_project(project).substations
    assert target.substation.manual_panels[-1].as_posix() == "panels/ws2.yaml"
    assert "ws2" in target.manual_panel_ids
    assert result.preview is not None


def test_create_refuses_a_panel_that_clashes(project: Path) -> None:
    clash = panel_data(project, "ws.yaml") | {"id": "ws3"}  # same tag prefix and sheet as ws
    result = create_panel(project, "gis01", clash)
    assert not result.written
    assert result.issues
    assert not (folder(project) / "panels" / "ws3.yaml").exists()
    with pytest.raises(EditError, match=r"panels/ws\.yaml already exists"):
        create_panel(project, "gis01", panel_data(project, "ws.yaml"))
    with pytest.raises(EditError, match="needs an id"):
        create_panel(project, "gis01", {"cabinet_name": "x"})


def test_delete_removes_the_file_and_its_entry(project: Path) -> None:
    new = panel_data(project, "ws.yaml") | {
        "id": "ws2",
        "cabinet_number": "861-GIS01-PSA-0011",
        "tag_prefix": "WS2",
        "sheet_name": "5",
    }
    assert create_panel(project, "gis01", new).written
    assert delete_panel(project, "gis01", "ws2").written
    assert not (folder(project) / "panels" / "ws2.yaml").exists()
    (target,) = load_project(project).substations
    assert [p.as_posix() for p in target.substation.manual_panels] == ["panels/ws.yaml"]


def test_delete_is_refused_while_the_panel_is_named(project: Path) -> None:
    result = delete_panel(project, "gis01", "ws")  # the loose material's host panel
    assert not result.written
    assert any("ws" in i.message for i in result.issues)
    assert (folder(project) / "panels" / "ws.yaml").exists()


def test_generated_panels_are_refused(project: Path) -> None:
    file = folder(project) / "panels" / "psa3.yaml"
    file.write_text(file.read_text("utf-8") + "generated: true\n", encoding="utf-8")
    with pytest.raises(EditError, match="written by the layout"):
        write_panel(project, "gis01", "psa3", panel_data(project, "psa3.yaml"))
    with pytest.raises(EditError, match="written by the layout"):
        delete_panel(project, "gis01", "psa3")


def test_unknown_panel(project: Path) -> None:
    with pytest.raises(EditError, match="no panel 'nope' in substation 'gis01'"):
        delete_panel(project, "gis01", "nope")


def test_create_starts_the_panels_folder(project: Path) -> None:
    sub = folder(project)
    (sub / "panels").rename(sub / "cabinets")
    text = (sub / "substation.yaml").read_text("utf-8")
    (sub / "substation.yaml").write_text(text.replace("panels/", "cabinets/"), "utf-8")
    new = read_yaml(sub / "cabinets" / "ws.yaml").data | {
        "id": "ws2",
        "cabinet_number": "861-GIS01-PSA-0011",
        "tag_prefix": "WS2",
        "sheet_name": "5",
    }
    result = create_panel(project, "gis01", new)
    assert result.written, result.issues
    assert (sub / "panels" / "ws2.yaml").is_file()
