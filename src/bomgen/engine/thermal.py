"""Heat checks and the ventilation choice (spec: Heat Dissipation and Heat Calculations
sheets, "Rule for the tool"; Data model and generation order, step 4)."""

from collections.abc import Sequence

from bomgen.models.calc import (
    CabinetHeat,
    ForcedVentCheck,
    HeatLine,
    LineUpCheck,
    NaturalConvCheck,
    PowerBlock,
    PowerConsumption,
)
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.project import DesignConstants


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
