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
from bomgen.models.library import McbCatalogue

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


def test_larger_fans_must_be_in_the_library(tmp_path: Path) -> None:
    library = branded_library()
    library["catalogues"]["housekeeping"]["larger_fans"] = [
        {"part_id": "FAN-999", "airflow_m3h": 600}
    ]
    (issue,) = issues_for(write_project(tmp_path, library=library))
    assert (issue.location, issue.message) == (
        "catalogues.housekeeping.larger_fans[0].part_id",
        "unknown part_id 'FAN-999' (not in library.yaml)",
    )


def dc_only_library() -> dict[str, Any]:
    library = branded_library()
    library["catalogue_brands"]["mcb"].append(
        {**ABB, "id": "c60h-dc", "family": "C60H-DC 2P", "ac_rated": False}
    )
    return library


def test_a_brand_not_rated_for_ac_cannot_be_the_mcb_choice(tmp_path: Path) -> None:
    substation = default_substation()
    substation["catalogue_choice"] = {"mcb": "c60h-dc"}
    project_file = write_project(tmp_path, substation=substation, library=dc_only_library())
    (issue,) = issues_for(project_file)
    substation_file = tmp_path / SUBSTATION_DIR / "substation.yaml"
    assert (issue.file, issue.location, issue.message) == (
        substation_file,
        "catalogue_choice.mcb",
        "mcb brand 'c60h-dc' is not rated for AC, and this choice also sizes the AC "
        "branches; choose an AC-rated brand (default, abb-s200m)",
    )
    assert issue.line == line_of(substation_file, "c60h-dc")


def test_a_brand_not_rated_for_ac_in_the_project_defaults_is_reported_there(
    tmp_path: Path,
) -> None:
    project = default_project()
    project["defaults"] = {"catalogue_choice": {"mcb": "c60h-dc"}}
    project_file = write_project(tmp_path, project=project, library=dc_only_library())
    (issue,) = issues_for(project_file)
    assert (issue.file, issue.location) == (project_file, "defaults.catalogue_choice.mcb")
    assert issue.message.startswith("mcb brand 'c60h-dc' is not rated for AC")


def test_an_ac_rated_brand_beside_a_dc_only_one_loads(tmp_path: Path) -> None:
    substation = default_substation()
    substation["catalogue_choice"] = {"mcb": "abb-s200m"}
    loaded = load_s1(write_project(tmp_path, substation=substation, library=dc_only_library()))
    assert loaded.library.catalogues.mcb.make == "ABB"


DC_BRAND = {**ABB, "id": "c60h-dc", "family": "C60H-DC 2P", "make": "Schneider", "dc_rating_v": 440}


def dc_library() -> dict[str, Any]:
    library = branded_library()
    library["catalogue_brands"]["mcb"].append(dict(DC_BRAND))
    return library


def test_mcb_dc_choice_sizes_dc_from_its_own_brand(tmp_path: Path) -> None:
    project = default_project()
    project["defaults"] = {"catalogue_choice": {"mcb": "abb-s200m"}}
    substation = default_substation()
    substation["catalogue_choice"] = {"mcb_dc": "c60h-dc"}
    loaded = load_s1(
        write_project(tmp_path, project=project, substation=substation, library=dc_library())
    )
    assert loaded.library.catalogues.mcb.make == "ABB"
    assert loaded.library.catalogues.dc_mcb.family == "C60H-DC 2P"


def test_an_mcb_dc_brand_without_a_dc_rating_is_refused(tmp_path: Path) -> None:
    substation = default_substation()
    substation["catalogue_choice"] = {"mcb_dc": "abb-s200m"}
    project_file = write_project(tmp_path, substation=substation, library=dc_library())
    (issue,) = issues_for(project_file)
    substation_file = tmp_path / SUBSTATION_DIR / "substation.yaml"
    assert (issue.file, issue.location, issue.message) == (
        substation_file,
        "catalogue_choice.mcb_dc",
        "mcb_dc brand 'abb-s200m' has no dc_rating_v, so it cannot size the DC branches; "
        "choose a DC-rated brand (c60h-dc)",
    )
    assert issue.line == line_of(substation_file, "mcb_dc")


def test_an_unknown_mcb_dc_brand_names_the_mcb_brands(tmp_path: Path) -> None:
    project = default_project()
    project["defaults"] = {"catalogue_choice": {"mcb_dc": "siemens-5sy"}}
    project_file = write_project(tmp_path, project=project, library=dc_library())
    (issue,) = issues_for(project_file)
    assert (issue.location, issue.message) == (
        "defaults.catalogue_choice.mcb_dc",
        "no mcb_dc brand 'siemens-5sy' in library.yaml (it has: default, abb-s200m, c60h-dc)",
    )


def test_a_brand_not_rated_for_ac_is_a_valid_mcb_dc_choice(tmp_path: Path) -> None:
    library = dc_library()
    library["catalogue_brands"]["mcb"][-1]["ac_rated"] = False
    substation = default_substation()
    substation["catalogue_choice"] = {"mcb_dc": "c60h-dc"}
    loaded = load_s1(write_project(tmp_path, substation=substation, library=library))
    assert loaded.library.catalogues.mcb.make == "Schneider"
    assert loaded.library.catalogues.dc_mcb.family == "C60H-DC 2P"
    assert type(loaded.library.catalogues.dc_mcb) is McbCatalogue
