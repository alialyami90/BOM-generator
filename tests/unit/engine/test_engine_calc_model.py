"""Power and heat formulas (spec: Power Consumption sheet -> Formulas; Heat Dissipation
and Heat Calculations sheets)."""

import pytest

from bomgen.models.calc import (
    ForcedVentCheck,
    HeatLine,
    LineRef,
    NaturalConvCheck,
    PowerBlock,
    PowerLine,
)
from bomgen.models.library import LoadType, SupplyType


def line(qty: int = 6, unit_w: float = 77, voltage: float = 125) -> PowerLine:
    return PowerLine(
        source=LineRef(panel_id="psa1", line=7),
        supply_type=SupplyType.VDC,
        voltage_v=voltage,
        qty=qty,
        unit_w=unit_w,
        load_type=LoadType.CONTINUOUS,
        current_factor=1.3,
    )


def test_total_power_is_qty_times_unit_power() -> None:
    assert line().total_w == 462


def test_sizing_columns_n_to_r() -> None:
    power = line()
    assert power.current_a == pytest.approx(77 / 125)  # N
    assert power.current_with_margin_a == pytest.approx(1.3 * 77 / 125)  # O
    assert power.device_mcb_a == 1  # P = ROUNDUP(O, 0)
    assert power.main_contribution_a == pytest.approx(6 * 1.3 * 77 / 125)  # Q (= R)


def test_supply_label() -> None:
    assert line().supply_label == "125V"
    assert line(voltage=230).supply_label == "230V"


def test_block_total_has_25_percent_margin() -> None:
    block = PowerBlock(supply_type=SupplyType.VDC, lines=(line(1), line(6)), margin=0.25)
    assert block.subtotal_w == 539
    assert block.total_w == pytest.approx(673.75)


def test_heat_line_btu() -> None:
    heat = HeatLine(power=line(), btu_per_w=3.41)
    assert heat.total_w == 462  # L = I x H
    assert heat.unit_btu_h == pytest.approx(77 * 3.41)  # J = L x 3.41 / H
    assert heat.total_btu_h == pytest.approx(462 * 3.41)  # K = H x J


def test_checks_pass_on_the_boundary() -> None:
    assert ForcedVentCheck(panel_id="p", heat_w=1, required_m3h=716, fan_m3h=716).passes
    natural = NaturalConvCheck(
        panel_id="p", heat_w=1, h_m=1, w_m=1, d_m=1, area_m2=1, delta_t_c=10, limit_c=10
    )
    assert natural.passes
