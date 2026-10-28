"""Create and delete projects and substations (plan M17d, ADR 0021)."""

import shutil
import zipfile
from datetime import date
from pathlib import Path

import pytest

from bomgen.io import fields
from bomgen.io.edit import EditError
from bomgen.io.lifecycle import (
    create_project,
    create_substation,
    delete_project,
    delete_substation,
    project_id_for,
)
from bomgen.io.loader import load_project

EXAMPLES = Path(__file__).parents[2] / "examples"
TODAY = date(2026, 10, 28)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "jfgp2")
    return tmp_path / "jfgp2" / "project.yaml"


def new_project(tmp_path: Path) -> Path:
    # library.file keeps the test away from the installed store
    shutil.copy(EXAMPLES / "library.yaml", tmp_path / "library.yaml")
    created = create_project(
        tmp_path / "ws", "Dhahran GIS 2", library_name="psa-devices", library_version="1.0.0"
    )
    text = created.project_file.read_text("utf-8")
    created.project_file.write_text(
        text.replace("version: 1.0.0\n", "version: 1.0.0\n  file: ../../library.yaml\n"),
        "utf-8",
    )
    return created.project_file


def test_project_id_comes_from_the_name() -> None:
    assert project_id_for("Dhahran GIS 2 (Package 3)") == "dhahran-gis-2-package-3"
    assert project_id_for("***") == "project"


def test_create_project_writes_a_loadable_project(tmp_path: Path) -> None:
    project_file = new_project(tmp_path)
    assert project_file == tmp_path / "ws" / "dhahran-gis-2" / "project.yaml"
    loaded = load_project(project_file)
    assert loaded.project.project.name == "Dhahran GIS 2"
    assert loaded.substations == ()


def test_a_taken_folder_gets_a_number(tmp_path: Path) -> None:
    (tmp_path / "ws" / "dhahran-gis-2").mkdir(parents=True)
    created = create_project(
        tmp_path / "ws", "Dhahran GIS 2", library_name="psa-devices", library_version="1.0.0"
    )
    assert created.project_file.parent.name == "dhahran-gis-2-2"
    assert created.issues  # psa-devices 1.0.0 is not installed in this test's store


def test_a_blank_substation_has_its_documents_and_no_panels(tmp_path: Path) -> None:
    project_file = new_project(tmp_path)
    result = create_substation(project_file, "s1", "Dhahran", today=TODAY)
    assert result.written, result.issues
    (target,) = load_project(project_file).substations
    assert target.substation.substation.name == "Dhahran"
    assert sorted(target.documents) == ["s1-bom", "s1-heat", "s1-power"]
    assert target.panels == ()
    assert ("documents", 0, "doc_no") in fields.assumed_fields(project_file)
    assert "  - substations/s1/substation.yaml\n" in project_file.read_text("utf-8")


def test_copy_a_substation_with_its_panels_and_documents(project: Path) -> None:
    result = create_substation(project, "gis02", "GIS Substation 2", copy_from="gis01")
    assert result.written, result.issues
    loaded = load_project(project)
    copy = next(s for s in loaded.substations if s.substation.substation.id == "gis02")
    assert copy.substation.document == "gis02-bom"
    assert sorted(copy.documents) == ["gis02-bom", "gis02-heat", "gis02-power"]
    assert [p.id for p in copy.panels] == ["psa1", "psa2", "psa3", "ws"]
    assert {p.document for p in copy.panels} == {"gis02-bom"}
    text = (project.parent / "substations" / "gis02" / "substation.yaml").read_text("utf-8")
    assert "# ASSUMED" in text  # the copy keeps the source's comments


def test_create_refuses_a_bad_or_taken_id(project: Path) -> None:
    with pytest.raises(EditError, match="lower case"):
        create_substation(project, "GIS 2", "x")
    with pytest.raises(EditError, match="already exists"):
        create_substation(project, "gis01", "x")


def test_delete_substation_backs_up_first(project: Path) -> None:
    assert create_substation(project, "gis02", "GIS 2", copy_from="gis01").written
    deleted = delete_substation(project, "gis02")
    assert deleted.result.written
    assert deleted.backup is not None
    assert deleted.backup.is_file()
    names = zipfile.ZipFile(deleted.backup).namelist()
    assert "substations/gis02/substation.yaml" in names
    assert not (project.parent / "substations" / "gis02").exists()
    loaded = load_project(project)
    assert [s.substation.substation.id for s in loaded.substations] == ["gis01"]
    assert all(e.substation == "gis01" for e in loaded.project.documents)


def test_delete_project_saves_a_bomproj(project: Path, tmp_path: Path) -> None:
    saved = delete_project(project, tmp_path / "Deleted")
    assert saved == tmp_path / "Deleted" / "jfgp2-pkg3.bomproj"
    assert saved.is_file()
    assert not project.parent.exists()
