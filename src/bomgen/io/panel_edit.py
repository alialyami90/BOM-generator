"""Writers for hand-written panel files (plan M17b, ADR 0021).

A hand-written panel is listed in the substation's ``panels`` or ``manual_panels``; the
app creates new ones under ``panels/`` and lists them in ``manual_panels``, where the
layout never touches them. Generated panels are the layout's and are refused here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from bomgen.io.edit import EditError, EditResult, commit, substation_file
from bomgen.io.errors import InputError
from bomgen.io.round_trip import (
    dump_text,
    edit_document,
    load_text,
    merge_value,
    remove_entry,
    set_entry,
)
from bomgen.io.yaml_source import read_yaml

if TYPE_CHECKING:
    from bomgen.library_store.store import LibraryStore

PANEL_FOLDER = "panels"


@dataclass(frozen=True)
class _Listed:
    substation: Path
    data: CommentedMap  # the substation file, parsed for editing
    key: str  # "panels" or "manual_panels"
    index: int
    file: Path


def _listed(project_file: Path, substation_id: str, panel_id: str) -> _Listed:
    file = substation_file(project_file, substation_id)
    data = load_text(file.read_text(encoding="utf-8-sig"))
    for key in ("panels", "manual_panels"):
        for index, entry in enumerate(data.get(key) or []):
            panel_file = file.parent / str(entry)
            try:
                panel = read_yaml(panel_file).data
            except InputError:
                continue  # a missing or broken file names no panel
            if panel.get("id") == panel_id:
                return _Listed(file, data, key, index, panel_file)
    raise EditError(f"no panel '{panel_id}' in substation '{substation_id}'")


def _hand_written(listed: _Listed) -> CommentedMap:
    panel = load_text(listed.file.read_text(encoding="utf-8-sig"))
    if panel.get("generated") is True:
        raise EditError(f"{listed.file.name} is written by the layout; edit generated_panels")
    return panel


def write_panel(
    project_file: Path,
    substation_id: str,
    panel_id: str,
    panel: Mapping[str, Any],
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Replace hand-written panel ``panel_id``'s contents with ``panel`` (a full panel or
    mirror), keeping the comments of what does not change."""
    listed = _listed(project_file, substation_id, panel_id)
    data = _hand_written(listed)
    edit_document(data, lambda root: merge_value(root, panel))
    return commit(project_file, substation_id, {listed.file: dump_text(data)}, store=store)


def create_panel(
    project_file: Path,
    substation_id: str,
    panel: Mapping[str, Any],
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Write ``panels/<id>.yaml`` and list it last in ``manual_panels``."""
    panel_id = panel.get("id")
    if not isinstance(panel_id, str) or not panel_id:
        raise EditError("a new panel needs an id")
    file = substation_file(project_file, substation_id)
    relative = f"{PANEL_FOLDER}/{panel_id}.yaml"
    panel_file = file.parent / relative
    if panel_file.exists():
        raise EditError(f"{relative} already exists")
    data = load_text(file.read_text(encoding="utf-8-sig"))

    def change(root: CommentedMap) -> None:
        manual = root.get("manual_panels")
        if isinstance(manual, CommentedSeq):
            set_entry(manual, len(manual), relative)
        else:
            set_entry(root, "manual_panels", [relative])

    edit_document(data, change)
    texts = {panel_file: dump_text(merge_value(None, panel)), file: dump_text(data)}
    return commit(project_file, substation_id, texts, store=store)


def delete_panel(
    project_file: Path,
    substation_id: str,
    panel_id: str,
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Delete hand-written panel ``panel_id``'s file and its entry in the substation; refused
    while something still names the panel (a mirror, loose material)."""
    listed = _listed(project_file, substation_id, panel_id)
    _hand_written(listed)
    edit_document(listed.data, lambda root: remove_entry(root[listed.key], listed.index))
    texts = {listed.substation: dump_text(listed.data), listed.file: None}
    return commit(project_file, substation_id, texts, store=store)
