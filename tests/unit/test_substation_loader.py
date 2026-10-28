"""Loading projects with substations: defaults, register keys, equipment, library (ADR 0012)."""

from pathlib import Path
from typing import Any

import pytest
from builders import (
    SUBSTATION_DIR,
    default_library,
    default_p1,
    default_p2,
    default_project,
    default_substation,
    write_project,
    write_yaml,
)

from bomgen.io.errors import InputError, Issue
from bomgen.io.loader import (
    LoadedProject,
    LoadedSubstation,
    load_inputs,
    load_project,
    load_substation,
)
from bomgen.library_store.package import pack
from bomgen.library_store.service import import_library
from bomgen.library_store.store import LibraryStore

ENCLOSURE = {
    "make": "Rawabi",
    "model": "Fixed Frame",
    "h_mm": 2100,
    "d_mm": 1000,
    "w_mm": 800,
    "cable_entry": "top",
}


def issues_for(project_file: Path) -> list[Issue]:
    with pytest.raises(InputError) as caught:
        load_project(project_file)
    return list(caught.value.issues)


def where(issues: list[Issue]) -> list[tuple[str, str, str]]:
    return [(i.file.name, i.location, i.message) for i in issues]


def with_equipment(substation: dict[str, Any]) -> dict[str, Any]:
    substation["equipment"] = [
        {"id": "l2", "part_id": "RST2228-L2", "role": "l2_switch", "redundant": True},
        {"id": "l1", "role": "l1_switch", "redundant": True},
    ]
    substation["generated_panels"] = {
        "id": "p{n}",
        "cabinet_number": "CAB-{n:03d}",
        "cabinet_name": "Cabinet {n}",
        "tag_prefix": "P{n}",
        "sheet_name": "{n}",
        "enclosure": ENCLOSURE,
        "document": "s1-bom",
    }
    return substation


def library_with_heights() -> dict[str, Any]:
    library = default_library()
    library["devices"][0]["height_u"] = 1
    l1_switch = {**library["devices"][0], "part_id": "RST2228-L1", "purdue_level": "L1"}
    library["devices"].append(l1_switch)
    return library


def test_load_project_returns_substations_with_merged_defaults(tmp_path: Path) -> None:
    project = default_project()
    project["defaults"] = {"spares": {"sfp_per_l1": 4}, "constants": {"t_max_c": 45}}
    substation = default_substation()
    substation["spares"] = {"port_fraction": 0.1}
    substation["constants"] = {"t_int_c": 40}
    loaded = load_project(write_project(tmp_path, project=project, substation=substation))
    (s1,) = loaded.substations
    assert (s1.spares.sfp_per_l1, s1.spares.port_fraction, s1.spares.ac_branches) == (4, 0.1, 1)
    assert (s1.constants.t_max_c, s1.constants.t_int_c) == (45, 40)
    assert sorted(s1.documents) == ["p1-bom", "p2-bom", "s1-bom", "s1-calc"]
    assert s1.panel_capacity_u == 32
    assert s1.manual_panel_ids == frozenset()


def test_merged_constants_that_break_t_max_are_reported_in_the_substation(tmp_path: Path) -> None:
    substation = default_substation()
    substation["constants"] = {"t_int_c": 40}
    issues = issues_for(write_project(tmp_path, substation=substation))
    assert where(issues) == [
        ("substation.yaml", "constants", "t_max_c must be greater than t_int_c")
    ]


def test_load_substation_finds_its_project(tmp_path: Path) -> None:
    write_project(tmp_path)
    substation_file = tmp_path / SUBSTATION_DIR / "substation.yaml"
    loaded = load_substation(substation_file)
    assert loaded.file == substation_file
    assert loaded.project.project.id == "gis"
    assert [p.id for p in loaded.panels] == ["p1", "p2"]


def test_substation_without_project_is_reported(tmp_path: Path) -> None:
    substation_file = tmp_path / "substation.yaml"
    write_yaml(substation_file, default_substation())
    with pytest.raises(InputError) as caught:
        load_substation(substation_file)
    (issue,) = caught.value.issues
    assert issue.file == substation_file
    assert "no project.yaml in a folder above lists this substation" in issue.message


def test_load_inputs_detects_file_kind(tmp_path: Path) -> None:
    project_file = write_project(tmp_path)
    assert isinstance(load_inputs(project_file), LoadedProject)
    assert isinstance(load_inputs(tmp_path / SUBSTATION_DIR / "substation.yaml"), LoadedSubstation)


def test_substation_listed_twice(tmp_path: Path) -> None:
    project = default_project()
    project["substations"] = [
        "substations/s1/substation.yaml",
        "substations/../substations/s1/substation.yaml",
    ]
    issues = issues_for(write_project(tmp_path, project=project))
    assert where(issues) == [
        ("project.yaml", "substations[1]", "substation file listed twice (first at substations[0])")
    ]


def test_missing_substation_file_is_reported(tmp_path: Path) -> None:
    project = default_project()
    project["substations"].append("substations/s2/substation.yaml")
    issues = issues_for(write_project(tmp_path, project=project))
    assert [(i.file, i.message) for i in issues] == [
        (tmp_path / "substations" / "s2" / "substation.yaml", "file not found")
    ]


def test_duplicate_substation_id(tmp_path: Path) -> None:
    project = default_project()
    project["substations"].append("substations/s2/substation.yaml")
    project_file = write_project(tmp_path, project=project)
    s2 = default_substation()
    s2["panels"] = ["../s1/panels/p1.yaml"]
    write_yaml(tmp_path / "substations" / "s2" / "substation.yaml", s2)
    issues = issues_for(project_file)
    assert (
        "substation.yaml",
        "substation.id",
        "duplicate substation id 's1' (first in "
        f"{(tmp_path / SUBSTATION_DIR / 'substation.yaml').as_posix()})",
    ) in where(issues)


def test_register_entry_names_unknown_substation(tmp_path: Path) -> None:
    project = default_project()
    project["documents"][3]["substation"] = "s9"
    issues = issues_for(write_project(tmp_path, project=project))
    assert (
        "project.yaml",
        "documents[3].substation",
        "substation 's9' is not listed in substations",
    ) in where(issues)


def test_panel_document_key_must_exist(tmp_path: Path) -> None:
    p1 = default_p1()
    p1["document"] = "nope"
    issues = issues_for(write_project(tmp_path, panels={"p1.yaml": p1}))
    assert where(issues) == [
        ("p1.yaml", "document", "unknown document key 'nope' (not in the project's documents)")
    ]


def test_panel_document_key_of_other_substation(tmp_path: Path) -> None:
    project = default_project()
    project["documents"][1]["substation"] = "s2"
    project["substations"].append("substations/s2/substation.yaml")
    project_file = write_project(tmp_path, project=project)
    s2 = default_substation()
    s2["substation"]["id"] = "s2"
    s2["panels"] = []
    s2["manual_panels"] = ["panels/q1.yaml"]
    s2_dir = tmp_path / "substations" / "s2"
    write_yaml(s2_dir / "substation.yaml", s2)
    write_yaml(s2_dir / "panels" / "q1.yaml", default_p1() | {"document": "p2-bom"})
    issues = issues_for(project_file)
    assert (
        "p1.yaml",
        "document",
        "document 'p1-bom' belongs to substation 's2', not 's1'",
    ) in where(issues)


def test_calculation_document_key_must_exist(tmp_path: Path) -> None:
    substation = default_substation()
    substation["calculations"]["heat_dissipation"] = {"document": "zz", "scope": "x"}
    issues = issues_for(write_project(tmp_path, substation=substation))
    assert where(issues) == [
        (
            "substation.yaml",
            "calculations.heat_dissipation.document",
            "unknown document key 'zz' (not in the project's documents)",
        )
    ]


def test_equipment_part_needs_height_u(tmp_path: Path) -> None:
    substation = with_equipment(default_substation())
    substation["equipment"][1]["part_id"] = "RST2228-L2"
    issues = issues_for(write_project(tmp_path, substation=substation))
    message = "height_u is needed for the panel layout ('RST2228-L2' has none)"
    assert where(issues) == [
        ("substation.yaml", "equipment[0].part_id", message),
        ("substation.yaml", "equipment[1].part_id", message),
        (
            "substation.yaml",
            "equipment[1].part_id",
            "a pinned l1_switch must be an L1 network_switch part (RST2228-L2 is L2)",
        ),
    ]
    del substation["equipment"][1]["part_id"]
    loaded = load_project(
        write_project(tmp_path, library=library_with_heights(), substation=substation)
    )
    assert loaded.substations[0].substation.equipment[0].role == "l2_switch"


def test_unpinned_l1_switch_needs_a_library_candidate(tmp_path: Path) -> None:
    substation = with_equipment(default_substation())
    library = default_library()
    library["devices"][0]["height_u"] = 1
    issues = issues_for(write_project(tmp_path, library=library, substation=substation))
    message = (
        "no L1 network_switch with height_u in library.yaml for the tool to pick; "
        "add one or set part_id"
    )
    assert where(issues) == [("substation.yaml", "equipment[1]", message)]
    library = library_with_heights()
    library["devices"][-1]["height_u"] = None
    issues = issues_for(write_project(tmp_path, library=library, substation=substation))
    assert where(issues) == [("substation.yaml", "equipment[1]", message)]


def test_equipment_unknown_part_and_non_switch_role(tmp_path: Path) -> None:
    substation = with_equipment(default_substation())
    substation["equipment"][1]["part_id"] = "LAMP"
    substation["equipment"].append({"id": "ghost", "part_id": "GHOST", "role": "other"})
    library = library_with_heights()
    library["devices"][2]["height_u"] = 0
    issues = issues_for(write_project(tmp_path, library=library, substation=substation))
    assert where(issues) == [
        (
            "substation.yaml",
            "equipment[1].part_id",
            "an l1_switch must be a network_switch part, not lamp",
        ),
        (
            "substation.yaml",
            "equipment[2].part_id",
            "unknown part_id 'GHOST' (not in library.yaml)",
        ),
    ]


def test_generated_panel_options_are_checked_per_panel(tmp_path: Path) -> None:
    substation = with_equipment(default_substation())
    substation["generated_panels"]["options"] = {"aux_socket_a": 10}
    substation["generated_panels"]["options_by_panel"] = {2: {"bogus": 1}}
    issues = issues_for(
        write_project(tmp_path, library=library_with_heights(), substation=substation)
    )
    assert where(issues) == [
        (
            "substation.yaml",
            "generated_panels.options_by_panel[2].bogus",
            "unknown key (check spelling)",
        )
    ]


def test_rack_u_reserved_must_leave_capacity(tmp_path: Path) -> None:
    substation = default_substation()
    substation["spares"] = {"rack_u_reserved": 42}
    issues = issues_for(write_project(tmp_path, substation=substation))
    message = "rack_u_reserved 42 leaves no usable rack space (catalogues.enclosure_u is 42)"
    assert where(issues) == [("substation.yaml", "spares.rack_u_reserved", message)]
    project = default_project()
    project["defaults"] = {"spares": {"rack_u_reserved": 50}}
    issues = issues_for(write_project(tmp_path, project=project))
    message = "rack_u_reserved 50 leaves no usable rack space (catalogues.enclosure_u is 42)"
    assert where(issues) == [("project.yaml", "defaults.spares.rack_u_reserved", message)]


def test_manual_panels_follow_generated_panels(tmp_path: Path) -> None:
    substation = default_substation()
    substation["panels"] = ["panels/p2.yaml"]
    substation["manual_panels"] = ["panels/p1.yaml"]
    (s1,) = load_project(write_project(tmp_path, substation=substation)).substations
    assert [p.id for p in s1.panels] == ["p2", "p1"]
    assert s1.manual_panel_ids == frozenset({"p1"})


def installed_store(tmp_path: Path) -> LibraryStore:
    source = tmp_path / "src" / "library.yaml"
    write_yaml(source, default_library())
    package = tmp_path / "src" / "test-lib.bomlib"
    pack(source, package, name="test-lib", version="1.0.0")
    store = LibraryStore(tmp_path / "store")
    import_library(package, store=store)
    return store


def test_library_from_store_by_name_and_version(tmp_path: Path) -> None:
    store = installed_store(tmp_path)
    project = default_project()
    project["library"] = {"name": "test-lib", "version": "1.0.0"}
    project_file = write_project(tmp_path / "p", project=project)
    (tmp_path / "p" / "library.yaml").unlink()
    loaded = load_project(project_file, store=store)
    assert loaded.library.get("RST2228-L2") is not None


def test_library_not_installed_is_reported(tmp_path: Path) -> None:
    store = installed_store(tmp_path)
    project = default_project()
    project["library"] = {"name": "test-lib", "version": "2.0.0"}
    project_file = write_project(tmp_path / "p", project=project)
    with pytest.raises(InputError) as caught:
        load_project(project_file, store=store)
    assert where(list(caught.value.issues)) == [
        ("project.yaml", "library", "library test-lib 2.0.0 is not installed")
    ]


def test_misspelt_root_keys_reach_the_right_model(tmp_path: Path) -> None:
    project = default_project()
    project["substation"] = project.pop("substations")
    project_file = write_project(tmp_path, project=project)
    with pytest.raises(InputError) as caught:
        load_inputs(project_file)
    assert {i.location for i in caught.value.issues} == {"substations", "substation"}
    substation = default_substation()
    substation["substations"] = substation.pop("substation")
    write_project(tmp_path, substation=substation)
    with pytest.raises(InputError) as caught:
        load_inputs(tmp_path / SUBSTATION_DIR / "substation.yaml")
    assert {i.location for i in caught.value.issues} == {"substation", "substations"}


def test_broken_project_file_above_a_substation_is_reported(tmp_path: Path) -> None:
    project_file = write_project(tmp_path)
    project_file.write_text(project_file.read_text() + "bad: [\n", encoding="utf-8")
    with pytest.raises(InputError) as caught:
        load_substation(tmp_path / SUBSTATION_DIR / "substation.yaml")
    assert [i.file for i in caught.value.issues] == [project_file]


def test_inherited_rack_reserve_is_reported_once(tmp_path: Path) -> None:
    project = default_project()
    project["defaults"] = {"spares": {"rack_u_reserved": 42}}
    project["substations"].append("substations/s2/substation.yaml")
    project["documents"].append(project["documents"][0] | {"key": "s2-bom", "substation": "s2"})
    project["documents"].append(project["documents"][3] | {"key": "s2-calc", "substation": "s2"})
    project_file = write_project(tmp_path, project=project)
    s2 = default_substation()
    s2["substation"]["id"] = "s2"
    s2["document"] = "s2-bom"
    for sheet in s2["calculations"].values():
        sheet["document"] = "s2-calc"
    s2["panels"] = []
    s2["manual_panels"] = ["panels/q1.yaml"]
    s2_dir = tmp_path / "substations" / "s2"
    write_yaml(s2_dir / "substation.yaml", s2)
    write_yaml(s2_dir / "panels" / "q1.yaml", default_p1() | {"document": "s2-bom"})
    issues = issues_for(project_file)
    assert [(i.file.name, i.location) for i in issues] == [
        ("project.yaml", "defaults.spares.rack_u_reserved")
    ]


def test_generated_panel_busbars_are_checked(tmp_path: Path) -> None:
    substation = with_equipment(default_substation())
    substation["generated_panels"]["options"] = {"grounding_busbars": ["nope"]}
    issues = issues_for(
        write_project(tmp_path, library=library_with_heights(), substation=substation)
    )
    assert [(i.location, i.message) for i in issues] == [
        (
            "generated_panels.options.grounding_busbars[0]",
            "unknown busbar 'nope' (not in catalogues.busbars)",
        )
    ]


def test_bad_document_key_of_an_unresolved_mirror_is_still_reported(tmp_path: Path) -> None:
    p2 = default_p2() | {"mirror_of": "zz", "document": "nokey"}
    issues = issues_for(write_project(tmp_path, panels={"p2.yaml": p2}))
    assert sorted(i.location for i in issues) == ["document", "mirror_of"]


def test_manual_panel_cannot_be_generated(tmp_path: Path) -> None:
    substation = default_substation()
    substation["panels"] = ["panels/p1.yaml", "panels/p2.yaml"]
    substation["manual_panels"] = ["panels/p3.yaml"]
    p3 = default_p1() | {"id": "p3", "tag_prefix": "P3", "sheet_name": "3", "generated": True}
    issues = issues_for(write_project(tmp_path, substation=substation, panels={"p3.yaml": p3}))
    assert where(issues) == [
        (
            "p3.yaml",
            "generated",
            "a manual panel is never written by the layout; remove generated: true",
        )
    ]
