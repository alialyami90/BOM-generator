"""Checks and Build for one substation (plan M10d; ``docs/ui/screens.md``, Checks and Build).

The checks are the loader's located problems and the engine's step 15 report; the
build is ``bomgen build``'s own ``build_substation``, with its failures mapped to the
refusals the Build page explains.
"""

from __future__ import annotations

import csv
import dataclasses
import io
import os
from pathlib import Path
from typing import Any

from bomgen.app.projects import library_note
from bomgen.app.substations import Resolved, resolve
from bomgen.build import build_substation, issue_refusal, record_issue, workbook_name
from bomgen.checks import check_report, unused_acceptances
from bomgen.engine.errors import EngineError
from bomgen.engine.network import unserved_links
from bomgen.engine.overrides import risky_notes
from bomgen.engine.pipeline import build as build_bom
from bomgen.engine.summary import summarize
from bomgen.io.errors import InputError
from bomgen.io.loader import LoadedSubstation
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.store import LibraryStore
from bomgen.models.bom import BuildResult
from bomgen.models.project import _FILE_NAME_FORBIDDEN
from bomgen.models.report import CheckReport, PreviousIssue
from bomgen.revision import (
    change_list,
    compare_with_previous,
    previous_from_record,
    read_previous_issue,
    record_warning,
)
from bomgen.sheets.summary_sheet import HEADERS as SUMMARY_HEADERS
from bomgen.sheets.workbook import build_workbook
from bomgen.writer import WriterError

OUT_FOLDER = "out"
WORKBOOK_SUFFIX = ".xlsx"


class OutputRefusedError(Exception):
    """A build that cannot go ahead; ``kind`` names why for the page."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def problems_of(project_file: Path, found: Resolved, store: LibraryStore) -> list[dict[str, Any]]:
    rows = [{"level": "error", **dataclasses.asdict(i)} for i in found.problems]
    rows += [{"level": "warning", **dataclasses.asdict(i)} for i in found.warnings]
    note = library_note(found.project, store)
    if note is not None:
        rows.append(
            {"level": "warning", "file": project_file, "location": "library", "message": note}
        )
    return rows


def _errors(found: Resolved) -> str:
    count = len(found.problems)
    return f"{count} error{'' if count == 1 else 's'} in the input files"


def _not_ready(found: Resolved) -> list[dict[str, Any]]:
    """What a substation that loads still lacks before it can be built: parts, then panels."""
    loaded = found.loaded
    if loaded is None:
        return []
    if not loaded.substation.equipment:
        location, message = "equipment", "No parts yet: pick this substation's parts on Parts."
    elif not loaded.panels:
        location, message = "panels", "No panels yet: lay them out on Panels."
    else:
        return _unserved_links(found.file, loaded)
    return [{"level": "error", "file": found.file, "location": location, "message": message}]


def _unserved_links(file: Path, loaded: LoadedSubstation) -> list[dict[str, Any]]:
    """Each L2 link no library SFP serves, on its Parts row, before the engine stops on it."""
    source = read_yaml(file)
    problems = []
    for index in unserved_links(loaded.substation.equipment, loaded.library):
        entry = loaded.substation.equipment[index]
        link = f"{entry.l2_speed.value} {entry.l2_media.value}"
        problems.append(
            {
                "level": "error",
                "file": file,
                "location": f"equipment[{index}].l2_speed",
                "line": source.line_for(("equipment", index, "l2_speed")),
                "message": f"no SFP in the library for {link}, so the L2 switch cannot take "
                f"{entry.id}'s link: pick another speed or media, or add a {link} SFP.",
            }
        )
    return problems


def checks_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The located problems, then the engine checks; these run only when the files load."""
    found = resolve(project_file, substation_id, store)
    engine: dict[str, Any] = {"run": False, "reason": None, "failed": False, "items": []}
    unused: list[dict[str, Any]] = []
    missing = _not_ready(found)
    if found.loaded is None:
        engine["reason"] = f"{_errors(found)} must be fixed before the engine checks run."
    elif missing:
        engine["reason"] = missing[0]["message"]
    else:
        try:
            report = check_report(found.loaded, build_bom(found.loaded))
        except EngineError as exc:
            engine["reason"] = f"The engine stopped: {exc}"
        else:
            engine = {"run": True, "reason": None, "failed": report.failed, "items": report.items}
            unused = _unused(found.loaded, report)
    return {
        "problems": problems_of(project_file, found, store) + missing,
        "engine": engine,
        "unused": unused,  # acceptances no warning matches any more (ADR 0036)
    }


def _unused(loaded: LoadedSubstation, report: CheckReport) -> list[dict[str, Any]]:
    accepted = loaded.substation.checks.accepted if loaded.substation.checks else []
    unused = unused_acceptances(report, accepted)
    shown = {"check", "panel_id", "subject", "reason"}
    return [
        {"index": index, **a.model_dump(mode="json", include=shown)}
        for index, a in enumerate(accepted)
        if a in unused
    ]


def build_target(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """Where Build writes by default, and what blocks it."""
    found = resolve(project_file, substation_id, store)
    folder = found.file.parent / OUT_FOLDER
    loaded = found.loaded
    name = sheets = revision = None
    flags = 0
    issue: dict[str, Any] = {"refusal": None, "record": None}  # ADR 0036
    if loaded is not None:
        issue = _issue(loaded)
        name = workbook_name(loaded)
        revision = loaded.documents[loaded.substation.document].rev
        try:
            bom = build_bom(loaded)
            workbook = build_workbook(loaded, bom)
            report = check_report(loaded, bom)
        except EngineError:
            pass  # Checks names the engine's problem; Build refuses with it
        else:
            flags = report.open_warnings
            cabinets = {panel.sheet_name: panel.cabinet_name for panel in loaded.panels}
            sheets = [{"name": s.name, "cabinet": cabinets.get(s.name)} for s in workbook.sheets]
    library = found.project.library
    return {
        "file_name": name,
        "folder": folder,
        "exists": name is not None and (folder / name).exists(),
        "sheets": sheets,
        "library": {"name": library.name, "version": library.version},
        "revision": revision,
        "flags": flags,  # the engine checks' open warnings, as Checks counts them
        "include": sorted(loaded.substation.output.include) if loaded else [],  # ADR 0035
        "issue": issue,
        "problems": problems_of(project_file, found, store) + _not_ready(found),
    }


def _issue(loaded: LoadedSubstation) -> dict[str, Any]:
    """Why Build as issued is refused, and the latest record the next build compares with."""
    records = loaded.substation.issues
    record = None
    if records:
        latest = records[-1]
        record = {
            "rev": latest.rev,
            "file": latest.file.as_posix(),
            "warning": record_warning(loaded),
        }
    return {"refusal": issue_refusal(loaded), "record": record}


def summary_rows(loaded: LoadedSubstation, result: BuildResult) -> list[dict[str, Any]]:
    """The Summary BOM's lines as the sheet prints them (ADR 0035)."""
    tables: dict[str | None, str] = {p.panel_id: p.sheet_name for p in result.panels}
    tables[None] = loaded.substation.output.sheet_names.loose_material
    return [
        {
            "description": line.description,
            "qty": line.qty,
            "make": line.make,
            "model": line.model,
            "ordering_code": line.ordering_code,
            "where_used": line.where_used(tables),
        }
        for line in summarize(result).lines
    ]


def export_summary_csv(
    project_file: Path, substation_id: str, store: LibraryStore, path: Path
) -> dict[str, Any]:
    """Write the Summary BOM as CSV, UTF-8 with a byte-order mark so Excel reads it."""
    found = resolve(project_file, substation_id, store)
    if found.loaded is None:
        raise OutputRefusedError("has_errors", f"{_errors(found)} block the export.")
    try:
        rows = summary_rows(found.loaded, build_bom(found.loaded))
    except EngineError as exc:
        raise OutputRefusedError("engine", f"The engine stopped: {exc}") from None
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(SUMMARY_HEADERS)
    for number, row in enumerate(rows, start=1):
        writer.writerow([number, *("" if value is None else value for value in row.values())])
    try:
        path.write_text(buffer.getvalue(), encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise OutputRefusedError("io", f"The CSV was not written: {exc}") from None
    return {"path": path, "lines": len(rows)}


# Windows device names, refused with or without an extension
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"{d}{n}" for d in ("COM", "LPT") for n in range(1, 10))}


def _checked_name(name: str) -> str:
    stem = name[: -len(WORKBOOK_SUFFIX)] if name.lower().endswith(WORKBOOK_SUFFIX) else ""
    if (
        not stem.strip(" .")
        or name != name.strip()
        or set(name) & _FILE_NAME_FORBIDDEN
        or "\0" in name
        or any(ord(c) < 32 for c in name)
        or stem.split(".")[0].upper() in _RESERVED
    ):
        raise OutputRefusedError(
            "bad_name",
            f"Use a file name ending in {WORKBOOK_SUFFIX}, without a folder or any of "
            '< > : " / \\ | ? *.',
        )
    return name


def _checked_folder(folder: Path) -> Path:
    if not str(folder).strip() or not folder.is_absolute():
        raise OutputRefusedError("bad_folder", "Choose the folder to save the workbook in.")
    return folder


def _locked(exc: BaseException) -> bool:
    """Whether a write failed for want of permission: another program, such as Excel,
    holds the file, or the folder is read-only."""
    seen: BaseException | None = exc
    while seen is not None:
        if isinstance(seen, PermissionError) or any(
            isinstance(arg, PermissionError) for arg in seen.args
        ):
            return True
        seen = seen.__cause__ or seen.__context__
    return False


def issue_changes(
    project_file: Path, substation_id: str, store: LibraryStore, compare: Path | None = None
) -> dict[str, Any]:
    """What Build as issued would record (plan M79): the compare's changes with ``compare``,
    else with the latest recorded issue, then the rows marked as revised."""
    found = resolve(project_file, substation_id, store)
    loaded = found.loaded
    if loaded is None:
        raise OutputRefusedError("has_errors", f"{_errors(found)} block the build.")
    previous: PreviousIssue | None
    if compare is not None:
        try:
            previous = read_previous_issue(compare)
        except InputError as exc:
            raise OutputRefusedError("bad_previous", str(exc)) from None
    else:
        previous, _ = previous_from_record(loaded)
    try:
        result = build_bom(loaded)
    except EngineError as exc:
        raise OutputRefusedError("engine", f"The engine stopped: {exc}") from None
    report = None
    if previous is not None:
        loose_sheet = loaded.substation.output.sheet_names.loose_material
        _, report = compare_with_previous(result, previous, loose_sheet=loose_sheet)
    return {
        "previous": report.previous if report else None,
        "rows": change_list(loaded, result, report),
    }


def build_file(
    project_file: Path,
    substation_id: str,
    store: LibraryStore,
    folder: Path,
    file_name: str | None = None,
    compare: Path | None = None,
    replace: bool = False,
    issue: str | None = None,
) -> dict[str, Any]:
    """Write one substation's workbook and its check report next to it; with ``issue`` (its
    description) also record it as issued unless a check failed (ADR 0036)."""
    found = resolve(project_file, substation_id, store)
    loaded = found.loaded
    if loaded is None:
        raise OutputRefusedError("has_errors", f"{_errors(found)} block the build.")
    path = _checked_folder(folder) / _checked_name(
        file_name if file_name is not None else workbook_name(loaded)
    )
    if issue is not None:
        if not issue.strip():
            raise OutputRefusedError("bad_description", "Describe the issue, e.g. For review.")
        refusal = issue_refusal(loaded)
        if refusal is not None:
            raise OutputRefusedError("already_issued", refusal)
    if path.exists() and not replace:
        raise OutputRefusedError("file_exists", f"{path.name} is already in {folder}.")
    previous = warning = None
    if compare is not None:
        try:
            previous = read_previous_issue(compare)
        except InputError as exc:
            raise OutputRefusedError("bad_previous", str(exc)) from None
    else:
        previous, warning = previous_from_record(loaded)
    try:
        outcome = build_substation(loaded, path, previous=previous)
    except EngineError as exc:
        raise OutputRefusedError("engine", f"The engine stopped: {exc}") from None
    except (WriterError, PermissionError) as exc:
        if _locked(exc) and folder.is_dir() and not os.access(folder, os.W_OK):
            raise OutputRefusedError(
                "io", f"{folder} is read-only. Choose another folder."
            ) from None
        if _locked(exc):
            raise OutputRefusedError(
                "file_open",
                f"{path.name} is open in another program, such as Excel.",
            ) from None
        raise OutputRefusedError("write", f"The workbook was not written: {exc}") from None
    except OSError as exc:  # write_workbook wraps its own: only the .checks.json is left
        raise OutputRefusedError(
            "io", f"The workbook {path} was written, but its check report was not: {exc}"
        ) from None
    report = outcome.checks
    assert report is not None
    issued = not_issued = None
    if issue is not None and report.failed:
        not_issued = "Not recorded as issued: a check failed."
    elif issue is not None:
        recorded = record_issue(
            project_file,
            loaded,
            path,
            issue.strip(),
            overrides=risky_notes(loaded, outcome.result),
        )
        issued = {"rev": recorded.rev, "file": recorded.file.as_posix()}
    return {
        "path": path,
        "size": path.stat().st_size,
        "sheets": list(outcome.sheets),
        "checks": {"failed": report.failed, "items": report.items},
        "revisions": outcome.revisions,
        "record_warning": warning,
        "issued": issued,
        "not_issued": not_issued,
    }
