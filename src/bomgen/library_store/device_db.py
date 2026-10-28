"""Device-database records shipped inside a `.bomlib` (ADR 0008 amendment).

The records are reference data: datasheet facts and two alternative brands per
part, researched in `data/device-db/` (its README is the format). The generator
never builds from them; the UI reads them next to the library's parts. A package
carries them in a `device-db/` folder of YAML files, which import extracts into
the version folder like any other member.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    StrictBool,
    StrictFloat,
    StrictInt,
    ValidationError,
    model_validator,
)

from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.models.library import PortKind, PortSpeed, PortUse

if TYPE_CHECKING:
    from bomgen.library_store.store import LibraryStore

DEVICE_DB_DIR = "device-db"
DEVICE_DB_SCHEMA_VERSION = 1

# Figures are numbers (a bool is not one); anything uncertain goes in `notes`.
Number = StrictInt | StrictFloat
WholeNumber = Annotated[int, Field(strict=True, ge=0)]
MountingKind = Literal["rack", "din_rail", "plug_in", "enclosure", "external"]


def _height_belongs_to_rack_parts(height_u: int | None, mounting_kind: str | None) -> None:
    if (
        height_u is not None
        and mounting_kind is not None
        and (height_u > 0) != (mounting_kind == "rack")
    ):
        raise ValueError("height_u is above 0 exactly when mounting_kind is rack")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, coerce_numbers_to_str=True)


class Power(_Model):
    input: str | None = None
    redundant_psu: bool | None = None
    typical_w: Number | None = None
    max_w: Number | None = None


class Dimensions(_Model):
    h: Number | None = None
    w: Number | None = None
    d: Number | None = None


class TemperatureRange(_Model):
    min: Number | None = None
    max: Number | None = None


class PortGroup(_Model):
    ports: str
    count: PositiveInt
    speed: PortSpeed
    media: str  # the library's Media lacks the SFP and SFP+ the database writes on slots
    kind: PortKind
    usable_for: PortUse
    note: str | None = None


class _Inrush(_Model):
    """Switch-on current of a part, with where the figure comes from."""

    inrush_a: Number | None = None
    inrush_ms: Number | None = None
    inrush_basis: Literal["datasheet", "not_given", "assumed"] | None = None
    inrush_note: str | None = None


class Datasheet(_Inrush):
    """Whatever could be confirmed; keys are left out when unknown."""

    full_name: str | None = None
    manufacturer: str | None = None
    summary: str
    notes: str | None = None
    power: Power | None = None
    ratings: dict[str, Any] | None = None
    ports: list[Any] | None = None
    dimensions_mm: Dimensions | None = None
    rack_units: Number | None = None
    weight_kg: Number | None = None
    mounting: str | None = None
    operating_temp_c: TemperatureRange | None = None
    certifications: list[str] | None = None
    ordering_code_decoded: dict[Any, Any] | None = None
    datasheet_url: str | None = None
    product_url: str | None = None
    mounting_kind: MountingKind
    height_u: WholeNumber
    height_note: str | None = None
    port_groups: list[PortGroup] | None = None

    @model_validator(mode="after")
    def _height_belongs_to_rack_parts(self) -> Self:
        _height_belongs_to_rack_parts(self.height_u, self.mounting_kind)
        return self


class Tier(_Inrush):
    """One part of an alternative; the keys after `same_as` are optional research findings."""

    model: str
    description: str
    ordering_code: str | None = None
    unit_power_w: Number | None = None
    url: str | None = None
    notes: str | None = None
    verified: bool
    same_as: Literal["low", "mid"] | None = None
    height_u: WholeNumber | None = None
    mounting_kind: MountingKind | None = None
    supply_type: Literal["VDC", "VAC", "none"] | None = None
    voltage_v: Number | None = None
    supply_option: str | None = None  # the PSU option that covers the supply
    supply_ok: StrictBool | None = None  # false: no variant takes 125 VDC / 230 VAC
    power_supplies: Annotated[int, Field(strict=True, ge=1, le=2)] | None = None
    power_basis: Literal["datasheet_max", "datasheet_typical", "computed", "assumed"] | None = None
    power_note: str | None = None
    port_groups: list[PortGroup] | None = None
    airflow_m3h: Number | None = None  # fans
    ratings: dict[str, Any] | None = None  # free-form, like `datasheet.ratings`
    sources: list[str] | None = None

    @model_validator(mode="after")
    def _height_belongs_to_rack_parts(self) -> Self:
        _height_belongs_to_rack_parts(self.height_u, self.mounting_kind)
        return self


class Tiers(_Model):
    low: Tier
    mid: Tier
    high: Tier


class Alternative(_Model):
    make: str
    manufacturer: str | None = None
    tiers: Tiers


class DeviceRecord(_Model):
    """One part, or one catalogue entry (`kind: catalogue`) with a database-local id."""

    part_id: str
    kind: Literal["device", "catalogue"]
    library_refs: list[str] | None = None
    description: str
    make: str | None = None
    verified: Literal["confirmed", "partial", "unverified"]
    datasheet: Datasheet
    alternatives: list[Alternative]
    sources: list[str]


class DeviceFile(_Model):
    schema_version: Literal[1]
    area: str
    title: str
    records: list[DeviceRecord]


def _location(loc: tuple[int | str, ...]) -> str:
    text = ""
    for part in loc:
        text += f"[{part}]" if isinstance(part, int) else f".{part}" if text else str(part)
    return text


def _describe(error: Any) -> str:
    where = _location(tuple(error["loc"]))
    message = "unknown key" if error["type"] == "extra_forbidden" else error["msg"]
    return f"{where}: {message}"


def parse_device_records(
    files: Mapping[str, bytes], *, kind: RefusalKind = RefusalKind.VALIDATION_FAILED
) -> dict[str, DeviceRecord]:
    """Parse the YAML files under `device-db/` and key the records by `part_id`.

    `files` maps a path to its bytes; only `device-db/*.yaml` and `*.yml` are read.
    Raises `LibraryPackageError` naming the file and the field of the first bad file.
    """
    records: dict[str, DeviceRecord] = {}
    origin: dict[str, str] = {}
    for name in sorted(files):
        path = PurePosixPath(name)
        if path.parts[:1] != (DEVICE_DB_DIR,) or path.suffix not in (".yaml", ".yml"):
            continue
        try:
            document = yaml.safe_load(files[name].decode("utf-8"))
            parsed = DeviceFile.model_validate(document)
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise LibraryPackageError(f"{name} is not valid YAML: {exc}", kind) from exc
        except ValidationError as exc:
            problems = "\n".join(f"  {_describe(error)}" for error in exc.errors())
            raise LibraryPackageError(f"{name} fails validation:\n{problems}", kind) from exc
        for record in parsed.records:
            if record.part_id in records:
                raise LibraryPackageError(
                    f"part_id {record.part_id!r} is in both {origin[record.part_id]} and {name}",
                    kind,
                )
            records[record.part_id] = record
            origin[record.part_id] = name
    return records


def load_device_records(store: LibraryStore, name: str, version: str) -> dict[str, DeviceRecord]:
    """The installed version's device-database records; `{}` when it ships none."""
    library_dir = store.library_file(name, version).parent
    folder = library_dir / DEVICE_DB_DIR
    if not folder.is_dir():
        return {}
    files: dict[str, bytes] = {}
    try:
        for path in sorted(folder.iterdir()):
            if path.is_file():
                files[f"{DEVICE_DB_DIR}/{path.name}"] = path.read_bytes()
    except OSError as exc:
        raise LibraryPackageError(
            f"library {name} {version}: cannot read {DEVICE_DB_DIR}: {exc}",
            RefusalKind.STORE_DAMAGED,
        ) from exc
    try:
        return parse_device_records(files, kind=RefusalKind.STORE_DAMAGED)
    except LibraryPackageError as exc:
        raise LibraryPackageError(
            f"library {name} {version}: installed device database is damaged: {exc}", exc.kind
        ) from exc


__all__ = [
    "DEVICE_DB_DIR",
    "DeviceRecord",
    "load_device_records",
    "parse_device_records",
]
