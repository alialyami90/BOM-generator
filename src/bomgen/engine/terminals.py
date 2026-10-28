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
from bomgen.engine.items import BomItem
from bomgen.engine.network import port_plan
from bomgen.engine.units import DeviceRow, lookup
from bomgen.models._base import template_fields
from bomgen.models.bom import BomLine, Group
from bomgen.models.library import Library, TerminalRule
from bomgen.models.panel import Panel, PanelKind, Ventilation

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


@dataclass(frozen=True)
class _Strip:
    code: str
    description: str
    block: str
    qty: int


def terminal_strips(
    panel: Panel, library: Library, rows: Sequence[DeviceRow], inputs: StripInputs
) -> list[BomItem]:
    """One row per strip, in the order of the example's group G rows ('Panel 1' and
    'Panel 3'; plan Q34)."""
    defaults = KIND_DEFAULTS[panel.kind]
    options = panel.options
    strips = [
        _fixed("X-AC", "AC Input Circuits", UT_16, defaults.incoming),
        _fixed("X3-AC", "AC Distribution Circuits", UT_MTD, 2 * inputs.ac_mcbs),
        _fixed("TBL", "Lighting Circuits", UT_MTD, LIGHTING),
        _fixed("THF", "Fan and Thermostat Circuits", UT_MTD, FAN_THERMOSTAT[inputs.ventilation]),
    ]
    if options.smoke_detector:
        strips.append(_fixed("XSD", "Smoke Detector", UT_MTD, SMOKE_DETECTOR))
    if options.aux_socket_a is not None:
        strips.append(_fixed("XPS", "Power Socket", UT_MTD, SOCKET))
    if inputs.dc_branches_per_feed:
        step = defaults.distribution_step
        distribution = step * math.ceil(2 * (inputs.dc_branches_per_feed + 1) / step)
        strips += [
            _fixed("X-DC1", "DC1 Circuits", UT_16, defaults.incoming),
            _fixed("X-DC2", "DC2 Circuits", UT_16, defaults.incoming),
            _fixed("X4-DC1", "DC1 Distribution Circuits", UT_MTD, distribution),
            _fixed("X4-DC2", "DC2 Distribution Circuits", UT_MTD, distribution),
        ]
    if inputs.change_over:
        strips.append(_fixed("X4-COD", "Change-over Circuits", UT_MTD, defaults.change_over))
    if inputs.annunciator_feeds:
        strips.append(
            _fixed("X-ANN", "Annunciator Circuits", UT_MTD, ANNUNCIATOR * inputs.annunciator_feeds)
        )
    strips += _device_strips(panel, library, rows, inputs.xdin_default)
    if options.inter_panel_terminals:
        strips.append(
            _fixed(
                "XIP",
                "Interpanel Wiring",
                defaults.inter_panel_block,
                options.inter_panel_terminals,
            )
        )

    overrides = dict(options.terminal_overrides)
    unknown = sorted(set(overrides) - {strip.code for strip in strips})
    if unknown:
        raise EngineError(f"{panel.id}: terminal_overrides name no strip of this panel: {unknown}")
    return [
        BomItem(_line(panel, library, strip, overrides.get(strip.code, strip.qty)))
        for strip in strips
    ]


def _fixed(code: str, circuits: str, block: str, qty: int) -> _Strip:
    return _Strip(code, f"Terminal Blocks For {circuits}", block, qty)


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
        [_Strip(XDIN, XDIN_DESCRIPTION, xdin_block, xdin_default)]
        if xdin_block is not None and (xdin_default or XDIN in panel.options.terminal_overrides)
        else []
    )
    return [*per_unit, *xdin, *per_port]


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
        return [_Strip(rule.strip, _describe(rule, rule.strip, {}), rule.block, rule.count * units)]
    strips = []
    for index in range(units):
        values: dict[str, object] = {"n": index + 1}
        if rule.first_slot is not None:
            values["slot"] = chr(ord(rule.first_slot) + index)
        code = rule.strip.format(**values)
        strips.append(_Strip(code, _describe(rule, code, values), rule.block, rule.count))
    return strips


def _describe(rule: TerminalRule, code: str, values: dict[str, object]) -> str:
    if rule.description is None:
        return f"Terminal Blocks For {code}"
    return rule.description.format(**values)


def _line(panel: Panel, library: Library, strip: _Strip, qty: int) -> BomLine:
    block = library.catalogues.terminal_blocks.get(strip.block)
    if block is None:
        raise EngineError(f"terminal block {strip.block} is not in the library catalogue")
    return BomLine(
        group=Group.G,
        tag=f"{panel.tag_prefix}-{strip.code}",
        description=strip.description,
        qty=qty,
        make=block.make,
        model=strip.block,
        ordering_code=block.ordering_code,
    )
