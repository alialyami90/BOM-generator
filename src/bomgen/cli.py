"""The ``bomgen`` command line."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from bomgen import __version__
from bomgen.io.errors import InputError
from bomgen.io.loader import load_project
from bomgen.io.schema import write_json_schemas
from bomgen.library_store.cli import library_app

app = typer.Typer(no_args_is_help=True, help="Substation SCADA BOM generator.")
app.add_typer(library_app, name="library")


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"bomgen {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Substation SCADA BOM generator."""


@app.command()
def validate(
    project: Annotated[
        Path, typer.Option("--project", "-p", help="Path to the project YAML file.")
    ],
) -> None:
    """Check the project, library and panel files without building anything."""
    try:
        loaded = load_project(project)
    except InputError as error:
        for issue in error.issues:
            typer.echo(str(issue), err=True)
        typer.echo(f"{len(error.issues)} problem(s) found.", err=True)
        raise typer.Exit(1) from None
    panel_ids = ", ".join(panel.id for panel in loaded.panels)
    typer.echo(
        f"OK: {loaded.project.project.name}: {len(loaded.panels)} panels ({panel_ids}), "
        f"{len(loaded.library.devices)} library parts"
    )


@app.command()
def schema(
    out: Annotated[
        Path, typer.Option("--out", "-o", help="Directory to write the JSON Schemas into.")
    ] = Path("schemas"),
) -> None:
    """Write the JSON Schemas of the input files for editor validation."""
    for path in write_json_schemas(out):
        typer.echo(str(path))


def main() -> None:
    app()
