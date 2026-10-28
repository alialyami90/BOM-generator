"""One substation as the Settings and Network screens show it (plan M10c).

Values come from the loader: the effective constants and spares are the project
defaults with this substation's written keys on top, and "changed" marks the keys
the substation writes itself (``docs/ui/screens.md``, Substation settings).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple

from pydantic import BaseModel, ValidationError

from bomgen.app.projects import load_with_issues, project_only
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import with_layout
from bomgen.io.errors import InputError, Issue
from bomgen.io.loader import LoadedSubstation, load_library
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.errors import LibraryPackageError
from bomgen.library_store.store import LibraryStore
from bomgen.models._base import InputModel
from bomgen.models.library import Library
from bomgen.models.project import (
    DesignConstants,
    Project,
    RegisterEntry,
    Spares,
    merge_defaults,
)
from bomgen.models.substation import Substation

CALCULATION_SHEETS = ("power_consumption", "heat_dissipation", "heat_calculations")


class SubstationNotFoundError(LookupError):
    """The project lists no substation with this id."""


class ProjectInvalidError(Exception):
    """project.yaml itself cannot be read, so no substation in it can be found."""

    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("\n".join(str(i) for i in issues))
        self.issues = issues


def _rows(
    effective: BaseModel, default: BaseModel, written: BaseModel | None
) -> list[dict[str, Any]]:
    changed = written.model_fields_set if written is not None else set()
    return [
        {
            "key": key,
            "value": getattr(effective, key),
            "default": getattr(default, key),
            "changed": key in changed,
        }
        for key in type(effective).model_fields
    ]


def _device(library: Library | None, part_id: str | None) -> dict[str, Any] | None:
    if library is None or part_id is None:
        return None
    device = next((d for d in library.devices if d.part_id == part_id), None)
    if device is None:
        return {"known": False}
    return {
        "known": True,
        "make": device.make,
        "model": device.model,
        "category": device.category,
        "height_u": device.height_u,
    }


def _file_name(substation: Substation, entries: dict[str, RegisterEntry]) -> str | None:
    main = entries.get(substation.document)
    if main is None:
        return None
    return substation.output.resolve_file_name(main.doc_no, main.rev)


def _effective[M: InputModel](default: M, written: InputModel | None) -> M:
    """The default with the written keys on top; unvalidated when the merge is refused,
    so the page shows what the file says next to the loader's located issue."""
    try:
        return merge_defaults(default, written)
    except ValidationError:
        assert written is not None
        return default.model_copy(update={k: getattr(written, k) for k in written.model_fields_set})


def _library(project_file: Path, project: Project, store: LibraryStore) -> Library | None:
    """The project's library on its own, to name each part when the project has errors."""
    selection = project.library
    try:
        file = (
            project_file.parent / selection.file
            if selection.file is not None
            else store.library_file(selection.name, selection.version)
        )
        return load_library(file)
    except (InputError, LibraryPackageError, OSError):
        return None


def _substation_file(project_file: Path, project: Project, substation_id: str) -> Path:
    """The listed ``substation.yaml`` whose folder is ``substation_id``."""
    for path in project.substations:
        file = project_file.parent / path
        if file.parent.name == substation_id:
            return file
    raise SubstationNotFoundError(substation_id)


def _page(
    project_file: Path,
    project: Project | None,
    file: Path,
    substation: Substation | None,
    loaded: LoadedSubstation | None,
    problems: list[Issue],
    library: Library | None,
) -> dict[str, Any]:
    entries = (
        {
            e.key: e
            for e in project.documents
            if substation and e.substation == substation.substation.id
        }
        if project is not None
        else {}
    )
    try:
        text = file.read_text(encoding="utf-8")
    except OSError:
        text = ""
    page: dict[str, Any] = {
        "id": substation.substation.id if substation else file.parent.name,
        "name": substation.substation.name if substation else file.parent.name,
        "file": file,
        "project": (
            {
                "file": project_file,
                "name": project.project.name,
                "client": project.project.client,
                "library": {"name": project.library.name, "version": project.library.version},
            }
            if project is not None
            else None
        ),
        "yaml": text,
        "problems": problems,
    }
    if substation is None:
        return page
    defaults_c = project.defaults.constants if project else DesignConstants()
    defaults_s = project.defaults.spares if project else Spares()
    constants = loaded.constants if loaded else _effective(defaults_c, substation.constants)
    spares = loaded.spares if loaded else _effective(defaults_s, substation.spares)
    page |= {
        "documents": list(entries.values()),
        "calculations": [
            {
                "key": key,
                "document": (sheet := getattr(substation.calculations, key)).document,
                "scope": sheet.scope,
                "entry": entries.get(sheet.document),
            }
            for key in CALCULATION_SHEETS
        ],
        "output": {
            "document": substation.document,
            "entry": entries.get(substation.document),
            "file_name": substation.output.file_name,
            "result": _file_name(substation, entries),
            "sheet_names": substation.output.sheet_names,
        },
        "constants": _rows(constants, defaults_c, substation.constants),
        "spares": _rows(spares, defaults_s, substation.spares),
        "loose_material": substation.loose_material,
        "equipment": [
            {**e.model_dump(mode="json"), "device": _device(library, e.part_id)}
            for e in substation.equipment
        ],
        "network": substation.network,
        "panels": len(loaded.panels) if loaded else None,
    }
    return page


class Resolved(NamedTuple):
    """One substation of a project: loaded, or its file and located problems."""

    project: Project
    file: Path
    loaded: LoadedSubstation | None
    problems: list[Issue]
    warnings: Sequence[Issue] = ()


def _laid_out(found: Resolved) -> Resolved:
    """Generated panels re-laid out, as ``bomgen build`` does; layout errors block."""
    assert found.loaded is not None
    try:
        loaded, report = with_layout(found.loaded)
    except EngineError as exc:
        return found._replace(loaded=None, problems=[Issue(found.file, "layout", str(exc))])
    if report is None:
        return found._replace(loaded=loaded)
    errors = [
        Issue(found.file, f"layout: {i.subject}", i.message) for i in report.issues if i.is_error
    ]
    warnings = [
        Issue(found.file, f"layout: {i.subject}", i.message)
        for i in report.issues
        if not i.is_error
    ]
    return found._replace(loaded=None if errors else loaded, problems=errors, warnings=warnings)


def resolve(project_file: Path, substation_id: str, store: LibraryStore) -> Resolved:
    """Load the project and find ``substation_id`` in it.

    When the project has errors, ``problems`` holds this substation's issues and the
    project's own, not those of its other substations.
    """
    loaded_project, issues = load_with_issues(project_file, store)
    if loaded_project is not None:
        for loaded in loaded_project.substations:
            if loaded.substation.substation.id == substation_id:
                return _laid_out(Resolved(loaded.project, loaded.file, loaded, []))
        raise SubstationNotFoundError(substation_id)
    project = project_only(project_file)
    if project is None:
        raise ProjectInvalidError(issues)
    file = _substation_file(project_file, project, substation_id)
    others = {(project_file.parent / p).parent.resolve() for p in project.substations} - {
        file.parent.resolve()
    }
    problems = [i for i in issues if not others & set(i.file.resolve().parents)]
    return Resolved(project, file, None, problems)


def substation_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The Settings and Network view of one substation, or its located problems."""
    found = resolve(project_file, substation_id, store)
    if found.loaded is not None:
        loaded = found.loaded
        return _page(
            project_file, loaded.project, loaded.file, loaded.substation, loaded, [], loaded.library
        )
    try:
        substation: Substation | None = Substation.model_validate(read_yaml(found.file).data)
    except (InputError, ValidationError):
        substation = None
    library = _library(project_file, found.project, store)
    return _page(project_file, found.project, found.file, substation, None, found.problems, library)
