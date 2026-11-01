"""Power and heat results, the engine's output for the calculation sheets (ADR 0005).

Models the spec sections "Power Consumption sheet" and "Heat Dissipation and Heat
Calculations sheets" (entities PowerLine and HeatLine). Each power line points at its
BOM row by table and index, so the sheet layer can write ``='1'!C8``-style references.
"""

import math
from typing import Literal

from pydantic import NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt

from bomgen.models.library import LoadType, SupplyType
from bomgen.models.output import OutputModel
from bomgen.models.panel import Ventilation


class LineRef(OutputModel):
    """A BOM row: ``panel_id`` names a panel's table, ``None`` the loose-material table."""

    panel_id: str | None
    line: NonNegativeInt


class PowerLine(OutputModel):
    """One powered BOM row (Power Consumption columns C-K and the sizing columns N-R)."""

    source: LineRef
    supply_type: SupplyType
    voltage_v: PositiveFloat
    qty: PositiveInt
    unit_w: NonNegativeFloat
    load_type: LoadType
    current_factor: PositiveFloat

    @property
    def supply_label(self) -> str:
        """Column C, e.g. ``125V``."""
        return f"{self.voltage_v:g}V"

    @property
    def total_w(self) -> float:
        """J = F x I."""
        return self.qty * self.unit_w

    @property
    def current_a(self) -> float:
        """N = I / V."""
        return self.unit_w / self.voltage_v

    @property
    def current_with_margin_a(self) -> float:
        """O = 1.3 N."""
        return self.current_factor * self.current_a

    @property
    def device_mcb_a(self) -> int:
        """P = ⌈O⌉."""
        return math.ceil(self.current_with_margin_a)

    @property
    def main_contribution_a(self) -> float:
        """Q = O x F; R (change-over current) equals Q."""
        return self.current_with_margin_a * self.qty


class PowerBlock(OutputModel):
    """A DC or AC block with its total including the margin."""

    supply_type: SupplyType
    lines: tuple[PowerLine, ...]
    margin: NonNegativeFloat

    @property
    def subtotal_w(self) -> float:
        return sum(line.total_w for line in self.lines)

    @property
    def total_w(self) -> float:
        """Block total = (1 + margin) x Σ J."""
        return (1 + self.margin) * self.subtotal_w


class CabinetPower(OutputModel):
    panel_id: str
    dc: PowerBlock | None
    ac: PowerBlock | None


class PowerConsumption(OutputModel):
    """Every cabinet's blocks, the external equipment block and the summary."""

    cabinets: tuple[CabinetPower, ...]
    external: PowerBlock | None

    @property
    def dc_total_w(self) -> float:
        blocks = [c.dc for c in self.cabinets] + [self.external]
        return sum(block.total_w for block in blocks if block is not None)

    @property
    def ac_total_w(self) -> float:
        return sum(c.ac.total_w for c in self.cabinets if c.ac is not None)

    @property
    def total_w(self) -> float:
        return self.dc_total_w + self.ac_total_w


class HeatLine(OutputModel):
    """One Heat Dissipation row, read from its Power Consumption row."""

    power: PowerLine
    btu_per_w: PositiveFloat

    @property
    def total_w(self) -> float:
        """L = I x H."""
        return self.power.total_w

    @property
    def unit_btu_h(self) -> float:
        """J = L x 3.41 / H."""
        return self.total_w * self.btu_per_w / self.power.qty

    @property
    def total_btu_h(self) -> float:
        """K = H x J."""
        return self.power.qty * self.unit_btu_h


class CabinetHeat(OutputModel):
    """A Heat Dissipation block: DC rows, then AC rows. ``panel_id`` ``None`` is the
    "PSA Auxiliary Equipment" block, outside the panels."""

    panel_id: str | None
    lines: tuple[HeatLine, ...]

    @property
    def total_w(self) -> float:
        return sum(line.total_w for line in self.lines)

    @property
    def total_btu_h(self) -> float:
        return sum(line.total_btu_h for line in self.lines)


class ForcedVentCheck(OutputModel):
    """Required airflow against the fitted fans' throughput."""

    panel_id: str
    heat_w: NonNegativeFloat
    required_m3h: NonNegativeFloat
    fan_m3h: NonNegativeFloat

    @property
    def passes(self) -> bool:
        return self.fan_m3h >= self.required_m3h


class NaturalConvCheck(OutputModel):
    """Temperature rise by natural convection through the cabinet's steel surface."""

    panel_id: str
    heat_w: NonNegativeFloat
    h_m: PositiveFloat
    w_m: PositiveFloat
    d_m: PositiveFloat
    area_m2: PositiveFloat
    delta_t_c: NonNegativeFloat
    limit_c: PositiveFloat

    @property
    def passes(self) -> bool:
        return self.delta_t_c <= self.limit_c


class CabinetThermal(OutputModel):
    """Both checks for one cabinet and the ventilation it got."""

    panel_id: str
    ventilation: Ventilation
    forced: ForcedVentCheck
    natural: NaturalConvCheck


class LineUpCheck(OutputModel):
    """The fan-ventilated cabinets treated as one internally open volume."""

    panel_ids: tuple[str, ...]
    required_m3h: NonNegativeFloat
    fan_m3h: NonNegativeFloat

    @property
    def passes(self) -> bool:
        return self.fan_m3h >= self.required_m3h


class DcMains(OutputModel):
    """A panel's Q1/Q2 rating against its per-feed design current ΣQ (spec: Derivation
    rules -> DC distribution; step 15 compares them)."""

    panel_id: str
    design_current_a: NonNegativeFloat
    rating_a: NonNegativeInt  # 0 when the panel has no DC loads
    rule_rating_a: NonNegativeInt  # without main_mcb_override_a (plan Q3)


class HeatResult(OutputModel):
    dissipation: tuple[CabinetHeat, ...]
    cabinets: tuple[CabinetThermal, ...]
    line_up: LineUpCheck | None


BranchCondition = Literal["running", "inrush", "floor"]


class BranchSizing(OutputModel):
    """A branch MCB's rating and the numbers behind it (plan Q35, ADR 0019)."""

    rating_a: PositiveInt
    running_a: NonNegativeFloat  # current factor x W / V of one unit
    inrush_a: PositiveFloat | None = None
    inrush_ms: PositiveFloat | None = None
    inrush_counted: bool = True  # False: shorter than inrush_min_ms, too short to trip
    trip_multiple: PositiveFloat | None = None  # None: the catalogue has no trip curve
    inrush_need_a: NonNegativeFloat | None = None  # inrush / trip multiple, when counted
    floor_a: PositiveInt
    set_by: tuple[BranchCondition, ...]  # every condition that alone gives the rating
    library_min_a: PositiveInt | None = None  # the deprecated min_branch_mcb_a


class BranchMcb(BranchSizing):
    """One Q1.n, Q2.n or QCOD-n with its sizing; spares are not listed."""

    panel_id: str
    tag: str
    load: str
    unit_tag: str | None = None  # the unit it feeds; None for a loose load
    feed: Literal[1, 2] | None = None  # None on a QCOD
