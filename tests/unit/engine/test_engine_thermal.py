"""Heat Dissipation and Heat Calculations (spec: Heat Dissipation and Heat Calculations
sheets, including "Rule for the tool"; Data model and generation order, step 4)."""

import pytest
from engine_factories import panel

from bomgen.engine.thermal import (
    choose_ventilation,
    forced_check,
    line_up_check,
    natural_check,
    surface_area_m2,
)
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
