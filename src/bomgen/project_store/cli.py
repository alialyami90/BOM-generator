"""`bomgen project ...`: share and back up projects as `.bomproj` files (plan M8b)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from bomgen.bundle.errors import LibraryPackageError
from bomgen.project_store.backup import backup_project
from bomgen.project_store.export import export_project
from bomgen.project_store.importer import import_project

project_app = typer.Typer(
    no_args_is_help=True,
    help="Share and back up projects as .bomproj files.",
)


def _fail(exc: Exception) -> typer.Exit:
    typer.echo(f"error: {exc}", err=True)
    if isinstance(exc, LibraryPackageError) and exc.hint:
        typer.echo(f"hint: {exc.hint}", err=True)
    return typer.Exit(1)


@project_app.command("export")
def export_command(
    project: Annotated[Path, typer.Argument(help="The project's project.yaml.")],
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="File to write (default: <id>.bomproj).")
    ] = None,
) -> None:
    """Write the project folder (without out/ and Backups/) as one .bomproj file."""
    try:
        result = export_project(project, out)
    except (LibraryPackageError, OSError) as exc:
        raise _fail(exc) from exc
    typer.echo(
        f"Wrote {result.path} ({result.manifest.project_id}, {len(result.manifest.files)} files)"
    )


@project_app.command("import")
def import_command(
    package: Annotated[Path, typer.Argument(help="The .bomproj file to open.")],
    workspace: Annotated[
        Path | None,
        typer.Option(
            help="Folder that holds the projects (default: BOMGEN_WORKSPACE or Documents)."
        ),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Replace a project with the same id (backed up first).")
    ] = False,
    rename_to: Annotated[
        str | None,
        typer.Option(
            "--rename-to",
            metavar="ID",
            help="Import under this new project id and keep the existing project.",
        ),
    ] = None,
) -> None:
    """Verify a .bomproj file and unpack it into the workspace."""
    try:
        result = import_project(package, workspace=workspace, force=force, rename_to=rename_to)
    except (LibraryPackageError, OSError) as exc:
        raise _fail(exc) from exc
    typer.echo(f"Imported project {result.manifest.project_id} into {result.project_dir}")
    if result.replaced:
        typer.echo(f"Replaced the existing project; its backup is {result.backup}")
    if result.library_note:
        typer.echo(f"note: {result.library_note}")
        if result.library_hint:
            typer.echo(f"hint: {result.library_hint}")


@project_app.command("backup")
def backup_command(
    project: Annotated[Path, typer.Argument(help="The project's project.yaml.")],
) -> None:
    """Save the project into its Backups/ folder."""
    try:
        path = backup_project(project)
    except (LibraryPackageError, OSError) as exc:
        raise _fail(exc) from exc
    typer.echo(f"Backup saved to {path}")
