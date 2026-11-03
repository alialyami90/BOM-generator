"""The Parts page of one substation (plan M23; ``docs/ui/screens.md``, Parts).

One row per equipment entry, with the *base* library part's values next to the entry's
overrides (ADR 0024), the SFP speeds and media its ports use, and, on the time server row,
the loose material linked to it by part. Every value comes from the files and the engine;
the screen only shows it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bomgen.app.loose import _records
from bomgen.app.substations import _library, resolve, substation_page
from bomgen.checks import duplicate_tag_checks
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import CABLE_MANAGED, LayoutResult, layout_preview, runs
from bomgen.engine.mcb import has_branch_mcb
from bomgen.engine.network import unserved_links
from bomgen.engine.rules_text import sfp_rule, sfp_spare_rule
from bomgen.engine.units import expand_devices
from bomgen.io.derived import effective_part_id
from bomgen.io.errors import InputError
from bomgen.io.loader import LoadedSubstation
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.store import LibraryStore
from bomgen.models.library import Category, DeviceType, Library, Media
from bomgen.models.output import Derived
from bomgen.models.project import Project
from bomgen.models.substation import Equipment, EquipmentRole, Substation

ROLE_LABEL = {
    EquipmentRole.TIME_SERVER: "Time server clock",
    EquipmentRole.L2_SWITCH: "L2 switch",
    EquipmentRole.L1_SWITCH: "L1 switch",
    EquipmentRole.OPERATOR_WS: "Operator workstation",
    EquipmentRole.ENGINEERING_WS: "Engineering workstation",
    EquipmentRole.DA_SERVER: "DA server",
    EquipmentRole.KVM: "KVM",
    EquipmentRole.CONSOLE: "Console",
    EquipmentRole.ANNUNCIATOR: "Annunciator",
    EquipmentRole.TIME_ACCESSORY: "Time accessory",
    EquipmentRole.EXT_SWITCH: "External switch",
    EquipmentRole.FIREWALL: "Firewall",
    EquipmentRole.FOPP: "Fibre patch panel",
}
# a row with role "other" is named by its part's category
CATEGORY_LABEL = {
    Category.GPS_CLOCK: "Time server clock",
    Category.GATEWAY: "Gateway",
    Category.RTAC: "RTAC",
    Category.IO_CHASSIS: "I/O rack",
    Category.WORKSTATION: "Workstation",
    Category.FIREWALL: "Firewall",
    Category.PATCH_PANEL: "Fibre patch panel",
    Category.NETWORK_SWITCH: "Switch",
    Category.ANNUNCIATOR: "Annunciator",
    Category.KVM: "KVM",
    Category.CONSOLE: "Console",
    Category.MONITOR: "Monitor",
    Category.PERIPHERAL: "Keyboard and mouse",
}
ROLE_CATEGORY = {
    EquipmentRole.TIME_SERVER: Category.GPS_CLOCK,
    EquipmentRole.L2_SWITCH: Category.NETWORK_SWITCH,
    EquipmentRole.L1_SWITCH: Category.NETWORK_SWITCH,
    EquipmentRole.EXT_SWITCH: Category.NETWORK_SWITCH,
    EquipmentRole.OPERATOR_WS: Category.WORKSTATION,
    EquipmentRole.ENGINEERING_WS: Category.WORKSTATION,
    EquipmentRole.DA_SERVER: Category.WORKSTATION,
    EquipmentRole.KVM: Category.KVM,
    EquipmentRole.CONSOLE: Category.CONSOLE,
    EquipmentRole.ANNUNCIATOR: Category.ANNUNCIATOR,
    EquipmentRole.FIREWALL: Category.FIREWALL,
    EquipmentRole.FOPP: Category.PATCH_PANEL,
}
# the design §3 rows a new substation starts with, in order
DEFAULT_ROWS = (
    EquipmentRole.TIME_SERVER,
    EquipmentRole.L2_SWITCH,
    EquipmentRole.L1_SWITCH,
    EquipmentRole.OPERATOR_WS,
    EquipmentRole.ENGINEERING_WS,
    EquipmentRole.DA_SERVER,
    EquipmentRole.KVM,
    EquipmentRole.CONSOLE,
    EquipmentRole.ANNUNCIATOR,
)
# the categories "Add a device" offers after the default rows (design §3, plus row)
ADD_CATEGORIES = (
    Category.PATCH_PANEL,
    Category.FIREWALL,
    Category.NETWORK_SWITCH,
    Category.GATEWAY,
    Category.RTAC,
    Category.IO_CHASSIS,
    Category.WORKSTATION,
    Category.KVM,
    Category.CONSOLE,
    Category.MONITOR,  # APP-23: the console's screen and keyboard
    Category.PERIPHERAL,
)
NETWORK_CATEGORIES = frozenset(
    {Category.NETWORK_SWITCH, Category.PATCH_PANEL, Category.FIREWALL, Category.GATEWAY}
)
VALUES = (
    "height_u",
    "unit_power_w",
    "supply_type",
    "voltage_v",
    "power_supplies",
    "inrush_a",
    "load_type",
)
SIZED = (EquipmentRole.L1_SWITCH, EquipmentRole.L2_SWITCH)


def _parts(library: Library) -> list[DeviceType]:
    """The library's own parts: derived parts are this design's, never a choice."""
    return [d for d in library.devices if d.derived_from is None]


def time_accessory_parts(library: Library, part_id: str) -> frozenset[str]:
    """The parts a time server row links to: its part's own loose items and the parts
    that share an alternative group with one of them (ADR 0017)."""
    part = library.get(part_id)
    if part is None:
        return frozenset()
    found: set[str] = set()
    for item in part.loose_items:
        found.add(item.part_id)
        own = library.get(item.part_id)
        if own is not None and own.alt_group is not None:
            found |= {d.part_id for d in library.alt_group(own.alt_group)}
    return frozenset(found)


def _category(entry: Equipment, part: DeviceType | None) -> Category | None:
    if part is not None:
        return part.category
    return ROLE_CATEGORY.get(entry.role)


BOM_TEXT = ("purpose", "tag", "tag_type", "first_nn", "hwio_points")  # Parts BOM text (M59)


def _label(entry: Equipment, category: Category | None) -> str:
    if entry.role in ROLE_LABEL:
        return ROLE_LABEL[entry.role]
    return CATEGORY_LABEL.get(category, "Other") if category is not None else "Other"


def row_label(entry: Equipment, library: Library) -> str:
    """The name Parts gives equipment ``entry``: its role, or else its part's category."""
    part = library.get(entry.part_id) if entry.part_id else None
    return _label(entry, _category(entry, part))


SfpCounts = dict[tuple[str, str], tuple[int, int]]  # (speed, media) -> (links, spare)


def _preview(loaded: LoadedSubstation | None) -> LayoutResult | None:
    """The layout the page describes; none for a blank substation, which has no switches
    to size yet (the model takes both or none, ADR 0013), or when the sizing fails."""
    if loaded is None or not loaded.substation.equipment:
        return None
    try:
        return layout_preview(loaded)
    except EngineError:
        return None


def _tag_info(
    loaded: LoadedSubstation, result: LayoutResult
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """For each entry, the tags the layout generates, one per panel row, ignoring a tag the
    entry writes (the BOM text placeholders), and the duplicate-tag sentence of the first
    tag of its units another unit shares (plan M59)."""
    generated: dict[str, list[str]] = {}
    owners: dict[str, list[str]] = {}  # unit tag -> entry ids
    expanded = []
    fills = [f for f in result.fills if f.units]
    for panel, fill in zip(result.panels, fills, strict=True):
        rows = expand_devices(panel, loaded.library, tagging=loaded.tagging)
        expanded.append((panel, rows))
        devices = [d.model_copy(update={"tag": None}) for d in panel.devices]
        untagged = expand_devices(
            panel.model_copy(update={"devices": devices}), loaded.library, tagging=loaded.tagging
        )
        for run, row, auto in zip(runs(fill), rows, untagged, strict=True):
            entry = run[0].device
            if auto.tag is not None:
                generated.setdefault(entry, []).append(auto.tag)
            for tag in row.unit_tags:
                if tag is not None:
                    owners.setdefault(tag, []).append(entry)
    duplicates: dict[str, str] = {}
    for item in duplicate_tag_checks(expanded):
        for entry in owners.get(item.subject or "", []):
            duplicates.setdefault(entry, f"{item.subject}: {item.message}")
    return generated, duplicates


def _sfp_needs(loaded: LoadedSubstation, result: LayoutResult) -> dict[str, SfpCounts]:
    """The (speed, media) pairs each sized switch entry's ports use, from the layout, with
    the links and automatic spare of the first panel row that hosts it (plan M49)."""
    needs: dict[str, SfpCounts] = {}
    for entry in loaded.substation.equipment:
        if entry.role not in SIZED or entry.part_id is None:
            continue
        key = (
            result.plan.l1_part_id
            if entry.role is EquipmentRole.L1_SWITCH
            else effective_part_id(entry)
        )
        for panel in result.panels:
            plan = panel.port_plans.get(str(key))
            if plan is None:
                continue
            counts: SfpCounts = {}
            for a in (*plan.uplinks_l3, *plan.uplinks, *plan.downlinks):
                if a.media is not Media.RJ45:
                    links, spare = counts.get((a.speed.value, a.media.value), (0, 0))
                    counts[(a.speed.value, a.media.value)] = (links + a.count, spare + a.spare)
            needs.setdefault(entry.id, {})
            for pair, value in counts.items():
                needs[entry.id].setdefault(pair, value)
    return needs


def _sfp(
    entry: Equipment, speed: str, media: str, counts: tuple[int, int], candidates: list[str]
) -> dict[str, Any]:
    """One SFP sub-row of a switch: its part choice and its quantity per BOM row."""
    choice = next((c for c in entry.sfp if (c.speed.value, c.media.value) == (speed, media)), None)
    used, auto = counts
    override = choice.spare if choice is not None else None
    extra = choice.extra if choice is not None else 0
    spare = auto if override is None else override
    rule = sfp_spare_rule(auto, l1=entry.role is EquipmentRole.L1_SWITCH)
    return {
        "speed": speed,
        "media": media,
        "choice": choice.part_id if choice is not None else None,
        "candidates": candidates,
        "used": used,
        "spare": Derived[int](value=auto, rule=rule, override=override).model_dump(mode="json"),
        "extra": extra,
        "total": used + spare + extra,
        "rule": sfp_rule(used, spare, extra),
    }


def _serves(device: DeviceType, speed: str, media: str) -> bool:
    return device.category is Category.SFP and any(
        p.speed.value == speed and p.media is not None and p.media.value == media
        for p in device.ports
    )


def _row(
    index: int,
    entry: Equipment,
    library: Library | None,
    needs: SfpCounts,
    loose: list[dict[str, Any]],
    host_panel: str | None,
) -> dict[str, Any]:
    part = library.get(entry.part_id) if library and entry.part_id else None
    category = _category(entry, part)
    default = category in CABLE_MANAGED  # the layout's rule (ADR 0013, amended)
    sfp = [
        _sfp(
            entry,
            speed,
            media,
            needs[(speed, media)],
            [d.part_id for d in _parts(library) if _serves(d, speed, media)] if library else [],
        )
        for speed, media in sorted(needs)
    ]
    accessories = None
    if part is not None and part.category is Category.GPS_CLOCK and library is not None:
        linked = time_accessory_parts(library, part.part_id)
        accessories = {
            "library": [{"part_id": i.part_id, "qty": i.qty} for i in part.loose_items],
            "added": [x for x in loose if x["part_id"] in linked],
            "parts": sorted(linked),
            "host_panel": host_panel,
        }
    return {
        "index": index,
        "id": entry.id,
        "role": entry.role.value,
        "label": _label(entry, category),
        "category": category.value if category is not None else None,
        "part_id": entry.part_id,
        "known": part is not None or entry.part_id is None,
        "ordering_code": entry.ordering_code,
        "qty": entry.qty,
        "sized": entry.role in SIZED,
        "redundant": entry.redundant,
        "network": category in NETWORK_CATEGORIES,
        "library": {k: getattr(part, k) for k in VALUES} if part is not None else None,
        # ADR 0037: the figures its part assumes, for the chip on the row
        "assumed": [
            {"field": name, "ref": source.ref}
            for name in ("unit_power_w", "inrush_a")
            if part is not None
            and (source := part.sources.get(name)) is not None
            and source.kind == "assumed"
        ],
        "overrides": entry.overrides.values() if entry.overrides is not None else {},
        "sfp": sfp,
        "bom_text": {k: getattr(entry, k) for k in BOM_TEXT},  # M59
        # M31: the link to the L2 switch (none for the sized switches and the patch panel)
        "link": None
        if entry.role in (*SIZED, EquipmentRole.FOPP)
        else {
            "l2_ports": entry.l2_ports,
            "l2_speed": entry.l2_speed.value,
            "l2_media": entry.l2_media.value,
            "no_sfp": library is not None and bool(unserved_links([entry], library)),  # M46
        },
        "serial_ports": (entry.port_plan.serial_ports if entry.port_plan else 0)
        if category is Category.RTAC
        else None,
        "accessories": accessories,
        "cable_manager": {
            "on": entry.cable_manager if entry.cable_manager is not None else default,
            "default": default,
        }
        if category in NETWORK_CATEGORIES
        else None,
        # M58: the alarm on its branch MCBs' trip, over the library's value
        "alarm": {
            "on": entry.alarm_on_branch_mcb
            if entry.alarm_on_branch_mcb is not None
            else part.alarm_on_branch_mcb,
            "default": part.alarm_on_branch_mcb,
        }
        if part is not None and has_branch_mcb(part)
        else None,
    }


def _source(
    project_file: Path, substation_id: str, store: LibraryStore
) -> tuple[Substation | None, Library | None, LoadedSubstation | None, Project]:
    found = resolve(project_file, substation_id, store)
    loaded = found.source or found.loaded
    if loaded is not None:
        return loaded.substation, loaded.library, loaded, found.project
    try:
        substation: Substation | None = Substation.model_validate(read_yaml(found.file).data)
    except (InputError, ValidationError):
        substation = None
    return substation, _library(project_file, found.project, store), None, found.project


def parts_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The substation page plus ``parts``: the rows, the options per category and the
    default rows; ``parts`` is ``None`` when the substation file cannot be read."""
    page = substation_page(project_file, substation_id, store)
    substation, library, loaded, project = _source(project_file, substation_id, store)
    if substation is None:
        return page | {"parts": None}
    result = _preview(loaded)
    needs = _sfp_needs(loaded, result) if loaded is not None and result is not None else {}
    tags, duplicates = _tag_info(loaded, result) if loaded and result else ({}, {})
    items = substation.loose_material.items if substation.loose_material else []
    # loose material starts with its host panel, so accessories can be added only then
    host = substation.loose_material.host_panel if substation.loose_material else None
    loose = [
        {"index": i, "part_id": x.part_id, "item": x.model_dump(mode="json", exclude_unset=True)}
        for i, x in enumerate(items)
        if x.part_id is not None
    ]
    own = _parts(library) if library is not None else []
    records = _records(project, store)  # the data quality the Device picker shows
    categories = {*ROLE_CATEGORY.values(), *ADD_CATEGORIES, Category.ACCESSORY}
    return page | {
        "parts": {
            "rows": [
                _row(i, e, library, needs.get(e.id, {}), loose, host)
                | {"tags": tags.get(e.id, []), "duplicate": duplicates.get(e.id)}
                for i, e in enumerate(substation.equipment)
            ],
            "options": {
                c.value: [
                    {
                        "part_id": d.part_id,
                        "make": d.make,
                        "model": d.model,
                        "supply_type": d.supply_type.value if d.supply_type else None,
                        "unit_power_w": d.unit_power_w,
                        "data_quality": records[d.part_id].verified
                        if d.part_id in records
                        else None,
                    }
                    for d in own
                    if d.category is c
                ]
                for c in sorted(categories)
            },
            "default_rows": [
                {"role": r.value, "label": ROLE_LABEL[r], "category": ROLE_CATEGORY[r].value}
                for r in DEFAULT_ROWS
            ],
            "add_categories": [
                {"category": c.value, "label": CATEGORY_LABEL[c]} for c in ADD_CATEGORIES
            ],
        }
    }
