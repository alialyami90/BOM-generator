"""Heat Dissipation and Heat Calculations sheets (spec: Heat Dissipation and Heat
Calculations sheets; Formatting → Calculation sheets)."""

import pytest

from bomgen.models.bom import BomLine, Group
from bomgen.models.calc import (
    CabinetHeat,
    CabinetPower,
    CabinetThermal,
    ForcedVentCheck,
    HeatLine,
    HeatResult,
    LineRef,
    LineUpCheck,
    NaturalConvCheck,
    PowerBlock,
    PowerConsumption,
    PowerLine,
)
from bomgen.models.library import LoadType, SupplyType
from bomgen.models.panel import Ventilation
from bomgen.models.project import DesignConstants
from bomgen.models.sheet import BorderStyle, Formula, SheetModel
from bomgen.sheets.heat_calc_sheet import heat_calculations_sheet
from bomgen.sheets.heat_diss_sheet import HeatDissSheet, heat_dissipation_sheet
from bomgen.sheets.power_sheet import BomSource, PowerSheet, power_sheet

DC, AC = SupplyType.VDC, SupplyType.VAC
CONSTANTS = DesignConstants()
NAMES = {"psa1": "PSA Cabinet - 001", "ws": "WS Console"}


def pline(
    panel: str | None, index: int, supply: SupplyType, unit_w: float, qty: int = 1
) -> PowerLine:
    dc = supply is DC
    return PowerLine(
        source=LineRef(panel_id=panel, line=index),
        supply_type=supply,
        voltage_v=125 if dc else 230,
        qty=qty,
        unit_w=unit_w,
        load_type=LoadType.CONTINUOUS,
        current_factor=1.3,
    )


L1 = pline("psa1", 6, DC, 77, qty=6)
LAMP = pline("psa1", 16, AC, 11)
WS = pline("ws", 3, DC, 91)
AUX = pline(None, 0, DC, 100)

POWER = PowerConsumption(
    cabinets=(
        CabinetPower(
            panel_id="psa1",
            dc=PowerBlock(supply_type=DC, lines=(L1,), margin=0.25),
            ac=PowerBlock(supply_type=AC, lines=(LAMP,), margin=0.25),
        ),
        CabinetPower(
            panel_id="ws", dc=PowerBlock(supply_type=DC, lines=(WS,), margin=0.25), ac=None
        ),
    ),
    external=PowerBlock(supply_type=DC, lines=(AUX,), margin=0.25),
)


def source(sheet: str, row: int, description: str, qty: int = 1) -> BomSource:
    bom = BomLine(group=Group.B, tag="T", description=description, qty=qty, make="Mk", model="Md")
    return BomSource(sheet=sheet, row=row, line=bom)


SOURCES = {
    L1.source: source("1", 9, "L1 switch", qty=6),
    LAMP.source: source("1", 19, "Lamp"),
    WS.source: source("4", 6, "Workstation"),
    AUX.source: source("4", 49, "Annunciator"),
}


def heat_line(line: PowerLine) -> HeatLine:
    return HeatLine(power=line, btu_per_w=3.41)


PSA1_W = 6 * 77 + 11
FORCED = CabinetThermal(
    panel_id="psa1",
    ventilation=Ventilation.FORCED,
    forced=ForcedVentCheck(panel_id="psa1", heat_w=PSA1_W, required_m3h=193.93, fan_m3h=716),
    natural=NaturalConvCheck(
        panel_id="psa1", heat_w=PSA1_W, h_m=2.1, w_m=0.8, d_m=0.8, area_m2=6.94,
        delta_t_c=12.39, limit_c=10,
    ),
)  # fmt: skip
NATURAL = CabinetThermal(
    panel_id="ws",
    ventilation=Ventilation.NATURAL,
    forced=ForcedVentCheck(panel_id="ws", heat_w=91, required_m3h=37.31, fan_m3h=0),
    natural=NaturalConvCheck(
        panel_id="ws", heat_w=91, h_m=1.2, w_m=1.0, d_m=0.8, area_m2=5.008,
        delta_t_c=3.30, limit_c=10,
    ),
)  # fmt: skip
HEAT = HeatResult(
    dissipation=(
        CabinetHeat(panel_id="psa1", lines=(heat_line(L1), heat_line(LAMP))),
        CabinetHeat(panel_id="ws", lines=(heat_line(WS),)),
        CabinetHeat(panel_id=None, lines=(heat_line(AUX),)),
    ),
    cabinets=(FORCED, NATURAL),
    line_up=LineUpCheck(panel_ids=("psa1",), required_m3h=193.93, fan_m3h=716),
)


@pytest.fixture
def power() -> PowerSheet:
    return power_sheet("Power Consumption", POWER, SOURCES, NAMES, CONSTANTS)


@pytest.fixture
def dissipation(power: PowerSheet) -> HeatDissSheet:
    return heat_dissipation_sheet(
        "Heat Dissipation", HEAT, "Power Consumption", power.rows, SOURCES, NAMES, CONSTANTS
    )


@pytest.fixture
def calculations(dissipation: HeatDissSheet) -> SheetModel:
    return heat_calculations_sheet(
        "Heat Calculations", HEAT, "Heat Dissipation", dissipation.totals, NAMES, CONSTANTS
    )


def value(model: SheetModel, cell: str) -> object:
    col = ord(cell[0]) - ord("A") + 1
    found = model.cells.get((int(cell[1:]), col))
    return None if found is None else found.value


def formula(model: SheetModel, cell: str) -> Formula:
    found = value(model, cell)
    assert isinstance(found, Formula), f"{cell} holds {found!r}"
    return found


# Heat Dissipation


def test_heat_dissipation_blocks_and_totals(dissipation: HeatDissSheet) -> None:
    m = dissipation.model
    assert value(m, "A2") == "Total Heat Dissipation for PSA Cabinet - 001"
    assert "A2:L2" in [x.name for x in m.merges]
    assert value(m, "B4") == "S.NO"
    assert "C4:D4" in [x.name for x in m.merges]
    assert dissipation.totals == {"psa1": 7, "ws": 13, None: 19}
    assert value(m, "A9") == "Total Heat Dissipation for WS Console"
    assert value(m, "A15") == "Total Heat Dissipation for PSA Auxiliary Equipment"
    assert value(m, "J7") == "TOTAL"


def test_heat_dissipation_reads_every_column_from_power_consumption(
    dissipation: HeatDissSheet, power: PowerSheet
) -> None:
    m = dissipation.model
    row = power.rows[L1.source]
    # Heat Dissipation C, D, E, F, G, H, I <- Power Consumption C, D, E, G, H, F, I
    expected = {"C": "C", "D": "D", "E": "E", "F": "G", "G": "H", "H": "F", "I": "I"}
    for heat_col, power_col in expected.items():
        assert formula(m, f"{heat_col}5").text == f"='Power Consumption'!{power_col}{row}"
    assert formula(m, "E5").result == "L1 switch"
    assert formula(m, "H5").result == 6
    assert formula(m, "I5").result == 77


def test_heat_dissipation_formulas(dissipation: HeatDissSheet) -> None:
    m = dissipation.model
    assert formula(m, "J5").text == "=(L5*3.41)/H5"
    assert formula(m, "K5").text == "=H5*J5"
    assert formula(m, "L5").text == "=I5*H5"
    assert formula(m, "L5").result == pytest.approx(462)
    assert formula(m, "K5").result == pytest.approx(462 * 3.41)
    total = formula(m, "K7")
    assert total.text == "=SUM(K5:K6)"
    assert total.result == pytest.approx(PSA1_W * 3.41)
    assert formula(m, "L7").text == "=SUM(L5:L6)"
    cell = m.cells[(5, 11)]
    assert cell.style is not None
    assert cell.style.number_format == "0.00"


def test_heat_dissipation_notes_and_print_setup(dissipation: HeatDissSheet) -> None:
    m = dissipation.model
    assert value(m, "B23") == "CALCULATIONS:"
    note = value(m, "B24")
    assert isinstance(note, str)
    assert "x 3.41" in note
    auxiliary = value(m, "B29")
    assert isinstance(auxiliary, str)
    assert "Auxiliary Equipment" in auxiliary
    setup = m.print_setup
    assert setup.orientation == "landscape"
    assert setup.scale == 50
    assert setup.print_area is not None
    assert setup.print_area.name == "A1:M29"


def test_heat_dissipation_framed_with_medium_outline(dissipation: HeatDissSheet) -> None:
    corner = dissipation.model.cells[(4, 2)]
    assert corner.style is not None
    assert corner.style.borders.top is BorderStyle.MEDIUM
    assert corner.style.borders.left is BorderStyle.MEDIUM


# Heat Calculations


def test_constants_box(calculations: SheetModel) -> None:
    assert [value(calculations, c) for c in ("J3", "K3", "K4", "K5")] == ["TMax =", 35, 25, 4.1]


def test_forced_ventilation_block(calculations: SheetModel) -> None:
    m = calculations
    assert value(m, "B3") == "TOTAL HEAT DISSIPATION FOR PSA CABINET - 001"
    heat = formula(m, "D6")
    assert heat.text == "='Heat Dissipation'!K7"
    assert heat.result == pytest.approx(PSA1_W * 3.41)
    assert formula(m, "G6").text == "=D6/3.41"
    airflow = formula(m, "E9")
    assert airflow.text == "=G6*$K$5/($K$3-$K$4)"
    assert airflow.result == pytest.approx(193.93)
    assert value(m, "E11") == 716
    sentence = formula(m, "B12")
    assert sentence.text.startswith("=IF(E11>=E9,")
    assert sentence.result == "Selected fan throughput is sufficient for this cabinet."


def test_line_up_check(calculations: SheetModel) -> None:
    m = calculations
    assert value(m, "B14") == "TOTAL HEAT DISSIPATION FOR 1 INTERNALLY OPEN PANELS"
    assert formula(m, "D17").text == "=SUM(E9)"
    assert formula(m, "D20").text == "=SUM(E11)"
    assert formula(m, "B21").text.startswith("=IF(D20>=D17,")


def test_natural_convection_block(calculations: SheetModel) -> None:
    m = calculations
    assert value(m, "B23") == "TOTAL HEAT DISSIPATION FOR WS CONSOLE"
    assert value(m, "M23") == 5.5
    assert formula(m, "D25").text == "='Heat Dissipation'!K13"
    assert [value(m, c) for c in ("D27", "E27", "F27")] == [1.2, 1.0, 0.8]
    area = formula(m, "D29")
    assert area.text == "=1.8*D27*(E27+F27)+1.4*E27*F27"
    assert area.result == pytest.approx(5.008)
    rise = formula(m, "D32")
    assert rise.text == "=G25/(D29*$M$23)"
    sentence = formula(m, "B33")
    assert sentence.text.startswith("=IF(D32<=$K$3-$K$4,")
    assert isinstance(sentence.result, str)
    assert sentence.result.startswith("Heat rise inside the cabinet is within the limit")


def test_failing_checks_say_not_sufficient() -> None:
    failing = FORCED.model_copy(
        update={"forced": FORCED.forced.model_copy(update={"fan_m3h": 100.0})}
    )
    heat = HEAT.model_copy(update={"cabinets": (failing,), "line_up": None})
    m = heat_calculations_sheet("H", heat, "Heat Dissipation", {"psa1": 7}, NAMES, CONSTANTS)
    sentence = formula(m, "B12")
    assert isinstance(sentence.result, str)
    assert "NOT sufficient" in sentence.result


def test_heat_calculations_print_setup(calculations: SheetModel) -> None:
    setup = calculations.print_setup
    assert setup.orientation == "landscape"
    assert setup.scale == 78
    assert setup.print_area is not None
    assert setup.print_area.name == "A1:N33"


def test_cabinet_without_powered_devices_has_zero_heat_loss() -> None:
    # The engine checks every cabinet, and gives an empty Heat Dissipation block to one
    # with no powered device; that block has no TOTAL row to read.
    empty = NaturalConvCheck(
        panel_id="spare", heat_w=0, h_m=2.0, w_m=0.8, d_m=0.6, area_m2=5.712, delta_t_c=0,
        limit_c=10,
    )  # fmt: skip
    spare = CabinetThermal(
        panel_id="spare",
        ventilation=Ventilation.NATURAL,
        forced=ForcedVentCheck(panel_id="spare", heat_w=0, required_m3h=0, fan_m3h=0),
        natural=empty,
    )
    heat = HEAT.model_copy(
        update={
            "dissipation": (*HEAT.dissipation, CabinetHeat(panel_id="spare", lines=())),
            "cabinets": (spare,),
            "line_up": None,
        }
    )
    power = power_sheet("Power Consumption", POWER, SOURCES, NAMES, CONSTANTS)
    names = {**NAMES, "spare": "Spare Cabinet"}
    dissipation = heat_dissipation_sheet(
        "Heat Dissipation", heat, "Power Consumption", power.rows, SOURCES, names, CONSTANTS
    )
    assert "spare" not in dissipation.totals
    m = heat_calculations_sheet(
        "Heat Calculations", heat, "Heat Dissipation", dissipation.totals, names, CONSTANTS
    )
    assert value(m, "B3") == "TOTAL HEAT DISSIPATION FOR SPARE CABINET"
    assert value(m, "D5") == 0
    assert formula(m, "G5").text == "=D5/3.41"
    assert formula(m, "G5").result == 0
