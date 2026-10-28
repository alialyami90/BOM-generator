"""Checks and Build for one substation (plan M10d; ``docs/ui/screens.md``, Checks and Build).

The checks are the loader's located problems and the engine's step 15 report; the
build is ``bomgen build``'s own ``build_substation``, with its failures mapped to the
refusals the Build page explains.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Any

import openpyxl

from bomgen.app.projects import library_note
from bomgen.app.substations import Resolved, resolve
from bomgen.build import build_substation, workbook_name
from bomgen.checks import check_report
from bomgen.checks import render_json as render_checks_json
from bomgen.engine.errors import EngineError
from bomgen.engine.pipeline import build as build_bom
from bomgen.io.errors import InputError
from bomgen.library_store.store import LibraryStore
from bomgen.models.project import _FILE_NAME_FORBIDDEN
from bomgen.revision import read_previous_issue
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


def checks_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The located problems, then the engine checks; these run only when the files load."""
    found = resolve(project_file, substation_id, store)
    engine: dict[str, Any] = {"run": False, "reason": None, "failed": False, "items": []}
    if found.loaded is None:
        engine["reason"] = f"{_errors(found)} must be fixed before the engine checks run."
    else:
        try:
            report = check_report(found.loaded, build_bom(found.loaded))
        except EngineError as exc:
            engine["reason"] = f"The engine stopped: {exc}"
        else:
            engine = {"run": True, "reason": None, "failed": report.failed, "items": report.items}
    return {"problems": problems_of(project_file, found, store), "engine": engine}


def build_target(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """Where Build writes by default, and what blocks it."""
    found = resolve(project_file, substation_id, store)
    folder = found.file.parent / OUT_FOLDER
    loaded = found.loaded
    name = sheets = revision = None
    if loaded is not None:
        name = workbook_name(loaded)
        revision = loaded.documents[loaded.substation.document].rev
        try:
            workbook = build_workbook(loaded, build_bom(loaded))
        except EngineError:
            pass  # Checks names the engine's problem; Build refuses with it
        else:
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
        "problems": problems_of(project_file, found, store),
    }


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


def build_file(
    project_file: Path,
    substation_id: str,
    store: LibraryStore,
    folder: Path,
    file_name: str | None = None,
    compare: Path | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Write one substation's workbook and its check report next to it."""
    found = resolve(project_file, substation_id, store)
    loaded = found.loaded
    if loaded is None:
        raise OutputRefusedError("has_errors", f"{_errors(found)} block the build.")
    path = _checked_folder(folder) / _checked_name(
        file_name if file_name is not None else workbook_name(loaded)
    )
    if path.exists() and not replace:
        raise OutputRefusedError("file_exists", f"{path.name} is already in {folder}.")
    previous = None
    if compare is not None:
        try:
            previous = read_previous_issue(compare)
        except InputError as exc:
            raise OutputRefusedError("bad_previous", str(exc)) from None
    try:
        outcome = build_substation(loaded, path, previous=previous, checks=False)
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
    report = check_report(loaded, outcome.result)
    try:
        path.with_suffix(".checks.json").write_text(render_checks_json(report), encoding="utf-8")
    except OSError as exc:
        raise OutputRefusedError(
            "io", f"The workbook {path} was written, but its check report was not: {exc}"
        ) from None
    book = openpyxl.load_workbook(path, read_only=True)
    try:
        sheets = book.sheetnames
    finally:
        book.close()
    return {
        "path": path,
        "size": path.stat().st_size,
        "sheets": sheets,
        "checks": {"failed": report.failed, "items": report.items},
        "revisions": outcome.revisions,
    }
