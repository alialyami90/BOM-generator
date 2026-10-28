"""`bomgen library ...`: build, install and roll back device-library packages (plan M8)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from bomgen.library_store.errors import LibraryPackageError
from bomgen.library_store.package import PACKAGE_SUFFIX, pack
from bomgen.library_store.store import ImportResult, LibraryStore, default_library_home

library_app = typer.Typer(
    no_args_is_help=True,
    help="Build, install and roll back device-library update packages (.bomlib).",
)


def _store() -> LibraryStore:
    return LibraryStore(default_library_home())


def _fail(exc: Exception) -> typer.Exit:
    typer.echo(f"error: {exc}", err=True)
    return typer.Exit(1)


def _report(result: ImportResult) -> None:
    manifest = result.manifest
    was = f" (active was {result.previous})" if result.previous else " (new library)"
    typer.echo(f"{manifest.name} {manifest.version}{was}")
    if manifest.release_notes:
        typer.echo(manifest.release_notes)
    for line in result.diff.summary_lines():
        typer.echo(line)


@library_app.command("pack")
def pack_command(
    library: Annotated[Path, typer.Argument(help="The library.yaml to package.")],
    name: Annotated[str, typer.Option(help="Library name, e.g. psa-devices.")],
    version: Annotated[str, typer.Option(help="Library version, MAJOR.MINOR.PATCH.")],
    out: Annotated[
        Path | None, typer.Option(help="Package file (default: <name>-<version>.bomlib).")
    ] = None,
    notes: Annotated[str, typer.Option(help="Release notes shown on import.")] = "",
    add: Annotated[
        list[Path] | None,
        typer.Option(help="Extra directory to include, e.g. data/device-db (repeatable)."),
    ] = None,
) -> None:
    """Build a .bomlib package from a library file."""
    out = out or Path(f"{name}-{version}{PACKAGE_SUFFIX}")
    try:
        manifest = pack(
            library, out, name=name, version=version, release_notes=notes, extra_dirs=add or []
        )
    except (LibraryPackageError, OSError) as exc:
        raise _fail(exc) from exc
    typer.echo(f"Wrote {out} ({manifest.name} {manifest.version}, {len(manifest.files)} files)")


@library_app.command("import")
def import_command(
    package: Annotated[Path, typer.Argument(help="The .bomlib package to install.")],
    force: Annotated[
        bool, typer.Option("--force", help="Allow a downgrade or a reinstall.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would change; install nothing.")
    ] = False,
) -> None:
    """Verify a package, show what changes, then install and activate it."""
    store = _store()
    try:
        if dry_run:
            _report(store.preview_import(package, force=force))
            typer.echo("Dry run: nothing was installed.")
            return
        result = store.import_package(package, force=force)
    except (LibraryPackageError, OSError) as exc:
        raise _fail(exc) from exc
    _report(result)
    typer.echo(f"Installed and activated {result.manifest.name} {result.manifest.version}.")


@library_app.command("list")
def list_command() -> None:
    """List installed libraries, their versions and the active one."""
    libraries = _store().list()
    if not libraries:
        typer.echo("No libraries installed.")
        return
    for library in libraries:
        active = f"{library.active} (active)" if library.active else "no active version"
        typer.echo(f"{library.name}  {active}  installed: {', '.join(library.versions)}")
        if library.problem:
            typer.echo(f"  warning: {library.problem}")


@library_app.command("rollback")
def rollback_command(
    name: Annotated[str, typer.Argument(help="Library name.")],
    to: Annotated[
        str | None, typer.Option(help="Version to activate (default: the previous one).")
    ] = None,
) -> None:
    """Switch back to an earlier installed version."""
    try:
        version = _store().rollback(name, to=to)
    except (LibraryPackageError, OSError) as exc:
        raise _fail(exc) from exc
    typer.echo(f"{name} {version} is now active.")
