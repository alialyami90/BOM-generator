"""Cross-record checks that single-file validation cannot do: duplicate and dangling
references within the library, a panel, and the project as a whole.

Each function returns located issues; none raises.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from bomgen.io.errors import Issue, Loc, format_location
from bomgen.io.yaml_source import YamlSource
from bomgen.models.library import (
    DEFAULT_BRAND,
    CatalogueChoice,
    Category,
    ChangeOverDiodes,
    DeviceType,
    Housekeeping,
    Library,
    PurdueLevel,
)
from bomgen.models.panel import Panel, PanelMirror
from bomgen.models.project import Project, RegisterEntry
from bomgen.models.substation import Equipment, EquipmentRole, PairMove, Substation, UnitRef


def _issue(source: YamlSource, loc: Loc, message: str) -> Issue:
    return Issue(source.path, format_location(loc), message, source.line_for(loc))


def _unknown_part(source: YamlSource, loc: Loc, part_id: str, library_name: str) -> Issue:
    return _issue(source, loc, f"unknown part_id '{part_id}' (not in {library_name})")


def _unknown_busbar(source: YamlSource, loc: Loc, busbar: str) -> Issue:
    return _issue(source, loc, f"unknown busbar '{busbar}' (not in catalogues.busbars)")


def library_issues(library: Library, source: YamlSource) -> list[Issue]:
    """Duplicate part ids and references from the library to parts and catalogue entries."""
    issues: list[Issue] = []
    first_at: dict[str, int] = {}
    for index, device in enumerate(library.devices):
        if device.part_id in first_at:
            first = first_at[device.part_id]
            message = f"duplicate part_id '{device.part_id}' (first at devices[{first}])"
            issues.append(_issue(source, ("devices", index, "part_id"), message))
        else:
            first_at[device.part_id] = index
    name = source.path.name
    for index, device in enumerate(library.devices):
        for k, child in enumerate(device.children):
            if child.part_id not in first_at:
                loc = ("devices", index, "children", k, "part_id")
                issues.append(_unknown_part(source, loc, child.part_id, name))
        for k, item in enumerate(device.loose_items):
            if item.part_id not in first_at:
                loc = ("devices", index, "loose_items", k, "part_id")
                issues.append(_unknown_part(source, loc, item.part_id, name))
        for k, rule in enumerate(device.terminals):
            if rule.block not in library.catalogues.terminal_blocks:
                loc = ("devices", index, "terminals", k, "block")
                message = (
                    f"unknown terminal block '{rule.block}' (not in catalogues.terminal_blocks)"
                )
                issues.append(_issue(source, loc, message))
    housekeeping_sets: list[tuple[Loc, Housekeeping]] = [
        (("catalogues", "housekeeping"), library.catalogues.housekeeping)
    ]
    for index, brand in enumerate(library.catalogue_brands.housekeeping):
        housekeeping_sets.append((("catalogue_brands", "housekeeping", index), brand))
    for base, housekeeping in housekeeping_sets:
        for role_loc, part_id in _housekeeping_refs(base, housekeeping):
            if part_id not in first_at:
                issues.append(_unknown_part(source, role_loc, part_id, name))
    return issues


def catalogue_choice_issues(
    choice: CatalogueChoice | None,
    source: YamlSource,
    prefix: Loc,
    library: Library,
    library_name: str,
) -> list[Issue]:
    """Brand ids in ``choice`` that the library does not have (ADR 0017)."""
    if choice is None:
        return []
    issues: list[Issue] = []
    for kind in sorted(choice.model_fields_set):
        brand_id = getattr(choice, kind)
        known = library.brand_ids(kind)
        if brand_id is not None and brand_id != DEFAULT_BRAND and brand_id not in known:
            message = f"no {kind} brand '{brand_id}' in {library_name} (it has: {', '.join(known)})"
            issues.append(_issue(source, (*prefix, kind), message))
    return issues


def _housekeeping_refs(base: Loc, housekeeping: Housekeeping) -> list[tuple[Loc, str]]:
    refs: list[tuple[Loc, str]] = []
    for role in Housekeeping.model_fields:
        ref = getattr(housekeeping, role)
        if isinstance(ref, ChangeOverDiodes):
            refs.append(((*base, role, "negative"), ref.negative))
            refs.append(((*base, role, "positive"), ref.positive))
        elif ref is not None:
            refs.append(((*base, role, "part_id"), ref.part_id))
    return refs


def panel_issues(
    panel: Panel, source: YamlSource, library: Library, library_name: str
) -> list[Issue]:
    """Unknown parts, port-plan keys matching no device, and unknown grounding busbars."""
    issues: list[Issue] = []
    known_parts = set(library.part_ids())
    for index, device in enumerate(panel.devices):
        if device.part_id not in known_parts:
            loc = ("devices", index, "part_id")
            issues.append(_unknown_part(source, loc, device.part_id, library_name))
    keys = {device.part_id for device in panel.devices}
    keys |= {device.tag for device in panel.devices if device.tag is not None}
    for key in panel.port_plans:
        if key not in keys:
            message = f"no device in this panel has part_id or tag '{key}'"
            issues.append(_issue(source, ("port_plans", key), message))
    for index, busbar in enumerate(panel.options.grounding_busbars):
        if busbar not in library.catalogues.busbars:
            issues.append(_unknown_busbar(source, ("options", "grounding_busbars", index), busbar))
    return issues


def mirror_issues(mirror: PanelMirror, source: YamlSource, library: Library) -> list[Issue]:
    """Unknown grounding busbars named in the mirror file's own ``options``.

    A mirror inherits the busbars of the panel it mirrors, which ``panel_issues`` already
    checked there; only a list the mirror file sets itself is checked here.
    """
    busbars = mirror.options.get("grounding_busbars")
    if not isinstance(busbars, list):
        return []
    return [
        _unknown_busbar(source, ("options", "grounding_busbars", index), busbar)
        for index, busbar in enumerate(busbars)
        if isinstance(busbar, str) and busbar not in library.catalogues.busbars
    ]


def substation_issues(
    substation: Substation,
    source: YamlSource,
    panels: Sequence[tuple[Panel, YamlSource]],
    library: Library,
    library_name: str,
) -> list[Issue]:
    """Duplicate panel ids, tag prefixes and sheet names, and loose-material references."""
    issues: list[Issue] = []
    sheets: dict[str, str] = {}
    for key, name in substation.output.sheet_names.model_dump().items():
        if name.casefold() in sheets:
            message = f"duplicate sheet name '{name}' (also used by {sheets[name.casefold()]})"
            issues.append(_issue(source, ("output", "sheet_names", key), message))
        else:
            sheets[name.casefold()] = f"output.sheet_names.{key}"
    ids: dict[str, str] = {}
    prefixes: dict[str, str] = {}
    for panel, panel_source in panels:
        if panel.id in ids:
            message = f"duplicate panel id '{panel.id}' (first in {ids[panel.id]})"
            issues.append(_issue(panel_source, ("id",), message))
        else:
            ids[panel.id] = panel_source.path.name
        if panel.tag_prefix in prefixes:
            owner = prefixes[panel.tag_prefix]
            message = f"duplicate tag_prefix '{panel.tag_prefix}' (first used by panel '{owner}')"
            issues.append(_issue(panel_source, ("tag_prefix",), message))
        else:
            prefixes[panel.tag_prefix] = panel.id
        sheet = panel.sheet_name.casefold()
        if sheet in sheets:
            message = f"duplicate sheet name '{panel.sheet_name}' (also used by {sheets[sheet]})"
            issues.append(_issue(panel_source, ("sheet_name",), message))
        else:
            sheets[sheet] = f"panel '{panel.id}'"

    loose = substation.loose_material
    if loose is not None:
        known_parts = set(library.part_ids())
        if loose.host_panel not in ids:
            message = f"host_panel '{loose.host_panel}' is not a panel id in this substation"
            issues.append(_issue(source, ("loose_material", "host_panel"), message))
        for index, item in enumerate(loose.items):
            base: Loc = ("loose_material", "items", index)
            if item.part_id is not None and item.part_id not in known_parts:
                issues.append(_unknown_part(source, (*base, "part_id"), item.part_id, library_name))
            for k, child in enumerate(item.children):
                if child not in known_parts:
                    issues.append(
                        _unknown_part(source, (*base, "children", k), child, library_name)
                    )
            if item.fed_from is not None and item.fed_from not in ids:
                message = f"fed_from '{item.fed_from}' is not a panel id in this substation"
                issues.append(_issue(source, (*base, "fed_from"), message))
    return issues


def project_issues(
    project: Project, source: YamlSource, substations: Sequence[tuple[Substation, YamlSource]]
) -> list[Issue]:
    """Duplicate substation ids, and register entries naming a substation not listed."""
    issues: list[Issue] = []
    first: dict[str, str] = {}
    for substation, sub_source in substations:
        sub_id = substation.substation.id
        if sub_id in first:
            message = f"duplicate substation id '{sub_id}' (first in {first[sub_id]})"
            issues.append(_issue(sub_source, ("substation", "id"), message))
        else:
            first[sub_id] = sub_source.path.as_posix()
    for index, entry in enumerate(project.documents):
        if entry.substation not in first:
            message = f"substation '{entry.substation}' is not listed in substations"
            issues.append(_issue(source, ("documents", index, "substation"), message))
    return issues


def _document_issue(
    source: YamlSource, loc: Loc, key: str, sub_id: str, register: Mapping[str, RegisterEntry]
) -> Issue | None:
    entry = register.get(key)
    if entry is None:
        return _issue(source, loc, f"unknown document key '{key}' (not in the project's documents)")
    if entry.substation != sub_id:
        message = f"document '{key}' belongs to substation '{entry.substation}', not '{sub_id}'"
        return _issue(source, loc, message)
    return None


def document_issues(
    substation: Substation,
    source: YamlSource,
    panels: Sequence[tuple[YamlSource, Panel | PanelMirror]],
    register: Mapping[str, RegisterEntry],
) -> list[Issue]:
    """Every document key a substation and its panels name must be one of its own."""
    sub_id = substation.substation.id
    refs: list[tuple[YamlSource, Loc, str]] = [(source, ("document",), substation.document)]
    for sheet, calc in substation.calculations:
        refs.append((source, ("calculations", sheet, "document"), calc.document))
    if substation.generated_panels is not None:
        refs.append(
            (source, ("generated_panels", "document"), substation.generated_panels.document)
        )
    refs.extend((panel_source, ("document",), panel.document) for panel_source, panel in panels)
    found = (_document_issue(src, loc, key, sub_id, register) for src, loc, key in refs)
    return [issue for issue in found if issue is not None]


def equipment_issues(
    substation: Substation, source: YamlSource, library: Library, library_name: str
) -> list[Issue]:
    """Equipment parts exist, have a rack height, and the switch roles are switches."""
    issues: list[Issue] = []
    for index, item in enumerate(substation.equipment):
        if item.part_id is None:
            if not any(_is_l1_switch(d) and d.height_u is not None for d in library.devices):
                message = (
                    f"no L1 network_switch with height_u in {library_name} for the tool "
                    "to pick; add one or set part_id"
                )
                issues.append(_issue(source, ("equipment", index), message))
            continue
        loc: Loc = ("equipment", index, "part_id")
        device = library.get(item.part_id)
        if device is None:
            issues.append(_unknown_part(source, loc, item.part_id, library_name))
            continue
        if device.height_u is None:
            message = f"height_u is needed for the panel layout ('{item.part_id}' has none)"
            issues.append(_issue(source, loc, message))
        switch_roles = (EquipmentRole.L1_SWITCH, EquipmentRole.L2_SWITCH)
        if item.role in switch_roles and device.category is not Category.NETWORK_SWITCH:
            message = f"an {item.role.value} must be a network_switch part, not {device.category}"
            issues.append(_issue(source, loc, message))
        elif item.role is EquipmentRole.L1_SWITCH and not _is_l1_switch(device):
            level = device.purdue_level or "no purdue_level"
            message = (
                f"a pinned l1_switch must be an L1 network_switch part ({item.part_id} is {level})"
            )
            issues.append(_issue(source, loc, message))
    return issues


def layout_issues(substation: Substation, source: YamlSource) -> list[Issue]:
    """Equipment ids are unique, and layout overrides and removals name them correctly."""
    issues: list[Issue] = []
    by_id: dict[str, tuple[int, Equipment]] = {}
    for index, item in enumerate(substation.equipment):
        if item.id in by_id:
            message = (
                f"duplicate equipment id '{item.id}' (first at equipment[{by_id[item.id][0]}])"
            )
            issues.append(_issue(source, ("equipment", index, "id"), message))
        else:
            by_id[item.id] = (index, item)
    entries = {name: item for name, (_index, item) in by_id.items()}
    for index, move in enumerate(substation.layout.overrides):
        base: Loc = ("layout", "overrides", index)
        if isinstance(move, PairMove):
            entry = entries.get(move.pair)
            if entry is None:
                issues.append(_issue(source, (*base, "pair"), f"no equipment id '{move.pair}'"))
            elif not entry.redundant:
                message = f"'{move.pair}' is not redundant, so it has no pair"
                issues.append(_issue(source, (*base, "pair"), message))
            else:
                issues.extend(_unit_issues(source, base, entry, move.unit))
        else:
            issues.extend(_unit_ref_issues(source, base, entries, move, side_required=True))
    for index, ref in enumerate(substation.layout.removed):
        base = ("layout", "removed", index)
        issues.extend(_unit_ref_issues(source, base, entries, ref, side_required=False))
    return issues


def _unit_ref_issues(
    source: YamlSource,
    base: Loc,
    entries: Mapping[str, Equipment],
    ref: UnitRef,
    *,
    side_required: bool,
) -> list[Issue]:
    entry = entries.get(ref.device)
    if entry is None:
        return [_issue(source, (*base, "device"), f"no equipment id '{ref.device}'")]
    if entry.redundant and ref.side is None and side_required:
        message = f"'{ref.device}' is redundant; name the side (a or b) to move"
        return [_issue(source, (*base, "side"), message)]
    if not entry.redundant and ref.side is not None:
        message = f"'{ref.device}' is not redundant; leave side out"
        return [_issue(source, (*base, "side"), message)]
    return _unit_issues(source, base, entry, ref.unit)


def _unit_issues(source: YamlSource, base: Loc, entry: Equipment, unit: int | None) -> list[Issue]:
    # The L1 switch count is computed from the IED count, so its units are not known here.
    if unit is None or entry.role is EquipmentRole.L1_SWITCH or unit <= entry.qty:
        return []
    message = f"'{entry.id}' has qty {entry.qty}; there is no unit {unit}"
    return [_issue(source, (*base, "unit"), message)]


def _is_l1_switch(device: DeviceType) -> bool:
    return device.category is Category.NETWORK_SWITCH and device.purdue_level is PurdueLevel.L1
