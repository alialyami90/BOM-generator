"""Automatic panel layout (ADR 0013, rules R5-R9).

``fill`` places units into panels of ``capacity_u``: redundant units in lock-step A
(odd panels) and B (even panels) streams, then common units into the panel with the
most free U. ``auto_layout`` drops removed units first and applies the engineer's moves
after. Units are named by equipment id and unit number, never by tag.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from bomgen.models.substation import DeviceMove, PairMove, Side, UnitRef

IssueKind = Literal[
    "device-too-tall",
    "move-does-not-fit",
    "stale-override",
    "stale-removal",
    "unknown-panel",
    "panel-empty",
    "missing-height",
]
WARNING_KINDS: frozenset[IssueKind] = frozenset({"stale-override", "stale-removal"})


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


def used_u(blocks: Iterable[int], blank_plate_u: int) -> int:
    """Rack units used: every block plus one blank plate between rack neighbours (R5)."""
    rack = [b for b in blocks if b > 0]
    return sum(rack) + max(0, len(rack) - 1) * blank_plate_u


def _order(unit: Unit) -> tuple[int, str, int]:
    return (unit.rank, unit.device, unit.n)


@dataclass
class PanelFill:
    number: int
    units: list[Unit] = field(default_factory=list)

    def used_u(self, rules: LayoutRules) -> int:
        return used_u((x.block_u for x in self.units), rules.blank_plate_u)

    def free_u(self, rules: LayoutRules) -> int:
        return rules.capacity_u - self.used_u(rules)

    def blank_plates(self) -> int:
        return max(0, sum(1 for x in self.units if x.block_u > 0) - 1)

    def din_rail_count(self) -> int:
        return sum(1 for x in self.units if x.block_u == 0)

    def fits(self, unit: Unit, rules: LayoutRules) -> bool:
        blocks = [x.block_u for x in self.units] + [unit.block_u]
        return used_u(blocks, rules.blank_plate_u) <= rules.capacity_u

    def add(self, unit: Unit) -> None:
        self.units.append(unit)
        self.units.sort(key=_order)


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

    def move(self, units: Sequence[Unit], number: int, what: str) -> None:
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
            target.add(unit)
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
    """Drop ``removed``, fill, then apply ``moves`` in order (R7)."""
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
        if not matched:
            builder.issues.append(
                LayoutIssue(
                    "stale-override",
                    _describe(ref),
                    f"a layout override names {_describe(ref)}, which the substation no longer has",
                )
            )
            continue
        for side, number in targets:
            group = [x for x in matched if side is None or x.side.value == side]
            if not group:
                continue
            what = _describe(ref) if side is None else f"{_describe(ref)} side {side.upper()}"
            builder.move(group, number, what)
    return builder.finish()


def fill_lines(layout: Layout, rules: LayoutRules) -> list[str]:
    """One check-report line per panel, blank plates included (R8)."""
    return [f"Panel {p.number}: {p.used_u(rules)} U / {rules.capacity_u} U" for p in layout.panels]
