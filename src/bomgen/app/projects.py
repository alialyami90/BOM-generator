"""The projects the app knows: the workspace's and the ones opened from elsewhere (plan M10b).

Everything here reads project files through the loader and the stores; the status
words match the Checks screen (``docs/ui/screens.md``, Home).
"""

from __future__ import annotations

import contextlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bomgen.io.errors import InputError, Issue
from bomgen.io.fields import assumed_fields, document_users
from bomgen.io.lifecycle import project_id_for
from bomgen.io.loader import PROJECT_FILE, LoadedProject, load_project
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.errors import LibraryPackageError
from bomgen.library_store.store import LibraryRef, LibraryStore, library_mismatch
from bomgen.models.library import DEFAULT_BRAND, CatalogueBrands, Library
from bomgen.models.project import Project

RECENT_FILE = "recent-projects.json"
MAX_RECENT = 50


class RecentProjects:
    """Project files opened outside the workspace, newest first, kept per user."""

    def __init__(self, folder: Path) -> None:
        self.file = folder / RECENT_FILE

    def load(self) -> list[Path]:
        try:
            paths = json.loads(self.file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [Path(p) for p in paths if isinstance(p, str)] if isinstance(paths, list) else []

    def add(self, project_file: Path) -> None:
        """Remember a project; best effort, since opening it must not depend on this list."""
        paths = [project_file, *(p for p in self.load() if p != project_file)][:MAX_RECENT]
        partial = self.file.with_name(f".{self.file.name}.partial")
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            partial.write_text(json.dumps([str(p) for p in paths], indent=2), encoding="utf-8")
            os.replace(partial, self.file)
        except OSError:
            with contextlib.suppress(OSError):
                partial.unlink(missing_ok=True)

    def remove(self, project_file: Path) -> None:
        """Forget a project (it was deleted); best effort, like ``add``."""
        paths = [p for p in self.load() if p != project_file]
        with contextlib.suppress(OSError):
            self.file.parent.mkdir(parents=True, exist_ok=True)
            self.file.write_text(json.dumps([str(p) for p in paths], indent=2), encoding="utf-8")


def free_id(name: str, taken: Path) -> str:
    """A folder id from ``name`` (lower case, words joined by ``-``) that ``taken`` does not
    hold yet: ``-2``, ``-3``, ... are added when it does."""
    base = project_id_for(name)
    candidate, number = base, 2
    while (taken / candidate).exists():
        candidate, number = f"{base}-{number}", number + 1
    return candidate


def project_files(workspace: Path, recent: RecentProjects) -> list[Path]:
    """Every project file to list: the workspace's folders, then the remembered ones."""
    found = sorted(workspace.glob(f"*/{PROJECT_FILE}")) if workspace.is_dir() else []
    seen = {p.resolve() for p in found}
    for path in recent.load():
        if path.is_file() and path.resolve() not in seen:
            found.append(path)
            seen.add(path.resolve())
    return found


def _status(errors: int, library_note: str | None) -> dict[str, Any]:
    if errors:
        return {
            "level": "bad",
            "text": f"{errors} error{'s' if errors != 1 else ''}",
            "errors": errors,
        }
    if library_note:
        return {"level": "warn", "text": "Library out of date", "errors": 0}
    return {"level": "ok", "text": "Ready", "errors": 0}


def project_only(project_file: Path) -> Project | None:
    """project.yaml validated on its own, for the header when the whole project has errors."""
    try:
        return Project.model_validate(read_yaml(project_file).data)
    except (InputError, ValidationError):
        return None


def library_note(project: Project, store: LibraryStore) -> str | None:
    """Why the recorded library differs from the active one; None when a local file is used."""
    selection = project.library
    if selection.file is not None:
        return None
    try:
        active = store.active_version(selection.name)
    except LibraryPackageError as exc:
        return str(exc)
    recorded = LibraryRef(selection.name, selection.version)
    return library_mismatch(recorded, LibraryRef(selection.name, active) if active else None)


def _changed(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, UTC)
    except OSError:
        return None


def load_with_issues(
    project_file: Path, store: LibraryStore
) -> tuple[LoadedProject | None, list[Issue]]:
    try:
        return load_project(project_file, store=store), []
    except InputError as exc:
        return None, list(exc.issues)


def _substations(
    project_file: Path, project: Project | None, loaded: LoadedProject | None, issues: list[Issue]
) -> list[dict[str, Any]]:
    def errors_in(file: Path) -> int:
        folder = file.parent.resolve()
        return sum(1 for i in issues if folder in i.file.resolve().parents)

    if loaded is not None:
        return [
            {
                "id": s.substation.substation.id,
                "name": s.substation.substation.name,
                "file": s.file,
                "panels": len(s.panels),
                "changed": _changed(s.file),
                "errors": 0,
            }
            for s in loaded.substations
        ]
    if project is None:
        return []
    rows = []
    for path in project.substations:
        file = project_file.parent / path
        rows.append(
            {
                "id": file.parent.name,
                "name": file.parent.name,
                "file": file,
                "panels": None,
                "changed": _changed(file),
                "errors": errors_in(file),
            }
        )
    return rows


def brands(library: Library) -> dict[str, list[dict[str, str]]]:
    """The brand sets a project can choose per catalogue, the library default first; the DC
    MCBs choose from every MCB brand, the AC ones from the AC-rated brands (ADR 0023)."""
    found: dict[str, list[dict[str, str]]] = {}
    for kind in CatalogueBrands.model_fields:
        sets = getattr(library.catalogue_brands, kind)
        found[kind] = [
            {"id": DEFAULT_BRAND, "name": "Library default"},
            *({"id": b.id, "name": b.name or b.id} for b in sets),
        ]
    found["mcb_dc"] = found["mcb"]
    found["mcb"] = [  # a DC-only family is refused for the AC branches (ADR 0023)
        b
        for b, s in zip(found["mcb"], [None, *library.catalogue_brands.mcb], strict=True)
        if s is None or s.ac_rated
    ]
    return found


def register(
    project_file: Path, project: Project, loaded: LoadedProject | None
) -> list[dict[str, Any]]:
    """The register's documents in file order, each with its fields marked ``ASSUMED`` and
    what uses it (None while the project does not load, so Remove stays off)."""
    assumed: dict[int, list[str]] = {}
    for loc in assumed_fields(project_file):
        if len(loc) == 3 and loc[0] == "documents" and isinstance(loc[1], int):
            assumed.setdefault(loc[1], []).append(str(loc[2]))
    return [
        {
            "index": index,
            **entry.model_dump(mode="json"),
            "assumed": assumed.get(index, []),
            "used_by": document_users(loaded, entry.key) if loaded is not None else None,
        }
        for index, entry in enumerate(project.documents)
    ]


def summarize(project_file: Path, store: LibraryStore, *, details: bool = False) -> dict[str, Any]:
    """One project as Home lists it; with ``details`` also what the Project page shows."""
    loaded, issues = load_with_issues(project_file, store)
    project = loaded.project if loaded is not None else project_only(project_file)
    note = library_note(project, store) if project is not None else None
    summary: dict[str, Any] = {
        "id": project.project.id if project else project_file.parent.name,
        "name": project.project.name if project else project_file.parent.name,
        "client": project.project.client if project else None,
        "file": project_file,
        "folder": project_file.parent,
        "changed": _changed(project_file),
        "library": (
            {
                "name": project.library.name,
                "version": project.library.version,
                "local_file": project.library.file is not None,
                "note": note,
            }
            if project
            else None
        ),
        "substations": _substations(project_file, project, loaded, issues),
        "status": _status(len(issues), note),
    }
    if details:
        summary |= {
            "brands": brands(loaded.library) if loaded is not None else {},
            "project": project.project if project else None,
            "defaults": project.defaults if project else None,
            "documents": project.documents if project else [],
            "register": register(project_file, project, loaded) if project else [],
            "problems": issues,
        }
    return summary
