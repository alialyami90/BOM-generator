"""Heat checks and the ventilation choice (spec: Heat Dissipation and Heat Calculations
sheets, "Rule for the tool"; Data model and generation order, step 4)."""

from collections.abc import Iterable, Sequence

from bomgen.engine.units import lookup
from bomgen.models.bom import BomLine
from bomgen.models.calc import (
    CabinetHeat,
    CabinetThermal,
    ForcedVentCheck,
    HeatLine,
    HeatResult,
    LineUpCheck,
    NaturalConvCheck,
    PowerBlock,
    PowerConsumption,
)
from bomgen.models.library import Category, Library
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.project import DesignConstants

VENTILATION_PARTS = frozenset({Category.FAN, Category.VENT_FILTER, Category.THERMOSTAT})


def forced_check(
    panel_id: str, heat_w: float, fan_m3h: float, constants: DesignConstants
) -> ForcedVentCheck:
    """V̇ = P x k / (TMax - TInt) against the fitted fans."""
    rise = constants.t_max_c - constants.t_int_c
    required = heat_w * constants.air_constant_m3k_per_wh / rise
    return ForcedVentCheck(panel_id=panel_id, heat_w=heat_w, required_m3h=required, fan_m3h=fan_m3h)


def surface_area_m2(h_m: float, w_m: float, d_m: float) -> float:
    """A = 1.8 H (W + D) + 1.4 W D."""
    return 1.8 * h_m * (w_m + d_m) + 1.4 * w_m * d_m


def natural_check(panel: Panel, heat_w: float, constants: DesignConstants) -> NaturalConvCheck:
    """ΔT = P / (A x steel coefficient), from the enclosure's H x W x D (no base frame)."""
    enclosure = panel.enclosure
    h_m, w_m, d_m = enclosure.h_mm / 1000, enclosure.w_mm / 1000, enclosure.d_mm / 1000
    area = surface_area_m2(h_m, w_m, d_m)
    return NaturalConvCheck(
        panel_id=panel.id,
        heat_w=heat_w,
        h_m=h_m,
        w_m=w_m,
        d_m=d_m,
        area_m2=area,
        delta_t_c=heat_w / (area * constants.steel_coefficient_w_per_m2c),
        limit_c=constants.t_max_c - constants.t_int_c,
    )


def line_up_check(checks: Sequence[ForcedVentCheck]) -> LineUpCheck:
    """The cabinets as one internally open volume: Σ required against Σ fans."""
    return LineUpCheck(
        panel_ids=tuple(check.panel_id for check in checks),
        required_m3h=sum(check.required_m3h for check in checks),
        fan_m3h=sum(check.fan_m3h for check in checks),
    )


def choose_ventilation(panel: Panel, heat_w: float, constants: DesignConstants) -> Ventilation:
    """The panel option, or on ``auto``: filters when natural convection keeps ΔT within
    TMax - TInt, else fans. ``heat_w`` excludes the ventilation parts (plan Q4)."""
    option = panel.options.ventilation
    if option is not Ventilation.AUTO:
        return option
    natural = natural_check(panel, heat_w, constants)
    return Ventilation.NATURAL if natural.passes else Ventilation.FORCED


def ventilation_heat_w(lines: Iterable[BomLine], library: Library) -> float:
    """The heat the ventilation choice is made from: every powered row except the
    ventilation parts themselves (plan Q4)."""
    total = 0.0
    for line in lines:
        if line.part_id is None or not isinstance(line.qty, int):
            continue
        device = lookup(library, line.part_id)
        if device.excluded_from_power or device.category in VENTILATION_PARTS:
            continue
        total += line.qty * (device.unit_power_w or 0)
    return total


def heat_dissipation(
    power: PowerConsumption, constants: DesignConstants
) -> tuple[CabinetHeat, ...]:
    """One block per cabinet (DC rows, then AC rows) and the auxiliary equipment block
    outside the panels; no margin."""

    def heat(panel_id: str | None, *blocks: PowerBlock | None) -> CabinetHeat:
        lines = tuple(
            HeatLine(power=line, btu_per_w=constants.btu_per_w)
            for block in blocks
            if block is not None
            for line in block.lines
        )
        return CabinetHeat(panel_id=panel_id, lines=lines)

    result = [heat(c.panel_id, c.dc, c.ac) for c in power.cabinets]
    if power.external is not None:
        result.append(heat(None, power.external))
    return tuple(result)


def heat_result(
    panels: Sequence[tuple[Panel, Ventilation]],
    power: PowerConsumption,
    fan_pair_m3h: float,
    constants: DesignConstants,
) -> HeatResult:
    """Both checks for every cabinet from its Heat Dissipation total, and the line-up
    check over the fan-ventilated cabinets. The forced check compares with the fan
    pair a cabinet has or would get."""
    dissipation = heat_dissipation(power, constants)
    heat_by_panel = {block.panel_id: block.total_w for block in dissipation}
    cabinets = []
    for panel, ventilation in panels:
        heat_w = heat_by_panel.get(panel.id, 0.0)
        cabinets.append(
            CabinetThermal(
                panel_id=panel.id,
                ventilation=ventilation,
                forced=forced_check(panel.id, heat_w, fan_pair_m3h, constants),
                natural=natural_check(panel, heat_w, constants),
            )
        )
    forced = [c.forced for c in cabinets if c.ventilation is Ventilation.FORCED]
    return HeatResult(
        dissipation=dissipation,
        cabinets=tuple(cabinets),
        line_up=line_up_check(forced) if forced else None,
    )
