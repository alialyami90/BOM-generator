"""Creating, renaming and deleting projects and substations in the app (plan M17d, ADR 0021).

The writers are tested in the io tests; these cover the bridge: ids from names, what the page
gets back, the recent list and the backups a delete leaves.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
    package = tmp_path / "lib.bomlib"
    pack(EXAMPLES / "library.yaml", package, name="psa-devices", version="1.0.0")
    LibraryStore(tmp_path / "libraries").import_package(package)
    return api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
            "BOMGEN_APP_HOME": str(tmp_path / "app"),
        }
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)
    return envelope["data"]


def refused(envelope: dict[str, object]) -> dict[str, str]:
    assert envelope["ok"] is False, envelope
    return envelope["error"]  # type: ignore[return-value]


def test_new_project_dialog_offers_installed_versions_and_the_folder(
    app: api.Api, tmp_path: Path
) -> None:
    form = ok(app.new_project_form("North Gas Plant"))
    assert form["folder"] == str(tmp_path / "workspace" / "north-gas-plant")
    assert form["library"] == {"name": "psa-devices", "version": "1.0.0"}
    assert form["versions"] == ["1.0.0"]


def test_a_new_project_is_written_in_the_workspace_with_its_first_substation(
    app: api.Api, tmp_path: Path
) -> None:
    made = ok(app.create_project("North Gas Plant", "Aramco", "1.0.0", "GIS Building 1"))
    file = Path(made["project_file"])
    assert file == tmp_path / "workspace" / "north-gas-plant" / "project.yaml"
    assert made["substation"] == "gis-building-1"
    data = read_yaml(file).data
    assert data["project"]["client"] == "Aramco"
    assert data["library"] == {"name": "psa-devices", "version": "1.0.0"}
    assert data["substations"] == ["substations/gis-building-1/substation.yaml"]
    assert any(p["file"] == str(file) for p in ok(app.list_projects()))


def test_a_new_project_without_a_name_is_refused(app: api.Api) -> None:
    assert refused(app.create_project("  ", None, "1.0.0", None))["kind"] == "invalid_edit"


def test_a_new_substation_takes_its_folder_from_the_name(app: api.Api, project: Path) -> None:
    made = ok(app.create_substation(str(project), "Substation 2", None))
    assert made["id"] == "substation-2"
    assert (project.parent / "substations" / "substation-2" / "substation.yaml").is_file()


def test_a_copied_substation_keeps_the_panels(app: api.Api, project: Path) -> None:
    made = ok(app.create_substation(str(project), "GIS 02", "gis01"))
    folder = project.parent / "substations" / made["id"]
    assert sorted(p.name for p in folder.rglob("*.yaml")) == sorted(
        p.name for p in (project.parent / "substations" / "gis01").rglob("*.yaml")
    )


def test_a_substation_name_whose_folder_exists_gets_a_free_id(app: api.Api, project: Path) -> None:
    assert ok(app.create_substation(str(project), "gis01", None))["id"] == "gis01-2"


def test_rename_changes_the_name_not_the_folder(app: api.Api, project: Path) -> None:
    ok(app.rename_substation(str(project), "gis01", "GIS Building A"))
    file = project.parent / "substations" / "gis01" / "substation.yaml"
    assert read_yaml(file).data["substation"]["name"] == "GIS Building A"
    ok(app.rename_project(str(project), "Renamed project"))
    assert read_yaml(project).data["project"]["name"] == "Renamed project"
    assert read_yaml(project).data["project"]["id"] == "jfgp2-pkg3"


def test_an_empty_name_is_refused_on_rename(app: api.Api, project: Path) -> None:
    assert refused(app.rename_project(str(project), " "))["kind"] == "invalid_edit"


def test_deleting_a_substation_saves_a_backup_first(app: api.Api, project: Path) -> None:
    made = ok(app.create_substation(str(project), "Spare", None))
    deleted = ok(app.delete_substation(str(project), made["id"]))
    assert Path(deleted["backup"]).is_file()
    assert not (project.parent / "substations" / made["id"]).exists()


def test_deleting_a_project_keeps_a_restorable_file_and_drops_it_from_the_list(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    deleted = ok(app.delete_project(str(project)))
    saved = Path(deleted["saved"])
    assert saved.is_file()
    assert saved.parent == tmp_path / "app" / "deleted-projects"
    assert not project.parent.exists()
    assert all(p["file"] != str(project) for p in ok(app.list_projects()))
