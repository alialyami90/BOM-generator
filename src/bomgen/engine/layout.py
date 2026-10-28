"""Automatic panel layout (ADR 0013, rules R5-R9).

``fill`` places units into panels of ``capacity_u``: redundant units in lock-step A
(odd panels) and B (even panels) streams, then common units into the panel with the
most free U. ``auto_layout`` drops removed units first and applies the engineer's moves
after. Units are named by equipment id and unit number, never by tag.
"""

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

import yaml

from bomgen.engine.sizing import (
    L1Candidate,
    L2Link,
    NetworkInputs,
    NetworkPlan,
    l1_links,
    l1_reserved_ports,
    l2_port_plan,
    pick_l1_switch,
    rank_l1_switches,
    size_network,
    switch_ports,
)
from bomgen.engine.tags import first_number
from bomgen.io.loader import LoadedSubstation
from bomgen.models.library import Category, Media, PortSpeed, PurdueLevel
from bomgen.models.panel import (
    DeviceInstance,
    Lan,
    Panel,
    PanelOptions,
    PortAllocation,
    PortPlan,
)
from bomgen.models.substation import DeviceMove, Equipment, EquipmentRole, PairMove, Side, UnitRef
from bomgen.models.substation import Layout as LayoutInputs

IssueKind = Literal[
    "device-too-tall",
    "move-does-not-fit",
    "stale-override",
    "stale-removal",
    "unknown-panel",
    "panel-empty",
    "missing-height",
    "missing-panel",
    "port-capacity",
    "replaced-panel",
]
WARNING_KINDS: frozenset[IssueKind] = frozenset(
    {"stale-override", "stale-removal", "replaced-panel"}
)


@dataclass(frozen=True)
class Unit:
    """One placeable unit of an equipment entry; ``(key, side)`` identifies it."""

    device: str  # equipment id
    n: int  # unit number, 1-based
    side: Side
    part_id: str
    rank: int  # the entry's position in BOM group order
    height_u: int
    cable_manager_u: int = 0  # a 1U manager directly under a rack switch or patch panel

    @property
    def key(self) -> str:
        return f"{self.device}#{self.n}"

    @property
    def block_u(self) -> int:
        return self.height_u + self.cable_manager_u


@dataclass(frozen=True)
class LayoutRules:
    capacity_u: int = 32
    blank_plate_u: int = 1


@dataclass(frozen=True)
class LayoutIssue:
    kind: IssueKind
    subject: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.kind not in WARNING_KINDS


def blank_plates(units: Iterable[Unit]) -> int:
    """Blank plates in a stack, top to bottom (R5).

    A plate goes between two rack neighbours only when the upper block ends in its
    active device; a block that ends in its cable manager, a passive plate, may touch
    the device below it (Ali, 2026-10-28, backlog point 8).
    """
    rack = [x for x in units if x.block_u > 0]
    return sum(1 for upper in rack[:-1] if upper.cable_manager_u == 0)


def used_u(units: Iterable[Unit], blank_plate_u: int) -> int:
    """Rack units used: every block plus the blank plates between them (R5)."""
    stack = list(units)
    return sum(x.block_u for x in stack) + blank_plates(stack) * blank_plate_u


def _order(unit: Unit) -> tuple[int, str, int]:
    return (unit.rank, unit.device, unit.n)


@dataclass
class PanelFill:
    number: int
    units: list[Unit] = field(default_factory=list)
    pins: dict[Unit, int | None] = field(default_factory=dict)  # pinned units, position (R7)

    def stack(self) -> list[Unit]:
        """The units top to bottom: group order, with positioned pins at their place."""
        placed = {x: p for x, p in self.pins.items() if p is not None and x.block_u > 0}
        order = [x for x in sorted(self.units, key=_order) if x not in placed]
        taken: dict[int, int] = {}
        for unit in sorted(placed, key=lambda x: (placed[x], _order(x))):
            position = placed[unit] + taken.get(placed[unit], 0)
            taken[placed[unit]] = taken.get(placed[unit], 0) + 1
            rack = [i for i, x in enumerate(order) if x.block_u > 0]
            order.insert(rack[position - 1] if position <= len(rack) else len(order), unit)
        return order

    def used_u(self, rules: LayoutRules) -> int:
        return used_u(self.stack(), rules.blank_plate_u)

    def free_u(self, rules: LayoutRules) -> int:
        return rules.capacity_u - self.used_u(rules)

    def blank_plates(self) -> int:
        return blank_plates(self.stack())

    def din_rail_count(self) -> int:
        return sum(1 for x in self.units if x.block_u == 0)

    def fits(self, unit: Unit, rules: LayoutRules) -> bool:
        trial = PanelFill(self.number, [*self.units, unit], dict(self.pins))
        return trial.used_u(rules) <= rules.capacity_u

    def add(self, unit: Unit) -> None:
        self.units.append(unit)
        self.units.sort(key=_order)

    def is_pinned(self, unit: Unit) -> bool:
        """A layout override placed this unit here, even where the fill would have."""
        return unit in self.pins

    def position(self, unit: Unit) -> int | None:
        """The unit's place among the panel's rack devices, 1 = top; None on DIN rail."""
        rack = [x for x in self.stack() if x.block_u > 0]
        return rack.index(unit) + 1 if unit in rack else None


@dataclass
class Layout:
    panels: list[PanelFill]
    issues: list[LayoutIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.is_error for issue in self.issues)


class _Builder:
    def __init__(self, rules: LayoutRules) -> None:
        self.rules = rules
        self.panels: list[PanelFill] = []
        self.issues: list[LayoutIssue] = []

    def open_pair(self) -> tuple[PanelFill, PanelFill]:
        count = len(self.panels)
        self.panels += [PanelFill(count + 1), PanelFill(count + 2)]
        return self.panels[-2], self.panels[-1]

    def panel(self, number: int) -> PanelFill | None:
        while len(self.panels) < number <= len(self.panels) + 2 and len(self.panels) % 2 == 0:
            self.open_pair()
        return self.panels[number - 1] if 1 <= number <= len(self.panels) else None

    def check_height(self, unit: Unit) -> bool:
        if unit.block_u <= self.rules.capacity_u:
            return True
        self.issues.append(
            LayoutIssue(
                "device-too-tall",
                f"{unit.key}/{unit.side.value}",
                f"{unit.part_id} needs {unit.block_u} U; a panel has {self.rules.capacity_u} U",
            )
        )
        return False

    def fill_streams(self, units: Sequence[Unit]) -> None:
        """A and B units in lock-step: a pair moves to new panels when either side is full."""
        sides: dict[str, dict[Side, Unit]] = {}
        for unit in sorted(units, key=_order):
            sides.setdefault(unit.key, {})[unit.side] = unit
        current: tuple[PanelFill, PanelFill] | None = None
        for halves in sides.values():
            tall = [not self.check_height(x) for x in halves.values()]
            fits = current is not None and all(
                current[0 if side is Side.A else 1].fits(x, self.rules)
                for side, x in halves.items()
            )
            if current is None or not fits or any(tall):
                current = self.open_pair()
            for side, x in halves.items():
                current[0 if side is Side.A else 1].add(x)

    def place_common(self, units: Sequence[Unit]) -> None:
        for unit in sorted(units, key=_order):
            tall = not self.check_height(unit)
            best = max(self.panels, key=lambda p: (p.free_u(self.rules), -p.number), default=None)
            if tall or best is None or not best.fits(unit, self.rules):
                best = self.open_pair()[0]
            best.add(unit)

    def move(
        self, units: Sequence[Unit], number: int, what: str, position: int | None = None
    ) -> None:
        target = self.panel(number)
        if target is None:
            self.issues.append(
                LayoutIssue(
                    "unknown-panel",
                    what,
                    f"cannot move {what} to panel {number}: there are {len(self.panels)} panels",
                )
            )
            return
        for unit in units:
            for panel in self.panels:
                if unit in panel.units:
                    panel.units.remove(unit)
                    panel.pins.pop(unit, None)
            target.add(unit)
            target.pins[unit] = position
        if target.used_u(self.rules) > self.rules.capacity_u:
            self.issues.append(
                LayoutIssue(
                    "move-does-not-fit",
                    f"panel {number}",
                    f"moving {what} fills panel {number} to {target.used_u(self.rules)} U "
                    f"of {self.rules.capacity_u} U",
                )
            )

    def finish(self) -> Layout:
        while self.panels and not self.panels[-1].units:
            self.panels.pop()
        for panel in self.panels:
            panel.units = panel.stack()
            if not panel.units:
                self.issues.append(
                    LayoutIssue(
                        "panel-empty",
                        f"panel {panel.number}",
                        f"panel {panel.number} has no devices left; move a device into it "
                        "or move the later panels' devices down",
                    )
                )
        return Layout(self.panels, self.issues)


def fill(units: Sequence[Unit], rules: LayoutRules) -> Layout:
    """The automatic fill (R5, R6)."""
    builder = _Builder(rules)
    builder.fill_streams([x for x in units if x.side is not Side.NONE])
    builder.place_common([x for x in units if x.side is Side.NONE])
    return builder.finish()


def _matches(unit: Unit, ref: UnitRef) -> bool:
    return (
        unit.device == ref.device
        and (ref.unit is None or unit.n == ref.unit)
        and (ref.side is None or unit.side.value == ref.side)
    )


def _describe(ref: UnitRef) -> str:
    unit = f"#{ref.unit}" if ref.unit is not None else ""
    side = f" side {ref.side.upper()}" if ref.side is not None else ""
    return f"{ref.device}{unit}{side}"


def auto_layout(
    units: Sequence[Unit],
    rules: LayoutRules,
    *,
    removed: Sequence[UnitRef] = (),
    moves: Sequence[DeviceMove | PairMove] = (),
) -> Layout:
    """Drop ``removed``, fill, then apply ``moves`` in order (R7).

    Every moved unit is pinned, also when the move names the panel the fill chose, so
    the pin holds when later changes would place it elsewhere. A move's ``position``
    puts the unit at that place among the panel's rack devices (1 = top, past the
    bottom = last); a later move of the same unit replaces it.

    A move to the next one or two panel numbers opens a new pair, as when a device is
    dragged onto the board's empty column; the unit keeps its own LAN letter there.
    """
    issues: list[LayoutIssue] = []
    kept = list(units)
    for ref in removed:
        matched = [x for x in kept if _matches(x, ref)]
        if not matched:
            issues.append(
                LayoutIssue(
                    "stale-removal",
                    _describe(ref),
                    f"layout.removed names {_describe(ref)}, which the substation no longer has",
                )
            )
        kept = [x for x in kept if x not in matched]
    builder = _Builder(rules)
    builder.issues = issues
    builder.fill_streams([x for x in kept if x.side is not Side.NONE])
    builder.place_common([x for x in kept if x.side is Side.NONE])
    for move in moves:
        if isinstance(move, PairMove):
            ref = UnitRef(device=move.pair, unit=move.unit)
            targets: list[tuple[str | None, int]] = [("a", move.panel[0]), ("b", move.panel[1])]
        else:
            ref = move
            targets = [(None, move.panel)]
        matched = [x for x in kept if _matches(x, ref)]
        if isinstance(move, PairMove) and all(x.side is Side.NONE for x in matched):
            matched = []  # not a redundant entry: it has no A/B pair to move
        if not matched:
            builder.issues.append(
                LayoutIssue(
                    "stale-override",
                    _describe(ref),
                    f"a layout override names {_describe(ref)}, which the substation has no "
                    f"{'pair of' if isinstance(move, PairMove) else 'unit'} for",
                )
            )
            continue
        for side, number in targets:
            group = [x for x in matched if side is None or x.side.value == side]
            if not group:
                continue
            what = _describe(ref) if side is None else f"{_describe(ref)} side {side.upper()}"
            builder.move(group, number, what, move.position)
    return builder.finish()


def fill_lines(layout: Layout, rules: LayoutRules) -> list[str]:
    """One check-report line per panel, blank plates included (R8)."""
    return [f"Panel {p.number}: {p.used_u(rules)} U / {rules.capacity_u} U" for p in layout.panels]


# --- The substation adapter: LoadedSubstation -> units -> generated Panel models -------

CABLE_MANAGED = frozenset({Category.NETWORK_SWITCH, Category.FIREWALL, Category.PATCH_PANEL})
_LAN: dict[Side, Lan | None] = {Side.A: "A", Side.B: "B", Side.NONE: None}
GENERATED_HEADER = (
    "# Generated by bomgen layout (ADR 0013). Change equipment, network or\n"
    "# layout.overrides in substation.yaml and run it again; edits here are overwritten.\n"
)


@dataclass
class LayoutReport:
    """The check-report lines of the layout step; the IED count appears only here (R4)."""

    ied_count: int
    port_lines: list[str]
    fill_lines: list[str]
    issues: list[LayoutIssue]

    @property
    def has_errors(self) -> bool:
        return any(issue.is_error for issue in self.issues)

    def problem_lines(self) -> list[str]:
        return [
            f"{'error' if i.is_error else 'warning'}: {i.subject}: {i.message}" for i in self.issues
        ]

    def lines(self) -> list[str]:
        return [
            f"IED count: {self.ied_count}",
            *self.port_lines,
            *self.fill_lines,
            *self.problem_lines(),
        ]


@dataclass
class LayoutResult:
    """Generated panels, the fill behind them, the sizing and the report."""

    panels: list[Panel]
    fills: list[PanelFill]
    plan: NetworkPlan
    l1_candidates: list[L1Candidate]
    report: LayoutReport
    rules: LayoutRules


def network_inputs(loaded: LoadedSubstation) -> NetworkInputs:
    network = loaded.substation.network
    return NetworkInputs(
        ied_count=network.ied_count,
        topology=network.topology,
        ring_max_switches=network.ring_max_switches,
        l1_uplinks_per_switch=network.l1_uplinks_per_switch,
        l1_interlink=network.l1_interlink,
        l3_uplinks_per_l2=network.l3_uplinks_per_l2,
        port_fraction=loaded.spares.port_fraction,
    )


def l1_candidates(loaded: LoadedSubstation) -> list[L1Candidate]:
    """Every library L1 switch with its count per side, best first (the Network tab)."""
    devices = [
        switch_ports(d)
        for d in loaded.library.devices
        if d.category is Category.NETWORK_SWITCH and d.purdue_level is PurdueLevel.L1
    ]
    return rank_l1_switches(devices, network_inputs(loaded))


def _role(loaded: LoadedSubstation, role: EquipmentRole) -> Equipment:
    return next(e for e in loaded.substation.equipment if e.role is role)


def _links(loaded: LoadedSubstation, side: Side) -> list[L2Link]:
    return [
        L2Link(e.id, e.l2_ports, e.l2_speed, e.l2_media)
        for e in loaded.substation.equipment
        if e.l2_ports and (e.redundant or e.side in (Side.NONE, side))
    ]


def _units(loaded: LoadedSubstation, plan: NetworkPlan, issues: list[LayoutIssue]) -> list[Unit]:
    devices = {d.part_id: d for d in loaded.library.devices}
    units: list[Unit] = []
    for rank, entry in enumerate(loaded.substation.equipment):
        part_id = _part_id(entry, plan)
        device = devices[part_id]
        if device.height_u is None:
            issues.append(
                LayoutIssue(
                    "missing-height",
                    entry.id,
                    f"{part_id} has no height_u in the library; placed as 0 U",
                )
            )
        height = device.height_u or 0
        manager = 1 if device.category in CABLE_MANAGED and height > 0 else 0
        count = {
            EquipmentRole.L1_SWITCH: plan.l1_per_side,
            EquipmentRole.L2_SWITCH: plan.l2_per_side,
        }.get(entry.role, entry.qty)
        sides = [Side.A, Side.B] if entry.redundant else [entry.side]
        units += [
            Unit(entry.id, n, side, part_id, rank, height, manager)
            for n in range(1, count + 1)
            for side in sides
        ]
    return units


def _part_id(entry: Equipment, plan: NetworkPlan) -> str:
    if entry.role is EquipmentRole.L1_SWITCH:
        return plan.l1_part_id
    if entry.role is EquipmentRole.L2_SWITCH:
        return plan.l2_part_id
    return str(entry.part_id)


@dataclass(frozen=True)
class _SidePorts:
    """One side's L2 demand from the units the layout keeps (R2, R7)."""

    links: list[L2Link]
    l1_switches: int
    l1_links: int

    @property
    def demand(self) -> int:
        return self.l1_links + sum(link.ports for link in self.links)


def _side_ports(
    loaded: LoadedSubstation, kept: Sequence[Unit], side: Side, net: NetworkInputs
) -> _SidePorts:
    counts: dict[str, int] = {}
    for unit in kept:
        if unit.side in (side, Side.NONE):
            counts[unit.device] = counts.get(unit.device, 0) + 1
    links = [
        L2Link(e.id, e.l2_ports, e.l2_speed, e.l2_media)  # per entry, as R2 counts them
        for e in loaded.substation.equipment
        if e.l2_ports and counts.get(e.id)
    ]
    l1 = sum(
        n for device, n in counts.items() if _entry(loaded, device).role is EquipmentRole.L1_SWITCH
    )
    return _SidePorts(links, l1, l1_links(l1, net))


def _entry(loaded: LoadedSubstation, device: str) -> Equipment:
    return next(e for e in loaded.substation.equipment if e.id == device)


def _removed(unit: Unit, removed: Sequence[UnitRef]) -> bool:
    return any(_matches(unit, ref) for ref in removed)


def _capacity_issues(
    plan: NetworkPlan, sides: dict[Side, _SidePorts], kept: Sequence[Unit], loaded: LoadedSubstation
) -> list[LayoutIssue]:
    issues = []
    for side, ports in sides.items():
        letter = side.value.upper()
        if ports.l1_switches * plan.l1_usable_ports < plan.ied_count:
            issues.append(
                LayoutIssue(
                    "port-capacity",
                    f"side {letter} L1",
                    f"{ports.l1_switches} L1 switches leave "
                    f"{ports.l1_switches * plan.l1_usable_ports} IED ports on side {letter}; "
                    "the IEDs need more (a removed L1 switch?)",
                )
            )
        l2 = sum(
            1
            for x in kept
            if x.side is side and _entry(loaded, x.device).role is EquipmentRole.L2_SWITCH
        )
        if l2 * plan.l2_usable_ports < ports.demand:
            issues.append(
                LayoutIssue(
                    "port-capacity",
                    f"side {letter} L2",
                    f"{ports.demand} L2 ports needed on side {letter}, "
                    f"{l2 * plan.l2_usable_ports} usable (a removed L2 switch?)",
                )
            )
    return issues


def _size(loaded: LoadedSubstation) -> tuple[NetworkPlan, NetworkInputs, list[L1Candidate]]:
    net = network_inputs(loaded)
    devices = {d.part_id: d for d in loaded.library.devices}
    candidates = l1_candidates(loaded)
    l1_entry = _role(loaded, EquipmentRole.L1_SWITCH)
    pinned: str | None = l1_entry.part_id
    if pinned is not None:
        l1 = switch_ports(devices[pinned])
    else:
        l1 = pick_l1_switch((c.ports for c in candidates), net)
    l2 = switch_ports(devices[str(_role(loaded, EquipmentRole.L2_SWITCH).part_id)])
    by_side = [_links(loaded, Side.A), _links(loaded, Side.B)]
    busiest = max(by_side, key=lambda links: sum(link.ports for link in links))
    return size_network(net, l1, l2, busiest), net, candidates


def _rows(panel: PanelFill, loaded: LoadedSubstation) -> list[DeviceInstance]:
    devices = {d.part_id: d for d in loaded.library.devices}
    entries = {e.id: e for e in loaded.substation.equipment}
    runs: list[list[Unit]] = []
    for unit in sorted(panel.units, key=lambda x: (x.rank, x.side.value, x.n)):
        last = runs[-1][-1] if runs else None
        if last and (last.device, last.side, last.n + 1) == (unit.device, unit.side, unit.n):
            runs[-1].append(unit)
        else:
            runs.append([unit])
    rows = []
    for run in runs:
        first = run[0]
        entry = entries[first.device]
        start = first_number(devices[first.part_id]) + first.n - 1 if first.n > 1 else None
        rows.append(
            DeviceInstance(
                part_id=first.part_id,
                qty=len(run),
                purpose=entry.purpose,
                lan=_LAN[first.side],
                hwio_points=entry.hwio_points,  # a row total, as on DeviceInstance
                first_nn=start,
            )
        )
    return rows


def _merge(allocations: Iterable[PortAllocation]) -> list[PortAllocation]:
    merged: dict[tuple[PortSpeed, Media | None], PortAllocation] = {}
    for a in allocations:
        key = (a.speed, a.media)
        if key in merged:
            old = merged[key]
            a = old.model_copy(update={"count": old.count + a.count, "spare": old.spare + a.spare})
        merged[key] = a
    return list(merged.values())


def _port_plans(
    panel: PanelFill,
    fills: Sequence[PanelFill],
    loaded: LoadedSubstation,
    plan: NetworkPlan,
    net: NetworkInputs,
    sides: dict[Side, _SidePorts],
) -> dict[str, PortPlan]:
    entries = {e.id: e for e in loaded.substation.equipment}
    plans: dict[str, list[PortPlan]] = {}
    l1_units = [x for x in panel.units if entries[x.device].role is EquipmentRole.L1_SWITCH]
    if l1_units:
        count = len(l1_units) * l1_reserved_ports(net)
        spare = loaded.spares.sfp_per_l1 * len({x.side for x in l1_units})
        uplink = PortAllocation(count=count, speed=PortSpeed.G1, media=Media.MM, spare=spare)
        plans.setdefault(plan.l1_part_id, []).append(PortPlan(uplinks=[uplink]))
    for side in (Side.A, Side.B):
        l2_units = [
            x
            for x in panel.units
            if entries[x.device].role is EquipmentRole.L2_SWITCH and x.side is side
        ]
        if not l2_units:
            continue
        side_plan = l2_port_plan(
            replace(plan, l1_links_per_side=sides[side].l1_links), net, sides[side].links
        )
        first_home = next(
            p for p in fills if any(x in p.units for x in _all_l2(fills, entries, side))
        )
        uplinks = [
            a.model_copy(update={"count": net.l3_uplinks_per_l2 * len(l2_units)})
            for a in side_plan.uplinks_l3
        ]
        downlinks = side_plan.downlinks if first_home is panel else []
        plans.setdefault(plan.l2_part_id, []).append(
            PortPlan(uplinks_l3=uplinks, downlinks=downlinks)
        )
    for unit in panel.units:
        extra = entries[unit.device].port_plan
        if extra is not None:
            plans.setdefault(unit.part_id, []).append(extra)
    return {
        part: PortPlan(
            uplinks_l3=_merge(a for p in parts for a in p.uplinks_l3),
            uplinks=_merge(a for p in parts for a in p.uplinks),
            downlinks=_merge(a for p in parts for a in p.downlinks),
            serial_ports=sum(p.serial_ports for p in parts),
        )
        for part, parts in plans.items()
    }


def _all_l2(fills: Sequence[PanelFill], entries: dict[str, Equipment], side: Side) -> list[Unit]:
    return [
        x
        for p in fills
        for x in p.units
        if entries[x.device].role is EquipmentRole.L2_SWITCH and x.side is side
    ]


def _panel(
    fill: PanelFill,
    fills: Sequence[PanelFill],
    loaded: LoadedSubstation,
    plan: NetworkPlan,
    net: NetworkInputs,
    sides: dict[Side, _SidePorts],
) -> Panel:
    spec = loaded.substation.generated_panels
    assert spec is not None  # the model requires it whenever equipment is listed
    n = fill.number
    options = spec.options | spec.options_by_panel.get(n, {})
    return Panel(
        id=spec.id.format(n=n),
        cabinet_number=spec.cabinet_number.format(n=n),
        cabinet_name=spec.cabinet_name.format(n=n),
        tag_prefix=spec.tag_prefix.format(n=n),
        lan="A" if n % 2 else "B",
        sheet_name=spec.sheet_name.format(n=n),
        kind=spec.kind,
        enclosure=spec.enclosure,
        devices=_rows(fill, loaded),
        port_plans=_port_plans(fill, fills, loaded, plan, net, sides),
        options=PanelOptions.model_validate(options),
        document=spec.document,
        generated=True,
    )


def layout_preview(loaded: LoadedSubstation, overrides: LayoutInputs | None = None) -> LayoutResult:
    """Size the network and lay out the panels (R1-R9); ``overrides`` replaces the file's.

    The UI's Panels board calls this with the dragged overrides before saving them.
    """
    inputs = overrides if overrides is not None else loaded.substation.layout
    rules = LayoutRules(capacity_u=loaded.panel_capacity_u, blank_plate_u=inputs.blank_plate_u)
    plan, net, candidates = _size(loaded)
    issues: list[LayoutIssue] = []
    units = _units(loaded, plan, issues)
    # Size the L2 switches and their port plans from the units the layout keeps (R7).
    kept = [x for x in units if not _removed(x, inputs.removed)]
    sides = {side: _side_ports(loaded, kept, side, net) for side in (Side.A, Side.B)}
    demand = max(s.demand for s in sides.values())
    kept_plan = replace(
        plan,
        l2_per_side=max(1, math.ceil(demand / plan.l2_usable_ports)),
        l2_demand_per_side=demand,
        l1_links_per_side=max(s.l1_links for s in sides.values()),
    )
    if kept_plan.l2_per_side != plan.l2_per_side:
        units = _units(loaded, kept_plan, [])
        kept = [x for x in units if not _removed(x, inputs.removed)]
    plan = kept_plan
    layout = auto_layout(units, rules, removed=inputs.removed, moves=inputs.overrides)
    panels = [_panel(f, layout.panels, loaded, plan, net, sides) for f in layout.panels if f.units]
    issues += _capacity_issues(plan, sides, kept, loaded)
    issues += _loose_material_issues(loaded, panels)
    report = LayoutReport(
        ied_count=plan.ied_count,
        port_lines=_port_lines(plan, net),
        fill_lines=fill_lines(layout, rules),
        issues=issues + layout.issues,
    )
    return LayoutResult(panels, layout.panels, plan, candidates, report, rules)


def _loose_material_issues(loaded: LoadedSubstation, panels: Sequence[Panel]) -> list[LayoutIssue]:
    """Loose material that names a panel the layout no longer writes."""
    loose = loaded.substation.loose_material
    if loose is None:
        return []
    known = {p.id for p in panels} | set(loaded.manual_panel_ids)
    named = [("loose_material.host_panel", loose.host_panel)]
    named += [
        (f"loose_material.items[{i}].fed_from", item.fed_from)
        for i, item in enumerate(loose.items)
        if item.fed_from is not None
    ]
    return [
        LayoutIssue(
            "missing-panel",
            where,
            f"{where} names panel '{panel}', which the layout does not write; "
            f"name one of {', '.join(sorted(known))}",
        )
        for where, panel in named
        if panel not in known
    ]


def layout_substation(loaded: LoadedSubstation) -> LayoutResult:
    """The layout from the substation file's own overrides (``bomgen layout``)."""
    return layout_preview(loaded)


def _port_lines(plan: NetworkPlan, net: NetworkInputs) -> list[str]:
    lines = [
        f"L1 switches: {plan.l1_per_side} per side of {plan.l1_part_id}, "
        f"{plan.l1_usable_ports} usable ports each "
        f"({l1_reserved_ports(net)} reserved, {net.port_fraction:.0%} spare)",
        f"L2 switches: {plan.l2_per_side} per side of {plan.l2_part_id}, "
        f"{plan.l2_demand_per_side} of {plan.l2_per_side * plan.l2_usable_ports} usable ports "
        f"used per side",
    ]
    if plan.rings_per_side:
        lines.append(f"L1 rings: {plan.rings_per_side} per side")
    return lines


def render_panel_yaml(panel: Panel) -> str:
    """The generated ``panels/<id>.yaml`` text."""
    data = panel.model_dump(mode="json", exclude_defaults=True)
    data["generated"] = True
    return GENERATED_HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def with_layout(loaded: LoadedSubstation) -> tuple[LoadedSubstation, LayoutReport | None]:
    """The substation with its generated panels re-laid out, for ``bomgen build``.

    The layout replaces the ``panels`` list only once it owns it: when at least one of
    those files was written by ``bomgen layout`` (``generated: true``). Hand-written
    panels, such as the spec example's, are built as they are; manual panels always.
    """
    listed = [p for p in loaded.panels if p.id not in loaded.manual_panel_ids]
    if not loaded.substation.equipment or not any(p.generated for p in listed):
        return loaded, None
    result = layout_substation(loaded)
    result.report.issues += [
        LayoutIssue(
            "replaced-panel",
            p.id,
            f"{loaded.panel_files[p.id]} is hand-written but listed in panels, which the "
            "layout writes; move it to manual_panels to keep it, or remove it from panels",
        )
        for p in listed
        if not p.generated
    ]
    manual = [p for p in loaded.panels if p.id in loaded.manual_panel_ids]
    return replace(loaded, panels=(*result.panels, *manual)), result.report


def reconcile_panels_list(text: str, files: Sequence[str]) -> str:
    """``substation.yaml`` text with its ``panels:`` list set to ``files``, comments kept.

    ``bomgen layout`` calls this so a layout that grows or shrinks stays listed.
    """
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if re.match(r"panels:(\s|$)", line)), None)
    indent = "  "
    if start is None:
        head = text if not text or text.endswith("\n") else text + "\n"
        return head + "panels:\n" + "".join(f"{indent}- {f}\n" for f in files)
    end = start + 1
    while end < len(lines) and re.match(r"[ \t]+\S|-(\s|$)", lines[end]):
        item = re.match(r"([ \t]*)-", lines[end])
        if item and end == start + 1:
            indent = item.group(1)
        end += 1
    block = re.match(r"panels:\s*(#.*)?$", lines[start])
    head = lines[start] if block else "panels:\n"  # a flow list becomes a block list
    items = [f"{indent}- {f}\n" for f in files]
    return "".join([*lines[:start], head, *items, *lines[end:]])
