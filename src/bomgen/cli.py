"""The ``bomgen`` command line."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer
import yaml

from bomgen import __version__
from bomgen.checks import check_report, render_text
from bomgen.checks import render_json as render_checks_json
from bomgen.engine.errors import EngineError
from bomgen.engine.pipeline import build as build_bom
from bomgen.io.errors import InputError
from bomgen.io.loader import LoadedProject, LoadedSubstation, load_inputs, load_substation
from bomgen.io.schema import write_json_schemas
from bomgen.library_store.cli import library_app
from bomgen.project_store.cli import project_app
from bomgen.revision import compare_with_previous, read_previous_issue, render_revisions
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


def _exit_on_input_error(error: InputError) -> NoReturn:
    for issue in error.issues:
        typer.echo(str(issue), err=True)
    typer.echo(f"{len(error.issues)} problem(s) found.", err=True)
    raise typer.Exit(1) from None


def _load_or_exit(path: Path) -> LoadedProject | LoadedSubstation:
    try:
        return load_inputs(path)
    except InputError as error:
        _exit_on_input_error(error)


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
    compare: Annotated[
        Path | None,
        typer.Option(
            "--compare",
            help="Mark the cells changed since this previously issued workbook (OUT-8). "
            "It is read from the values Excel last saved: a file re-saved by a non-Excel "
            "tool has no formula results, so formula cells such as =24+3 show as changed.",
            show_default=False,
        ),
    ] = None,
    no_checks: Annotated[bool, typer.Option("--no-checks", help="Skip the check report.")] = False,
    no_layout: Annotated[
        bool, typer.Option("--no-layout", help="Build the panel files as they are.")
    ] = False,
) -> None:
    """Build one BOM workbook per substation, print each file's path and its check report.

    Exits 1 when a check fails; the report is also written next to the workbook as
    <name>.checks.json.
    """
    from bomgen.engine.layout import with_layout

    loaded = _load_or_exit(file)
    targets = _selected(loaded, substation)
    previous = None
    if compare is not None:
        if len(targets) != 1:
            raise typer.BadParameter(
                "compares one substation; choose it with --substation", param_hint="--compare"
            )
        try:
            previous = read_previous_issue(compare)
        except InputError as error:
            _exit_on_input_error(error)
    failed = False
    for target in targets:
        try:
            if not no_layout:
                target, layout_report = with_layout(target)
                if layout_report is not None:
                    # Warnings show too; errors stop the build with the whole report.
                    bad = layout_report.has_errors
                    lines = layout_report.lines() if bad else layout_report.problem_lines()
                    for line in lines:
                        typer.echo(f"{target.substation.substation.id}: {line}", err=True)
                    if bad:
                        raise typer.Exit(1)
            result = build_bom(target)
            marked = result
            if previous is not None:
                marked, revisions = compare_with_previous(result, previous)
            workbook = build_workbook(target, marked, logo=target.logo)
            path = write_workbook(workbook, out / _workbook_name(target))
        except (EngineError, WriterError) as error:
            typer.echo(f"{target.substation.substation.id}: {error}", err=True)
            raise typer.Exit(1) from None
        typer.echo(str(path))
        if previous is not None:
            typer.echo(render_revisions(revisions))
        if not no_checks:
            report = check_report(target, result)
            path.with_suffix(".checks.json").write_text(
                render_checks_json(report), encoding="utf-8"
            )
            typer.echo(render_text(report), nl=False)
            failed = failed or report.failed
    if failed:
        raise typer.Exit(1)


@app.command()
def layout(
    substation: Annotated[
        Path, typer.Option("--substation", "-s", help="The substation.yaml to lay out.")
    ],
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Write the panel files here, not to panels/."),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite hand-written panel files too.")
    ] = False,
) -> None:
    """Size the switches and write the generated panel files (ADR 0013)."""
    from bomgen.engine.errors import EngineError
    from bomgen.engine.layout import layout_substation, render_panel_yaml

    try:
        loaded = load_substation(substation)
        result = layout_substation(loaded)
    except InputError as error:
        for issue in error.issues:
            typer.echo(str(issue), err=True)
        typer.echo(f"{len(error.issues)} problem(s) found.", err=True)
        raise typer.Exit(1) from None
    except EngineError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(1) from None
    folder = out if out is not None else substation.parent / "panels"
    targets = {folder / f"{panel.id}.yaml": panel for panel in result.panels}
    hand_written = [t for t in targets if t.exists() and not _is_generated(t)]
    if hand_written and not force:
        for target in hand_written:
            typer.echo(f"{target}: hand-written panel file; not overwritten", err=True)
        typer.echo("Use --out to write elsewhere, or --force to replace them.", err=True)
        raise typer.Exit(1)
    folder.mkdir(parents=True, exist_ok=True)
    for target, panel in targets.items():
        target.write_text(render_panel_yaml(panel), encoding="utf-8")
        typer.echo(f"wrote {target}")
    if out is None:
        _relist_panels(substation, folder, list(targets))
    for line in result.report.lines():
        typer.echo(line)
    if result.report.has_errors:
        raise typer.Exit(1)


def _relist_panels(substation: Path, folder: Path, written: list[Path]) -> None:
    """Point substation.yaml's ``panels:`` at the written files; drop stale generated ones."""
    from bomgen.engine.layout import reconcile_panels_list

    text = substation.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    base = substation.parent
    files = [path.relative_to(base).as_posix() for path in written]
    new_text = reconcile_panels_list(text, files)
    if new_text != text:
        substation.write_text(new_text, encoding="utf-8")
        typer.echo(f"updated the panels list in {substation}")
    kept = {path.resolve() for path in written}
    listed = {(base / entry).resolve() for entry in data.get("panels") or []}
    for path in sorted(listed | {p.resolve() for p in folder.glob("*.yaml")}):
        if path in kept or not path.exists():
            continue
        if _is_generated(path):
            path.unlink()
            typer.echo(f"removed {path}: the layout no longer writes it")
        elif path in listed:
            typer.echo(f"{path}: hand-written, no longer listed in panels (manual_panels keeps it)")


def _is_generated(path: Path) -> bool:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return False
    return isinstance(data, dict) and data.get("generated") is True


@app.command()
def schema(
    out: Annotated[
        Path, typer.Option("--out", "-o", help="Directory to write the JSON Schemas into.")
    ] = Path("schemas"),
) -> None:
    """Write the JSON Schemas of the input files for editor validation."""
    for path in write_json_schemas(out):
        typer.echo(str(path))


def utf8_console() -> None:
    """Write UTF-8 even where the console is not (the frozen exe on Windows gets cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("_", "-")
        if reconfigure is not None and encoding not in ("utf-8", "utf8"):
            reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    utf8_console()
    app()
