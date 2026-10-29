"""The library's pending set: edits held in the app until they are applied (M16, ADR 0018).

docs/ui/editing.md "The pending set": saved device edits collect here, per library, with the
installed version they started from. They are `library_store.edit` operations as plain JSON,
so applying them is A5's `save_edits`; this module only keeps them between sessions, folds
repeated edits of one field together and describes the result for the review.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args

from bomgen.io.errors import InputError
from bomgen.io.loader import load_library
from bomgen.library_store.alternatives import compare_alternatives
from bomgen.library_store.device_db import DeviceRecord, MountingKind, load_device_records
from bomgen.library_store.edit import apply_edits, check_field, parse_edits
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.local import next_local_version, save_edits
from bomgen.library_store.records import apply_record_edits, check_record_field
from bomgen.library_store.store import LibraryStore
from bomgen.library_store.versions import Version
from bomgen.models.library import (
    Category,
    Library,
    LoadType,
    Media,
    PortKind,
    PortSpeed,
    PortUse,
    PurdueLevel,
    SupplyType,
    Tier,
)

PENDING_DIR = "library-pending"
# The values the model takes for the editor's choice fields, so the page never lists its own.
CHOICES = {
    "category": [c.value for c in Category],
    "supply_type": [c.value for c in SupplyType],
    "load_type": [c.value for c in LoadType],
    "purdue_level": [c.value for c in PurdueLevel],
    "speed": [c.value for c in PortSpeed],
    "media": [c.value for c in Media],
    "kind": [c.value for c in PortKind],
    "usable_for": [c.value for c in PortUse],
    "per": ["unit", "serial_port"],
    "tier": list(get_args(Tier)),
    # the datasheet record's
    "verified": list(get_args(DeviceRecord.model_fields["verified"].annotation)),
    "mounting_kind": list(get_args(MountingKind)),
}
# What a copy leaves behind: it is a new part, not a member of the source's alternative group.
_NOT_COPIED = ("alt_group", "tier")
_MISSING = object()


@dataclass(frozen=True)
class Pending:
    """The edits waiting for one library, the version they started from, and why the file
    could not be read (then `base` is None and `edits` empty, so the set can be discarded)."""

    base: str | None
    edits: list[dict[str, Any]] = field(default_factory=list)
    problem: str | None = None
    # Edits of the device-database records: one `set` or `remove` per changed top-level key
    # of a record ([part_id, key]), so a record's edits are always its whole new value.
    record_edits: list[dict[str, Any]] = field(default_factory=list)


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
            records = data.get("record_edits", [])
            if not isinstance(base, str) or not isinstance(edits, list):
                raise ValueError("base must be text and edits a list")
            if not isinstance(records, list):
                raise ValueError("record_edits must be a list")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return Pending(None, [], f"the pending changes file {path.name} cannot be read: {exc}")
        return Pending(base, edits, record_edits=records)

    def save(self, name: str, pending: Pending) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.file(name)
        temp = path.with_suffix(".tmp")
        data = {"base": pending.base, "edits": pending.edits, "record_edits": pending.record_edits}
        temp.write_text(json.dumps(data), "utf-8")
        os.replace(temp, path)

    def clear(self, name: str) -> None:
        self.file(name).unlink(missing_ok=True)


class EditRefusedError(Exception):
    """An edit the library cannot take; the message names each place and its problem."""


class LibraryEditor:
    """The pending set of one installed library, with what the bridge shows of it."""

    def __init__(self, store: LibraryStore, pending: PendingEdits, name: str) -> None:
        self.store, self.pending, self.name = store, pending, name
        self._records_read: dict[str, dict[str, DeviceRecord]] = {}

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

    def _saved_records(self, version: str) -> dict[str, DeviceRecord]:
        """The installed version's device records, read once per editor (one bridge call)."""
        if version not in self._records_read:
            self._records_read[version] = load_device_records(self.store, self.name, version)
        return self._records_read[version]

    def _records(self, pending: Pending, more: Sequence[dict[str, Any]] | None = None) -> Any:
        """The base version's device records with the pending record edits (or `more`
        instead of them) applied."""
        assert pending.base is not None
        edits = pending.record_edits if more is None else more
        records = self._saved_records(pending.base)
        if not edits:
            return records
        result = apply_record_edits(records, parse_edits(edits))
        if result.records is None:
            listed = "; ".join(
                f"{p.location}: {p.message.removeprefix('Value error, ')}" for p in result.problems
            )
            raise EditRefusedError(listed)
        return result.records

    def _ready(self) -> Pending:
        pending = self._current()
        if pending.base is None or pending.problem:
            raise LibraryPackageError(
                pending.problem or "no library is active", RefusalKind.NOT_INSTALLED
            )
        return pending

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
        if problem is None and pending.base is not None and pending.record_edits:
            saved = self._saved_records(pending.base)
            entries += describe_records(saved, self._records(pending))
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
            "choices": CHOICES,
        }

    def device(self, part_id: str) -> dict[str, Any]:
        """A device as the editor shows it: with the pending edits, beside its saved values."""
        pending = self._ready()
        assert pending.base is not None
        saved = next((d for d in self._library(pending.base).devices if d.part_id == part_id), None)
        library = self._edited(pending)
        edited = next((d for d in library.devices if d.part_id == part_id), None)
        if edited is None:
            raise KeyError(part_id)
        now = edited.model_dump(mode="json")
        was = saved.model_dump(mode="json") if saved else None
        record = self._records(pending).get(part_id)
        saved_record = self._saved_records(pending.base).get(part_id)
        return {
            "device": now,
            "saved": was,
            "record": record.model_dump(mode="json") if record else None,
            "saved_record": saved_record.model_dump(mode="json") if saved_record else None,
            "pending_fields": [k for k, v in now.items() if was is None or was.get(k) != v],
            "used_by": [],
            "choices": CHOICES,
            "part_ids": sorted(d.part_id for d in library.devices),
            "part_names": {
                d.part_id: " ".join(filter(None, (d.make, d.model))) for d in library.devices
            },
        }

    def check(self, part_id: str, key: str, value: object) -> str | None:
        """The model's message for setting one device field, or None when it fits."""
        pending = self._current()
        assert pending.base is not None
        return in_words(key, check_field(self._edited(pending), ["devices", part_id, key], value))

    def alternatives(self, part_id: str) -> dict[str, Any]:
        """The device and its alternatives as comparison rows, pending edits applied."""
        pending = self._ready()
        library = self._edited(pending)
        rows = compare_alternatives(library, part_id, self._records(pending))
        device = library.get(part_id)
        assert device is not None
        return {
            "group": device.alt_group,
            "rows": [
                {
                    **dataclasses.asdict(row),
                    "first_port_group": row.first_port_group.model_dump(mode="json")
                    if row.first_port_group
                    else None,
                }
                for row in rows
            ],
        }

    def check_record(self, part_id: str, path: str, value: object) -> str | None:
        """The model's message for setting one record field (a dotted path), or None."""
        pending = self._ready()
        records = self._records(pending)
        if part_id not in records:
            raise KeyError(part_id)
        record = records[part_id].model_dump(mode="json", exclude_none=True)
        key, new = _with_field(record, path.split("."), value)
        message = check_record_field(records, [part_id, key], new)
        return in_words(key, message.removeprefix("Value error, ") if message else None)

    def set_record_fields(self, part_id: str, fields: Mapping[str, object]) -> dict[str, Any]:
        """Set fields of a device's record (dotted paths; None empties one) in the pending set.

        The record's edits are rewritten as one `set` (or `remove`) per top-level key that now
        differs from the saved record, so a value set back to the saved one leaves the set.
        """
        pending = self._ready()
        assert pending.base is not None
        records = self._records(pending)
        if part_id not in records:
            raise KeyError(part_id)
        record = records[part_id].model_dump(mode="json", exclude_none=True)
        for path, value in fields.items():
            key, record[key] = _with_field(record, path.split("."), value)
            if record[key] is None:
                del record[key]
        saved_records = self._saved_records(pending.base)
        saved = saved_records[part_id].model_dump(mode="json", exclude_none=True)
        mine: list[dict[str, Any]] = []
        for key in sorted(saved.keys() | record.keys()):
            if key not in record:
                mine.append({"op": "remove", "path": [part_id, key]})
            elif record[key] != saved.get(key):
                mine.append({"op": "set", "path": [part_id, key], "value": record[key]})
        others = [e for e in pending.record_edits if e["path"][0] != part_id]
        record_edits = others + mine
        self._records(pending, record_edits)  # refused before anything is kept
        kept = Pending(pending.base, pending.edits, record_edits=record_edits)
        if kept.edits or kept.record_edits:
            self.pending.save(self.name, kept)
        else:
            self.pending.clear(self.name)
        return self.page()

    def add(
        self, edits: Sequence[dict[str, Any]], record_edits: Sequence[dict[str, Any]] = ()
    ) -> dict[str, Any]:
        """Check `edits` against the pending library and keep them; refuse them all if one fails.

        `record_edits` (as `discard` returns them, for Undo) replace the pending record edits of
        the parts they name."""
        pending = self._ready()
        assert pending.base is not None
        parse_edits(edits)  # a malformed edit is refused before anything is kept
        self._edited(pending, edits)
        if record_edits:
            parts = {e["path"][0] for e in record_edits}
            mine = [e for e in pending.record_edits if e["path"][0] not in parts]
            self._records(pending, [*mine, *record_edits])
            pending = Pending(pending.base, pending.edits, record_edits=[*mine, *record_edits])
        assert pending.base is not None
        base = self._library(pending.base).model_dump(mode="json")
        saved = {
            ("devices", d["part_id"], key): value
            for d in base["devices"]
            for key, value in d.items()
        }
        merged = merge(pending.edits, edits, saved)
        if merged or pending.record_edits:
            self.pending.save(
                self.name, Pending(pending.base, merged, record_edits=pending.record_edits)
            )
        else:
            self.pending.clear(self.name)
        return self.page()

    def add_device(
        self,
        part_id: str,
        category: str,
        make: str,
        model: str,
        copy_of: str | None,
        alt_group: str | None = None,
    ) -> dict[str, Any]:
        """Add a device to the pending set: blank, or a copy of `copy_of` under a new identity;
        with `alt_group`, as an alternative in that group."""
        pending = self._ready()
        body: dict[str, Any] = {}
        edited = self._edited(pending)
        if copy_of:
            source = next((d for d in edited.devices if d.part_id == copy_of), None)
            if source is None:
                raise KeyError(copy_of)
            body = source.model_dump(mode="json", exclude_none=True, exclude=set(_NOT_COPIED))
        name = " ".join(filter(None, (make.strip(), model.strip()))) or part_id
        body.update(part_id=part_id, category=category, make=make or None, model=model or None)
        body["alt_group"] = alt_group
        body.setdefault("description_template", name)
        body = {k: v for k, v in body.items() if v is not None}
        if any(d.part_id == part_id for d in edited.devices):
            raise EditRefusedError(f"devices: {part_id} is already in the library")
        return self.add([{"op": "insert", "path": ["devices"], "value": body}])

    def discard(self) -> dict[str, Any]:
        """Drop the set; the edits come back so the page can offer Undo."""
        pending = self.pending.load(self.name)
        self.pending.clear(self.name)
        return {
            "discarded": pending.edits if pending else [],
            "discarded_records": pending.record_edits if pending else [],
            "page": self.page(),
        }

    def apply(self, note: str) -> dict[str, Any]:
        """Write the set as the next local version of its base, make it active, clear the set."""
        pending = self._current()
        if pending.base is None or pending.problem or not (pending.edits or pending.record_edits):
            raise LibraryPackageError(
                pending.problem or f"library {self.name}: there are no pending changes",
                RefusalKind.NO_CHANGES,
            )
        saved = save_edits(
            self.store,
            self.name,
            parse_edits(pending.edits),
            record_edits=parse_edits(pending.record_edits),
            base=pending.base,
            note=note,
        )
        self.pending.clear(self.name)
        return {"version": saved.manifest.version, "previous": saved.previous, "diff": saved.diff}


_PART_LISTS = frozenset({"children", "loose_items"})
_TYPE_WORDS = (
    ("Input should be a valid integer", "Enter a whole number, for example 2."),
    ("Input should be a valid number", "Enter a number, for example 12.5."),
    ("Input should be a valid boolean", "Choose yes or no."),
)


def in_words(key: str, message: str | None) -> str | None:
    """The model's message as the page shows it (editing.md "Validation"): a pattern or type
    error names what to enter; any other message is already in words and is kept."""
    if message is None:
        return None
    if message.startswith("String should match pattern"):
        if key in _PART_LISTS:
            return "Pick a part from the library."
        return "Use letters, digits, dots, dashes, plus signs or underscores."
    for start, words in _TYPE_WORDS:
        if message.startswith(start):
            return words
    return message


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
        if edit["op"] == "remove" and len(path) == 2 and path[0] == "devices":
            added = [
                e
                for e in merged
                if e["op"] == "insert"
                and tuple(e["path"]) == ("devices",)
                and isinstance(e.get("value"), dict)
                and e["value"].get("part_id") == path[1]
            ]
            if added:
                merged = [e for e in merged if e not in added and tuple(e["path"][:2]) != path]
                continue
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


def describe_records(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[dict[str, str]]:
    """One review entry per changed record field (a dotted path such as datasheet.weight_kg)."""
    entries: list[dict[str, str]] = []
    for part_id in sorted(after.keys() & before.keys()):
        old = _leaves(before[part_id].model_dump(mode="json", exclude_none=True))
        new = _leaves(after[part_id].model_dump(mode="json", exclude_none=True))
        for key in sorted(old.keys() | new.keys()):
            if old.get(key) != new.get(key):
                was, now = _text(old.get(key)), _text(new.get(key))
                entries.append(_entry("Datasheet", part_id, "changed", key, was, now))
    return entries


def _leaves(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Nested dicts flattened to dotted paths; lists stay whole."""
    flat: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            flat |= _leaves(value, f"{prefix}{key}.")
        else:
            flat[f"{prefix}{key}"] = value
    return flat


def _with_field(record: Mapping[str, Any], path: Sequence[str], value: object) -> tuple[str, Any]:
    """The record's top-level key on `path` and its value with `path` set (None removes it,
    and a parent left empty goes too); missing parents are made."""
    key = path[0]
    if len(path) == 1:
        return key, value
    top = copy.deepcopy(record.get(key)) or {}
    node = top
    trail = [top]
    for part in path[1:-1]:
        node = node.setdefault(part, {})
        trail.append(node)
    if value is None:
        node.pop(path[-1], None)
        for i in range(len(trail) - 1, 0, -1):
            if trail[i]:
                break
            trail[i - 1].pop(path[i], None)
    else:
        node[path[-1]] = value
    return key, top or None


def _entry(area: str, label: str, kind: str, key: str, was: str, now: str) -> dict[str, str]:
    return {"area": area, "label": label, "kind": kind, "field": key, "from": was, "to": now}


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, str | int | float):
        return str(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return ", ".join(value)
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return "; ".join(_item_text(item) for item in value)
    return json.dumps(value, ensure_ascii=False)


def _item_text(item: dict[str, Any]) -> str:
    """A list item as words: a count or quantity leads ("4 x 1G sfp_slot any")."""
    lead = item.get("count", item.get("qty"))
    rest = " ".join(
        _text(v) for k, v in item.items() if k not in ("count", "qty") and v not in (None, "")
    )
    return f"{_text(lead)} x {rest}" if lead is not None else rest
