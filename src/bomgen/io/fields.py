"""Field-level writers and checks for the app's forms (plan M17c, ADR 0021).

A field is named by its path in a file, e.g. ``("defaults", "spares", "port_fraction")``
in the project file or ``("equipment", 2, "qty")`` in a substation file. The target file
is the project file, a substation file (``substation=``) or a hand-written panel file
(``panel=`` with ``substation=``). Every writer goes through :func:`edit.edit_file`, so
it is checked against the whole project before it is written.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from bomgen.io.edit import EditError, EditResult, edit_file, substation_file
from bomgen.io.errors import Loc, format_location
from bomgen.io.loader import LoadedProject
from bomgen.io.panel_edit import panel_file
from bomgen.io.round_trip import (
    Node,
    child_map,
    comment_of,
    insert_entry,
    load_text,
    move_entry,
    remove_entry,
    set_comment,
    set_entry,
)

if TYPE_CHECKING:
    from bomgen.library_store.store import LibraryStore

ASSUMED = "ASSUMED"  # the marker of a value the source workbook does not give


def target_file(
    project_file: Path, substation: str | None = None, panel: str | None = None
) -> Path:
    """The file a field path is in."""
    if panel is not None:
        if substation is None:
            raise EditError("a panel is named within its substation")
        return panel_file(project_file, substation, panel)
    if substation is not None:
        return substation_file(project_file, substation)
    return project_file


def _walk(data: CommentedMap, path: Loc, *, create: bool) -> Node:
    """The container holding ``path``'s last key; mappings on the way are created when
    ``create`` is set."""
    node: Node = data
    for key in path[:-1]:
        if isinstance(node, CommentedSeq):
            if not isinstance(key, int) or not 0 <= key < len(node):
                raise EditError(f"no item {key} at {format_location(path)}")
            child = node[key]
        elif create and not isinstance(node.get(key), (CommentedMap, CommentedSeq)):
            child = child_map(node, key)
        elif key in node:
            child = node[key]
        else:
            raise EditError(f"nothing at {format_location(path)}")
        if not isinstance(child, (CommentedMap, CommentedSeq)):
            raise EditError(f"{format_location(path)} is inside a value, not a mapping or list")
        node = child
    return node


def _list_at(data: CommentedMap, path: Loc) -> CommentedSeq:
    parent = _walk(data, path, create=True)
    key = path[-1]
    node = parent[key] if isinstance(parent, CommentedSeq) or key in parent else None
    if node is None:
        set_entry(parent, key, [])
        node = parent[key]
    if not isinstance(node, CommentedSeq):
        raise EditError(f"{format_location(path)} is not a list")
    return node


def _edit(
    project_file: Path,
    change: Any,
    substation: str | None,
    panel: str | None,
    store: LibraryStore | None,
    dry_run: bool = False,
) -> EditResult:
    file = target_file(project_file, substation, panel)
    return edit_file(project_file, file, change, substation, store=store, dry_run=dry_run)


def set_field(
    project_file: Path,
    path: Loc,
    value: Any,
    *,
    substation: str | None = None,
    panel: str | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Set the field at ``path`` (missing mappings on the way are added)."""
    _check_path(path)
    return _edit(
        project_file,
        lambda data: set_entry(_walk(data, path, create=True), path[-1], value),
        substation,
        panel,
        store,
    )


def remove_field(
    project_file: Path,
    path: Loc,
    *,
    substation: str | None = None,
    panel: str | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Remove the field at ``path`` so its default or inherited value applies again; a
    mapping the removal leaves empty goes too."""
    _check_path(path)

    def change(data: CommentedMap) -> None:
        for depth in range(len(path), 0, -1):
            parent = _walk(data, path[:depth], create=False)
            key = path[depth - 1]
            if isinstance(parent, CommentedMap) and key not in parent:
                return
            value = parent[key]
            if depth < len(path) and not (isinstance(value, CommentedMap) and not value):
                return
            remove_entry(parent, key)

    return _edit(project_file, change, substation, panel, store)


def insert_item(
    project_file: Path,
    path: Loc,
    index: int | None,
    value: Any,
    *,
    substation: str | None = None,
    panel: str | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Insert ``value`` into the list at ``path`` at ``index`` (``None``: at the end)."""
    _check_path(path)

    def change(data: CommentedMap) -> None:
        items = _list_at(data, path)
        insert_entry(items, len(items) if index is None else index, value)

    return _edit(project_file, change, substation, panel, store)


def remove_item(
    project_file: Path,
    path: Loc,
    index: int,
    *,
    substation: str | None = None,
    panel: str | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Remove item ``index`` of the list at ``path``."""
    _check_path(path)

    def change(data: CommentedMap) -> None:
        items = _list_at(data, path)
        if not 0 <= index < len(items):
            raise EditError(f"no item {index} at {format_location(path)}")
        remove_entry(items, index)

    return _edit(project_file, change, substation, panel, store)


def move_item(
    project_file: Path,
    path: Loc,
    source: int,
    target: int,
    *,
    substation: str | None = None,
    panel: str | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Move item ``source`` of the list at ``path`` to position ``target``."""
    _check_path(path)

    def change(data: CommentedMap) -> None:
        items = _list_at(data, path)
        if not (0 <= source < len(items) and 0 <= target < len(items)):
            raise EditError(f"cannot move item {source} to {target} at {format_location(path)}")
        move_entry(items, source, target)

    return _edit(project_file, change, substation, panel, store)


def validate_field(
    project_file: Path,
    path: Loc,
    value: Any,
    *,
    substation: str | None = None,
    panel: str | None = None,
    store: LibraryStore | None = None,
) -> str | None:
    """The engine's message for setting ``path`` to ``value``, or ``None`` when the value is
    fine; nothing is written. Problems the value causes elsewhere are not reported here
    (the writer reports them)."""
    _check_path(path)
    file = target_file(project_file, substation, panel)
    result = _edit(
        project_file,
        lambda data: set_entry(_walk(data, path, create=True), path[-1], value),
        substation,
        panel,
        store,
        dry_run=True,
    )
    location = format_location(path)
    for issue in result.issues if not result.written else ():
        if issue.file.resolve() != file.resolve():
            continue
        if _related(issue.location, location):
            return issue.message
    return None


def _related(issue_location: str, location: str) -> bool:
    """One location is the other or inside it, e.g. ``constants`` (a rule over several
    keys) and ``constants.t_max_c``."""
    shorter, longer = sorted((issue_location, location), key=len)
    return longer == shorter or longer.startswith((f"{shorter}.", f"{shorter}["))


def _check_path(path: Loc) -> None:
    if not path:
        raise EditError("a field path names at least one key")


# --- the register ---


def document_users(loaded: LoadedProject, key: str) -> list[str]:
    """What uses register document ``key``, e.g. ``"gis01: Power Consumption sheet"``; the
    UI keeps Remove disabled while this is not empty."""
    users: list[str] = []
    for target in loaded.substations:
        sub = target.substation
        name = sub.substation.id
        if sub.document == key:
            users.append(f"{name}: workbook")
        sheets = sub.calculations.model_dump()
        for sheet, info in sheets.items():
            if info["document"] == key:
                users.append(f"{name}: {sheet.replace('_', ' ')} sheet")
        if sub.generated_panels is not None and sub.generated_panels.document == key:
            users.append(f"{name}: generated panels")
        for panel in target.panels:
            if panel.document == key and not panel.generated:
                users.append(f"{name}: panel {panel.id}")
    return users


# --- values marked "# ASSUMED" ---


def assumed_fields(file: Path) -> list[Loc]:
    """Paths of the values in ``file`` whose comment marks them ``ASSUMED``."""
    found: list[Loc] = []

    def walk(node: Node, loc: Loc) -> None:
        keys: Sequence[Any] = list(node) if isinstance(node, CommentedMap) else range(len(node))
        for key in keys:
            if ASSUMED in comment_of(node, key).split():
                found.append((*loc, key))
            child = node[key]
            if isinstance(child, (CommentedMap, CommentedSeq)):
                walk(child, (*loc, key))

    walk(load_text(file.read_text(encoding="utf-8-sig")), ())
    return found


def confirm_field(
    project_file: Path,
    path: Loc,
    *,
    substation: str | None = None,
    panel: str | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Drop the ``ASSUMED`` mark from the field at ``path``; the rest of its comment stays."""
    _check_path(path)

    def change(data: CommentedMap) -> None:
        parent = _walk(data, path, create=False)
        words = comment_of(parent, path[-1]).split()
        if ASSUMED not in words:
            raise EditError(f"{format_location(path)} is not marked {ASSUMED}")
        set_comment(parent, path[-1], " ".join(w for w in words if w != ASSUMED))

    return _edit(project_file, change, substation, panel, store)


def file_fingerprint(path: Path) -> str:
    """A hash of ``path``'s bytes, so the app can tell whether a file changed on disk since
    it was read."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
