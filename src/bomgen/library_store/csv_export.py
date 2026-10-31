"""Write a library as CSV tables for Excel (ADR 0018).

One file per table: devices, a child table per nested list of a device, and one table per
commodity catalogue with a row per brand set. Rows are keyed by `part_id` (and `seq`, the
position in the list) or by `catalogue_id`, so the tables hold everything `library.yaml` does
and read back to an equal library.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from bomgen.io.errors import InputError
from bomgen.io.loader import load_library
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.manifest import LIBRARY_SCHEMA_VERSION
from bomgen.library_store.store import LibraryStore
from bomgen.models.library import (
    DEFAULT_BRAND,
    ChildRule,
    DeviceType,
    Housekeeping,
    Library,
    LooseItem,
    McbCatalogue,
    PortGroup,
    TerminalRule,
)

CSV_FORMAT = 1
DEFAULT_DC_ID = "default_dc"  # the mcb.csv row of `catalogues.mcb_dc`; not a valid brand id
ENCODING = "utf-8-sig"  # UTF-8 with a byte-order mark, so Excel does not guess a code page
LINE_END = "\r\n"
LIST_SEPARATOR = "|"
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

Row = dict[str, str]

# DeviceType list field -> its file, and the columns the referenced part is written under.
CHILD_TABLES = {
    "ports": "device_ports.csv",
    "children": "device_children.csv",
    "terminals": "device_terminals.csv",
    "loose_items": "device_loose_items.csv",
}
_CHILD_MODELS: dict[str, type[BaseModel]] = {
    "ports": PortGroup,
    "children": ChildRule,
    "terminals": TerminalRule,
    "loose_items": LooseItem,
}
LOADER_ONLY = ("derived_from", "sfp_choice")  # set on derived parts, never in a library (ADR 0024)
_REFERENCE_COLUMN = {"children": "child_part_id", "loose_items": "item_part_id"}

HOUSEKEEPING_ROLES = tuple(
    role
    for field in Housekeeping.model_fields
    for role in (
        ("change_over_diode_negative", "change_over_diode_positive")
        if field == "change_over_diodes"
        else ("larger_fan",)  # a row per fan
        if field == "larger_fans"
        else (field,)
    )
)


def _child_columns(field: str) -> tuple[str, ...]:
    rename = _REFERENCE_COLUMN.get(field)
    columns = tuple(
        rename if (rename and name == "part_id") else name
        for name in _CHILD_MODELS[field].model_fields
    )
    return ("part_id", "seq", *columns)


TABLES: dict[str, tuple[str, ...]] = {
    "library.csv": ("key", "value"),
    "devices.csv": tuple(
        name for name in DeviceType.model_fields if name not in {*CHILD_TABLES, *LOADER_ONLY}
    ),
    **{file: _child_columns(field) for field, file in CHILD_TABLES.items()},
    "mcb.csv": (
        "catalogue_id",
        "name",
        *(name for name in McbCatalogue.model_fields if name != "codes"),
        "ac_rated",  # brands only (McbBrand); blank on the default row
    ),
    "mcb_codes.csv": ("catalogue_id", "rating_a", "code"),
    "aux_contacts.csv": ("catalogue_id", "name", "make", "model", "ordering_code"),
    "terminal_blocks.csv": ("catalogue_id", "name", "type", "make", "ordering_code"),
    "busbars.csv": ("catalogue_id", "name", "role", "description", "tag"),
    "housekeeping.csv": ("catalogue_id", "name", "role", "part_id", "airflow_m3h", "rating_a"),
}
GROUPS: dict[str, tuple[str, ...]] = {
    "devices": ("devices.csv", *CHILD_TABLES.values()),
    "catalogues": (
        "mcb.csv",
        "mcb_codes.csv",
        "aux_contacts.csv",
        "terminal_blocks.csv",
        "busbars.csv",
        "housekeeping.csv",
    ),
}


def cell(value: object) -> str:
    """How a value is written in a cell: blank for none, `true`/`false`, `|` between list items."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, list):
        return LIST_SEPARATOR.join(cell(item) for item in value)
    return str(value)


def _row(model: BaseModel, columns: Sequence[str], **extra: object) -> Row:
    return {c: cell(extra[c] if c in extra else getattr(model, c, None)) for c in columns}


def library_tables(library: Library, *, name: str = "", based_on: str = "") -> dict[str, list[Row]]:
    """Every table of `library` as rows of cells, by file name."""
    tables: dict[str, list[Row]] = {file: [] for file in TABLES}
    settings: list[tuple[str, object]] = [("csv_format", CSV_FORMAT)]
    if name:
        settings += [
            ("library_name", name),
            ("based_on_version", based_on),
            ("schema_version", LIBRARY_SCHEMA_VERSION),
        ]
    settings.append(("enclosure_u", library.catalogues.enclosure_u))
    tables["library.csv"] = [{"key": key, "value": cell(value)} for key, value in settings]
    _device_rows(library, tables)
    _catalogue_rows(library, tables)
    return tables


def _device_rows(library: Library, tables: dict[str, list[Row]]) -> None:
    for device in library.devices:
        tables["devices.csv"].append(_row(device, TABLES["devices.csv"]))
        for field, file in CHILD_TABLES.items():
            rename = _REFERENCE_COLUMN.get(field)
            for seq, item in enumerate(getattr(device, field), start=1):
                extra: dict[str, object] = {"part_id": device.part_id, "seq": seq}
                if rename:
                    extra[rename] = item.part_id
                tables[file].append(_row(item, TABLES[file], **extra))


def _catalogue_rows(library: Library, tables: dict[str, list[Row]]) -> None:
    default = library.catalogues
    brands = library.catalogue_brands
    sets: dict[str, list[tuple[str, str | None, Any]]] = {
        "mcb": [(DEFAULT_BRAND, None, default.mcb), *((b.id, b.name, b) for b in brands.mcb)],
        "aux_contact": [
            (DEFAULT_BRAND, None, default.aux_contact),
            *((b.id, b.name, b) for b in brands.aux_contact),
        ],
        "terminal_blocks": [
            (DEFAULT_BRAND, None, default.terminal_blocks),
            *((b.id, b.name, b.types) for b in brands.terminal_blocks),
        ],
        "busbars": [
            (DEFAULT_BRAND, None, default.busbars),
            *((b.id, b.name, b.entries) for b in brands.busbars),
        ],
        "housekeeping": [
            (DEFAULT_BRAND, None, default.housekeeping),
            *((b.id, b.name, b) for b in brands.housekeeping),
        ],
    }
    if default.mcb_dc is not None:
        sets["mcb"].insert(1, (DEFAULT_DC_ID, None, default.mcb_dc))
    for brand_id, name, mcb in sets["mcb"]:
        tables["mcb.csv"].append(_row(mcb, TABLES["mcb.csv"], catalogue_id=brand_id, name=name))
        for rating, code in (mcb.codes or {}).items():
            tables["mcb_codes.csv"].append(
                {"catalogue_id": brand_id, "rating_a": cell(rating), "code": code}
            )
    for brand_id, name, contact in sets["aux_contact"]:
        row = _row(contact, TABLES["aux_contacts.csv"], catalogue_id=brand_id, name=name)
        tables["aux_contacts.csv"].append(row)
    for brand_id, name, types in sets["terminal_blocks"]:
        for type_, block in types.items():
            tables["terminal_blocks.csv"].append(
                _row(
                    block,
                    TABLES["terminal_blocks.csv"],
                    catalogue_id=brand_id,
                    name=name,
                    type=type_,
                )
            )
    for brand_id, name, entries in sets["busbars"]:
        for role, busbar in entries.items():
            tables["busbars.csv"].append(
                _row(busbar, TABLES["busbars.csv"], catalogue_id=brand_id, name=name, role=role)
            )
    for brand_id, name, housekeeping in sets["housekeeping"]:
        tables["housekeeping.csv"].extend(_housekeeping_rows(brand_id, name, housekeeping))


def _housekeeping_rows(brand_id: str, name: str | None, housekeeping: Housekeeping) -> list[Row]:
    columns = TABLES["housekeeping.csv"]
    rows: list[Row] = []
    for role in HOUSEKEEPING_ROLES:
        if role == "larger_fan":
            rows += [
                {c: cell(fan.part_id if c == "part_id" else getattr(fan, c, None)) for c in columns}
                | {"catalogue_id": brand_id, "name": cell(name), "role": role}
                for fan in housekeeping.larger_fans
            ]
            continue
        if role.startswith("change_over_diode_"):
            part_id: str | None = getattr(
                housekeeping.change_over_diodes, role.removeprefix("change_over_diode_")
            )
            ref: BaseModel | None = None
        else:
            ref = getattr(housekeeping, role)
            if ref is None:
                continue  # a role left out stays out
            part_id = getattr(ref, "part_id")  # noqa: B009
        extra: dict[str, object] = {
            "catalogue_id": brand_id,
            "name": name,
            "role": role,
            "part_id": part_id,
        }
        rows.append({c: cell(extra[c] if c in extra else getattr(ref, c, None)) for c in columns})
    return rows


def render(columns: Sequence[str], rows: Sequence[Mapping[str, str]]) -> bytes:
    """One table as the bytes of a CSV file: header, CRLF line ends, UTF-8 with a BOM."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(columns), lineterminator=LINE_END)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode(ENCODING)


def export_csv(
    library: Library,
    destination: Path,
    *,
    name: str,
    based_on: str,
    include: Sequence[str] = tuple(GROUPS),
) -> list[str]:
    """Write the tables of `library` to a `.zip` file, or to a folder for any other name.

    `include` picks table groups (`devices`, `catalogues`); `library.csv`, which says what the
    export was made from, is always written. Returns the file names written.
    """
    unknown = [group for group in include if group not in GROUPS]
    if unknown:
        raise ValueError(
            f"unknown table group {', '.join(unknown)} (choose from {', '.join(GROUPS)})"
        )
    tables = library_tables(library, name=name, based_on=based_on)
    wanted = ["library.csv", *(file for group in include for file in GROUPS[group])]
    files = {file: render(TABLES[file], tables[file]) for file in wanted}
    if destination.suffix.lower() == ".zip":
        _write_zip(destination, files)
    else:
        destination.mkdir(parents=True, exist_ok=True)
        for file, data in files.items():
            (destination / file).write_bytes(data)
    return list(files)


def _write_zip(destination: Path, files: Mapping[str, bytes]) -> None:
    partial = destination.with_name(f".{destination.name}.partial")
    try:
        with zipfile.ZipFile(partial, "w") as archive:
            for file, data in files.items():
                info = zipfile.ZipInfo(file, date_time=_ZIP_EPOCH)
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)


def export_installed_csv(
    store: LibraryStore,
    name: str,
    destination: Path,
    *,
    version: str | None = None,
    include: Sequence[str] = tuple(GROUPS),
) -> list[str]:
    """`export_csv` for an installed version (default: the active one)."""
    version = version or store.active_version(name)
    if version is None:
        raise LibraryPackageError(
            f"library {name} has no active version", RefusalKind.NOT_INSTALLED
        )
    try:
        library = load_library(store.library_file(name, version))
    except InputError as exc:
        raise LibraryPackageError(
            f"library {name} {version}: the installed library is damaged", RefusalKind.STORE_DAMAGED
        ) from exc
    return export_csv(library, destination, name=name, based_on=version, include=include)
