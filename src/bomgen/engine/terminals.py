"""Group G: terminal strips (spec: Derivation rules -> Terminal block quantities
(group G); Data model and generation order, step 8).

Quantities the spec gives as fixed per cabinet come from the panel kind (plan Q6);
``terminal_overrides`` replaces any strip's quantity. Device strips come from the
library ``terminals`` rules of each row and its kit children (plan Q34).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from bomgen.engine.errors import EngineError
from bomgen.engine.housekeeping import KitCounts, kit_counts, kit_role
from bomgen.engine.items import BomItem
from bomgen.engine.network import port_plan
from bomgen.engine.units import DeviceRow, expand_devices, lookup
from bomgen.models._base import template_fields
from bomgen.models.bom import BomLine, Group, StripRow
from bomgen.models.library import Library, TerminalRule
from bomgen.models.panel import DeviceInstance, Panel, PanelKind, PanelOptions, Ventilation

UT_16 = "UT-16"
UT_MTD = "UT-2.5-MTD"
UT_MT = "UT-2.5-MT"


@dataclass(frozen=True)
class KindDefaults:
    """Per-cabinet values the terminal table states without a rule (plan Q6)."""

    incoming: int  # X-AC, X-DC1, X-DC2
    change_over: int  # X4-COD
    distribution_step: int  # X4-DC1/X4-DC2 rounded up to a multiple of this
    inter_panel_block: str  # XIP


KIND_DEFAULTS = {
    # 28 -> 32 ("rounded up to 32 in network cabinets")
    PanelKind.NETWORK: KindDefaults(6, 8, 8, UT_MT),
    PanelKind.CONTROL: KindDefaults(6, 8, 1, UT_MT),
    PanelKind.CONSOLE: KindDefaults(4, 6, 1, UT_MTD),
}
FAN_THERMOSTAT = {Ventilation.FORCED: 12, Ventilation.NATURAL: 5}
LIGHTING = 4
SMOKE_DETECTOR = 4
SOCKET = 4
ANNUNCIATOR = 4
XDIN = "XDIN"
XDIN_DESCRIPTION = "Knife Disconnect Terminal Blocks For DI Negative"


@dataclass(frozen=True)
class StripInputs:
    """What the strips depend on from groups D-F."""

    ventilation: Ventilation
    ac_mcbs: int
    dc_branches_per_feed: int
    change_over: bool
    annunciator_feeds: int
    xdin_default: int  # the project's HWIO total (spec: HWIO points)
    spare_fraction: float = 0.0  # spares.terminals_fraction (ADR 0033)
    kit: KitCounts | None = None  # the housekeeping kit (ADR 0032); None: the spec's


@dataclass(frozen=True)
class _Strip:
    code: str
    description: str
    block: str
    qty: int
    rule: str
    spared: bool = True  # the spare fraction applies (ADR 0033: not to the devices' strips)


THF_RULE = {
    Ventilation.FORCED: "two fans and three thermostats",
    Ventilation.NATURAL: "three thermostats",
}


def strip_table(
    panel: Panel, library: Library, rows: Sequence[DeviceRow], inputs: StripInputs
) -> list[StripRow]:
    """Every strip of the panel in group G order, before the BOM rows are written."""
    defaults = KIND_DEFAULTS[panel.kind]
    options = panel.options
    kind = panel.kind.value
    strips = [
        _fixed("X-AC", "AC Input Circuits", UT_16, defaults.incoming, f"incoming, {kind} panel"),
        _fixed(
            "X3-AC",
            "AC Distribution Circuits",
            UT_MTD,
            2 * inputs.ac_mcbs,
            f"2 x {inputs.ac_mcbs} AC MCBs = {2 * inputs.ac_mcbs}",
        ),
        _fixed("TBL", "Lighting Circuits", UT_MTD, LIGHTING, "lighting"),
        _fixed("THF", "Fan and Thermostat Circuits", UT_MTD, *_thf(panel, inputs)),
    ]
    if options.smoke_detector != "none":
        strips.append(_fixed("XSD", "Smoke Detector", UT_MTD, SMOKE_DETECTOR, "smoke detector"))
    if options.aux_socket_a is not None:
        strips.append(_fixed("XPS", "Power Socket", UT_MTD, SOCKET, "power socket"))
    if inputs.dc_branches_per_feed:
        step = defaults.distribution_step
        raw = 2 * (inputs.dc_branches_per_feed + 1)
        distribution = step * math.ceil(raw / step)
        rule = f"2 x ({inputs.dc_branches_per_feed} branches + 1) = {raw}"
        if distribution != raw or step > 1:
            rule += f", up to a multiple of {step} = {distribution}"
        incoming = f"incoming, {kind} panel"
        strips += [
            _fixed("X-DC1", "DC1 Circuits", UT_16, defaults.incoming, incoming),
            _fixed("X-DC2", "DC2 Circuits", UT_16, defaults.incoming, incoming),
            _fixed("X4-DC1", "DC1 Distribution Circuits", UT_MTD, distribution, rule),
            _fixed("X4-DC2", "DC2 Distribution Circuits", UT_MTD, distribution, rule),
        ]
    if inputs.change_over:
        strips.append(
            _fixed(
                "X4-COD",
                "Change-over Circuits",
                UT_MTD,
                defaults.change_over,
                f"change-over, {kind} panel",
            )
        )
    if inputs.annunciator_feeds:
        feeds = inputs.annunciator_feeds
        strips.append(
            _fixed(
                "X-ANN",
                "Annunciator Circuits",
                UT_MTD,
                ANNUNCIATOR * feeds,
                f"{ANNUNCIATOR} x {feeds} annunciator feeds = {ANNUNCIATOR * feeds}",
            )
        )
    kit = inputs.kit
    extra = [  # a heater or hygrostat brings its part's own strips (ADR 0032 item 5)
        DeviceInstance(part_id=kit_role(panel, library, role).part_id)
        for role in ("heater", "hygrostat")
        if kit is not None and getattr(kit, role)
    ]
    rows = [*rows, *expand_devices(panel, library, extra)] if extra else rows
    strips += _device_strips(panel, library, rows, inputs.xdin_default)
    if options.inter_panel_terminals:
        strips.append(
            _fixed(
                "XIP",
                "Interpanel Wiring",
                defaults.inter_panel_block,
                options.inter_panel_terminals,
                "the panel's inter-panel terminals",
            )
        )

    codes = {strip.code for strip in strips}
    for name, given in (
        ("terminal_overrides", options.terminal_overrides),
        ("terminal_block_overrides", options.terminal_block_overrides),
    ):
        unknown = sorted(set(given) - codes)
        if unknown:
            raise EngineError(f"{panel.id}: {name} name no strip of this panel: {unknown}")
    return [
        _row(
            strip,
            inputs.spare_fraction,
            options.terminal_overrides.get(strip.code),
            options.terminal_block_overrides.get(strip.code),
        )
        for strip in strips
    ]


def _thf(panel: Panel, inputs: StripInputs) -> tuple[int, str]:
    """The spec's THF for the ventilation, plus 3 per fan and 2 per thermostat more (or
    fewer) than the spec's kit (ADR 0032 item 5)."""
    base = FAN_THERMOSTAT[inputs.ventilation]
    spec = kit_counts(panel.model_copy(update={"options": PanelOptions()}), inputs.ventilation)
    kit = inputs.kit or spec
    changes = [
        (kit.fans - spec.fans, 3, "fan"),
        (kit.thermostats - spec.thermostats, 2, "thermostat"),
    ]
    qty = max(base + sum(n * per for n, per, _ in changes), 0)
    if not any(n for n, _, _ in changes):
        return qty, THF_RULE[inputs.ventilation]
    rule = f"{base} for {THF_RULE[inputs.ventilation]}"
    for n, per, what in changes:
        if n:
            rule += f", {'+' if n > 0 else '-'}{per} x {abs(n)} {what}{'' if abs(n) == 1 else 's'}"
    return qty, f"{rule} = {qty}"


def terminal_strips(
    panel: Panel, library: Library, rows: Sequence[DeviceRow], inputs: StripInputs
) -> list[BomItem]:
    """One row per strip, in the order of the example's group G rows ('Panel 1' and
    'Panel 3'; plan Q34)."""
    return [BomItem(_line(panel, library, r)) for r in strip_table(panel, library, rows, inputs)]


def _row(strip: _Strip, fraction: float, override: int | None, block: str | None) -> StripRow:
    auto, rule = strip.qty, strip.rule
    if strip.spared and fraction:
        auto = math.ceil(round(strip.qty * (1 + fraction), 9))
        rule += f", +{fraction * 100:g}% spare = {auto}"
    return StripRow(
        code=strip.code,
        description=strip.description,
        block=strip.block,
        block_override=block,
        rule=rule,
        auto_qty=auto,
        override=override,
        spared=strip.spared,
    )


def _fixed(code: str, circuits: str, block: str, qty: int, why: str) -> _Strip:
    rule = why if why[:1].isdigit() else f"{qty}: {why}"
    return _Strip(code, f"Terminal Blocks For {circuits}", block, qty, rule)


def _device_strips(
    panel: Panel, library: Library, rows: Sequence[DeviceRow], xdin_default: int
) -> list[_Strip]:
    """Strips from the devices' own rules: per-unit strips, XDIN after the DI slot
    strips, then per-serial-port strips (plan Q34)."""
    per_unit: list[_Strip] = []
    per_port: list[_Strip] = []
    xdin_block: str | None = None
    for row in rows:
        ports = plan.serial_ports if (plan := port_plan(panel, row)) else 0
        for rule, units in _rules(row, library):
            if rule.per == "serial_port":
                per_port += _expand(rule, ports)
                continue
            per_unit += _expand(rule, units)
            if rule.first_slot is not None:
                xdin_block = xdin_block or rule.block
    xdin = (
        [
            _Strip(
                XDIN,
                XDIN_DESCRIPTION,
                xdin_block,
                xdin_default,
                f"{xdin_default}: the project's HWIO total",
                spared=False,
            )
        ]
        if xdin_block is not None and (xdin_default or XDIN in panel.options.terminal_overrides)
        else []
    )
    return [*per_unit, *xdin, *per_port]


def unit_strips(row: DeviceRow, library: Library, index: int) -> tuple[str, ...]:
    """The strip codes of the row's ``index``-th unit (0-based), as group G names them;
    a strip shared by the row's units counts for each, serial-port strips are left out."""
    codes: list[str] = []
    for rule, units in _rules(row, library):
        if rule.per == "serial_port":
            continue
        strips = _expand(rule, units)
        if len(strips) < units:  # one strip holds every unit's terminals
            codes += [x.code for x in strips]
            continue
        per = units // row.instance.qty
        codes += [x.code for x in strips[index * per : (index + 1) * per]]
    return tuple(dict.fromkeys(codes))


def _rules(row: DeviceRow, library: Library) -> list[tuple[TerminalRule, int]]:
    """The row's terminal rules and its kit children's, each with its unit count."""
    device, qty = row.device, row.instance.qty
    result = [(rule, qty) for rule in device.terminals]
    for child_rule in device.children:
        per_unit = device.cores if child_rule.qty == "cores" else child_rule.qty
        assert per_unit is not None  # the library model requires cores for a "cores" child
        child = lookup(library, child_rule.part_id)
        result += [(rule, per_unit * qty) for rule in child.terminals]
    return result


def _expand(rule: TerminalRule, units: int) -> list[_Strip]:
    """One strip per unit when the code is numbered ({n}) or slotted ({slot}), else one
    strip holding every unit's terminals."""
    if not template_fields(rule.strip) & {"n", "slot"}:
        qty = rule.count * units
        why = f"{rule.count} x {units} units = {qty}: the device's terminals"
        return [_Strip(rule.strip, _describe(rule, rule.strip, {}), rule.block, qty, why, False)]
    strips = []
    for index in range(units):
        values: dict[str, object] = {"n": index + 1}
        if rule.first_slot is not None:
            values["slot"] = chr(ord(rule.first_slot) + index)
        code = rule.strip.format(**values)
        why = f"{rule.count}: the device's terminals per unit"
        strips.append(
            _Strip(code, _describe(rule, code, values), rule.block, rule.count, why, False)
        )
    return strips


def _describe(rule: TerminalRule, code: str, values: dict[str, object]) -> str:
    if rule.description is None:
        return f"Terminal Blocks For {code}"
    return rule.description.format(**values)


def _line(panel: Panel, library: Library, strip: StripRow) -> BomLine:
    block = library.catalogues.terminal_blocks.get(strip.model)
    if block is None:
        raise EngineError(f"terminal block {strip.model} is not in the library catalogue")
    return BomLine(
        group=Group.G,
        tag=f"{panel.tag_prefix}-{strip.code}",
        description=strip.description,
        qty=strip.qty,
        make=block.make,
        model=strip.model,
        ordering_code=block.ordering_code,
    )
