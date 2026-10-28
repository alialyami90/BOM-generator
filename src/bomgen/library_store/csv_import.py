"""Read CSV tables back into a library: the dry-run, and the import (ADR 0018).

`preview_csv_import` reads a `.zip` or a folder of the tables `csv_export` writes, builds the
library the rows describe, and reports what it found as checks, row problems and the changes
against the installed version. Nothing is written. `import_csv` saves a clean result as the
next local version.

A table or a column the file lacks is left as the library has it, so a partial export, or one
from an older app, never wipes data. A table the file has replaces the library's rows of that
table: a device with no row is removed.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel, TypeAdapter, ValidationError

from bomgen.bundle.checks import Check, CheckStatus
from bomgen.io.loader import load_library
from bomgen.library_store.csv_export import (
    _CHILD_MODELS,
    _REFERENCE_COLUMN,
    CHILD_TABLES,
    CSV_FORMAT,
    HOUSEKEEPING_ROLES,
    LIST_SEPARATOR,
    TABLES,
    cell,
)
from bomgen.library_store.diff import LibraryDiff
from bomgen.library_store.edit import Insert, Remove, SetValue, apply_edits
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.local import LocalSave, next_local_version, save_local_version
from bomgen.library_store.store import LibraryStore
from bomgen.library_store.versions import Version
from bomgen.models._base import PartId
from bomgen.models.library import (
    DEFAULT_BRAND,
    AuxContact,
    Busbar,
    DeviceType,
    FanRef,
    HousekeepingRef,
    Library,
    McbBrand,
    McbCatalogue,
    SocketRef,
    TerminalBlockType,
)

Edit = SetValue | Insert | Remove
MAX_LISTED = 20
_LABELS = {
    "files": "Files are readable tables",
    "encoding": "Text is UTF-8",
    "columns": "Columns are the expected ones",
    "rows": "Every row reads cleanly",
    "links": "Rows link to each other",
    "cells": "Cells look as written",
    "library": "Library passes the schema",
    "base": "Starts from the installed version",
    "changes": "What changes",
}
_ORDER = tuple(_LABELS)
_EXCEL_DAMAGE = re.compile(
    r"^\d+(\.\d+)?[eE][+-]?\d+$"
    r"|^\d{1,2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$"
    r"|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{1,2}$",
    re.IGNORECASE,
)
_FORMULA_START = ("=", "+", "@")
_DECIMAL_COMMA = re.compile(r"^-?\d+,\d+$")
_WHOLE = re.compile(r"^\d+$")
_PART_ID = TypeAdapter(PartId)


@dataclass(frozen=True)
class RowProblem:
    """A row (or cell) the import cannot use. `row` is the row number Excel shows."""

    table: str
    row: int
    column: str | None
    message: str
    key: str | None = None  # the part_id or catalogue_id of the row


@dataclass(frozen=True)
class Change:
    """One value that differs from the installed version."""

    area: str  # devices | catalogues | catalogue_brands
    key: str
    field: str
    old: str
    new: str


@dataclass(frozen=True)
class CsvPreview:
    """What importing the tables would do. `library` is None when a check failed."""

    checks: list[Check]
    problems: list[RowProblem]
    rows: dict[str, int]
    diff: LibraryDiff | None
    changes: list[Change]
    edits: list[Edit]
    library: Library | None
    base: str | None

    @property
    def can_import(self) -> bool:
        return self.library is not None and all(
            c.status is not CheckStatus.FAILED for c in self.checks
        )


# -- reading the files ---------------------------------------------------------------------


@dataclass
class _Table:
    file: str
    delimiter: str
    columns: list[str]
    records: list[tuple[int, dict[str, str]]]  # (the row number in Excel, known cells)
    unknown: list[str]
    missing: list[str]


def _required(file: str) -> set[str]:
    keyed = {"devices.csv": ("part_id",), "library.csv": ("key", "value")}
    if file in keyed:
        extra = {n for n, i in DeviceType.model_fields.items() if i.is_required()}
        return set(keyed[file]) | (extra if file == "devices.csv" else set())
    for fld, name in CHILD_TABLES.items():
        if name == file:
            rename = _REFERENCE_COLUMN.get(fld, "part_id")
            model = _CHILD_MODELS[fld]
            need = {
                rename if n == "part_id" else n
                for n, i in model.model_fields.items()
                if i.is_required()
            }
            return {"part_id", "seq", rename} | need
    return {
        "mcb.csv": {"catalogue_id"}
        | {n for n, i in McbCatalogue.model_fields.items() if i.is_required()},
        "mcb_codes.csv": {"catalogue_id", "rating_a", "code"},
        "aux_contacts.csv": {"catalogue_id", "make", "model", "ordering_code"},
        "terminal_blocks.csv": {"catalogue_id", "type", "make", "ordering_code"},
        "busbars.csv": {"catalogue_id", "role", "description"},
        "housekeeping.csv": {"catalogue_id", "role", "part_id"},
    }[file]


def _numeric(annotation: Any) -> bool:
    if annotation in (int, float):
        return True
    if get_origin(annotation) is Literal:
        return any(
            isinstance(arg, int) and not isinstance(arg, bool) for arg in get_args(annotation)
        )
    if get_origin(annotation) is not None:
        return any(_numeric(arg) for arg in get_args(annotation))
    return False


def _number(value: str) -> Any:
    """A whole number or decimal in a cell as a number; anything else is left to the model."""
    text = value.strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return value


def _numeric_columns(file: str) -> set[str]:
    models: dict[str, type[BaseModel]] = {"devices.csv": DeviceType, "mcb.csv": McbCatalogue}
    for fld, name in CHILD_TABLES.items():
        models[name] = _CHILD_MODELS[fld]
    columns = (
        {n for n, i in models[file].model_fields.items() if _numeric(i.annotation)}
        if file in models
        else set()
    )
    return columns | {
        "housekeeping.csv": {"airflow_m3h", "rating_a"},
        "mcb_codes.csv": {"rating_a"},
    }.get(file, set())


def _read_source(source: Path) -> dict[str, bytes]:
    """The `.csv` files of a zip or a folder, by base name."""
    if source.is_dir():
        return {p.name: p.read_bytes() for p in sorted(source.iterdir()) if p.suffix == ".csv"}
    if not source.exists():
        raise OSError(f"{source} does not exist")
    with zipfile.ZipFile(source) as archive:
        files: dict[str, bytes] = {}
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if (
                info.is_dir()
                or path.suffix != ".csv"
                or path.name.startswith(".")
                or "__MACOSX" in path.parts
            ):
                continue
            files.setdefault(path.name, archive.read(info))
        return files


def _parse_table(file: str, text: str) -> tuple[_Table | None, str | None]:
    header_line = text.split("\n", 1)[0]
    delimiter = ";" if header_line.count(";") > header_line.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        header = [name.strip() for name in next(reader)]
    except StopIteration:
        return None, f"{file} is empty"
    if len(set(header)) != len(header):
        repeated = sorted({name for name in header if header.count(name) > 1})
        return None, f"{file} repeats the column {', '.join(repeated)}"
    known = list(TABLES[file])
    numeric = _numeric_columns(file)
    records: list[tuple[int, dict[str, str]]] = []
    for number, record in enumerate(reader, start=2):
        if not any(value.strip() for value in record):
            continue
        cells: dict[str, str] = {}
        for name, value in zip(header, record, strict=False):
            if name not in known:
                continue
            if delimiter == ";" and name in numeric and _DECIMAL_COMMA.match(value.strip()):
                value = value.strip().replace(",", ".")
            cells[name] = value
        records.append((number, cells))
    table = _Table(
        file,
        delimiter,
        header,
        records,
        unknown=[name for name in header if name and name not in known],
        missing=[name for name in known if name not in header],
    )
    return table, None


# -- assembling the library from the rows --------------------------------------------------

_CATALOGUE_FILES = {
    "mcb": "mcb.csv",
    "aux_contact": "aux_contacts.csv",
    "terminal_blocks": "terminal_blocks.csv",
    "busbars": "busbars.csv",
    "housekeeping": "housekeeping.csv",
}


@dataclass
class _Assembly:
    problems: list[RowProblem] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    device_rows: dict[str, int] = field(default_factory=dict)
    devices: list[dict[str, Any]] | None = None
    defaults: dict[str, Any] = field(default_factory=dict)
    brands: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    enclosure_u: int | None = None
    settings: dict[str, str] = field(default_factory=dict)

    def problem(
        self, table: str, row: int, column: str | None, message: str, key: str | None
    ) -> None:
        found = RowProblem(table, row, column, message, key)
        if found not in self.problems:
            self.problems.append(found)

    def model_problems(
        self, table: str, row: int, key: str | None, error: ValidationError, columns: Iterable[str]
    ) -> None:
        for item in error.errors():
            column = str(item["loc"][0]) if item["loc"] else None
            if column is not None and column not in columns:
                column = None
            message = "is required" if item["type"] == "missing" else str(item["msg"])
            self.problem(table, row, column, message.removeprefix("Value error, "), key)


def _text(value: object) -> str:
    return json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else cell(value)


def _row_dict(
    table: _Table, cells: Mapping[str, str], columns: Iterable[str], start: Mapping[str, Any] | None
) -> dict[str, Any]:
    """The cells of a row as a model's fields: blank cells are left out, columns the file does
    not have keep the value of `start` (the installed entry), if there is one."""
    data: dict[str, Any] = {}
    numeric = _numeric_columns(table.file)
    for name in columns:
        if name in table.columns:
            value = cells.get(name, "")
            if value != "":
                data[name] = _number(value) if name in numeric else value
        elif start is not None and name in start and start[name] is not None:
            data[name] = start[name]
    return data


def _keyed(table: _Table, column: str, asm: _Assembly) -> Iterable[tuple[int, str, dict[str, str]]]:
    """Rows with a non-blank key; a blank key is a problem."""
    for row, cells in table.records:
        key = cells.get(column, "").strip()
        if not key:
            asm.problem(table.file, row, column, "is required", None)
            continue
        yield row, key, cells


def _scan_cells(table: _Table, asm: _Assembly) -> None:
    numeric = _numeric_columns(table.file)
    for row, cells in table.records:
        for name, value in cells.items():
            if name in numeric or not value:
                continue
            if _EXCEL_DAMAGE.match(value) or value.startswith(_FORMULA_START):
                asm.warnings.append(f"{table.file} row {row}, {name}: {value!r}")


def _assemble(
    tables: Mapping[str, _Table], base: Mapping[str, Any], skip_invalid: bool
) -> _Assembly:
    asm = _Assembly()
    for table in tables.values():
        _scan_cells(table, asm)
    if "library.csv" in tables:
        asm.settings = {
            cells.get("key", "").strip(): cells.get("value", "").strip()
            for _row, cells in tables["library.csv"].records
        }
        if "enclosure_u" in asm.settings:
            try:
                asm.enclosure_u = TypeAdapter(int).validate_python(asm.settings["enclosure_u"])
            except ValidationError:
                asm.problem(
                    "library.csv", 0, "value", "enclosure_u must be a whole number", "enclosure_u"
                )
    if "devices.csv" in tables:
        _devices(tables, base, skip_invalid, asm)
    _mcb(tables, base, skip_invalid, asm)
    _aux(tables, base, skip_invalid, asm)
    _typed_rows(
        tables,
        base,
        skip_invalid,
        asm,
        "terminal_blocks",
        "type",
        ("make", "ordering_code"),
        TerminalBlockType,
        "types",
    )
    _typed_rows(
        tables,
        base,
        skip_invalid,
        asm,
        "busbars",
        "role",
        ("description", "tag"),
        Busbar,
        "entries",
    )
    _housekeeping(tables, base, skip_invalid, asm)
    return asm


def _devices(
    tables: Mapping[str, _Table], base: Mapping[str, Any], skip: bool, asm: _Assembly
) -> None:
    table = tables["devices.csv"]
    base_by_id = {d["part_id"]: d for d in base["devices"]}
    children: dict[str, dict[str, list[tuple[int, int, dict[str, Any]]]]] = {
        f: defaultdict(list) for f in CHILD_TABLES
    }
    ids: dict[str, int] = {}
    for row, pid, _cells in _keyed(table, "part_id", asm):
        if pid in ids:
            asm.links.append(
                f"duplicate part_id {pid!r} in devices.csv (rows {ids[pid]} and {row})"
            )
        else:
            ids[pid] = row
    asm.device_rows = ids
    for fld, file in CHILD_TABLES.items():
        child = tables.get(file)
        if child is None:
            continue
        reference = _REFERENCE_COLUMN.get(fld, "part_id")
        seen: set[tuple[str, int]] = set()
        for row, pid, cells in _keyed(child, "part_id", asm):
            if pid not in ids:
                asm.links.append(f"{file} row {row}: part_id {pid!r} has no row in devices.csv")
                continue
            seq_text = cells.get("seq", "").strip()
            if not _WHOLE.match(seq_text) or int(seq_text) < 1:
                asm.links.append(
                    f"{file} row {row}: seq {seq_text!r} is not a position (1, 2, 3 ...)"
                )
                continue
            if (pid, int(seq_text)) in seen:
                asm.links.append(f"{file} row {row}: {pid!r} has position {seq_text} twice")
                continue
            seen.add((pid, int(seq_text)))
            item = _row_dict(child, cells, _CHILD_MODELS[fld].model_fields, None)
            if reference != "part_id":
                value = cells.get(reference, "")
                item.pop("part_id", None)
                if value != "":
                    item["part_id"] = value
            children[fld][pid].append((int(seq_text), row, item))
    candidates: list[dict[str, Any]] = []
    for row, cells in table.records:
        pid = cells.get("part_id", "").strip()
        if not pid or ids.get(pid) != row:
            continue
        old = base_by_id.get(pid)
        data = _row_dict(table, cells, TABLES["devices.csv"], old)
        data["part_id"] = pid
        rows_of: dict[str, list[int]] = {}
        for fld, file in CHILD_TABLES.items():
            if file in tables:
                ordered = sorted(children[fld].get(pid, []), key=lambda t: t[0])
                data[fld] = [item for _seq, _row, item in ordered]
                rows_of[fld] = [r for _seq, r, _item in ordered]
            elif old is not None:
                data[fld] = old.get(fld, [])
        try:
            device = DeviceType.model_validate(data).model_dump(mode="json")
        except ValidationError as exc:
            _device_problems(exc, pid, row, rows_of, asm)
            if skip and old is not None:
                candidates.append(old)
            continue
        candidates.append(device)
    asm.devices = candidates


def _device_problems(
    error: ValidationError, pid: str, row: int, rows_of: Mapping[str, list[int]], asm: _Assembly
) -> None:
    for item in error.errors():
        loc = item["loc"]
        message = ("is required" if item["type"] == "missing" else str(item["msg"])).removeprefix(
            "Value error, "
        )
        if loc and loc[0] in CHILD_TABLES and len(loc) > 1 and isinstance(loc[1], int):
            fld = str(loc[0])
            rows = rows_of.get(fld, [])
            child_row = rows[loc[1]] if loc[1] < len(rows) else 0
            column = str(loc[2]) if len(loc) > 2 else None
            if column == "part_id":
                column = _REFERENCE_COLUMN.get(fld, "part_id")
            asm.problem(CHILD_TABLES[fld], child_row, column, message, pid)
        else:
            column = str(loc[0]) if loc else None
            asm.problem("devices.csv", row, column, message, pid)


def _base_entry(base: Mapping[str, Any], kind: str, cid: str) -> dict[str, Any] | None:
    if cid == DEFAULT_BRAND:
        value = base["catalogues"].get(kind)
        return value if isinstance(value, dict) else None
    return next((b for b in base["catalogue_brands"].get(kind, []) if b.get("id") == cid), None)


def _unique(
    table: _Table, columns: Sequence[str], asm: _Assembly
) -> Iterable[tuple[int, dict[str, str]]]:
    seen: dict[tuple[str, ...], int] = {}
    for row, cells in table.records:
        key = tuple(cells.get(c, "").strip() for c in columns)
        if not all(key):
            asm.problem(
                table.file,
                row,
                next(c for c, k in zip(columns, key, strict=True) if not k),
                "is required",
                key[0] or None,
            )
            continue
        if key in seen:
            asm.links.append(
                f"{table.file} row {row}: {' / '.join(key)} is also on row {seen[key]}"
            )
            continue
        seen[key] = row
        yield row, cells


def _names(table: _Table, asm: _Assembly) -> dict[str, str]:
    """The name of each brand set in a table; a set whose rows disagree is a link problem."""
    names: dict[str, str] = {}
    for row, cells in table.records:
        cid, name = cells.get("catalogue_id", "").strip(), cells.get("name", "").strip()
        if cid and name and names.setdefault(cid, name) != name:
            first = names[cid]
            asm.links.append(f"{table.file} row {row}: {cid!r} is {name!r} here, {first!r} above")
    return names


def _file_brand(
    kind: str, cid: str, name: str | None, entry: Mapping[str, Any], asm: _Assembly
) -> None:
    if cid == DEFAULT_BRAND:
        asm.defaults[kind] = dict(entry)
    else:
        brand = {"id": cid, **({"name": name} if name else {}), **entry}
        asm.brands.setdefault(kind, []).append(brand)


def _mcb(tables: Mapping[str, _Table], base: Mapping[str, Any], skip: bool, asm: _Assembly) -> None:
    table = tables.get("mcb.csv")
    if table is None:
        return
    names = _names(table, asm)
    codes: dict[str, dict[str, str]] = defaultdict(dict)
    if "mcb_codes.csv" in tables:
        for _row, cells in _unique(tables["mcb_codes.csv"], ("catalogue_id", "rating_a"), asm):
            codes[cells["catalogue_id"].strip()][cells["rating_a"].strip()] = cells.get("code", "")
    asm.brands.setdefault("mcb", [])
    for row, cells in _unique(table, ("catalogue_id",), asm):
        cid = cells["catalogue_id"].strip()
        old = _base_entry(base, "mcb", cid)
        data = _row_dict(table, cells, (n for n in McbCatalogue.model_fields if n != "codes"), old)
        if isinstance(data.get("ratings_a"), str):
            data["ratings_a"] = [
                p.strip() for p in data["ratings_a"].split(LIST_SEPARATOR) if p.strip()
            ]
        if "mcb_codes.csv" in tables:
            if cid in codes:
                data["codes"] = dict(codes[cid])
        elif old is not None and old.get("codes") is not None:
            data["codes"] = old["codes"]
        model = McbCatalogue if cid == DEFAULT_BRAND else McbBrand
        extra = (
            {}
            if cid == DEFAULT_BRAND
            else {"id": cid, **({"name": names[cid]} if cid in names else {})}
        )
        try:
            entry = model.model_validate({**data, **extra}).model_dump(
                mode="json", exclude_none=True
            )
        except ValidationError as exc:
            asm.model_problems("mcb.csv", row, cid, exc, TABLES["mcb.csv"])
            if skip and old is not None:
                entry = old
            else:
                continue
        entry = {k: v for k, v in entry.items() if k not in ("id", "name")}
        _file_brand("mcb", cid, names.get(cid), entry, asm)


def _aux(tables: Mapping[str, _Table], base: Mapping[str, Any], skip: bool, asm: _Assembly) -> None:
    table = tables.get("aux_contacts.csv")
    if table is None:
        return
    names = _names(table, asm)
    asm.brands.setdefault("aux_contact", [])
    for row, cells in _unique(table, ("catalogue_id",), asm):
        cid = cells["catalogue_id"].strip()
        old = _base_entry(base, "aux_contact", cid)
        data = _row_dict(table, cells, AuxContact.model_fields, old)
        try:
            entry = AuxContact.model_validate(data).model_dump(mode="json")
        except ValidationError as exc:
            asm.model_problems("aux_contacts.csv", row, cid, exc, TABLES["aux_contacts.csv"])
            if skip and old is not None:
                entry = {k: v for k, v in old.items() if k not in ("id", "name")}
            else:
                continue
        _file_brand("aux_contact", cid, names.get(cid), entry, asm)


def _typed_rows(
    tables: Mapping[str, _Table],
    base: Mapping[str, Any],
    skip: bool,
    asm: _Assembly,
    kind: str,
    key_column: str,
    value_columns: tuple[str, ...],
    model: type[BaseModel],
    brand_field: str,
) -> None:
    file = _CATALOGUE_FILES[kind]
    table = tables.get(file)
    if table is None:
        return
    names = _names(table, asm)
    sets: dict[str, dict[str, Any]] = {}
    for row, cells in _unique(table, ("catalogue_id", key_column), asm):
        cid, key = cells["catalogue_id"].strip(), cells[key_column].strip()
        old_set = (
            _base_entry(base, kind, cid) if cid != DEFAULT_BRAND else base["catalogues"].get(kind)
        )
        old_rows = (old_set if cid == DEFAULT_BRAND else (old_set or {}).get(brand_field)) or {}
        old = old_rows.get(key) if isinstance(old_rows, dict) else None
        data = _row_dict(table, cells, value_columns, old)
        try:
            value = model.model_validate(data).model_dump(mode="json")
        except ValidationError as exc:
            asm.model_problems(file, row, f"{cid}/{key}", exc, TABLES[file])
            if skip and old is not None:
                value = old
            else:
                continue
        sets.setdefault(cid, {})[key] = value
    for cid, rows in sets.items():
        if cid == DEFAULT_BRAND:
            asm.defaults[kind] = rows
        else:
            asm.brands.setdefault(kind, []).append(
                {"id": cid, **({"name": names[cid]} if cid in names else {}), brand_field: rows}
            )
    asm.brands.setdefault(kind, [])


def _housekeeping(
    tables: Mapping[str, _Table], base: Mapping[str, Any], skip: bool, asm: _Assembly
) -> None:
    table = tables.get("housekeeping.csv")
    if table is None:
        return
    names = _names(table, asm)
    sets: dict[str, dict[str, Any]] = {}
    for row, cells in _unique(table, ("catalogue_id", "role"), asm):
        cid, role = cells["catalogue_id"].strip(), cells["role"].strip()
        if role not in HOUSEKEEPING_ROLES:
            asm.problem(
                "housekeeping.csv",
                row,
                "role",
                f"{role!r} is not a housekeeping role ({', '.join(HOUSEKEEPING_ROLES)})",
                cid,
            )
            continue
        part_id = cells.get("part_id", "").strip()
        data: dict[str, Any] = {"part_id": part_id}
        model: type[BaseModel]
        if role == "fan":
            model, extra = FanRef, "airflow_m3h"
        elif role == "socket":
            model, extra = SocketRef, "rating_a"
        else:
            model, extra = HousekeepingRef, ""
        if extra and cells.get(extra, "") != "":
            data[extra] = cells[extra]
        try:
            value = model.model_validate(data).model_dump(mode="json")
        except ValidationError as exc:
            asm.model_problems("housekeeping.csv", row, cid, exc, TABLES["housekeeping.csv"])
            continue
        target = sets.setdefault(cid, {})
        if role.startswith("change_over_diode_"):
            target.setdefault("change_over_diodes", {})[role.removeprefix("change_over_diode_")] = (
                value["part_id"]
            )
        else:
            target[role] = value
    for cid, roles in sets.items():
        if cid == DEFAULT_BRAND:
            asm.defaults["housekeeping"] = roles
        else:
            asm.brands.setdefault("housekeeping", []).append(
                {"id": cid, **({"name": names[cid]} if cid in names else {}), **roles}
            )
    asm.brands.setdefault("housekeeping", [])


# -- the dry-run -----------------------------------------------------------------------------


def _listed(lines: Sequence[str]) -> str:
    shown = "; ".join(lines[:MAX_LISTED])
    return shown + (f"; and {len(lines) - MAX_LISTED} more" if len(lines) > MAX_LISTED else "")


def _line(problem: RowProblem) -> str:
    where = f"{problem.table} row {problem.row}" if problem.row else problem.table
    column = f", {problem.column}" if problem.column else ""
    return f"{where}{column}: {problem.message}"


def preview_csv_import(
    source: Path,
    store: LibraryStore,
    name: str,
    *,
    base: str | None = None,
    skip_invalid: bool = False,
) -> CsvPreview:
    """Read the tables in `source` (a `.zip` or a folder) against the installed `name`.

    `base` is the version the rows are compared with (default: the active one). With
    `skip_invalid`, rows with a problem are left out and reported instead of failing the import.
    """
    base = base or store.active_version(name)
    if base is None:
        raise LibraryPackageError(f"library {name} is not installed", RefusalKind.NOT_INSTALLED)
    base_library = load_library(store.library_file(name, base))
    base_dict = base_library.model_dump(mode="json")
    checks: list[Check] = []

    def add(check_id: str, status: CheckStatus, detail: str = "") -> None:
        kind = RefusalKind.VALIDATION_FAILED if status is CheckStatus.FAILED else None
        checks.append(Check(check_id, _LABELS[check_id], status, detail, kind))

    def stop(problems: list[RowProblem], rows: dict[str, int]) -> CsvPreview:
        for check_id in _ORDER[len(checks) :]:
            add(check_id, CheckStatus.SKIPPED)
        return CsvPreview(checks, problems, rows, None, [], [], None, base)

    # files
    try:
        files = _read_source(source)
    except (OSError, zipfile.BadZipFile) as exc:
        add("files", CheckStatus.FAILED, f"cannot read {source}: {exc}")
        return stop([], {})
    known = {file: data for file, data in files.items() if file in TABLES}
    problem = _file_problem(known)
    if problem:
        add("files", CheckStatus.FAILED, problem)
        return stop([], {})
    ignored = sorted(set(files) - set(known))
    add(
        "files",
        CheckStatus.OK,
        f"{len(known)} tables: {', '.join(sorted(known))}"
        + (f"; ignored: {', '.join(ignored)}" if ignored else ""),
    )

    # encoding
    texts: dict[str, str] = {}
    bad: list[str] = []
    for file, data in known.items():
        try:
            texts[file] = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            bad.append(file)
    if bad:
        add(
            "encoding",
            CheckStatus.FAILED,
            f"{', '.join(sorted(bad))} is not UTF-8 text. In Excel, use Save As and choose "
            "CSV UTF-8 (Comma delimited).",
        )
        return stop([], {})
    add("encoding", CheckStatus.OK)

    # columns
    tables: dict[str, _Table] = {}
    errors: list[str] = []
    notes: list[str] = []
    for file, text in texts.items():
        table, error = _parse_table(file, text)
        if table is None:
            errors.append(error or file)
            continue
        tables[file] = table
        lacking = sorted(_required(file) - set(table.columns))
        if lacking:
            errors.append(f"{file} has no column {', '.join(lacking)}")
        optional = [c for c in table.missing if c not in _required(file)]
        if optional:
            notes.append(f"{file} has no column {', '.join(optional)}; the library's values stay")
        if table.unknown:
            notes.append(f"{file}: ignored column {', '.join(table.unknown)}")
    if errors:
        add("columns", CheckStatus.FAILED, "; ".join(errors))
        return stop([], {})
    add("columns", CheckStatus.WARNING if notes else CheckStatus.OK, "; ".join(notes))

    # rows
    rows = {file: len(table.records) for file, table in tables.items()}
    asm = _assemble(tables, base_dict, skip_invalid)
    if asm.problems:
        status = CheckStatus.WARNING if skip_invalid else CheckStatus.FAILED
        detail = _listed([_line(p) for p in asm.problems])
        if skip_invalid:
            detail = f"{len(asm.problems)} problems; the rows are left out. {detail}"
        add("rows", status, detail)
        if not skip_invalid:
            return stop(asm.problems, rows)
    else:
        add("rows", CheckStatus.OK)

    # links
    if asm.links:
        add("links", CheckStatus.FAILED, _listed(asm.links))
        return stop(asm.problems, rows)
    add("links", CheckStatus.OK)

    # cells
    add(
        "cells",
        CheckStatus.WARNING if asm.warnings else CheckStatus.OK,
        f"These look changed by Excel or like formulas: {_listed(asm.warnings)}"
        if asm.warnings
        else "",
    )

    # library
    edits: list[Edit] = []
    if asm.devices is not None:
        edits.append(SetValue(path=["devices"], value=asm.devices))
    for kind, value in asm.defaults.items():
        edits.append(SetValue(path=["catalogues", kind], value=value))
    if asm.enclosure_u is not None:
        edits.append(SetValue(path=["catalogues", "enclosure_u"], value=asm.enclosure_u))
    for kind, brands in asm.brands.items():
        edits.append(SetValue(path=["catalogue_brands", kind], value=brands))
    result = apply_edits(base_library, edits)
    if result.library is None:
        mapped = [_where(p.location, p.message, asm) for p in result.problems]
        add(
            "library",
            CheckStatus.FAILED,
            _listed([f"{p.location}: {p.message}" for p in result.problems]),
        )
        return stop([*asm.problems, *mapped], rows)
    library = result.library
    add("library", CheckStatus.OK)

    # base
    mismatch = _base_mismatch(asm.settings, name, base)
    add("base", CheckStatus.WARNING if mismatch else CheckStatus.OK, mismatch)

    # changes
    new_dict = library.model_dump(mode="json")
    diff, changes, derived = _compare(base_dict, new_dict)
    if diff.is_empty:
        add(
            "changes",
            CheckStatus.WARNING,
            "Nothing differs from the installed version, so nothing would be saved.",
        )
    else:
        version = next_local_version(store, name, Version.parse(base))
        add(
            "changes",
            CheckStatus.OK,
            f"Would be saved as {version}. " + " ".join(diff.summary_lines()),
        )
    return CsvPreview(checks, asm.problems, rows, diff, changes, derived, library, base)


def _file_problem(known: Mapping[str, bytes]) -> str | None:
    if not known:
        return "no library tables found (expected files such as devices.csv and mcb.csv)"
    if any(name in known for name in CHILD_TABLES.values()) and "devices.csv" not in known:
        return "the device tables need devices.csv in the same import"
    if "mcb_codes.csv" in known and "mcb.csv" not in known:
        return "mcb_codes.csv needs mcb.csv in the same import"
    if "library.csv" in known:
        try:
            settings = {
                row[0].strip(): row[1].strip()
                for row in csv.reader(
                    io.StringIO(known["library.csv"].decode("utf-8-sig"), newline=""), delimiter=","
                )
                if len(row) > 1
            }
        except UnicodeDecodeError:
            return None
        format_text = settings.get("csv_format", "")
        if format_text.isdigit() and int(format_text) > CSV_FORMAT:
            return (
                f"these tables use CSV format {format_text}; this bomgen reads format {CSV_FORMAT}"
            )
    return None


def _base_mismatch(settings: Mapping[str, str], name: str, base: str) -> str:
    notes: list[str] = []
    other = settings.get("library_name", "")
    if other and other != name:
        notes.append(f"the tables were exported from library {other}, not {name}")
    started = settings.get("based_on_version", "")
    if started and started != base:
        notes.append(
            f"the tables were exported from {started} but {base} is the version they are compared "
            "with; changes made since will be replaced"
        )
    return "; ".join(notes)


def _where(location: str, message: str, asm: _Assembly) -> RowProblem:
    device = re.match(r"devices\[([^\]]+)\](?:\.(\w+))?", location)
    if device:
        pid, fld = device.group(1), device.group(2)
        if fld in CHILD_TABLES:
            return RowProblem(CHILD_TABLES[fld], 0, None, message, pid)
        return RowProblem("devices.csv", asm.device_rows.get(pid, 0), fld, message, pid)
    for kind, file in _CATALOGUE_FILES.items():
        if f"catalogues.{kind}" in location or f"catalogue_brands.{kind}" in location:
            return RowProblem(file, 0, None, f"{location}: {message}", None)
    return RowProblem("library.csv", 0, None, f"{location}: {message}", None)


def _field_changes(area: str, key: str, old: object, new: object, prefix: str = "") -> list[Change]:
    if isinstance(old, dict) and isinstance(new, dict):
        found: list[Change] = []
        for name in sorted(old.keys() | new.keys()):
            found += _field_changes(
                area, key, old.get(name), new.get(name), f"{prefix}.{name}" if prefix else name
            )
        return found
    return [] if old == new else [Change(area, key, prefix, _text(old), _text(new))]


def _top_keys(old: Mapping[str, Any], new: Mapping[str, Any]) -> list[str]:
    return sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))


def _compare(
    old: Mapping[str, Any], new: Mapping[str, Any]
) -> tuple[LibraryDiff, list[Change], list[Edit]]:
    changes: list[Change] = []
    edits: list[Edit] = []
    removals: list[Edit] = []
    old_devices = {d["part_id"]: d for d in old["devices"]}
    new_devices = {d["part_id"]: d for d in new["devices"]}
    added = [pid for pid in new_devices if pid not in old_devices]
    removed = [pid for pid in old_devices if pid not in new_devices]
    changed: dict[str, list[str]] = {}
    for pid, device in new_devices.items():
        if pid in added:
            edits.append(Insert(path=["devices"], value=device))
        elif device != old_devices[pid]:
            changed[pid] = _top_keys(old_devices[pid], device)
            changes += _field_changes("devices", pid, old_devices[pid], device)
            edits.append(SetValue(path=["devices", pid], value=device))
    removals += [Remove(path=["devices", pid]) for pid in removed]
    catalogues: list[str] = []
    for kind in (*_CATALOGUE_FILES, "enclosure_u"):
        before, after = old["catalogues"].get(kind), new["catalogues"].get(kind)
        if before != after:
            catalogues.append(kind)
            changes += _field_changes("catalogues", kind, before, after)
            edits.append(SetValue(path=["catalogues", kind], value=after))
    for kind in _CATALOGUE_FILES:
        before_set = {b["id"]: b for b in old["catalogue_brands"].get(kind, [])}
        after_set = {b["id"]: b for b in new["catalogue_brands"].get(kind, [])}
        for brand_id, brand in after_set.items():
            key = f"{kind}:{brand_id}"
            if brand_id not in before_set:
                catalogues.append(key)
                edits.append(Insert(path=["catalogue_brands", kind], value=brand))
            elif brand != before_set[brand_id]:
                catalogues.append(key)
                changes += _field_changes("catalogue_brands", key, before_set[brand_id], brand)
                edits.append(SetValue(path=["catalogue_brands", kind, brand_id], value=brand))
        for brand_id in before_set:
            if brand_id not in after_set:
                catalogues.append(f"{kind}:{brand_id}")
                removals.append(Remove(path=["catalogue_brands", kind, brand_id]))
    diff = LibraryDiff(added=added, removed=removed, changed=changed, catalogues_changed=catalogues)
    return diff, changes, [*edits, *removals]


# -- the import ------------------------------------------------------------------------------


def import_csv(
    source: Path,
    store: LibraryStore,
    name: str,
    *,
    base: str | None = None,
    skip_invalid: bool = False,
    note: str = "",
) -> LocalSave:
    """Save the rows in `source` as the next local version of `name` and make it active.

    Raises `LibraryPackageError` listing what failed (`VALIDATION_FAILED`) or, when nothing
    differs, `NO_CHANGES`. The store is untouched on any refusal.
    """
    preview = preview_csv_import(source, store, name, base=base, skip_invalid=skip_invalid)
    if preview.library is None or not preview.can_import:
        failed = [
            f"{c.label}: {c.detail}" for c in preview.checks if c.status is CheckStatus.FAILED
        ]
        raise LibraryPackageError("\n".join(failed), RefusalKind.VALIDATION_FAILED)
    return save_local_version(store, name, preview.library, base=preview.base, note=note)
