"""Project loading: file resolution, mirroring and cross-file reference checks."""

from pathlib import Path
from typing import Any

import pytest
from builders import (
    default_library,
    default_p1,
    default_p2,
    default_project,
    write_project,
    write_yaml,
)

from bomgen.io.errors import InputError, Issue
from bomgen.io.loader import load_library, load_project


def issues_for(project_file: Path) -> list[Issue]:
    with pytest.raises(InputError) as caught:
        load_project(project_file)
    return list(caught.value.issues)


def texts(project_file: Path) -> list[str]:
    return [str(issue) for issue in issues_for(project_file)]


def line_of(path: Path, needle: str) -> int:
    """1-based line of the first line of ``path`` containing ``needle``."""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if needle in line:
            return number
    raise AssertionError(f"{needle!r} not in {path}")


def with_third_panel(tmp_path: Path, panel: dict[str, Any]) -> Path:
    project = default_project()
    project["panels"] = [*project["panels"], "panels/p3.yaml"]
    return write_project(tmp_path, project=project, panels={"p3.yaml": panel})


def test_loads_minimal_project_in_panel_order(tmp_path: Path) -> None:
    project_file = write_project(tmp_path)
    loaded = load_project(project_file)
    assert loaded.project_file == project_file
    assert [panel.id for panel in loaded.panels] == ["p1", "p2"]
    assert loaded.project.project.name == "GIS 01"
    assert loaded.library.get("RST2228-L2") is not None
    assert loaded.panel_files == {
        "p1": tmp_path / "panels" / "p1.yaml",
        "p2": tmp_path / "panels" / "p2.yaml",
    }


def test_mirror_panel_is_resolved(tmp_path: Path) -> None:
    loaded = load_project(write_project(tmp_path))
    p1, p2 = loaded.panels
    assert (p2.tag_prefix, p2.lan, p2.sheet_name) == ("P2", "B", "2")
    assert p2.devices[0].tag == "P2-L2-ESW-B01"
    assert [d.part_id for d in p2.devices] == [d.part_id for d in p1.devices]
    assert list(p2.port_plans) == ["P2-L2-ESW-B01"]
    assert p2.enclosure == p1.enclosure


def test_unknown_part_id_reports_file_path_and_line(tmp_path: Path) -> None:
    p1 = default_p1()
    p1["devices"][1]["part_id"] = "NOPE"
    project_file = write_project(tmp_path, panels={"p1.yaml": p1})
    panel_file = tmp_path / "panels" / "p1.yaml"
    line = line_of(panel_file, "NOPE")
    assert texts(project_file) == [
        f"{panel_file.as_posix()}:{line}: devices[1].part_id: "
        "unknown part_id 'NOPE' (not in library.yaml)"
    ]


def test_project_schema_error_stops_before_reading_other_files(tmp_path: Path) -> None:
    project = default_project()
    project["colour"] = "red"
    project_file = write_project(tmp_path, project=project)
    (tmp_path / "library.yaml").unlink()
    issues = issues_for(project_file)
    assert [(i.file, i.location) for i in issues] == [(project_file, "colour")]


def test_reports_issues_from_several_files_at_once(tmp_path: Path) -> None:
    library = default_library()
    library["catalogues"]["extra"] = 1
    p1 = default_p1()
    p1["devices"] = []
    p2 = default_p2()
    p2["sheet_name"] = "bad/name"
    project_file = write_project(tmp_path, library=library, panels={"p1.yaml": p1, "p2.yaml": p2})
    files = {issue.file for issue in issues_for(project_file)}
    assert files == {
        tmp_path / "library.yaml",
        tmp_path / "panels" / "p1.yaml",
        tmp_path / "panels" / "p2.yaml",
    }


def test_issues_are_sorted_by_file_then_line(tmp_path: Path) -> None:
    library = default_library()
    library["devices"].append(dict(library["devices"][1]))
    library["catalogues"]["housekeeping"]["lamp"]["part_id"] = "NOLAMP"
    p1 = default_p1()
    p1["devices"][0]["part_id"] = "NOPE"
    p1["devices"][1]["part_id"] = "NOPE"
    issues = issues_for(write_project(tmp_path, library=library, panels={"p1.yaml": p1}))
    keys = [(issue.file.as_posix(), issue.line or 0) for issue in issues]
    assert len(issues) == 4
    assert keys == sorted(keys)


def test_duplicate_library_part_id(tmp_path: Path) -> None:
    library = default_library()
    library["devices"].append(dict(library["devices"][1]))
    issues = issues_for(write_project(tmp_path, library=library))
    assert [(i.location, i.message) for i in issues] == [
        ("devices[10].part_id", "duplicate part_id 'SFP-1G-SM' (first at devices[1])")
    ]


def test_unknown_child_and_terminal_block(tmp_path: Path) -> None:
    library = default_library()
    switch = library["devices"][0]
    switch["children"] = [{"part_id": "GHOST-CHILD"}]
    switch["loose_items"] = [{"part_id": "GHOST-LOOSE"}]
    switch["terminals"] = [{"strip": "X1", "block": "NO-BLOCK", "count": 2}]
    library["catalogues"]["housekeeping"]["lamp"]["part_id"] = "NO-LAMP"
    issues = issues_for(write_project(tmp_path, library=library))
    assert [(i.location, i.message) for i in issues] == [
        ("devices[0].children[0].part_id", "unknown part_id 'GHOST-CHILD' (not in library.yaml)"),
        (
            "devices[0].loose_items[0].part_id",
            "unknown part_id 'GHOST-LOOSE' (not in library.yaml)",
        ),
        (
            "devices[0].terminals[0].block",
            "unknown terminal block 'NO-BLOCK' (not in catalogues.terminal_blocks)",
        ),
        (
            "catalogues.housekeeping.lamp.part_id",
            "unknown part_id 'NO-LAMP' (not in library.yaml)",
        ),
    ]
    assert all(issue.line is not None for issue in issues)


def test_port_plan_key_must_match_a_device(tmp_path: Path) -> None:
    p1 = default_p1()
    p1["port_plans"]["SFP-1G-SM"] = {"serial_ports": 1}  # a part_id key is fine
    p1["port_plans"]["NO-SUCH"] = {"serial_ports": 1}
    issues = issues_for(write_project(tmp_path, panels={"p1.yaml": p1}))
    assert [(i.file.name, i.location, i.message) for i in issues] == [
        ("p1.yaml", "port_plans.NO-SUCH", "no device in this panel has part_id or tag 'NO-SUCH'")
    ]


def test_unknown_grounding_busbar(tmp_path: Path) -> None:
    p1 = default_p1()
    p1["options"] = {"grounding_busbars": ["ac_safety_ground", "nope"]}
    issues = issues_for(write_project(tmp_path, panels={"p1.yaml": p1}))
    assert [(i.file.name, i.location, i.message) for i in issues] == [
        (
            "p1.yaml",
            "options.grounding_busbars[1]",
            "unknown busbar 'nope' (not in catalogues.busbars)",
        )
    ]


def test_mirror_unknown_grounding_busbar_is_reported_in_mirror_file(tmp_path: Path) -> None:
    p2 = default_p2()
    p2["options"] = {"grounding_busbars": ["ac_safety_ground", "nope"]}
    project_file = write_project(tmp_path, panels={"p2.yaml": p2})
    panel_file = tmp_path / "panels" / "p2.yaml"
    assert texts(project_file) == [
        f"{panel_file.as_posix()}:{line_of(panel_file, 'nope')}: options.grounding_busbars[1]: "
        "unknown busbar 'nope' (not in catalogues.busbars)"
    ]


def test_duplicate_sheet_names_ignore_case(tmp_path: Path) -> None:
    p1 = default_p1()
    p1["sheet_name"] = "power consumption"
    issues = issues_for(write_project(tmp_path, panels={"p1.yaml": p1}))
    assert [(i.file.name, i.location) for i in issues] == [("p1.yaml", "sheet_name")]
    assert "power consumption" in issues[0].message


def test_duplicate_sheet_name_between_panels_is_reported_in_the_later_panel(
    tmp_path: Path,
) -> None:
    p2 = default_p2()
    p2["sheet_name"] = "1"
    p1 = default_p1()
    p1["sheet_name"] = "1"
    issues = issues_for(write_project(tmp_path, panels={"p1.yaml": p1, "p2.yaml": p2}))
    assert [(i.file.name, i.location) for i in issues] == [("p2.yaml", "sheet_name")]


def test_duplicate_calculation_sheet_names_are_reported_in_the_project_file(
    tmp_path: Path,
) -> None:
    project = default_project()
    project["output"] = {"sheet_names": {"heat_calculations": "HEAT DISSIPATION"}}
    project_file = write_project(tmp_path, project=project)
    issues = issues_for(project_file)
    assert [(i.file, i.location) for i in issues] == [
        (project_file, "output.sheet_names.heat_calculations")
    ]


def test_duplicate_tag_prefix(tmp_path: Path) -> None:
    p2 = default_p2()
    p2["tag_prefix"] = "P1"
    issues = issues_for(write_project(tmp_path, panels={"p2.yaml": p2}))
    assert [(i.file.name, i.location) for i in issues] == [("p2.yaml", "tag_prefix")]
    assert "duplicate tag_prefix 'P1'" in issues[0].message


def test_duplicate_panel_id(tmp_path: Path) -> None:
    p3 = default_p1() | {"tag_prefix": "P3", "sheet_name": "3"}
    issues = issues_for(with_third_panel(tmp_path, p3))
    assert [(i.file.name, i.location) for i in issues] == [("p3.yaml", "id")]
    assert "duplicate panel id 'p1'" in issues[0].message


def test_same_panel_file_listed_twice(tmp_path: Path) -> None:
    project = default_project()
    project["panels"] = ["panels/p1.yaml", "panels/p2.yaml", "panels/../panels/p1.yaml"]
    project_file = write_project(tmp_path, project=project)
    issues = issues_for(project_file)
    assert [(i.file, i.location) for i in issues] == [(project_file, "panels[2]")]


def test_mirror_of_unknown_panel(tmp_path: Path) -> None:
    p2 = default_p2()
    p2["mirror_of"] = "zz"
    project_file = write_project(tmp_path, panels={"p2.yaml": p2})
    panel_file = tmp_path / "panels" / "p2.yaml"
    assert texts(project_file) == [
        f"{panel_file.as_posix()}:{line_of(panel_file, 'mirror_of')}: mirror_of: "
        "mirror_of 'zz' is not a panel in this project"
    ]


def test_mirror_of_a_mirror_is_rejected(tmp_path: Path) -> None:
    p3 = default_p2() | {"id": "p3", "mirror_of": "p2", "tag_prefix": "P3", "sheet_name": "3"}
    issues = issues_for(with_third_panel(tmp_path, p3))
    assert [(i.file.name, i.location, i.message) for i in issues] == [
        (
            "p3.yaml",
            "mirror_of",
            "mirror_of 'p2' is itself a mirror; mirror the original panel instead",
        )
    ]


def test_mirror_bad_option_is_reported_in_mirror_file(tmp_path: Path) -> None:
    p2 = default_p2()
    p2["options"] = {"ac_spare_branches": -1, "bogus": True}
    project_file = write_project(tmp_path, panels={"p2.yaml": p2})
    panel_file = tmp_path / "panels" / "p2.yaml"
    issues = issues_for(project_file)
    assert {(i.file, i.location) for i in issues} == {
        (panel_file, "options.ac_spare_branches"),
        (panel_file, "options.bogus"),
    }
    assert {i.line for i in issues} == {
        line_of(panel_file, "ac_spare_branches"),
        line_of(panel_file, "bogus"),
    }


def test_missing_panel_file_is_reported(tmp_path: Path) -> None:
    project = default_project()
    project["panels"] = ["panels/p1.yaml", "panels/missing.yaml"]
    issues = issues_for(write_project(tmp_path, project=project))
    assert [(i.file, i.message) for i in issues] == [
        (tmp_path / "panels" / "missing.yaml", "file not found")
    ]


def test_missing_logo_is_reported(tmp_path: Path) -> None:
    project = default_project()
    project["project"]["logo"] = "assets/logo.png"
    project_file = write_project(tmp_path, project=project)
    assert texts(project_file) == [
        f"{project_file.as_posix()}:{line_of(project_file, 'logo')}: project.logo: "
        f"file not found: {(tmp_path / 'assets' / 'logo.png').as_posix()}"
    ]
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.png").write_bytes(b"")
    assert load_project(project_file).project.project.logo == Path("assets/logo.png")


def test_loose_material_references_are_checked(tmp_path: Path) -> None:
    project = default_project()
    project["loose_material"] = {
        "host_panel": "p1",
        "items": [{"part_id": "SFP-1G-SM", "children": ["SFP-1G-SM"], "fed_from": "p2"}],
    }
    load_project(write_project(tmp_path, project=project))

    project["loose_material"] = {
        "host_panel": "zz",
        "items": [{"part_id": "GHOST", "children": ["SFP-1G-SM", "GHOST-KID"], "fed_from": "yy"}],
    }
    project_file = write_project(tmp_path, project=project)
    issues = issues_for(project_file)
    assert all(issue.file == project_file for issue in issues)
    assert [(i.location, i.message) for i in issues] == [
        ("loose_material.host_panel", "host_panel 'zz' is not a panel id in this project"),
        ("loose_material.items[0].part_id", "unknown part_id 'GHOST' (not in library.yaml)"),
        (
            "loose_material.items[0].children[1]",
            "unknown part_id 'GHOST-KID' (not in library.yaml)",
        ),
        ("loose_material.items[0].fed_from", "fed_from 'yy' is not a panel id in this project"),
    ]


def library_file_for(tmp_path: Path, library: dict[str, Any]) -> Path:
    path = tmp_path / "library.yaml"
    write_yaml(path, library)
    return path


def test_load_library_returns_library(tmp_path: Path) -> None:
    library = load_library(library_file_for(tmp_path, default_library()))
    assert library.get("RST2228-L2") is not None
    assert len(library.devices) == 10


def test_load_library_reports_duplicate_part_id(tmp_path: Path) -> None:
    data = default_library()
    data["devices"].append(dict(data["devices"][1]))
    path = library_file_for(tmp_path, data)
    with pytest.raises(InputError) as caught:
        load_library(path)
    assert [(i.file, i.location, i.message) for i in caught.value.issues] == [
        (path, "devices[10].part_id", "duplicate part_id 'SFP-1G-SM' (first at devices[1])")
    ]


def test_load_library_reports_schema_error_with_line(tmp_path: Path) -> None:
    data = default_library()
    data["devices"][1]["category"] = "toaster"
    path = library_file_for(tmp_path, data)
    with pytest.raises(InputError) as caught:
        load_library(path)
    (issue,) = caught.value.issues
    assert issue.file == path
    assert issue.location == "devices[1].category"
    assert issue.line == line_of(path, "category: toaster")
