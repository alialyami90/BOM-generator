"""Group G: terminal strips (spec: Derivation rules -> Terminal block quantities
(group G); Data model and generation order, step 8).

Quantities the spec gives as fixed per cabinet come from the panel kind (plan Q6);
``terminal_overrides`` replaces any strip's quantity.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from bomgen.engine.errors import EngineError
from bomgen.engine.items import BomItem
from bomgen.engine.units import DeviceRow
from bomgen.models.bom import BomLine, Group
from bomgen.models.library import Library
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


@dataclass(frozen=True)
class StripInputs:
    """What the strips depend on from groups D-F."""

    ventilation: Ventilation
    ac_mcbs: int
    dc_branches_per_feed: int
    change_over: bool
    annunciator_feeds: int
    xdin_default: int


@dataclass(frozen=True)
class _Strip:
    code: str
    description: str
    block: str
    qty: int


def terminal_strips(
    panel: Panel, library: Library, rows: Sequence[DeviceRow], inputs: StripInputs
) -> list[BomItem]:
    """One row per strip, in the order of the spec's terminal table."""
    defaults = KIND_DEFAULTS[panel.kind]
    options = panel.options
    strips = [
        _Strip("X-AC", "AC Input Circuits", UT_16, defaults.incoming),
        _Strip("X3-AC", "AC Distribution Circuits", UT_MTD, 2 * inputs.ac_mcbs),
        _Strip("TBL", "Lighting Circuits", UT_MTD, LIGHTING),
        _Strip("THF", "Fan and Thermostat Circuits", UT_MTD, FAN_THERMOSTAT[inputs.ventilation]),
    ]
    if options.smoke_detector:
        strips.append(_Strip("XSD", "Smoke Detector", UT_MTD, SMOKE_DETECTOR))
    if options.aux_socket_a is not None:
        strips.append(_Strip("XPS", "Power Socket", UT_MTD, SOCKET))
    if inputs.dc_branches_per_feed:
        step = defaults.distribution_step
        distribution = step * math.ceil(2 * (inputs.dc_branches_per_feed + 1) / step)
        strips += [
            _Strip("X-DC1", "DC1 Circuits", UT_16, defaults.incoming),
            _Strip("X-DC2", "DC2 Circuits", UT_16, defaults.incoming),
            _Strip("X4-DC1", "DC1 Distribution Circuits", UT_MTD, distribution),
            _Strip("X4-DC2", "DC2 Distribution Circuits", UT_MTD, distribution),
        ]
    if inputs.change_over:
        strips.append(_Strip("X4-COD", "Change-over Circuits", UT_MTD, defaults.change_over))
    if inputs.annunciator_feeds:
        strips.append(
            _Strip("X-ANN", "Annunciator Circuits", UT_MTD, ANNUNCIATOR * inputs.annunciator_feeds)
        )
    if options.inter_panel_terminals:
        strips.append(
            _Strip(
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


def _line(panel: Panel, library: Library, strip: _Strip, qty: int) -> BomLine:
    block = library.catalogues.terminal_blocks.get(strip.block)
    if block is None:
        raise EngineError(f"terminal block {strip.block} is not in the library catalogue")
    return BomLine(
        group=Group.G,
        tag=f"{panel.tag_prefix}-{strip.code}",
        description=f"Terminal Blocks For {strip.description}",
        qty=qty,
        make=block.make,
        model=strip.block,
        ordering_code=block.ordering_code,
    )
