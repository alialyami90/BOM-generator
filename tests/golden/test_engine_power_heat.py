"""Power Consumption, Heat Dissipation and Heat Calculations built from ``examples/``
(plan M4). Every expected value is one the spec states, cited by section."""

from pathlib import Path

import pytest

from bomgen.engine.pipeline import build
from bomgen.io.loader import load_substation
from bomgen.models.bom import BuildResult
from bomgen.models.calc import HeatResult, PowerConsumption
from bomgen.models.panel import Ventilation

pytestmark = pytest.mark.golden

SUBSTATION_FILE = (
    Path(__file__).resolve().parents[2] / "examples" / "substations" / "gis01" / "substation.yaml"
)


@pytest.fixture(scope="module")
def result() -> BuildResult:
    return build(load_substation(SUBSTATION_FILE))


@pytest.fixture(scope="module")
def power(result: BuildResult) -> PowerConsumption:
    assert result.power is not None
    return result.power


@pytest.fixture(scope="module")
def heat(result: BuildResult) -> HeatResult:
    assert result.heat is not None
    return result.heat


def test_power_totals(power: PowerConsumption) -> None:
    # Power Consumption sheet: 2,177.5 W DC + 1,090.3 W AC = 3,267.8 W.
    assert power.dc_total_w == pytest.approx(2177.5)
    assert power.ac_total_w == pytest.approx(1090.3)
    assert power.total_w == pytest.approx(3267.8)


def test_power_blocks_per_cabinet_and_external_equipment(power: PowerConsumption) -> None:
    # Power Consumption sheet, layout: a DC and an AC block per cabinet in BOM order, then
    # "Power Consumption for External Equipment" (the annunciator), DC only.
    assert [c.panel_id for c in power.cabinets] == ["psa1", "psa2", "psa3", "ws"]
    assert all(c.dc is not None and c.ac is not None for c in power.cabinets)
    assert power.external is not None
    assert [line.source.panel_id for line in power.external.lines] == [None]


def test_required_airflow_of_the_psa_cabinets(heat: HeatResult) -> None:
    # Heat Dissipation and Heat Calculations sheets: 391, 391 and 172 m3/h against 716.
    forced = {c.panel_id: c.forced for c in heat.cabinets}
    assert [round(forced[p].required_m3h) for p in ("psa1", "psa2", "psa3")] == [391, 391, 172]
    assert all(forced[p].fan_m3h == 716 and forced[p].passes for p in ("psa1", "psa2", "psa3"))


def test_line_up_check(heat: HeatResult) -> None:
    # Heat Calculations - forced ventilation: sum 954.8 m3/h against 3 x 716 = 2,148.
    assert heat.line_up is not None
    assert heat.line_up.panel_ids == ("psa1", "psa2", "psa3")
    assert heat.line_up.required_m3h == pytest.approx(954.8, abs=0.05)
    assert heat.line_up.fan_m3h == 2148
    assert heat.line_up.passes


def test_ws_console_natural_convection(heat: HeatResult) -> None:
    # Heat Calculations - natural convection: A = 4.848 m2, dT = 6.96 C under 10 C.
    (ws,) = [c for c in heat.cabinets if c.panel_id == "ws"]
    assert ws.natural.area_m2 == pytest.approx(4.848, abs=0.0005)
    assert ws.natural.delta_t_c == pytest.approx(6.96, abs=0.005)
    assert ws.natural.limit_c == 10
    assert ws.natural.passes


def test_ventilation_choice(heat: HeatResult) -> None:
    # "Rule for the tool": 001/002 are auto and get fans from the heat of their other
    # parts; 003 is set to forced and the console to natural in the example (plan Q4).
    assert [c.ventilation for c in heat.cabinets] == [
        Ventilation.FORCED,
        Ventilation.FORCED,
        Ventilation.FORCED,
        Ventilation.NATURAL,
    ]


def test_heat_dissipation_blocks(heat: HeatResult) -> None:
    # Heat Dissipation layout: one block per cabinet, then "PSA Auxiliary Equipment"
    # outside the panels; no margin, unit heat = W x 3.41.
    blocks = heat.dissipation
    assert [b.panel_id for b in blocks] == ["psa1", "psa2", "psa3", "ws", None]
    for block in blocks:
        assert block.total_btu_h == pytest.approx(block.total_w * 3.41)
