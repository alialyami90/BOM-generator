"""Edit the device-database records of a library by path (ADR 0018, edit operations).

Record edits are the same `set`, `insert` and `remove` operations as library edits, on the
records keyed by `part_id`: ``["SW-1", "datasheet", "weight_kg"]`` is a record's weight,
``["SW-1"]`` the whole record (set it to add one, remove it to delete one). Each edited record
is checked with the `DeviceRecord` model.

A saved version writes each changed record back into the `device-db/` file it came from and
new records into `device-db/local.yaml`; files without a change keep their bytes. YAML comments
in a rewritten file are not kept, as with `library.yaml`.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

import yaml
from pydantic import ValidationError

from bomgen.library_store.device_db import (
    DEVICE_DB_DIR,
    DEVICE_DB_SCHEMA_VERSION,
    DeviceFile,
    DeviceRecord,
    _location,
    parse_device_records,
)
from bomgen.library_store.edit import Insert, Problem, Remove, SetValue, _apply, _PathError
from bomgen.library_store.edit import _describe as _path_text

LOCAL_RECORDS_FILE = f"{DEVICE_DB_DIR}/local.yaml"


@dataclass(frozen=True)
class RecordEditResult:
    """The edited records, or `None` and every problem that stops them from being valid."""

    records: dict[str, DeviceRecord] | None
    problems: list[Problem] = field(default_factory=list)


def apply_record_edits(
    records: Mapping[str, DeviceRecord], edits: Sequence[SetValue | Insert | Remove]
) -> RecordEditResult:
    """Apply `edits` in order to a copy of `records`; the argument is never changed."""
    data = _dump(records)
    for edit in edits:
        try:
            _apply(data, edit)
        except _PathError as exc:
            return RecordEditResult(None, [Problem(_path_text(edit.path), str(exc))])
    edited, problems = _validate(records, data)
    return RecordEditResult(None if problems else edited, problems)


def check_record_field(
    records: Mapping[str, DeviceRecord], path: Sequence[str | int], value: object
) -> str | None:
    """The message for setting `path` to `value`, or `None` when the record stays valid."""
    result = apply_record_edits(records, [SetValue(path=list(path), value=value)])
    return result.problems[0].message if result.problems else None


def changed_records(old: Mapping[str, DeviceRecord], new: Mapping[str, DeviceRecord]) -> list[str]:
    """The part ids added, removed or changed between two sets of records."""
    return sorted(pid for pid in old.keys() | new.keys() if old.get(pid) != new.get(pid))


def write_records(
    files: Mapping[str, bytes], records: Mapping[str, DeviceRecord]
) -> dict[str, bytes]:
    """`files` with the `device-db/` files rewritten to hold exactly `records`.

    A record stays in the file it is in; a new one goes to `device-db/local.yaml`. Only files
    whose records change are rewritten.
    """
    known = parse_device_records(files)  # also checks that every file is valid
    new = [record for pid, record in records.items() if pid not in known]
    result = dict(files)
    for name in sorted(files):
        path = PurePosixPath(name)
        if path.parts[:1] != (DEVICE_DB_DIR,) or path.suffix not in (".yaml", ".yml"):
            continue
        file = DeviceFile.model_validate(yaml.safe_load(files[name].decode("utf-8")))
        kept = [records[r.part_id] for r in file.records if r.part_id in records]
        if name == LOCAL_RECORDS_FILE:
            kept += new
        if kept != file.records:
            result[name] = _dump_file(file, kept)
    if new and LOCAL_RECORDS_FILE not in files:
        local = DeviceFile(
            schema_version=DEVICE_DB_SCHEMA_VERSION,
            area="local",
            title="Records added in this library",
            records=[],
        )
        result[LOCAL_RECORDS_FILE] = _dump_file(local, new)
    return result


def _dump_file(file: DeviceFile, records: list[DeviceRecord]) -> bytes:
    data = file.model_copy(update={"records": records}).model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode("utf-8")


def _dump(records: Mapping[str, DeviceRecord]) -> dict[str, Any]:
    return {
        pid: copy.deepcopy(record.model_dump(mode="json", exclude_none=True))
        for pid, record in records.items()
    }


def _validate(
    original: Mapping[str, DeviceRecord], data: Mapping[str, Any]
) -> tuple[dict[str, DeviceRecord], list[Problem]]:
    before = _dump(original)
    edited: dict[str, DeviceRecord] = {}
    problems: list[Problem] = []
    for pid, value in data.items():
        if pid in original and value == before[pid]:
            edited[pid] = original[pid]
            continue
        try:
            record = DeviceRecord.model_validate(value)
        except ValidationError as exc:
            problems.extend(_problems(pid, value, exc))
            continue
        if record.part_id != pid:
            problems.append(
                Problem(f"{pid}.part_id", f"must be {pid!r}, the part the record belongs to")
            )
            continue
        edited[pid] = record
    return edited, problems


def _problems(pid: str, value: Any, exc: ValidationError) -> list[Problem]:
    """One problem per field. A union (a figure is an int or a float) reports each member,
    so the members' tags are cut off the location and the last member's message is kept."""
    found: dict[str, str] = {}
    for error in exc.errors():
        loc = _field_loc(value, tuple(error["loc"]))
        joiner = "" if not loc or isinstance(loc[0], int) else "."
        message = "unknown key" if error["type"] == "extra_forbidden" else error["msg"]
        found[f"{pid}{joiner}{_location(loc)}"] = message
    return [Problem(location, message) for location, message in found.items()]


def _field_loc(value: Any, loc: tuple[int | str, ...]) -> tuple[int | str, ...]:
    """`loc` up to the first segment that reaches a single value in `value`."""
    node = value
    for depth, segment in enumerate(loc):
        if isinstance(node, dict):
            node = node.get(segment)
        elif isinstance(node, list) and isinstance(segment, int) and segment < len(node):
            node = node[segment]
        else:
            return loc[:depth]
    return loc


__all__ = [
    "LOCAL_RECORDS_FILE",
    "RecordEditResult",
    "apply_record_edits",
    "changed_records",
    "check_record_field",
    "write_records",
]
