"""The library's pending set: edits held in the app until they are applied (M16, ADR 0018).

docs/ui/editing.md "The pending set": saved device edits collect here, per library, with the
installed version they started from. They are `library_store.edit` operations as plain JSON,
so applying them is A5's `save_edits`; this module only keeps them between sessions, folds
repeated edits of one field together and describes the result for the review.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bomgen.io.errors import InputError
from bomgen.io.loader import load_library
from bomgen.library_store.edit import apply_edits, check_field, parse_edits
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.local import next_local_version, save_edits
from bomgen.library_store.store import LibraryStore
from bomgen.library_store.versions import Version
from bomgen.models.library import Library

PENDING_DIR = "library-pending"
_MISSING = object()


@dataclass(frozen=True)
class Pending:
    """The edits waiting for one library, the version they started from, and why the file
    could not be read (then `base` is None and `edits` empty, so the set can be discarded)."""

    base: str | None
    edits: list[dict[str, Any]] = field(default_factory=list)
    problem: str | None = None


class PendingEdits:
    """Pending sets kept as one JSON file per library in the app home."""

    def __init__(self, app_home: Path) -> None:
        self.folder = app_home / PENDING_DIR

    def file(self, name: str) -> Path:
        return self.folder / f"{name}.json"

    def load(self, name: str) -> Pending | None:
        path = self.file(name)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            base, edits = data["base"], data["edits"]
            if not isinstance(base, str) or not isinstance(edits, list):
                raise ValueError("base must be text and edits a list")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return Pending(None, [], f"the pending changes file {path.name} cannot be read: {exc}")
        return Pending(base, edits)

    def save(self, name: str, pending: Pending) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.file(name)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps({"base": pending.base, "edits": pending.edits}), "utf-8")
        os.replace(temp, path)

    def clear(self, name: str) -> None:
        self.file(name).unlink(missing_ok=True)


class EditRefusedError(Exception):
    """An edit the library cannot take; the message names each place and its problem."""


class LibraryEditor:
    """The pending set of one installed library, with what the bridge shows of it."""

    def __init__(self, store: LibraryStore, pending: PendingEdits, name: str) -> None:
        self.store, self.pending, self.name = store, pending, name

    def _active(self) -> str | None:
        try:
            return self.store.active_version(self.name)
        except LibraryPackageError:
            return None

    def _current(self) -> Pending:
        return self.pending.load(self.name) or Pending(self._active(), [])

    def _library(self, version: str) -> Library:
        try:
            return load_library(self.store.library_file(self.name, version))
        except InputError as exc:
            raise LibraryPackageError(
                f"library {self.name} {version}: the installed library is damaged",
                RefusalKind.STORE_DAMAGED,
            ) from exc

    def _edited(self, pending: Pending, more: Sequence[dict[str, Any]] = ()) -> Library:
        """The base library with the pending edits (and `more`) applied."""
        assert pending.base is not None
        result = apply_edits(self._library(pending.base), parse_edits([*pending.edits, *more]))
        if result.library is None:
            listed = "; ".join(f"{p.location}: {p.message}" for p in result.problems)
            raise EditRefusedError(listed)
        return result.library

    def page(self) -> dict[str, Any]:
        """The pending set for the bar and the review."""
        pending, active = self._current(), self._active()
        problem = pending.problem
        if problem is None and pending.base not in self.store.versions(self.name):
            problem = (
                f"the pending changes started from {self.name} {pending.base}, "
                "which is no longer installed"
            )
        entries: list[dict[str, str]] = []
        if problem is None and pending.base is not None and pending.edits:
            entries = describe(self._library(pending.base), self._edited(pending))
        base = pending.base or active
        return {
            "name": self.name,
            "base": base,
            "active": active,
            "entries": entries,
            "count": len(entries),
            "next_version": str(next_local_version(self.store, self.name, Version.parse(base)))
            if base
            else None,
            "problem": problem,
        }

    def device(self, part_id: str) -> dict[str, Any]:
        """A device as the editor shows it: with the pending edits, beside its saved values."""
        pending = self._current()
        if pending.base is None or pending.problem:
            raise LibraryPackageError(
                pending.problem or "no library is active", RefusalKind.NOT_INSTALLED
            )
        saved = next((d for d in self._library(pending.base).devices if d.part_id == part_id), None)
        edited = next((d for d in self._edited(pending).devices if d.part_id == part_id), None)
        if edited is None:
            raise KeyError(part_id)
        now = edited.model_dump(mode="json")
        was = saved.model_dump(mode="json") if saved else None
        return {
            "device": now,
            "saved": was,
            "pending_fields": [k for k, v in now.items() if was is None or was.get(k) != v],
            "used_by": [],
        }

    def check(self, part_id: str, key: str, value: object) -> str | None:
        """The model's message for setting one device field, or None when it fits."""
        pending = self._current()
        assert pending.base is not None
        return check_field(self._edited(pending), ["devices", part_id, key], value)

    def add(self, edits: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Check `edits` against the pending library and keep them; refuse them all if one fails."""
        pending = self._current()
        if pending.base is None or pending.problem:
            raise LibraryPackageError(
                pending.problem or "no library is active", RefusalKind.NOT_INSTALLED
            )
        parse_edits(edits)  # a malformed edit is refused before anything is kept
        self._edited(pending, edits)
        base = self._library(pending.base).model_dump(mode="json")
        saved = {
            ("devices", d["part_id"], key): value
            for d in base["devices"]
            for key, value in d.items()
        }
        merged = merge(pending.edits, edits, saved)
        if merged:
            self.pending.save(self.name, Pending(pending.base, merged))
        else:
            self.pending.clear(self.name)
        return self.page()

    def discard(self) -> dict[str, Any]:
        """Drop the set; the edits come back so the page can offer Undo."""
        pending = self.pending.load(self.name)
        self.pending.clear(self.name)
        return {"discarded": pending.edits if pending else [], "page": self.page()}

    def apply(self, note: str) -> dict[str, Any]:
        """Write the set as the next local version of its base, make it active, clear the set."""
        pending = self._current()
        if pending.base is None or pending.problem or not pending.edits:
            raise LibraryPackageError(
                pending.problem or f"library {self.name}: there are no pending changes",
                RefusalKind.NO_CHANGES,
            )
        saved = save_edits(
            self.store, self.name, parse_edits(pending.edits), base=pending.base, note=note
        )
        self.pending.clear(self.name)
        return {"version": saved.manifest.version, "previous": saved.previous, "diff": saved.diff}


def merge(
    edits: Sequence[dict[str, Any]],
    new: Sequence[dict[str, Any]],
    base: Mapping[tuple[Any, ...], Any],
) -> list[dict[str, Any]]:
    """`edits` followed by `new`, keeping one set or remove per path.

    A field set back to its saved value (`base`, keyed by path) is no longer an edit, so its
    entry goes. Inserts are kept as they come.
    """
    merged = list(edits)
    for edit in new:
        path = tuple(edit["path"])
        if edit["op"] == "insert":
            merged.append(edit)
            continue
        merged = [e for e in merged if e["op"] == "insert" or tuple(e["path"]) != path]
        saved = base.get(path, _MISSING)
        now = edit.get("value") if edit["op"] == "set" else None
        if saved is _MISSING or now != saved:
            merged.append(edit)
    return merged


def describe(before: Library, after: Library) -> list[dict[str, str]]:
    """One review entry per changed device field, added or removed device, and catalogue."""
    old = {d.part_id: d.model_dump(mode="json") for d in before.devices}
    new = {d.part_id: d.model_dump(mode="json") for d in after.devices}
    entries: list[dict[str, str]] = []
    for part_id, device in new.items():
        if part_id not in old:
            text = " ".join(filter(None, (device.get("make"), device.get("model"))))
            entries.append(_entry("Device", part_id, "added", "", "", text))
            continue
        for key, value in device.items():
            was = old[part_id].get(key)
            if value != was:
                entries.append(_entry("Device", part_id, "changed", key, _text(was), _text(value)))
    for part_id in old.keys() - new.keys():
        entries.append(_entry("Device", part_id, "removed", "", part_id, ""))
    cat_old = before.catalogues.model_dump(mode="json")
    cat_new = after.catalogues.model_dump(mode="json")
    for key in cat_new:
        if cat_new[key] != cat_old.get(key):
            entries.append(_entry("Catalogue", key, "changed", "", "", ""))
    return entries


def _entry(area: str, label: str, kind: str, key: str, was: str, now: str) -> dict[str, str]:
    return {"area": area, "label": label, "kind": kind, "field": key, "from": was, "to": now}


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, str | int | float):
        return str(value)
    return json.dumps(value, ensure_ascii=False)
