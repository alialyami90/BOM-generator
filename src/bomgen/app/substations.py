"""One substation as the Settings and Network screens show it (plan M10c).

Values come from the loader: the effective constants and spares are the project
defaults with this substation's written keys on top, and "changed" marks the keys
the substation writes itself (``docs/ui/screens.md``, Substation settings).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from bomgen.app.projects import load_with_issues, project_only
from bomgen.io.errors import InputError, Issue
from bomgen.io.loader import LoadedSubstation
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.store import LibraryStore
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
    return substation.output.file_name.format(doc_no=main.doc_no, rev=main.rev)


def _substation_file(project_file: Path, project: Project | None, substation_id: str) -> Path:
    """The listed ``substation.yaml`` whose folder, or validated id, is ``substation_id``."""
    if project is None:
        raise SubstationNotFoundError(substation_id)
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
) -> dict[str, Any]:
    library = loaded.library if loaded is not None else None
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
    constants = loaded.constants if loaded else merge_defaults(defaults_c, substation.constants)
    spares = loaded.spares if loaded else merge_defaults(defaults_s, substation.spares)
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


def substation_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The Settings and Network view of one substation, or its located problems."""
    loaded_project, issues = load_with_issues(project_file, store)
    if loaded_project is not None:
        for loaded in loaded_project.substations:
            if loaded.substation.substation.id == substation_id:
                return _page(
                    project_file, loaded.project, loaded.file, loaded.substation, loaded, []
                )
        raise SubstationNotFoundError(substation_id)
    project = project_only(project_file)
    file = _substation_file(project_file, project, substation_id)
    folder = file.parent.resolve()
    problems = [i for i in issues if folder in i.file.resolve().parents]
    try:
        substation: Substation | None = Substation.model_validate(read_yaml(file).data)
    except (InputError, ValidationError):
        substation = None
    return _page(project_file, project, file, substation, None, problems)
