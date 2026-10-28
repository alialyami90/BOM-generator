"""Writers for a substation's loose material (plan M18, ADRs 0021 and 0022).

An item is a library part (``part_id``, optionally ``children`` and ``fed_from``) or free
text (``description``); both take ``qty`` and ``tag``, the designation printed in the Tag
column. Every writer is checked against the whole project before it writes.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from bomgen.io.edit import EditError, EditResult, edit_file, edit_substation, substation_file
from bomgen.io.errors import Loc, format_location
from bomgen.io.fields import move_item, remove_item, set_field
from bomgen.io.round_trip import insert_entry, set_entry

if TYPE_CHECKING:
    from bomgen.library_store.store import LibraryStore

ITEMS: Loc = ("loose_material", "items")


def _items(data: CommentedMap) -> CommentedSeq:
    material = data.get("loose_material")
    items = material.get("items") if isinstance(material, CommentedMap) else None
    if not isinstance(items, CommentedSeq):
        raise EditError("the substation has no loose material")
    return items


def _index(items: CommentedSeq, index: int) -> None:
    if not 0 <= index < len(items):
        raise EditError(f"no loose item {index}")


def add_loose_item(
    project_file: Path,
    substation_id: str,
    item: Mapping[str, Any],
    *,
    index: int | None = None,
    host_panel: str | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Insert ``item`` at ``index`` (``None``: at the end). The first item starts the
    substation's ``loose_material``, which needs ``host_panel``."""

    def change(data: CommentedMap) -> None:
        material = data.get("loose_material")
        if not isinstance(material, CommentedMap):
            if host_panel is None:
                raise EditError("the first loose item needs host_panel")
            set_entry(data, "loose_material", {"host_panel": host_panel, "items": []})
            material = data["loose_material"]
        items = material.get("items")
        if not isinstance(items, CommentedSeq):
            set_entry(material, "items", [])
            items = material["items"]
        position = len(items) if index is None else index
        if not 0 <= position <= len(items):
            raise EditError(f"no loose item {position}")
        insert_entry(items, position, dict(item))

    return edit_substation(project_file, substation_id, change, store=store)


def set_loose_item(
    project_file: Path,
    substation_id: str,
    index: int,
    item: Mapping[str, Any],
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Replace loose item ``index`` with ``item``; the keys it keeps keep their comments,
    so switching between a part and free text drops only the keys that no longer apply."""

    def change(data: CommentedMap) -> None:
        items = _items(data)
        _index(items, index)
        set_entry(items, index, dict(item))

    return edit_substation(project_file, substation_id, change, store=store)


def remove_loose_item(
    project_file: Path, substation_id: str, index: int, *, store: LibraryStore | None = None
) -> EditResult:
    """Remove loose item ``index``; ``loose_material`` stays, with ``items: []`` after the
    last, so its host panel and title are kept for the next item."""
    return remove_item(project_file, ITEMS, index, substation=substation_id, store=store)


def move_loose_item(
    project_file: Path,
    substation_id: str,
    source: int,
    target: int,
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Move loose item ``source`` to position ``target`` (the sheet's order)."""
    return move_item(project_file, ITEMS, source, target, substation=substation_id, store=store)


def set_host_panel(
    project_file: Path, substation_id: str, panel_id: str, *, store: LibraryStore | None = None
) -> EditResult:
    """Issue the Loose Material sheet under ``panel_id``'s document."""
    path: Loc = ("loose_material", "host_panel")
    return set_field(project_file, path, panel_id, substation=substation_id, store=store)


def validate_loose_item(
    project_file: Path,
    substation_id: str,
    index: int | None,
    item: Mapping[str, Any],
    *,
    store: LibraryStore | None = None,
) -> dict[str, str]:
    """The engine's messages for ``item`` as item ``index`` (``None``: a new last item), by
    field (``"part_id"``, ``"fed_from"``, ``"children[0]"``; ``""`` for the item as a
    whole, e.g. neither a part nor a description). Nothing is written."""
    at = 0  # the item's index once placed

    def change(data: CommentedMap) -> None:
        material = data.get("loose_material")
        if not isinstance(material, CommentedMap):
            set_entry(data, "loose_material", {"host_panel": "", "items": []})
        items = data["loose_material"].get("items")
        if not isinstance(items, CommentedSeq):
            set_entry(data["loose_material"], "items", [])
            items = data["loose_material"]["items"]
        if index is not None:
            _index(items, index)
        position = len(items) if index is None else index
        set_entry(items, position, dict(item))
        nonlocal at
        at = position

    file = substation_file(project_file, substation_id)
    result = edit_file(project_file, file, change, substation_id, store=store, dry_run=True)
    base = format_location((*ITEMS, at))
    messages: dict[str, str] = {}
    for issue in result.issues if not result.written else ():
        if issue.file.resolve() != file.resolve():
            continue
        if issue.location == base:
            messages.setdefault("", issue.message)
        elif issue.location.startswith(f"{base}."):
            messages.setdefault(issue.location.removeprefix(f"{base}."), issue.message)
    return messages
