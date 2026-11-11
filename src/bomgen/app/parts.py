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
from bomgen.engine.layout import CABLE_MANAGED, PRIORITY, LayoutResult, layout_preview, runs
from bomgen.engine.mcb import has_branch_mcb
from bomgen.engine.network import automatic_sfp, port_plan, unserved_links
from bomgen.engine.rules_text import sfp_rule, sfp_spare_rule, sfp_total_rule
from bomgen.engine.units import expand_devices
from bomgen.io import ied_csv
from bomgen.io.derived import effective_part_id
from bomgen.io.edit import EditError
from bomgen.io.errors import InputError
from bomgen.io.loader import LoadedSubstation
from bomgen.io.parts_edit import has_l2_link
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.store import LibraryStore
from bomgen.models.library import Category, DeviceType, Library, Media, PortSpeed, PurdueLevel
from bomgen.models.output import Derived
from bomgen.models.panel import Panel
from bomgen.models.project import Project
from bomgen.models.substation import Equipment, EquipmentRole, Side, Substation

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
    EquipmentRole.REDBOX: "RedBox",
    EquipmentRole.MEDIA_CONVERTER: "Media converter",
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
    Category.REDBOX: "RedBox",
    Category.MEDIA_CONVERTER: "Media converter",
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
    EquipmentRole.REDBOX: Category.REDBOX,
    EquipmentRole.MEDIA_CONVERTER: Category.MEDIA_CONVERTER,
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
    Category.REDBOX,  # ADR 0038
    Category.MEDIA_CONVERTER,
    Category.RTAC,
    Category.IO_CHASSIS,
    Category.WORKSTATION,
    Category.KVM,
    Category.CONSOLE,
    Category.MONITOR,  # APP-23: the console's screen and keyboard
    Category.PERIPHERAL,
)
NETWORK_CATEGORIES = frozenset(
    {
        Category.NETWORK_SWITCH,
        Category.PATCH_PANEL,
        Category.FIREWALL,
        Category.GATEWAY,
        Category.REDBOX,
        Category.MEDIA_CONVERTER,
    }
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


# Add a device makes a row of this role for its category; "other" for the rest
ADD_ROLE = {
    Category.PATCH_PANEL: EquipmentRole.FOPP,
    Category.FIREWALL: EquipmentRole.FIREWALL,
    Category.NETWORK_SWITCH: EquipmentRole.EXT_SWITCH,
    Category.KVM: EquipmentRole.KVM,
    Category.CONSOLE: EquipmentRole.CONSOLE,
    Category.REDBOX: EquipmentRole.REDBOX,
    Category.MEDIA_CONVERTER: EquipmentRole.MEDIA_CONVERTER,
}
# the switch roles offer the switches of their Purdue level (the loader's L1 rule, plan M83)
ROLE_LEVEL = {
    EquipmentRole.L1_SWITCH: PurdueLevel.L1,
    EquipmentRole.L2_SWITCH: PurdueLevel.L2,
    EquipmentRole.EXT_SWITCH: PurdueLevel.EXT,
}


def _parts(library: Library) -> list[DeviceType]:
    """The library's own parts: derived parts are this design's, never a choice."""
    return [d for d in library.devices if d.derived_from is None]


def row_choices(
    library: Library, role: EquipmentRole, category: Category, current: str | None
) -> list[DeviceType]:
    """The parts a row of ``role`` offers (plan M83, Q74 (a)): its category, at the role's
    level for a switch; an alternative only of the current part's group; no obsolete part;
    and the current part always."""
    own = library.get(current) if current else None
    group = own.alt_group if own is not None else None
    level = ROLE_LEVEL.get(role)
    return [
        d
        for d in _parts(library)
        if d.part_id == current
        or (
            d.category is category
            and (level is None or d.purdue_level is level)
            and (d.tier is None or (group is not None and d.alt_group == group))
            and d.state != "obsolete"
        )
    ]


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


BOM_TEXT = ("purpose", "tag", "tag_type", "first_nn", "hwio_points", "note")  # M59; note M71


def _label(entry: Equipment, category: Category | None) -> str:
    if entry.role in ROLE_LABEL:
        return ROLE_LABEL[entry.role]
    return CATEGORY_LABEL.get(category, "Other") if category is not None else "Other"


def row_label(entry: Equipment, library: Library) -> str:
    """The name Parts gives equipment ``entry``: its role, or else its part's category."""
    part = library.get(entry.part_id) if entry.part_id else None
    return _label(entry, _category(entry, part))


SfpRow = tuple[str, int, int]  # one BOM row of a switch entry: cabinet name, links, spare
SfpCounts = dict[tuple[str, str], list[SfpRow]]  # (speed, media) -> its BOM rows, panel order


def _typed_on(rows: list[SfpRow]) -> SfpRow:
    """The BOM row a typed SFP total is computed on: the one with the most links, the first
    of equals (plan M87), so the spare it implies leaves no row short of its links."""
    return max(rows, key=lambda r: r[1])


NOT_LOADED = (
    "The SFPs cannot be counted until the substation loads: fix the problems listed at the "
    "top of this page."
)


def _preview(loaded: LoadedSubstation | None) -> tuple[LayoutResult | None, str | None]:
    """The layout the page describes, or why the switch rows have no SFP rows (plan M86);
    neither for a blank substation, which has no switches to size yet (the model takes
    both or none, ADR 0013)."""
    if loaded is None:
        return None, NOT_LOADED
    if not loaded.substation.equipment:
        return None, None
    try:
        return layout_preview(loaded), None
    except EngineError as exc:
        return None, f"The SFPs cannot be counted while the layout fails: {str(exc).rstrip('.')}."


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


HAND_WRITTEN = (
    "These cabinets are hand-written: the BOM takes these SFPs from the port plans in the "
    "panel files, which name the library part, so an SFP choice made here does not reach "
    "it. Generate the panels on Panels to set them here, or change the panel files."
)
NOT_PLACED = "The hand-written panel files do not place this switch, so the BOM has no SFPs for it."


def _hand_written(loaded: LoadedSubstation) -> bool:
    """Whether a build uses the panel files as they are: panels are listed and none was
    generated, the case where ``engine/layout.with_layout`` leaves them alone (plan M87)."""
    listed = [p for p in loaded.panels if p.id not in loaded.manual_panel_ids]
    return bool(listed) and not any(p.generated for p in listed)


def _built_panels(loaded: LoadedSubstation, result: LayoutResult) -> tuple[Panel, ...]:
    """The panels a build of ``loaded`` uses, as ``with_layout`` gives them: the files when
    they are hand-written, else the layout's with the manual panels after them (before any
    panel is listed, the layout's: what Generate writes)."""
    if _hand_written(loaded):
        return loaded.panels
    manual = tuple(p for p in loaded.panels if p.id in loaded.manual_panel_ids)
    return (*result.panels, *manual)


def _sfp_needs(loaded: LoadedSubstation, result: LayoutResult) -> dict[str, SfpCounts]:
    """The (speed, media) pairs each sized switch entry's ports use, with the links and
    automatic spare of every BOM row that hosts it (plan M49), read from the panels the
    build uses, as the BOM reads them (plan M87). An L1 row with no part has those of the
    switch the sizing picked (plan M86); hand-written files place the library part."""
    hand = _hand_written(loaded)
    built = [
        (panel, expand_devices(panel, loaded.library, tagging=loaded.tagging))
        for panel in _built_panels(loaded, result)
    ]
    needs: dict[str, SfpCounts] = {}
    for entry in loaded.substation.equipment:
        if entry.role not in SIZED or (
            entry.role is EquipmentRole.L2_SWITCH and entry.part_id is None
        ):
            continue
        key = (
            result.plan.l1_part_id
            if entry.role is EquipmentRole.L1_SWITCH
            else effective_part_id(entry)
        )
        keys = {key, entry.part_id} if hand else {key}
        for panel, rows in built:
            for row in rows:
                plan = port_plan(panel, row) if row.device.part_id in keys else None
                if plan is None:
                    continue
                counts: dict[tuple[str, str], tuple[int, int]] = {}
                for a in (*plan.uplinks_l3, *plan.uplinks, *plan.downlinks):
                    if a.media is not Media.RJ45:
                        links, spare = counts.get((a.speed.value, a.media.value), (0, 0))
                        counts[(a.speed.value, a.media.value)] = (links + a.count, spare + a.spare)
                found = needs.setdefault(entry.id, {})
                for pair, (links, spare) in counts.items():
                    found.setdefault(pair, []).append((panel.cabinet_name, links, spare))
    return needs


def sfp_links(
    project_file: Path,
    substation_id: str,
    store: LibraryStore,
    index: int,
    speed: str,
    media: str,
) -> int:
    """The ``speed`` ``media`` links of the BOM row of switch row ``index`` a typed total is
    computed on, as its SFP row on the page counts them (plan M87); an ``EditError`` says
    why there are none."""
    _substation, _lib, loaded, _project = _source(project_file, substation_id, store)
    result, reason = _preview(loaded)
    if loaded is None or result is None:
        raise EditError(reason or NOT_LOADED)
    if _hand_written(loaded):
        raise EditError(HAND_WRITTEN)
    rows = loaded.substation.equipment
    if not 0 <= index < len(rows):
        raise EditError(f"no equipment row {index + 1}")
    counts = _sfp_needs(loaded, result).get(rows[index].id, {}).get((speed, media))
    if counts is None:
        raise EditError(f"Equipment row {index + 1} has no {speed} {media} SFPs to count.")
    return _typed_on(counts)[1]


def _sfp(
    entry: Equipment,
    speed: str,
    media: str,
    counts: list[SfpRow],
    candidates: list[str],
    pick: str | None,
    *,
    hand: bool = False,
) -> dict[str, Any]:
    """One SFP sub-row of a switch: its part choice, the part the engine takes without
    one (``pick``, plan M86) and its quantity, computed on the BOM row a typed total is
    computed on, then on each BOM row (plan M87). On ``hand``-written panels the BOM takes
    none of the entry's choices, so neither does the row (plan M87)."""
    choices = () if hand else entry.sfp
    choice = next((c for c in choices if (c.speed.value, c.media.value) == (speed, media)), None)
    on, used, auto = _typed_on(counts)
    override = choice.spare if choice is not None else None
    extra = choice.extra if choice is not None else 0
    spare = auto if override is None else override
    l1 = entry.role is EquipmentRole.L1_SWITCH
    rule = sfp_spare_rule(auto, l1=l1)
    # M87, Q77 (a): the quantity is the value typed; it is stored as the spare it implies
    quantity = Derived[int](
        value=used + auto + extra,
        rule=sfp_total_rule(used, auto, extra, l1=l1),
        override=None if override is None else used + override + extra,
    )
    return {
        "speed": speed,
        "media": media,
        "choice": choice.part_id if choice is not None else None,
        "candidates": candidates,
        "auto": pick,
        "used": used,
        "spare": Derived[int](value=auto, rule=rule, override=override).model_dump(mode="json"),
        "extra": extra,
        "total": used + spare + extra,
        "quantity": quantity.model_dump(mode="json"),
        "rule": sfp_rule(used, spare, extra),
        # M87: the BOM rows that carry these SFPs, each with what it prints; the typed total
        # is computed on ``on``, and the spare it implies goes on every row
        "on": on,
        "agree": len({(n, s) for _cabinet, n, s in counts}) == 1,
        "rows": [
            {
                "cabinet": cabinet,
                "links": n,
                "auto_spare": s,
                "spare": (row_spare := s if override is None else override),
                "extra": extra,
                "quantity": n + row_spare + extra,
                "rule": sfp_rule(n, row_spare, extra),
            }
            for cabinet, n, s in counts
        ],
    }


def _serves(device: DeviceType, speed: str, media: str) -> bool:
    return device.category is Category.SFP and any(
        p.speed.value == speed and p.media is not None and p.media.value == media
        for p in device.ports
    )


def _effective(part: DeviceType | None, entry: Equipment) -> DeviceType | None:
    """``part`` with ``entry``'s overrides, the values its derived part has (ADR 0024)."""
    if part is None or entry.overrides is None:
        return part
    return part.model_copy(update=entry.overrides.values())


def offers_ab(role: EquipmentRole) -> bool:
    """Whether a row of ``role`` offers the A and B box (plan M90): never a sized switch,
    which the model needs redundant, nor an annunciator, one loose item of its qty."""
    return role not in SIZED and role is not EquipmentRole.ANNUNCIATOR


def _row(
    index: int,
    entry: Equipment,
    library: Library | None,
    needs: SfpCounts,
    loose: list[dict[str, Any]],
    host_panel: str | None,
    named: dict[str, dict[str, Any]],
    sized_part: DeviceType | None,
    sfp_reason: str | None,
    hand: bool = False,
) -> dict[str, Any]:
    """``named``: each library part as the picker names it; ``sized_part``: the switch the
    sizing picked for an L1 row with no part; ``sfp_reason``: why a switch row has no SFP
    rows (plan M86); ``hand``: the build uses hand-written panel files (plan M87). An SFP
    row names its parts by id; ``options["sfp"]`` names them."""
    part = library.get(entry.part_id) if library and entry.part_id else None
    category = _category(entry, part)
    default = category in CABLE_MANAGED  # the layout's rule (ADR 0013, amended)
    host = part or sized_part  # the switch whose ports take the SFPs
    # M90: the layout racks no annunciator and gives a 0 U part no cable manager; the
    # engine takes the supply from the derived part
    racked = entry.role is not EquipmentRole.ANNUNCIATOR
    effective = _effective(host, entry)
    zero_u = effective is not None and not effective.height_u
    supplied = _effective(part, entry)

    def auto(speed: str, media: str) -> str | None:
        if host is None or library is None:
            return None
        pick = automatic_sfp(host, PortSpeed(speed), Media(media), library)
        return pick.part_id if pick is not None else None

    sfp = [
        _sfp(
            entry,
            speed,
            media,
            needs[(speed, media)],
            [d.part_id for d in _parts(library) if _serves(d, speed, media)] if library else [],
            auto(speed, media),
            hand=hand,
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
        "ab": offers_ab(entry.role),  # M90
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
<<<<<<< HEAD
        # M86, Q76 (a): the sized L1's SFP rows are read-only until its switch is pinned
        "pin": named.get(sized_part.part_id) if sized_part is not None else None,
        "sfp_reason": sfp_reason if entry.role in SIZED else None,
        "bom_text": {k: getattr(entry, k) for k in BOM_TEXT} if racked else None,  # M59
=======
        # M86, Q76 (a): the sized L1's SFP rows are read-only until its switch is pinned;
        # M87: on hand-written panels they are read-only, and pinning would change nothing
        "pin": named.get(sized_part.part_id) if sized_part is not None and not hand else None,
        "sfp_reason": None
        if entry.role not in SIZED
        else sfp_reason or (NOT_PLACED if hand and not needs else None),
        "sfp_hand": HAND_WRITTEN if hand and needs and entry.role in SIZED else None,
        "bom_text": {k: getattr(entry, k) for k in BOM_TEXT},  # M59
>>>>>>> origin/main
        # M74: a common row may be steered to a panel; a redundant or one-side row follows its LAN
        "placement": {
            "panel_hint": entry.panel_hint,
            "steerable": not entry.redundant and entry.side is Side.NONE,
            "priority": entry.priority,  # M76: the row's rack stack order, or the category's
            "default_priority": PRIORITY.get(category, 4) if category is not None else 4,
        }
        if racked
        else None,
        # M31: the link to the L2 switch, on the rows that have one (M89)
        "link": None
        if not has_l2_link(entry, part)
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
        # M90: a 0 U part shows only a choice written in the file; the BOM has none for it
        "cable_manager": {
            "on": entry.cable_manager if entry.cable_manager is not None else default,
            "default": default,
            "zero_u": zero_u,
        }
        if category in NETWORK_CATEGORIES and (not zero_u or entry.cable_manager is not None)
        else None,
        # M58: the alarm on its branch MCBs' trip, over the library's value
        "alarm": {
            "on": entry.alarm_on_branch_mcb
            if entry.alarm_on_branch_mcb is not None
            else supplied.alarm_on_branch_mcb,
            "default": supplied.alarm_on_branch_mcb,
        }
        if supplied is not None and racked and has_branch_mcb(supplied)
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
    result, sfp_reason = _preview(loaded)
    needs = _sfp_needs(loaded, result) if loaded is not None and result is not None else {}
    hand = loaded is not None and result is not None and _hand_written(loaded)  # plan M87
    picked = library.get(result.plan.l1_part_id) if library and result else None
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
    basis = substation.design_basis
    avl = project.vendor_list(basis.vendor_list) if basis is not None else None

    def on_list(part_id: str | None) -> bool:  # plan M53: off the list gets a warning chip
        part = library.get(part_id) if library is not None and part_id else None
        return avl is None or part is None or avl.allows(part.part_id, part.make)

    originals = {d.alt_group: d for d in own if d.alt_group is not None and d.tier is None}

    def option(d: DeviceType) -> dict[str, Any]:
        """What the picker shows of a part; an alternative names the part it replaces (M83)."""
        replaced = originals.get(d.alt_group) if d.tier is not None and d.alt_group else None
        return {
            "part_id": d.part_id,
            "make": d.make,
            "model": d.model,
            "tags": d.tags,
            "supply_type": d.supply_type.value if d.supply_type else None,
            "unit_power_w": d.unit_power_w,
            "data_quality": records[d.part_id].verified if d.part_id in records else None,
            "on_list": on_list(d.part_id),
            "tier": d.tier,
            # two switches may share a make and model: the level tells them apart (Q82)
            "level": f"{d.purdue_level.value} switch"
            if d.category is Category.NETWORK_SWITCH and d.purdue_level is not None
            else None,
            "replaces": None
            if replaced is None
            else {"part_id": replaced.part_id, "make": replaced.make, "model": replaced.model},
        }

    opts = {d.part_id: option(d) for d in own}

    def first(d: DeviceType) -> bool:  # the list's parts first
        return not opts[d.part_id]["on_list"]

    def choices(
        role: EquipmentRole, category: Category | None, current: str | None
    ) -> list[dict[str, Any]]:
        if library is None or category is None:
            return []
        found = row_choices(library, role, category, current)
        return [opts[d.part_id] for d in sorted(found, key=first)]

    def row_category(entry: Equipment) -> Category | None:
        return _category(entry, library.get(entry.part_id) if library and entry.part_id else None)

    # SFP: the names of the parts the SFP rows offer (plan M86)
    categories = {*ROLE_CATEGORY.values(), *ADD_CATEGORIES, Category.ACCESSORY, Category.SFP}
    return page | {
        "parts": {
            "rows": [
                _row(
                    i,
                    e,
                    library,
                    needs.get(e.id, {}),
                    loose,
                    host,
                    opts,
                    picked if e.role is EquipmentRole.L1_SWITCH and e.part_id is None else None,
                    sfp_reason,
                    hand,
                )
                | {"tags": tags.get(e.id, []), "duplicate": duplicates.get(e.id)}
                | {"on_list": on_list(e.part_id)}
                | {"choices": choices(e.role, row_category(e), e.part_id)}  # M83
                for i, e in enumerate(substation.equipment)
            ],
            # the whole category, for "Search all parts"
            "options": {
                c.value: [opts[d.part_id] for d in sorted(own, key=first) if d.category is c]
                for c in sorted(categories)
            },
            "ieds": [ied_csv.shown(r) for r in substation.network.ied_schedule],  # M60
            "links": [x.model_dump(mode="json") for x in substation.network.external_links],
            "default_rows": [
                {
                    "role": r.value,
                    "label": ROLE_LABEL[r],
                    "category": ROLE_CATEGORY[r].value,
                    "choices": choices(r, ROLE_CATEGORY[r], None),
                    "ab": offers_ab(r),  # M90
                }
                for r in DEFAULT_ROWS
            ],
            "add_categories": [
                {
                    "category": c.value,
                    "label": CATEGORY_LABEL[c],
                    "role": (role := ADD_ROLE.get(c, EquipmentRole.OTHER)).value,
                    "choices": choices(role, c, None),
                }
                for c in ADD_CATEGORIES
            ],
            "vendor_list": avl.name if avl is not None else None,
        }
    }
