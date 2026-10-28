"""Library export and CSV import for the app (M16 b, ADR 0018).

docs/ui/editing.md "Export and import": export writes the active version as CSV tables or a
backup package; a CSV import is first a dry run (A5's `preview_csv_import`) and then its
valid rows go to the pending set, never straight into the library.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bomgen.app.library_edit import LibraryEditor
from bomgen.bundle.checks import CheckStatus
from bomgen.library_store.csv_export import export_installed_csv
from bomgen.library_store.csv_import import CsvPreview, preview_csv_import
from bomgen.library_store.store import LibraryStore

_WHOLE = re.compile(r"^-?\d+\.0$")


def export_folder(folder: Path, name: str, version: str) -> Path:
    """The folder an export writes its tables into, inside the one the person chose."""
    return folder / f"{name}-{version}-csv"


def export_tables(
    store: LibraryStore, name: str, folder: Path, include: list[str]
) -> dict[str, Any]:
    """Write the active version's tables (`include`: devices, catalogues) under `folder`."""
    version = store.active_version(name)
    assert version is not None
    target = export_folder(folder, name, version)
    files = export_installed_csv(store, name, target, version=version, include=include)
    return {"folder": target, "files": files}


def csv_source(path: Path) -> Path:
    """What the dry run reads: a `.zip`, or the folder of a chosen `.csv` file."""
    if path.is_file() and path.suffix.lower() == ".csv":
        return path.parent
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _preview(editor: LibraryEditor, path: Path) -> CsvPreview:
    base = editor.page()["base"]
    return preview_csv_import(
        csv_source(path), editor.store, editor.name, base=base, skip_invalid=True
    )


def preview(editor: LibraryEditor, path: Path) -> dict[str, Any]:
    """The review of a CSV import: file facts, checks, rows with a problem, what changes."""
    result = _preview(editor, path)
    diff = result.diff
    return {
        "file": path.name,
        "size": path.stat().st_size if path.is_file() else None,
        "base": result.base,
        "rows": result.rows,
        "checks": [
            {"label": c.label, "status": c.status.value, "detail": c.detail} for c in result.checks
        ],
        "problems": [
            {
                "table": p.table,
                "row": p.row,
                "column": p.column,
                "message": p.message,
                "key": p.key,
            }
            for p in result.problems
        ],
        "added": diff.added if diff else [],
        "changed": sorted(diff.changed) if diff else [],
        "removed": diff.removed if diff else [],
        "catalogues": diff.catalogues_changed if diff else [],
        "changes": [
            {"area": c.area, "key": c.key, "field": c.field, "from": _n(c.old), "to": _n(c.new)}
            for c in result.changes
        ],
        "can_import": result.can_import,
    }


def _n(text: str) -> str:
    """A whole number without its ".0", as the review shows numbers elsewhere."""
    return text.removesuffix(".0") if _WHOLE.match(text) else text


def add_to_pending(editor: LibraryEditor, path: Path) -> dict[str, Any]:
    """Put the valid rows of a CSV import in the pending set; returns the pending page."""
    result = _preview(editor, path)
    if not result.can_import:
        failed = [
            c.label + (f": {c.detail}" if c.detail else "")
            for c in result.checks
            if c.status is CheckStatus.FAILED
        ]
        raise ValueError("; ".join(failed))
    edits = [e.model_dump(mode="json") for e in result.edits]
    return editor.add(edits) if edits else editor.page()
