"""Where imported projects live."""

from pathlib import Path

from bomgen.project_store.workspace import default_workspace


def test_default_workspace_is_documents_bom_generator(tmp_path: Path) -> None:
    assert default_workspace({}, home=tmp_path) == tmp_path / "Documents" / "BOM Generator"


def test_workspace_env_override() -> None:
    assert default_workspace({"BOMGEN_WORKSPACE": "/work/space"}, home=Path("/h")) == Path(
        "/work/space"
    )


def test_blank_workspace_override_is_ignored(tmp_path: Path) -> None:
    assert default_workspace({"BOMGEN_WORKSPACE": "  "}, home=tmp_path) == (
        tmp_path / "Documents" / "BOM Generator"
    )
