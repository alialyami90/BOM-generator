"""Keep both: import a project under a new id when its own id is taken (ADR 0012)."""

from pathlib import Path

import pytest
from project_builders import FILES, PROJECT_YAML, make_project

from bomgen.bundle.container import sha256
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.store import LibraryStore
from bomgen.project_store.export import export_project, read_project_identity
from bomgen.project_store.importer import import_project
from bomgen.project_store.preview import preview_project_import
from bomgen.project_store.rename import rewrite_project_id, suggest_project_id


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


@pytest.fixture
def package(tmp_path: Path) -> Path:
    project_file = make_project(tmp_path / "source" / "jfgp2")
    return export_project(project_file, tmp_path / "jfgp2.bomproj").path


# -- rewriting project.id ----------------------------------------------------------------


def test_only_the_project_id_line_changes() -> None:
    text = "# header\nproject:\n  id: jfgp2  # the id\n  name: Plant\nlibrary:\n  name: psa\n"

    assert rewrite_project_id(text, "jfgp2-2") == text.replace("jfgp2  #", "jfgp2-2  #")


def test_a_quoted_id_stays_quoted_and_line_endings_are_kept() -> None:
    text = 'project:\r\n  id: "jfgp2"\r\n  name: Plant\r\n'

    assert rewrite_project_id(text, "jfgp2-2") == 'project:\r\n  id: "jfgp2-2"\r\n  name: Plant\r\n'


def test_an_id_that_yaml_would_read_as_a_number_is_quoted() -> None:
    assert rewrite_project_id("project:\n  id: a\n", "1.5") == 'project:\n  id: "1.5"\n'


def test_only_the_id_under_project_is_rewritten() -> None:
    text = "library:\n  id: other\nproject:\n  name: X\n  id: a\nextra:\n  id: b\n"

    assert rewrite_project_id(text, "z") == (
        "library:\n  id: other\nproject:\n  name: X\n  id: z\nextra:\n  id: b\n"
    )


def test_a_byte_order_mark_is_kept() -> None:
    assert rewrite_project_id("﻿project:\n  id: a\n", "b") == "﻿project:\n  id: b\n"


def test_flow_style_project_is_refused() -> None:
    with pytest.raises(LibraryPackageError, match="cannot rewrite") as caught:
        rewrite_project_id("project: {id: a, name: X}\n", "b")

    assert caught.value.kind is RefusalKind.INVALID_PROJECT


# -- importing under a new id --------------------------------------------------------------


def test_import_under_a_new_id_keeps_the_existing_project(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    existing = make_project(workspace / "jfgp2")
    (existing.parent / "mine.txt").write_text("keep me")

    result = import_project(package, workspace=workspace, store=store, rename_to="jfgp2-2")

    assert result.project_dir == workspace / "jfgp2-2"
    assert not result.replaced
    assert result.backup is None
    assert (workspace / "jfgp2" / "mine.txt").read_text() == "keep me"
    assert read_project_identity(result.project_dir / "project.yaml").id == "jfgp2-2"
    assert result.manifest.project_id == "jfgp2-2"
    new_yaml = (result.project_dir / "project.yaml").read_bytes()
    assert result.manifest.files["project.yaml"] == sha256(new_yaml)
    assert new_yaml.decode() == PROJECT_YAML.replace("id: jfgp2", "id: jfgp2-2")
    for name, text in FILES.items():
        assert (result.project_dir / name).read_text() == text


def test_the_renamed_project_exports_cleanly_again(
    tmp_path: Path, workspace: Path, package: Path, store: LibraryStore
) -> None:
    result = import_project(package, workspace=workspace, store=store, rename_to="copy")

    again = export_project(result.project_dir / "project.yaml", tmp_path / "copy.bomproj")

    assert again.manifest.project_id == "copy"


def test_the_library_note_still_comes_from_the_package(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    result = import_project(package, workspace=workspace, store=store, rename_to="copy")

    assert result.library_note is not None
    assert "psa-devices 1.2.0" in result.library_note


def test_a_taken_new_id_is_refused_and_nothing_is_written(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    make_project(workspace / "jfgp2")
    make_project(workspace / "taken")
    before = sorted(p.name for p in workspace.iterdir())

    with pytest.raises(LibraryPackageError, match="'taken' already exists") as caught:
        import_project(package, workspace=workspace, store=store, rename_to="taken")

    assert caught.value.kind is RefusalKind.PROJECT_EXISTS
    assert sorted(p.name for p in workspace.iterdir()) == before


@pytest.mark.parametrize("bad", ["../escape", "", "con", "a/b", "x" * 65])
def test_an_unsafe_new_id_is_refused(
    workspace: Path, package: Path, store: LibraryStore, bad: str
) -> None:
    with pytest.raises(LibraryPackageError) as caught:
        import_project(package, workspace=workspace, store=store, rename_to=bad)

    assert caught.value.kind is RefusalKind.INVALID_PROJECT
    assert not workspace.exists()


def test_a_new_id_cannot_be_combined_with_force(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    with pytest.raises(LibraryPackageError, match="force") as caught:
        import_project(package, workspace=workspace, store=store, rename_to="copy", force=True)

    assert caught.value.kind is RefusalKind.INVALID_PROJECT


def test_a_project_yaml_that_cannot_be_rewritten_is_refused_before_writing(
    tmp_path: Path, workspace: Path, store: LibraryStore
) -> None:
    flow = PROJECT_YAML.replace(
        "project:\n  id: jfgp2\n  name: JAFURAH JFGP2 PKG.3\n", "project: {id: jfgp2, name: X}\n"
    )
    package = export_project(
        make_project(tmp_path / "flow" / "jfgp2", flow), tmp_path / "flow.bomproj"
    ).path

    with pytest.raises(LibraryPackageError, match="cannot rewrite"):
        import_project(package, workspace=workspace, store=store, rename_to="copy")

    assert not workspace.exists()


# -- suggesting a free id -----------------------------------------------------------------


def test_the_suggestion_is_the_first_free_numbered_id(tmp_path: Path) -> None:
    (tmp_path / "jfgp2").mkdir()
    (tmp_path / "jfgp2-2").mkdir()

    assert suggest_project_id("jfgp2", tmp_path) == "jfgp2-3"


def test_a_long_id_is_shortened_to_fit(tmp_path: Path) -> None:
    suggestion = suggest_project_id("a" * 64, tmp_path)

    assert suggestion == "a" * 62 + "-2"


def test_the_preview_suggests_an_id_only_when_the_project_exists(
    workspace: Path, package: Path, store: LibraryStore
) -> None:
    free = preview_project_import(package, workspace=workspace, store=store)
    make_project(workspace / "jfgp2")
    taken = preview_project_import(package, workspace=workspace, store=store)

    assert free.suggested_id is None
    assert taken.suggested_id == "jfgp2-2"
