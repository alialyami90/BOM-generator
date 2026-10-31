"""The Device preview: the layout, the in-memory build and its checks, per unit (M24).

Nothing is written: the screen calls this with the candidate layout overrides it is
about to save, as the Panels board calls ``layout_preview``.
"""

from dataclasses import replace

from bomgen.checks import check_report
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import LayoutRules, PanelFill, Unit, layout_preview, runs, waist_u
from bomgen.engine.pipeline import build
from bomgen.engine.terminals import unit_strips
from bomgen.engine.units import DeviceRow, expand_devices
from bomgen.io.loader import LoadedSubstation
from bomgen.models.calc import BranchMcb
from bomgen.models.library import DeviceType, SupplyType
from bomgen.models.panel import Panel
from bomgen.models.preview import (
    DevicePreview,
    PreviewIssue,
    PreviewMcb,
    PreviewPanel,
    PreviewUnit,
)
from bomgen.models.report import CheckStatus
from bomgen.models.substation import Equipment, PartOverrides, Side
from bomgen.models.substation import Layout as LayoutInputs


def device_preview(
    loaded: LoadedSubstation, overrides: LayoutInputs | None = None
) -> DevicePreview:
    """Every generated unit with its panel, top U, MCBs and strips, and the issues.

    ``overrides`` replaces the file's layout inputs. An ``EngineError`` becomes one error
    issue with no panels.
    """
    try:
        panels, issues = _preview(loaded, overrides)
    except EngineError as error:
        panels, issues = [], [PreviewIssue(severity="error", kind="engine", message=str(error))]
    heights = loaded.project.defaults.layout
    return DevicePreview(
        waist_u=waist_u(heights),
        waist_height_mm=heights.waist_height_mm,
        rack_start_mm=heights.rack_start_mm,
        capacity_u=loaded.panel_capacity_u,
        enclosure_u=loaded.library.catalogues.enclosure_u,
        panels=tuple(panels),
        issues=tuple(issues),
    )


def _preview(
    loaded: LoadedSubstation, overrides: LayoutInputs | None
) -> tuple[list[PreviewPanel], list[PreviewIssue]]:
    layout = layout_preview(loaded, overrides)
    manual = [p for p in loaded.panels if p.id in loaded.manual_panel_ids]
    target = replace(loaded, panels=(*layout.panels, *manual))
    result = build(target)
    fills = [f for f in layout.fills if f.units]
    numbers = {p.id: f.number for p, f in zip(layout.panels, fills, strict=True)}
    issues = [
        PreviewIssue(
            severity="error" if x.is_error else "warning",
            kind=x.kind,
            message=x.message,
            subject=x.subject,
            device=x.subject.split("#")[0] if "#" in x.subject else None,
            panel=_panel_number(x.subject),
        )
        for x in layout.report.issues
    ]
    panels = []
    for panel, fill in zip(layout.panels, fills, strict=True):
        units = _units(target, panel, fill, layout.rules, result.branch_mcbs)
        issues += [
            _away_issue(x, fill.number, layout.rules) for x in units.values() if x.away_from_waist
        ]
        placement = fill.placement(layout.rules)
        frame = panel.enclosure.base_frame
        panels.append(
            PreviewPanel(
                panel_id=panel.id,
                name=panel.cabinet_name,
                number=fill.number,
                side="a" if panel.lan == "A" else "b" if panel.lan == "B" else None,
                used_u=placement.used_u,
                overflow_u=placement.overflow_u,
                base_frame_mm=frame.h_mm if frame is not None else None,
                units=tuple(_ordered(units, fill, layout.rules)),
            )
        )
    for item in check_report(target, result).items:
        if item.status is CheckStatus.PASS:
            continue
        issues.append(
            PreviewIssue(
                severity="error" if item.status is CheckStatus.FAIL else "warning",
                kind=item.check,
                message=item.message,
                subject=item.subject,
                panel=numbers.get(item.panel_id or ""),
            )
        )
    return panels, issues


def _panel_number(subject: str) -> int | None:
    word, _, number = subject.partition(" ")
    return int(number) if word == "panel" and number.isdigit() else None


def _units(
    loaded: LoadedSubstation,
    panel: Panel,
    fill: PanelFill,
    rules: LayoutRules,
    mcbs: tuple[BranchMcb, ...],
) -> dict[Unit, PreviewUnit]:
    entries = {e.id: e for e in loaded.substation.equipment}
    tops = fill.placement(rules).tops
    rows = expand_devices(panel, loaded.library)
    feeds: dict[tuple[str | None, int | None], BranchMcb] = {
        (m.unit_tag, m.feed): m for m in mcbs if m.panel_id == panel.id
    }
    units: dict[Unit, PreviewUnit] = {}
    for row, run in zip(rows, runs(fill), strict=True):
        for index, unit in enumerate(run):
            units[unit] = _unit(
                loaded, entries[unit.device], unit, row, index, fill, rules, tops, feeds
            )
    return units


def _unit(
    loaded: LoadedSubstation,
    entry: Equipment,
    unit: Unit,
    row: DeviceRow,
    index: int,
    fill: PanelFill,
    rules: LayoutRules,
    tops: dict[Unit, int],
    feeds: dict[tuple[str | None, int | None], BranchMcb],
) -> PreviewUnit:
    device = row.device
    tag = row.unit_tags[index]
    top = tops.get(unit)
    pinned_place = fill.pins.get(unit) is not None or unit in fill.fixed
    away = (
        unit.waist
        and pinned_place
        and top is not None
        and rules.waist_u is not None
        and top - unit.block_u + 1 != rules.waist_u
    )
    set_fields = entry.overrides.model_fields_set if entry.overrides is not None else set()
    return PreviewUnit(
        device=unit.device,
        role=entry.role.value,
        tag=tag,
        part_id=unit.part_id,
        library_part_id=device.derived_from or unit.part_id,
        n=unit.n,
        side=None if unit.side is Side.NONE else unit.side.value,
        bom_code=device.ordering_code,
        has_part_number=device.ordering_code is not None,
        overridden=tuple(name for name in PartOverrides.model_fields if name in set_fields),
        placed=unit.block_u == 0 or top is not None,
        din_rail=unit.block_u == 0,
        pinned=fill.is_pinned(unit),
        waist=unit.waist,
        away_from_waist=away,
        top_u=top,
        height_u=unit.height_u,
        cable_manager_u=unit.cable_manager_u,
        watts=device.unit_power_w,
        supply=_supply(device, loaded),
        ps1=_mcb(feeds.get((tag, 1)) or feeds.get((tag, None))),
        ps2=_mcb(feeds.get((tag, 2))),
        strips=unit_strips(row, loaded.library, index),
    )


def _supply(device: DeviceType, loaded: LoadedSubstation) -> str | None:
    if device.supply_type is None:
        return None
    constants = loaded.constants
    system = (
        constants.dc_voltage_v if device.supply_type is SupplyType.VDC else constants.ac_voltage_v
    )
    return f"{device.voltage_v or round(system)} {device.supply_type.value}"


def _mcb(record: BranchMcb | None) -> PreviewMcb | None:
    if record is None:
        return None
    return PreviewMcb(
        tag=record.tag, rating_a=record.rating_a, at_minimum=record.rating_a == record.floor_a
    )


def _ordered(
    units: dict[Unit, PreviewUnit], fill: PanelFill, rules: LayoutRules
) -> list[PreviewUnit]:
    """Placed rack units in stack order, then the unplaced, then DIN rail."""
    stack = fill.stack()
    placed = [units[x] for x in stack if x.block_u > 0 and units[x].top_u is not None]
    unplaced = [units[x] for x in fill.placement(rules).unplaced]
    din = [units[x] for x in stack if x.block_u == 0]
    return [*placed, *unplaced, *din]


def _away_issue(unit: PreviewUnit, number: int, rules: LayoutRules) -> PreviewIssue:
    label = f"{unit.device}#{unit.n}" + (f"/{unit.side}" if unit.side else "")
    return PreviewIssue(
        severity="warning",
        kind="pinned-away-from-waist",
        message=f"{label} is pinned at U{unit.top_u}, away from waist height (U{rules.waist_u})",
        subject=label,
        device=unit.device,
        panel=number,
    )
