"""Cross-record checks that single-file validation cannot do: duplicate and dangling
references within the library, a panel, and the project as a whole.

Each function returns located issues; none raises.
"""

from __future__ import annotations

from collections.abc import Sequence

from bomgen.io.errors import Issue, Loc, format_location
from bomgen.io.yaml_source import YamlSource
from bomgen.models.library import ChangeOverDiodes, Housekeeping, Library
from bomgen.models.panel import Panel, PanelMirror
from bomgen.models.project import Project


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
    for role_loc, part_id in _housekeeping_refs(library.catalogues.housekeeping):
        if part_id not in first_at:
            issues.append(_unknown_part(source, role_loc, part_id, name))
    return issues


def _housekeeping_refs(housekeeping: Housekeeping) -> list[tuple[Loc, str]]:
    base = ("catalogues", "housekeeping")
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


def project_issues(
    project: Project,
    source: YamlSource,
    panels: Sequence[tuple[Panel, YamlSource]],
    library: Library,
    library_name: str,
) -> list[Issue]:
    """Duplicate panel ids, tag prefixes and sheet names, and loose-material references."""
    issues: list[Issue] = []
    sheets: dict[str, str] = {}
    for key, name in project.output.sheet_names.model_dump().items():
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

    loose = project.loose_material
    if loose is not None:
        known_parts = set(library.part_ids())
        if loose.host_panel not in ids:
            message = f"host_panel '{loose.host_panel}' is not a panel id in this project"
            issues.append(_issue(source, ("loose_material", "host_panel"), message))
        for index, item in enumerate(loose.items):
            base: Loc = ("loose_material", "items", index)
            if item.part_id not in known_parts:
                issues.append(_unknown_part(source, (*base, "part_id"), item.part_id, library_name))
            for k, child in enumerate(item.children):
                if child not in known_parts:
                    issues.append(
                        _unknown_part(source, (*base, "children", k), child, library_name)
                    )
            if item.fed_from is not None and item.fed_from not in ids:
                message = f"fed_from '{item.fed_from}' is not a panel id in this project"
                issues.append(_issue(source, (*base, "fed_from"), message))
    return issues
