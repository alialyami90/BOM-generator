"""The ``bomgen`` command line."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from bomgen import __version__
from bomgen.engine.errors import EngineError
from bomgen.engine.pipeline import build as build_bom
from bomgen.io.errors import InputError
from bomgen.io.loader import LoadedProject, LoadedSubstation, load_inputs
from bomgen.io.schema import write_json_schemas
from bomgen.library_store.cli import library_app
from bomgen.project_store.cli import project_app
from bomgen.sheets.workbook import build_workbook
from bomgen.writer import WriterError, write_workbook

app = typer.Typer(no_args_is_help=True, help="Substation SCADA BOM generator.")
app.add_typer(library_app, name="library")
app.add_typer(project_app, name="project")


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


def _panel_summary(substation: LoadedSubstation) -> str:
    panel_ids = ", ".join(panel.id for panel in substation.panels)
    return f"{len(substation.panels)} panels ({panel_ids})"


def _load_or_exit(path: Path) -> LoadedProject | LoadedSubstation:
    try:
        return load_inputs(path)
    except InputError as error:
        for issue in error.issues:
            typer.echo(str(issue), err=True)
        typer.echo(f"{len(error.issues)} problem(s) found.", err=True)
        raise typer.Exit(1) from None


@app.command()
def validate(
    file: Annotated[
        Path | None,
        typer.Argument(help="A project.yaml or a substation.yaml.", show_default=False),
    ] = None,
    project: Annotated[
        Path | None,
        typer.Option("--project", "-p", help="Same as FILE, kept for older scripts."),
    ] = None,
) -> None:
    """Check a project or substation, its library and panel files, building nothing."""
    if (file is None) == (project is None):
        raise typer.BadParameter("give one project or substation file, as FILE or --project")
    path = file if file is not None else project
    assert path is not None
    loaded = _load_or_exit(path)
    parts = f"{len(loaded.library.devices)} library parts"
    if isinstance(loaded, LoadedProject):
        substations = "; ".join(
            f"{s.substation.substation.id}: {_panel_summary(s)}" for s in loaded.substations
        )
        count = len(loaded.substations)
        typer.echo(
            f"OK: {loaded.project.project.name}: {count} substation(s); {substations}; {parts}"
        )
    else:
        typer.echo(
            f"OK: {loaded.project.project.name} / {loaded.substation.substation.id}: "
            f"{_panel_summary(loaded)}, {parts}"
        )


def _workbook_name(substation: LoadedSubstation) -> str:
    """The workbook file name (spec: Output requirements, OUT-2)."""
    document = substation.documents[substation.substation.document]
    return substation.substation.output.file_name.format(doc_no=document.doc_no, rev=document.rev)


def _selected(
    loaded: LoadedProject | LoadedSubstation, substation_id: str | None
) -> list[LoadedSubstation]:
    substations = list(loaded.substations) if isinstance(loaded, LoadedProject) else [loaded]
    if substation_id is None:
        return substations
    chosen = [s for s in substations if s.substation.substation.id == substation_id]
    if not chosen:
        known = ", ".join(s.substation.substation.id for s in substations)
        raise typer.BadParameter(
            f"no substation '{substation_id}' (the project has: {known})",
            param_hint="--substation",
        )
    return chosen


@app.command()
def build(
    file: Annotated[
        Path, typer.Argument(help="A project.yaml or a substation.yaml.", show_default=False)
    ],
    out: Annotated[
        Path, typer.Option("--out", "-o", help="Directory to write the workbooks into.")
    ] = Path("out"),
    substation: Annotated[
        str | None,
        typer.Option("--substation", "-s", help="Build only the substation with this id."),
    ] = None,
) -> None:
    """Build one BOM workbook per substation and print each file's path."""
    loaded = _load_or_exit(file)
    targets = _selected(loaded, substation)
    for target in targets:
        try:
            workbook = build_workbook(target, build_bom(target), logo=target.logo)
            path = write_workbook(workbook, out / _workbook_name(target))
        except (EngineError, WriterError) as error:
            typer.echo(f"{target.substation.substation.id}: {error}", err=True)
            raise typer.Exit(1) from None
        typer.echo(str(path))


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
