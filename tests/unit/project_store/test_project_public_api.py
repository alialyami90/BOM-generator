"""What other code (the launcher, the desktop app) imports from `bomgen.project_store`."""

from bomgen import project_store


def test_the_public_entry_points_are_exported() -> None:
    for name in (
        "backup_project",
        "default_workspace",
        "export_project",
        "import_project",
        "ProjectImportResult",
    ):
        assert hasattr(project_store, name), name
