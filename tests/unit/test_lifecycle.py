"""Create and delete projects and substations (plan M17d, ADR 0021)."""

import shutil
import zipfile
from datetime import date
from pathlib import Path

import pytest

from bomgen.io import fields, lifecycle
from bomgen.io.edit import EditError
from bomgen.io.lifecycle import (
    create_project,
    create_substation,
    delete_project,
    delete_substation,
    project_id_for,
)
from bomgen.io.loader import load_project
from bomgen.project_store.export import project_files

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


def bundle_files(saved: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(saved) as zf:
        return {name: zf.read(name) for name in zf.namelist() if name != "manifest.json"}


def test_a_deleted_project_is_all_in_its_bomproj(project: Path, tmp_path: Path) -> None:
    before = project_files(project.parent)
    saved = delete_project(project, tmp_path / "Deleted")
    assert bundle_files(saved) == before


def test_a_project_folder_holding_git_is_refused_and_left_untouched(
    project: Path, tmp_path: Path
) -> None:
    (project.parent / ".git").mkdir()
    (project.parent / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    before = sorted(p.relative_to(project.parent) for p in project.parent.rglob("*"))
    with pytest.raises(EditError, match=r"holds a \.git folder"):
        delete_project(project, tmp_path / "Deleted")
    assert sorted(p.relative_to(project.parent) for p in project.parent.rglob("*")) == before
    assert not (tmp_path / "Deleted").exists()


@pytest.mark.parametrize("where", ["home", "root"])
def test_a_project_in_the_home_folder_or_a_drive_root_is_refused(
    where: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "top"
    folder.mkdir()
    (folder / "project.yaml").write_text("project: {id: p}\n", encoding="utf-8")
    if where == "home":
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: folder))
    else:
        monkeypatch.setattr(lifecycle, "_is_drive_root", lambda path: path == folder)
    with pytest.raises(EditError, match="refusing to delete"):
        delete_project(folder / "project.yaml", tmp_path / "Deleted")
    assert (folder / "project.yaml").is_file()


def test_delete_project_keeps_what_the_bomproj_does_not_carry(
    project: Path, tmp_path: Path
) -> None:
    folder = project.parent
    (folder / "out").mkdir()
    (folder / "out" / "built.xlsx").write_bytes(b"x")
    (folder / "Backups").mkdir()
    (folder / "Backups" / "old.bomproj").write_bytes(b"b")
    (folder / "notes.bomproj").write_bytes(b"n")
    delete_project(project, tmp_path / "Deleted")
    left = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*"))
    assert left == ["Backups", "Backups/old.bomproj", "notes.bomproj"]


def test_a_new_substation_writes_every_value_in_full_without_anchors(tmp_path: Path) -> None:
    project_file = new_project(tmp_path)
    assert create_substation(project_file, "s1", "Dhahran", today=TODAY).written
    text = project_file.read_text("utf-8")
    assert "&id" not in text
    assert "*id" not in text
    assert text.count("2026-10-28") >= 3


def test_a_blank_substation_seeds_generated_panels_so_equipment_can_be_added(
    tmp_path: Path,
) -> None:
    project_file = new_project(tmp_path)
    assert create_substation(project_file, "gis02", "GIS 2", today=TODAY).written
    equipment = [
        {"id": "l2", "part_id": "RST2228-L2", "role": "l2_switch", "redundant": True},
        {"id": "l1", "role": "l1_switch", "redundant": True},
    ]
    result = fields.set_field(project_file, ("equipment",), equipment, substation="gis02")
    assert result.written, result.issues
    (target,) = load_project(project_file).substations
    seeded = target.substation.generated_panels
    assert seeded is not None
    assert seeded.document == "gis02-bom"
    assert seeded.cabinet_number.format(n=1) == "GIS02-PSA-0001"
    assert seeded.options == {"inter_panel_terminals": 40}  # network cabinets (spec, XIP)
    assert [e.id for e in target.substation.equipment] == ["l2", "l1"]
    substation_file = project_file.parent / "substations" / "gis02" / "substation.yaml"
    assumed = fields.assumed_fields(substation_file)
    assert ("generated_panels", "enclosure") in assumed
    assert ("generated_panels", "cabinet_number") in assumed


def test_a_copied_substation_keeps_its_sources_generated_panels(project: Path) -> None:
    assert create_substation(project, "gis02", "GIS 2", copy_from="gis01").written
    copy = next(
        s for s in load_project(project).substations if s.substation.substation.id == "gis02"
    )
    seeded = copy.substation.generated_panels
    assert seeded is not None
    assert seeded.cabinet_number == "861-GIS01-PSA-{n:04d}"  # the source's block, as written
    assert seeded.document == "gis02-bom"
