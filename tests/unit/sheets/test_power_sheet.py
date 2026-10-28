"""Power Consumption sheet (spec: Power Consumption sheet; Formatting → Calculation sheets)."""

import pytest

from bomgen.models.bom import BomLine, Group
from bomgen.models.calc import CabinetPower, LineRef, PowerBlock, PowerConsumption, PowerLine
from bomgen.models.library import LoadType, SupplyType
from bomgen.models.project import DesignConstants
from bomgen.models.sheet import BorderStyle, Formula, SheetModel
from bomgen.sheets.power_sheet import BomSource, PowerSheet, power_sheet


def pline(
    panel: str | None, index: int, supply: SupplyType, unit_w: float, qty: int = 1
) -> PowerLine:
    dc = supply is SupplyType.VDC
    return PowerLine(
        source=LineRef(panel_id=panel, line=index),
        supply_type=supply,
        voltage_v=125 if dc else 230,
        qty=qty,
        unit_w=unit_w,
        load_type=LoadType.CONTINUOUS if dc else LoadType.INTERMITTENT,
        current_factor=1.3,
    )


DC, AC = SupplyType.VDC, SupplyType.VAC
L2 = pline("psa1", 5, DC, 77)
L1 = pline("psa1", 6, DC, 77, qty=6)
LAMP = pline("psa1", 16, AC, 11)
WS = pline("ws", 3, DC, 91)
ANN = pline(None, 0, DC, 100)

POWER = PowerConsumption(
    cabinets=(
        CabinetPower(
            panel_id="psa1",
            dc=PowerBlock(supply_type=DC, lines=(L2, L1), margin=0.25),
            ac=PowerBlock(supply_type=AC, lines=(LAMP,), margin=0.25),
        ),
        CabinetPower(
            panel_id="ws", dc=PowerBlock(supply_type=DC, lines=(WS,), margin=0.25), ac=None
        ),
    ),
    external=PowerBlock(supply_type=DC, lines=(ANN,), margin=0.25),
)


def source(sheet: str, row: int, description: str, qty: int = 1) -> BomSource:
    bom = BomLine(group=Group.B, tag="T", description=description, qty=qty, make="Mk", model="Md")
    return BomSource(sheet=sheet, row=row, line=bom)


SOURCES = {
    L2.source: source("1", 8, "L2 switch"),
    L1.source: source("1", 9, "L1 switch", qty=6),
    LAMP.source: source("1", 19, "Lamp"),
    WS.source: source("4", 6, "Workstation"),
    ANN.source: source("4", 49, "Annunciator"),
}


@pytest.fixture
def sheet() -> PowerSheet:
    return power_sheet(
        "Power Consumption",
        POWER,
        SOURCES,
        {"psa1": "PSA Cabinet - 001", "ws": "WS Console"},
        DesignConstants(),
    )


def value(model: SheetModel, cell: str) -> object:
    col = ord(cell[0]) - ord("A") + 1
    found = model.cells.get((int(cell[1:]), col))
    return None if found is None else found.value


def text(model: SheetModel, cell: str) -> str:
    found = value(model, cell)
    assert isinstance(found, Formula)
    return found.text


def test_layout_of_the_first_cabinet(sheet: PowerSheet) -> None:
    m = sheet.model
    assert value(m, "A2") == "Power Consumption for PSA Cabinet - 001"
    assert "A2:L2" in [x.name for x in m.merges]
    assert value(m, "B4") == "DC LOAD"
    assert "B4:C4" in [x.name for x in m.merges]
    assert value(m, "B6") == "S.NO"
    assert value(m, "E6") == "COMPONENT DESCRIPTION"
    assert value(m, "N6") == "Required Load"
    assert sheet.rows[L2.source] == 7
    assert sheet.rows[L1.source] == 8
    assert value(m, "I9") == "TOTAL POWER (W)"
    assert value(m, "B11") == "AUX AC LOAD"
    assert value(m, "N13") is None  # sizing headers on the first header row only
    assert sheet.rows[LAMP.source] == 14


def test_bom_references(sheet: PowerSheet) -> None:
    m = sheet.model
    assert text(m, "E7") == "='1'!C8"
    assert text(m, "F7") == "='1'!D8"
    assert text(m, "G7") == "='1'!E8"
    assert text(m, "H7") == "='1'!F8"
    e8 = value(m, "E8")
    assert isinstance(e8, Formula)
    assert e8.result == "L1 switch"
    f8 = value(m, "F8")
    assert isinstance(f8, Formula)
    assert f8.result == 6


def test_typed_columns(sheet: PowerSheet) -> None:
    m = sheet.model
    assert [value(m, c) for c in ("B7", "C7", "D7", "I7", "K7")] == [
        1,
        "125V",
        "VDC",
        77,
        "CONTINUOUS",
    ]
    assert [value(m, c) for c in ("C14", "D14", "K14")] == ["230V", "VAC", "INTERMITTENT"]


def test_power_and_sizing_formulas(sheet: PowerSheet) -> None:
    m = sheet.model
    assert text(m, "J8") == "=F8*I8"
    assert text(m, "N8") == "=I8/125"
    assert text(m, "O8") == "=N8*1.3"
    assert text(m, "P8") == "=ROUNDUP(O8,0)"
    assert text(m, "Q8") == "=O8*F8"
    assert text(m, "R8") == "=Q8"
    assert text(m, "N14") == "=I14/230"
    j8 = value(m, "J8")
    assert isinstance(j8, Formula)
    assert j8.result == 462


def test_block_total_includes_margin(sheet: PowerSheet) -> None:
    total = value(sheet.model, "J9")
    assert isinstance(total, Formula)
    assert total.text == "=SUM(J7:J8)*1.25"
    assert total.result == pytest.approx(1.25 * 539)


def test_cabinet_without_ac_block_and_external_equipment(sheet: PowerSheet) -> None:
    m = sheet.model
    assert value(m, "A17") == "Power Consumption for WS Console"
    assert sheet.rows[WS.source] == 22
    assert text(m, "E22") == "='4'!C6"
    assert value(m, "A25") == "Power Consumption for External Equipment"
    assert sheet.rows[ANN.source] == 30
    assert text(m, "E30") == "='4'!C49"
    assert text(m, "N30") == "=I30/125"


def test_summary_sums_every_block_total(sheet: PowerSheet) -> None:
    m = sheet.model
    assert value(m, "A33") == "TOTAL POWER CONSUMPTION SUMMARY"
    assert value(m, "C36") == "125V DC LOAD"
    assert text(m, "G36") == "=SUM(J9,J23,J31)"
    assert value(m, "C37") == "230V AUX AC LOAD"
    assert text(m, "G37") == "=SUM(J15)"
    total = value(m, "G38")
    assert isinstance(total, Formula)
    assert total.text == "=SUM(G36:G37)"
    assert total.result == pytest.approx(POWER.total_w)
    assert value(m, "B40") == "NOTES:"
    note = value(m, "B41")
    assert isinstance(note, str)
    assert "25% margin" in note


def test_columns_and_print_setup(sheet: PowerSheet) -> None:
    m = sheet.model
    assert m.columns[5].width == 65.57
    assert m.columns[13].hidden
    assert m.columns[14].hidden
    setup = m.print_setup
    assert setup.orientation == "landscape"
    assert setup.scale == 49
    assert (setup.margins.left_cm, setup.margins.top_cm, setup.margins.bottom_cm) == (1.8, 1.9, 1.9)
    assert setup.print_area is not None
    assert setup.print_area.name == "A1:L42"
    assert setup.repeat_rows is None


def test_data_rows_are_framed(sheet: PowerSheet) -> None:
    cell = sheet.model.cells[(6, 2)]
    assert cell.style is not None
    assert cell.style.borders.left is BorderStyle.MEDIUM
    assert cell.style.borders.top is BorderStyle.MEDIUM
    inner = sheet.model.cells[(7, 5)]
    assert inner.style is not None
    assert inner.style.borders.left is BorderStyle.THIN
