"""Group F: DC distribution (spec: Derivation rules -> DC distribution (group F);
Data model and generation order, step 7)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from bomgen.engine.errors import EngineError
from bomgen.engine.items import BomItem
from bomgen.engine.mcb import (
    alarms_wired,
    aux_contact_line,
    mcb_line,
    rating_at_least,
)
from bomgen.engine.tags import without_prefix
from bomgen.engine.units import DeviceRow, lookup
from bomgen.models.bom import BomLine, Group
from bomgen.models.calc import BranchCondition, BranchMcb, BranchSizing
from bomgen.models.library import DeviceType, Library, McbCatalogue, SupplyType
from bomgen.models.panel import Panel
from bomgen.models.project import DesignConstants, LooseExtra

FEEDS: tuple[Literal[1, 2], ...] = (1, 2)
QCOD_SPARES = 1  # "QCOD-2 spare"


@dataclass(frozen=True)
class FedLoad:
    """A single-fed DC load on the change-over diodes, named in its QCOD description."""

    name: str
    device: DeviceType
    unit_tag: str | None = None  # a panel unit's tag; None for a loose item


@dataclass(frozen=True)
class DcCircuits:
    items: list[BomItem]
    branches_per_feed: int  # used + spare, for the X4-DC1/X4-DC2 strips
    qcods: int
    design_current_a: float  # ΣQ per feed
    main_a: int
    rule_main_a: int  # the rating without main_mcb_override_a
    branch_mcbs: list[BranchMcb]


@dataclass(frozen=True)
class _Branch:
    load: str
    rating: int
    alarmed: bool
    sizing: BranchSizing | None  # None for a spare
    unit_tag: str | None = None


def single_fed_loads(
    panel: Panel, rows: Sequence[DeviceRow], library: Library, loose: Sequence[LooseExtra]
) -> list[FedLoad]:
    """Group B units with one supply, then loose items fed from this panel."""
    units = [(row.device, tag) for row in rows for tag in row.unit_tags]
    units += [
        (lookup(library, item.part_id), None)
        for item in loose
        if item.part_id is not None and item.fed_from == panel.id
    ]
    return [FedLoad(_load_name(d), d, tag) for d, tag in units if d.power_supplies == 1]


def _load_name(device: DeviceType) -> str:
    return device.category.value.replace("_", " ").title()


def unit_current(device: DeviceType, constants: DesignConstants) -> float:
    """Design current of one unit with margin: current factor x W / V (column O)."""
    voltage = device.voltage_v or constants.dc_voltage_v
    return constants.current_factor * (device.unit_power_w or 0) / voltage


def branch_sizing(device: DeviceType, library: Library, constants: DesignConstants) -> BranchSizing:
    """The smallest catalogue MCB that carries the running current with margin, whose
    magnetic trip clears an inrush lasting at least ``inrush_min_ms``, and that is at
    least the floor (plan Q35, ADR 0019)."""
    mcb = library.catalogues.dc_mcb
    running = unit_current(device, constants)
    multiple = _trip_multiple(mcb, device) if device.inrush_a else None
    counted = device.inrush_ms is None or device.inrush_ms >= constants.inrush_min_ms
    inrush_need = None
    if device.inrush_a and multiple and counted:
        inrush_need = device.inrush_a / multiple
    floor = constants.min_branch_mcb_a
    needs: dict[BranchCondition, float | None] = {
        "running": running,
        "inrush": inrush_need,
        "floor": floor,
    }
    rating = rating_at_least(mcb, max(n for n in needs.values() if n is not None))
    set_by = tuple(
        name
        for name, need in needs.items()
        if need is not None and rating_at_least(mcb, need) == rating
    )
    return BranchSizing(
        rating_a=rating,
        running_a=running,
        inrush_a=device.inrush_a,
        inrush_ms=device.inrush_ms,
        inrush_counted=counted,
        trip_multiple=multiple,
        inrush_need_a=inrush_need,
        floor_a=floor,
        set_by=set_by,
        library_min_a=device.min_branch_mcb_a,
    )


def _trip_multiple(mcb: McbCatalogue, device: DeviceType) -> float | None:
    """The set's magnetic trip multiple for the device's supply: the DC value for a DC
    load when the set gives one, otherwise the AC value or its curve's lower bound."""
    if device.supply_type is SupplyType.VDC and mcb.magnetic_trip_multiple_dc is not None:
        return mcb.magnetic_trip_multiple_dc
    return mcb.magnetic_multiple


def dc_distribution(
    panel: Panel,
    library: Library,
    constants: DesignConstants,
    rows: Sequence[DeviceRow],
    fed: Sequence[FedLoad],
    change_over: bool,
) -> DcCircuits:
    """Q1 + Q1.n + spares, Q2 + Q2.n + spares, QCOD circuits, aux contacts."""
    if fed and not change_over:
        names = ", ".join(load.name for load in fed)
        raise EngineError(f"{panel.id}: single-fed loads ({names}) need change-over diodes")
    branches: list[_Branch] = []
    current = 0.0
    for row in rows:
        # ΣQ is the cabinet's own DC loads, its Power Consumption block; loose loads fed
        # from it are "External Equipment" (spec: Power Consumption sheet).
        if row.device.power_supplies:
            current += unit_current(row.device, constants) * row.instance.qty
        if row.device.power_supplies != 2:
            continue
        sizing = branch_sizing(row.device, library, constants)
        for unit_tag in row.unit_tags:
            name = _unit_name(unit_tag, row.device, panel.tag_prefix)
            alarm = row.device.alarm_on_branch_mcb
            branches.append(_Branch(name, sizing.rating_a, alarm, sizing, unit_tag))
    if not branches and not fed:
        return DcCircuits([], 0, 0, 0.0, 0, 0, [])

    mcb = library.catalogues.dc_mcb
    floor_a = rating_at_least(mcb, constants.min_branch_mcb_a)
    spare_a = max((b.rating for b in branches), default=floor_a)
    branches += [_Branch("SPARE", spare_a, False, None)] * panel.options.dc_spare_branches_per_feed
    rule_main_a = rating_at_least(mcb, max(current, constants.min_main_mcb_a))
    main_a = panel.options.main_mcb_override_a or rule_main_a

    prefix = panel.tag_prefix
    lines: list[BomLine] = []
    sized: list[BranchMcb] = []

    def branch_line(tag: str, branch: _Branch, load: str, feed: Literal[1, 2] | None) -> None:
        lines.append(mcb_line(mcb, Group.F, tag, branch.rating, load))
        if branch.sizing is not None:
            fields = branch.sizing.model_dump()
            unit = branch.unit_tag
            sized.append(
                BranchMcb(panel_id=panel.id, tag=tag, load=load, unit_tag=unit, feed=feed, **fields)
            )

    for feed in FEEDS:
        lines.append(mcb_line(mcb, Group.F, f"{prefix}-Q{feed}", main_a, f"Main DC supply-{feed}"))
        for n, branch in enumerate(branches, start=1):
            load = branch.load if branch.load == "SPARE" else f"{branch.load} PS{feed}"
            branch_line(f"{prefix}-Q{feed}.{n}", branch, load, feed)

    qcod: list[_Branch] = []
    for single in fed:
        sizing = branch_sizing(single.device, library, constants)
        qcod.append(_Branch(single.name, sizing.rating_a, False, sizing, single.unit_tag))
    if qcod:
        qcod += [_Branch("SPARE", max(b.rating for b in qcod), False, None)] * QCOD_SPARES
    for n, branch in enumerate(qcod, start=1):
        branch_line(f"{prefix}-QCOD-{n}", branch, branch.load, None)

    alarmed = [f"Q{feed}" for feed in FEEDS]
    alarmed += [f"Q{f}.{n}" for n, b in enumerate(branches, 1) if b.alarmed for f in FEEDS]
    description = f"DC Auxiliary Contacts (For MCB {', '.join(alarmed)})"
    hwio = len(FEEDS) if alarms_wired(panel) else 0  # mains only (Columns of a panel BOM, HWIO)
    lines.append(aux_contact_line(library, Group.F, description, len(alarmed), hwio))
    return DcCircuits(
        items=[BomItem(line) for line in lines],
        branches_per_feed=len(branches),
        qcods=len(qcod),
        design_current_a=current,
        main_a=main_a,
        rule_main_a=rule_main_a,
        branch_mcbs=sized,
    )


def _unit_name(unit_tag: str | None, device: DeviceType, prefix: str) -> str:
    """The load as named inside MCB descriptions: no panel prefix, underscores."""
    if unit_tag is None:
        return device.model or device.part_id
    return without_prefix(unit_tag, prefix).replace("-", "_")
