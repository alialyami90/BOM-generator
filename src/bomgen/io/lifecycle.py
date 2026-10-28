"""Create and delete projects and substations (plan M17d, ADR 0021).

Names are edited with ``fields.set_field`` (``project.name``, ``substation.name``); ids
name folders and register keys, so the app shows them read-only. A delete saves a backup
first (ADR 0012) and returns its file.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from bomgen.io.edit import EditError, EditResult, commit, project_problems, substation_file
from bomgen.io.errors import Issue
from bomgen.io.round_trip import (
    dump_text,
    edit_document,
    load_text,
    remove_entry,
    set_comment,
    set_entry,
    write_atomic,
)
from bomgen.io.yaml_source import read_yaml
from bomgen.project_store.backup import backup_project
from bomgen.project_store.export import export_project
from bomgen.project_store.manifest import PROJECT_SUFFIX
from bomgen.project_store.rename import suggest_project_id

if TYPE_CHECKING:
    from bomgen.library_store.store import LibraryStore

PROJECT_FILE = "project.yaml"
SUBSTATIONS = "substations"
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")  # PanelId: a folder and register-key prefix


@dataclass(frozen=True)
class Created:
    """A new project: its file and the problems it has (e.g. a library not installed)."""

    project_file: Path
    issues: tuple[Issue, ...]


@dataclass(frozen=True)
class Deleted:
    """What a delete did; ``backup`` is the ``.bomproj`` saved first."""

    result: EditResult
    backup: Path | None


def project_id_for(name: str) -> str:
    """A folder-safe id from a project name: lower case, words joined by ``-``."""
    words = re.findall(r"[a-z0-9]+", name.lower())
    return "-".join(words)[:64].strip("-") or "project"


def create_project(
    workspace: Path,
    name: str,
    *,
    library_name: str,
    library_version: str,
    client: str | None = None,
    store: LibraryStore | None = None,
) -> Created:
    """Write ``<workspace>/<id>/project.yaml`` for a new project with no substations; the
    id comes from ``name`` and gets ``-2``, ``-3``, ... when the folder is taken."""
    if not name.strip():
        raise EditError("a project needs a name")
    project_id = project_id_for(name)
    if (workspace / project_id).exists():
        project_id = suggest_project_id(project_id, workspace)
    project: dict[str, Any] = {"id": project_id, "name": name.strip()}
    if client:
        project["client"] = client
    data = {
        "project": project,
        "library": {"name": library_name, "version": library_version},
        "documents": [],
        SUBSTATIONS: [],
    }
    project_file = workspace / project_id / PROJECT_FILE
    write_atomic(project_file, dump_text(_map(data)))
    return Created(project_file, tuple(project_problems(project_file, store=store)))


def create_substation(
    project_file: Path,
    substation_id: str,
    name: str,
    *,
    copy_from: str | None = None,
    today: date | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Add substation ``substation_id``: blank, or a copy of substation ``copy_from`` with
    its panels, settings and register documents. A blank substation gets three register
    documents (BOM, power, heat) whose number and date are marked ``ASSUMED``."""
    if not _ID.fullmatch(substation_id):
        raise EditError(
            f"substation id '{substation_id}' must be lower case letters, digits, - or _"
        )
    folder = project_file.parent / SUBSTATIONS / substation_id
    if folder.exists():
        raise EditError(f"{SUBSTATIONS}/{substation_id} already exists")
    project = load_text(project_file.read_text(encoding="utf-8-sig"))
    if copy_from is None:
        texts, entries = _blank(folder, substation_id, name, today or date.today())
    else:
        texts, entries = _copy(project_file, project, copy_from, folder, substation_id, name)
    keys = {e.get("key") for e in project.get("documents") or []}
    clash = sorted(str(e["key"]) for e in entries if e["key"] in keys)
    if clash:
        raise EditError(f"the register already has {', '.join(clash)}")

    def change(root: CommentedMap) -> None:
        documents = _list(root, "documents")
        for entry in entries:
            set_entry(documents, len(documents), entry)
            if copy_from is None:
                for field in ("doc_no", "issue_date"):
                    set_comment(documents[len(documents) - 1], field, "ASSUMED")
        listed = _list(root, SUBSTATIONS)
        set_entry(listed, len(listed), f"{SUBSTATIONS}/{substation_id}/substation.yaml")

    edit_document(project, change)
    texts[project_file] = dump_text(project)
    return commit(project_file, substation_id, texts, store=store)


def _blank(
    folder: Path, substation_id: str, name: str, today: date
) -> tuple[dict[Path, str | None], list[dict[str, Any]]]:
    keys = {kind: f"{substation_id}-{kind}" for kind in ("bom", "power", "heat")}
    sheet = {"scope": name}
    data = {
        "substation": {"id": substation_id, "name": name},
        "document": keys["bom"],
        "calculations": {
            "power_consumption": {"document": keys["power"], **sheet},
            "heat_dissipation": {"document": keys["heat"], **sheet},
            "heat_calculations": {"document": keys["heat"], **sheet},
        },
        "panels": [],
    }
    entries = [
        {
            "key": key,
            "substation": substation_id,
            "doc_no": "TBD",
            "rev": DoubleQuotedScalarString("00"),  # a revision stays text
            "issue_date": today,
        }
        for key in keys.values()
    ]
    texts: dict[Path, str | None] = {folder / "substation.yaml": dump_text(_map(data))}
    return texts, entries


def _copy(
    project_file: Path,
    project: CommentedMap,
    source_id: str,
    folder: Path,
    substation_id: str,
    name: str,
) -> tuple[dict[Path, str | None], list[dict[str, Any]]]:
    source_file = substation_file(project_file, source_id)
    renamed: dict[str, str] = {}
    entries: list[dict[str, Any]] = []
    for entry in project.get("documents") or []:
        if entry.get("substation") != source_id:
            continue
        key = str(entry["key"])
        new_key = (
            substation_id + key[len(source_id) :]
            if key.startswith(source_id)
            else f"{substation_id}-{key}"
        )
        renamed[key] = new_key
        entries.append({**dict(entry), "key": new_key, "substation": substation_id})
    texts: dict[Path, str | None] = {}
    for path in sorted(source_file.parent.rglob("*.yaml")):
        data = load_text(path.read_text(encoding="utf-8-sig"))
        if path == source_file:
            set_entry(data["substation"], "id", substation_id)
            set_entry(data["substation"], "name", name)
        _rename_documents(data, renamed)
        texts[folder / path.relative_to(source_file.parent)] = dump_text(data)
    return texts, entries


def _rename_documents(node: Any, renamed: Mapping[str, str]) -> None:
    """Point every ``document:`` key at the copy's register entries."""
    if isinstance(node, CommentedMap):
        for key, value in node.items():
            if key == "document" and isinstance(value, str) and value in renamed:
                set_entry(node, key, renamed[value])
            else:
                _rename_documents(value, renamed)
    elif isinstance(node, CommentedSeq):
        for item in node:
            _rename_documents(item, renamed)


def delete_substation(
    project_file: Path,
    substation_id: str,
    *,
    store: LibraryStore | None = None,
) -> Deleted:
    """Back the project up, then remove the substation's folder, its entry in
    ``substations`` and its register documents."""
    file = substation_file(project_file, substation_id)
    project = load_text(project_file.read_text(encoding="utf-8-sig"))

    def change(root: CommentedMap) -> None:
        documents = _list(root, "documents")
        for index in reversed(range(len(documents))):
            if documents[index].get("substation") == substation_id:
                remove_entry(documents, index)
        listed = root[SUBSTATIONS]
        for index in reversed(range(len(listed))):
            if (project_file.parent / str(listed[index])).resolve() == file.resolve():
                remove_entry(listed, index)

    edit_document(project, change)
    texts: dict[Path, str | None] = {project_file: dump_text(project)}
    texts |= {path: None for path in file.parent.rglob("*.yaml")}
    check = commit(project_file, None, texts, store=store, dry_run=True)
    if not check.written:
        return Deleted(check, None)
    backup = backup_project(project_file)
    result = commit(project_file, None, texts, store=store)
    if result.written:
        shutil.rmtree(file.parent, ignore_errors=True)
    return Deleted(result, backup)


def delete_project(project_file: Path, deleted_folder: Path) -> Path:
    """Save the project as ``<deleted_folder>/<id>.bomproj``, then remove its folder; the
    returned file restores it (ADR 0012)."""
    data = read_yaml(project_file).data
    project_id = str((data.get("project") or {}).get("id") or project_file.parent.name)
    deleted_folder.mkdir(parents=True, exist_ok=True)
    target = deleted_folder / f"{project_id}{PROJECT_SUFFIX}"
    for number in range(2, 1000):
        if not target.exists():
            break
        target = deleted_folder / f"{project_id}-{number}{PROJECT_SUFFIX}"
    saved = export_project(project_file, target).path
    shutil.rmtree(project_file.parent)
    return saved


def _map(data: Mapping[str, Any]) -> CommentedMap:
    node = CommentedMap()
    set_entry(node, "_", dict(data))
    value: CommentedMap = node["_"]
    return value


def _list(root: CommentedMap, key: str) -> CommentedSeq:
    if not isinstance(root.get(key), CommentedSeq):
        set_entry(root, key, [])
    value: CommentedSeq = root[key]
    if value.fa.flow_style():
        value.fa.set_block_style()  # entries one per line, as the files write them
    return value
