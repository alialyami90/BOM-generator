"""Heat Dissipation and Heat Calculations (spec: Heat Dissipation and Heat Calculations
sheets, including "Rule for the tool"; Data model and generation order, step 4)."""

import pytest
from engine_factories import library, panel, powered

from bomgen.engine.errors import EngineError
from bomgen.engine.thermal import (
    choose_ventilation,
    forced_check,
    heat_dissipation,
    line_up_check,
    natural_check,
    surface_area_m2,
    ventilation_heat_w,
)
from bomgen.models.bom import BomLine, Group
from bomgen.models.calc import CabinetPower, LineRef, PowerBlock, PowerConsumption, PowerLine
from bomgen.models.library import LoadType, SupplyType
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.project import DesignConstants

C = DesignConstants()


def ws_console() -> Panel:
    enclosure = {
        "make": "Rittal",
        "model": "PC",
        "h_mm": 1600,
        "d_mm": 636,
        "w_mm": 800,
        "cable_entry": "side",
    }
    return panel([{"part_id": "LAMP"}], id="ws", kind="console", enclosure=enclosure)


def test_required_airflow_is_heat_times_k_over_temperature_difference() -> None:
    # Cabinet 001: 954.56 W -> 391.37 m³/h against 716 m³/h.
    check = forced_check("psa1", 954.56, 716, C)
    assert check.required_m3h == pytest.approx(391.37, abs=0.01)
    assert check.passes


def test_surface_area_of_the_ws_console() -> None:
    # A = 1.8 H (W + D) + 1.4 W D with H 1.6, W 0.8, D 0.636 -> 4.848 m².
    assert surface_area_m2(1.6, 0.8, 0.636) == pytest.approx(4.848, abs=0.001)


def test_natural_convection_rise_of_the_ws_console() -> None:
    check = natural_check(ws_console(), 185.56, C)
    assert (check.h_m, check.w_m, check.d_m) == (1.6, 0.8, 0.636)
    assert check.delta_t_c == pytest.approx(6.96, abs=0.01)
    assert check.limit_c == 10
    assert check.passes


def test_line_up_sums_required_airflow_against_all_fans() -> None:
    checks = [forced_check(p, w, 716, C) for p, w in (("a", 954.56), ("b", 954.56), ("c", 419.56))]
    line_up = line_up_check(checks)
    assert line_up.panel_ids == ("a", "b", "c")
    assert line_up.required_m3h == pytest.approx(954.8, abs=0.05)
    assert line_up.fan_m3h == 2148
    assert line_up.passes


@pytest.mark.parametrize(
    ("heat_w", "expected"), [(190, Ventilation.NATURAL), (300, Ventilation.FORCED)]
)
def test_auto_ventilation_picks_filters_when_natural_rise_is_within_limit(
    heat_w: float, expected: Ventilation
) -> None:
    # 300 W / (4.848 m² x 5.5) = 11.3 °C > 10 °C -> fans.
    assert choose_ventilation(ws_console(), heat_w, C) is expected


def test_explicit_ventilation_option_wins() -> None:
    forced = panel([{"part_id": "LAMP"}], options={"ventilation": "forced"})
    assert choose_ventilation(forced, 1, C) is Ventilation.FORCED


def test_explicit_natural_wins_over_a_hot_cabinet() -> None:
    natural = panel([{"part_id": "LAMP"}], options={"ventilation": "natural"})
    assert choose_ventilation(natural, 5000, C) is Ventilation.NATURAL


def test_ventilation_heat_needs_counted_rows() -> None:
    lib = library(powered("SW", "network_switch"))
    lines = [BomLine(group=Group.B, description="SW", qty="1 Lot", part_id="SW")]
    with pytest.raises(EngineError, match="needs a count"):
        ventilation_heat_w(lines, lib)


def power_line(panel_id: str | None, unit_w: float, supply: SupplyType, qty: int = 1) -> PowerLine:
    return PowerLine(
        source=LineRef(panel_id=panel_id, line=0),
        supply_type=supply,
        voltage_v=125 if supply is SupplyType.VDC else 230,
        qty=qty,
        unit_w=unit_w,
        load_type=LoadType.CONTINUOUS,
        current_factor=1.3,
    )


def block(supply: SupplyType, *lines: PowerLine) -> PowerBlock:
    return PowerBlock(supply_type=supply, lines=lines, margin=0.25)


def test_heat_dissipation_has_dc_then_ac_rows_per_cabinet_and_an_auxiliary_block() -> None:
    dc = block(SupplyType.VDC, power_line("psa1", 77, SupplyType.VDC, 6))
    ac = block(SupplyType.VAC, power_line("psa1", 87, SupplyType.VAC, 2))
    external = block(SupplyType.VDC, power_line(None, 100, SupplyType.VDC))
    power = PowerConsumption(
        cabinets=(CabinetPower(panel_id="psa1", dc=dc, ac=ac),), external=external
    )
    cabinet, auxiliary = heat_dissipation(power, C)
    assert cabinet.panel_id == "psa1"
    assert [line.power.unit_w for line in cabinet.lines] == [77, 87]
    assert cabinet.total_w == 6 * 77 + 2 * 87  # no margin
    assert cabinet.total_btu_h == pytest.approx((6 * 77 + 2 * 87) * 3.41)
    assert auxiliary.panel_id is None
    assert auxiliary.total_w == 100


def test_ventilation_heat_leaves_out_fans_filters_and_thermostats() -> None:
    # Plan Q4: decide ventilation from the heat of everything except its own parts.
    ac = {"supply_type": "VAC", "voltage_v": 230, "power_supplies": 0, "min_branch_mcb_a": None}
    lib = library(
        powered("SW", "network_switch", unit_power_w=77),
        powered("PFAN", "fan", unit_power_w=87, **ac),
        powered("PTH", "thermostat", unit_power_w=30, **ac),
        powered("PLAMP", "lamp", unit_power_w=11, **ac),
    )

    def line(part_id: str, qty: int) -> BomLine:
        return BomLine(group=Group.B, description=part_id, qty=qty, part_id=part_id)

    lines = [line("SW", 2), line("PFAN", 2), line("PTH", 3), line("PLAMP", 1), line("TH", 1)]
    assert ventilation_heat_w(lines, lib) == 2 * 77 + 11
