"""The app's editing endpoints over the substation writers (plan M17, ADR 0021).

``bomgen.io.edit`` does the work: it writes ``substation.yaml`` only when the edit
causes no new problem. This module turns its result into what the page shows: whether
the file was written, the problems, and, once written, the refreshed Panels board.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bomgen.app.network import layout_page
from bomgen.app.substations import layout_message, resolve
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import layout_preview
from bomgen.io.edit import EditError, EditResult
from bomgen.io.edit import panel_options as options_of
from bomgen.library_store.store import LibraryStore
from bomgen.models.substation import Layout


def edit_reply(
    result: EditResult, project_file: Path, substation_id: str, store: LibraryStore
) -> dict[str, Any]:
    """``written``, the ``issues`` (caused when not written, else still open) and the
    board ``page`` after a write, or ``None`` when nothing was written."""
    return {
        "written": result.written,
        "issues": [dataclasses.asdict(issue) for issue in result.issues],
        "page": layout_page(project_file, substation_id, store) if result.written else None,
    }


def panel_options_page(
    project_file: Path, substation_id: str, panel: int, store: LibraryStore
) -> list[dict[str, Any]]:
    """Every option of generated panel ``panel``: its value, the shared value, and
    whether the panel has its own."""
    found = resolve(project_file, substation_id, store)
    if found.loaded is None:
        raise EditError("the substation's files have errors; fix them on Checks first")
    return [dataclasses.asdict(option) for option in options_of(found.loaded, panel)]


def layout_check(
    project_file: Path,
    substation_id: str,
    store: LibraryStore,
    *,
    overrides: list[dict[str, Any]] | None = None,
    removed: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Whether the layout can take these overrides or removed units: the layout errors
    the engine finds with them that it does not find now and, when there are none, the
    rack space each panel would use. Nothing is written; problems in the files are the
    writer's to report."""
    found = resolve(project_file, substation_id, store)
    loaded = found.source or found.loaded
    if loaded is None:
        return {"issues": [], "panels": []}
    current = loaded.substation.layout
    change = {k: v for k, v in (("overrides", overrides), ("removed", removed)) if v is not None}
    try:
        candidate = Layout.model_validate(current.model_dump(mode="json") | change)
        before = {
            (i.subject, i.message) for i in layout_preview(loaded).report.issues if i.is_error
        }
        after = layout_preview(loaded, candidate)
    except (ValidationError, EngineError):
        return {"issues": [], "panels": []}
    issues = [
        {
            "file": found.file,
            "location": f"layout: {issue.subject}",
            "message": layout_message(issue),
            "line": None,
        }
        for issue in after.report.issues
        if issue.is_error and (issue.subject, issue.message) not in before
    ]
    rules = after.rules
    panels = [
        {"number": f.number, "used_u": f.used_u(rules), "capacity_u": rules.capacity_u}
        for f in after.fills
    ]
    return {"issues": issues, "panels": [] if issues else panels}


def layout_issues(
    project_file: Path,
    substation_id: str,
    store: LibraryStore,
    *,
    overrides: list[dict[str, Any]] | None = None,
    removed: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """The layout errors these overrides or removed units would add (``layout_check``)."""
    check = layout_check(project_file, substation_id, store, overrides=overrides, removed=removed)
    issues: list[dict[str, Any]] = check["issues"]
    return issues
