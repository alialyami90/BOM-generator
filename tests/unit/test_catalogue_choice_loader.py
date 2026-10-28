"""Catalogue brand choice resolved per substation by the loader (ADR 0017)."""

import copy
from pathlib import Path
from typing import Any

from builders import (
    SUBSTATION_DIR,
    default_library,
    default_project,
    default_substation,
    write_project,
)
from test_loader import issues_for, line_of, load_s1

from bomgen.io.loader import load_project

ABB = {
    "id": "abb-s200m",
    "family": "S200M 2P",
    "make": "ABB",
    "ratings_a": [1, 2, 6, 10, 16],
    "code_pattern": "2CDS272{rating:03d}R0014",
}


def branded_library() -> dict[str, Any]:
    library = default_library()
    housekeeping = copy.deepcopy(library["catalogues"]["housekeeping"])
    housekeeping["fan"]["airflow_m3h"] = 200.0
    library["catalogue_brands"] = {
        "mcb": [ABB],
        "housekeeping": [{"id": "rittal", **housekeeping}],
    }
    return library


def test_without_a_choice_the_substation_uses_the_default_catalogues(tmp_path: Path) -> None:
    loaded = load_project(write_project(tmp_path, library=branded_library()))
    (substation,) = loaded.substations
    assert substation.library is loaded.library
    assert substation.library.catalogues.mcb.make == "Schneider"


def test_project_default_choice_applies_to_every_substation(tmp_path: Path) -> None:
    project = default_project()
    project["defaults"] = {"catalogue_choice": {"mcb": "abb-s200m"}}
    loaded = load_s1(write_project(tmp_path, project=project, library=branded_library()))
    assert loaded.library.catalogues.mcb.code_for(10) == "2CDS272010R0014"
    assert loaded.library.catalogues.housekeeping.fan.airflow_m3h == 110.0


def test_substation_choice_overrides_the_project_key_by_key(tmp_path: Path) -> None:
    project = default_project()
    project["defaults"] = {"catalogue_choice": {"mcb": "abb-s200m", "housekeeping": "rittal"}}
    substation = default_substation()
    substation["catalogue_choice"] = {"mcb": "default"}
    loaded = load_s1(
        write_project(tmp_path, project=project, substation=substation, library=branded_library())
    )
    assert loaded.library.catalogues.mcb.make == "Schneider"
    assert loaded.library.catalogues.housekeeping.fan.airflow_m3h == 200.0


def test_unknown_brand_in_the_substation_names_the_brands(tmp_path: Path) -> None:
    substation = default_substation()
    substation["catalogue_choice"] = {"mcb": "siemens-5sy"}
    project_file = write_project(tmp_path, substation=substation, library=branded_library())
    (issue,) = issues_for(project_file)
    substation_file = tmp_path / SUBSTATION_DIR / "substation.yaml"
    assert (issue.file, issue.location, issue.message) == (
        substation_file,
        "catalogue_choice.mcb",
        "no mcb brand 'siemens-5sy' in library.yaml (it has: default, abb-s200m)",
    )
    assert issue.line == line_of(substation_file, "siemens-5sy")


def test_unknown_brand_in_the_project_defaults_is_reported_once(tmp_path: Path) -> None:
    project = default_project()
    project["defaults"] = {"catalogue_choice": {"busbars": "copper"}}
    project_file = write_project(tmp_path, project=project, library=branded_library())
    (issue,) = issues_for(project_file)
    assert (issue.file, issue.location, issue.message) == (
        project_file,
        "defaults.catalogue_choice.busbars",
        "no busbars brand 'copper' in library.yaml (it has: default)",
    )


def test_housekeeping_brand_parts_must_be_in_the_library(tmp_path: Path) -> None:
    library = branded_library()
    library["catalogue_brands"]["housekeeping"][0]["fan"]["part_id"] = "FAN-999"
    (issue,) = issues_for(write_project(tmp_path, library=library))
    assert (issue.location, issue.message) == (
        "catalogue_brands.housekeeping[0].fan.part_id",
        "unknown part_id 'FAN-999' (not in library.yaml)",
    )
