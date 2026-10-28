"""Heat Dissipation sheet (spec: Heat Dissipation and Heat Calculations sheets; plan M5).

Every row reads its Power Consumption row, so this sheet repeats no device data.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from bomgen.models.bom import QtySum
from bomgen.models.calc import CabinetHeat, HeatLine, HeatResult, LineRef
from bomgen.models.project import DesignConstants
from bomgen.models.sheet import (
    BorderStyle,
    CellRange,
    CellValue,
    Formula,
    HeaderFooter,
    PrintSetup,
    SheetModel,
)
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder, ref
from bomgen.sheets.power_sheet import BomSource

WIDTHS = {
    1: 6.0, 2: 11.71, 3: 14.0, 4: 10.0, 5: 61.71, 6: 17.86, 7: 34.86, 8: 9.71,
    10: 30.29, 11: 28.57, 12: 22.71, 13: 3.57,
}  # fmt: skip
LAST_PRINTED_COL = 13  # M
SCALE = 50
ZOOM = 70
AUXILIARY = "PSA Auxiliary Equipment"
HEAT = "0.00"

HEADERS = {
    2: "S.NO",
    3: "POWER SUPPLY INPUT\nTYPE",
    5: "COMPONENT DESCRIPTION",
    6: "MAKE",
    7: "MODEL NUMBER",
    8: "QTY",
    9: "UNIT W",
    10: "UNIT HEAT DISSIPATION\n(BTU/HR)",
    11: "TOTAL HEAT DISSIPATION (BTU/HR)",
    12: "TOTAL HEAT DISSIPATION\n(W)",
}
# Heat Dissipation column ← Power Consumption column (spec: C, D, E, F, G, H, I)
FROM_POWER = {3: 3, 4: 4, 5: 5, 6: 7, 7: 8, 8: 6, 9: 9}


@dataclass(frozen=True)
class HeatDissSheet:
    model: SheetModel
    totals: dict[str | None, int]  # TOTAL row per block; None is the auxiliary block


def heat_dissipation_sheet(
    name: str,
    heat: HeatResult,
    power_sheet: str,
    power_rows: Mapping[LineRef, int],
    sources: Mapping[LineRef, BomSource],
    cabinet_names: Mapping[str, str],
    constants: DesignConstants,
    header_footer: HeaderFooter | None = None,
) -> HeatDissSheet:
    sheet = SheetBuilder(name)
    for col, width in WIDTHS.items():
        sheet.width(col, width)
    sheet.height(1, 19.5)
    totals: dict[str | None, int] = {}
    row = 2
    for block in heat.dissipation:
        if not block.lines:
            continue
        title = AUXILIARY if block.panel_id is None else cabinet_names[block.panel_id]
        totals[block.panel_id] = _block(
            sheet, row, f"Total Heat Dissipation for {title}", block, power_sheet, power_rows,
            sources,
        )  # fmt: skip
        row = totals[block.panel_id] + 2
    _notes(sheet, row + 2, constants.btu_per_w, auxiliary=None in totals)

    setup = PrintSetup(
        orientation="landscape",
        scale=SCALE,
        margins=styles.CALC_MARGINS,
        center_horizontally=True,
        print_area=CellRange(
            first_row=1, first_col=1, last_row=sheet.last_row, last_col=LAST_PRINTED_COL
        ),
        zoom=ZOOM,
    )
    return HeatDissSheet(model=sheet.build(setup, header_footer), totals=totals)


def _block(
    sheet: SheetBuilder,
    row: int,
    title: str,
    block: CabinetHeat,
    power_sheet: str,
    power_rows: Mapping[LineRef, int],
    sources: Mapping[LineRef, BomSource],
) -> int:
    """Write one block from ``row``; return its TOTAL row."""
    sheet.merge(row, 1, row, 12, title, styles.CALC_TITLE)
    sheet.height(row, 23.25)
    sheet.height(row + 1, 16.5)
    header = row + 2
    for col, label in HEADERS.items():
        if col == 3:
            sheet.merge(header, 3, header, 4, label, styles.CALC_HEADER)
        else:
            sheet.set(header, col, label, styles.CALC_HEADER)
    sheet.height(header, 48.0)
    first = header + 1
    for number, line in enumerate(block.lines, start=1):
        _line(sheet, first + number - 1, number, line, power_sheet, power_rows, sources)
    last = first + len(block.lines) - 1
    sheet.box(header, 2, last, 12, outer=BorderStyle.MEDIUM, inner=BorderStyle.THIN)

    total = last + 1
    number_total = styles.with_format(styles.CALC_TOTAL, HEAT)
    sheet.set(total, 10, "TOTAL", styles.CALC_TOTAL)
    k = Formula(text=f"=SUM(K{first}:K{last})", result=block.total_btu_h)
    sheet.set(total, 11, k, number_total)
    sheet.set(
        total, 12, Formula(text=f"=SUM(L{first}:L{last})", result=block.total_w), number_total
    )
    sheet.height(total, 18.75)
    sheet.height(total + 1, 15.75)
    return total


def _line(
    sheet: SheetBuilder,
    row: int,
    number: int,
    line: HeatLine,
    power_sheet: str,
    power_rows: Mapping[LineRef, int],
    sources: Mapping[LineRef, BomSource],
) -> None:
    power = line.power
    source_row = power_rows[power.source]
    bom = sources[power.source].line
    qty: CellValue = bom.qty.value if isinstance(bom.qty, QtySum) else bom.qty
    results: dict[int, CellValue] = {
        3: power.supply_label,
        4: power.supply_type.value,
        5: bom.description,
        6: bom.make,
        7: bom.model,
        8: qty,
        9: power.unit_w,
    }
    data, number_style = styles.CALC_DATA, styles.with_format(styles.CALC_DATA, HEAT)
    sheet.set(row, 2, number, data)
    for col, power_col in FROM_POWER.items():
        text = "=" + ref(power_sheet, source_row, power_col)
        style = styles.CALC_DATA_TEXT if col == 5 else data
        sheet.set(row, col, Formula(text=text, result=results[col]), style)
    j = Formula(text=f"=(L{row}*{line.btu_per_w:g})/H{row}", result=line.unit_btu_h)
    sheet.set(row, 10, j, number_style)
    sheet.set(row, 11, Formula(text=f"=H{row}*J{row}", result=line.total_btu_h), number_style)
    sheet.set(row, 12, Formula(text=f"=I{row}*H{row}", result=line.total_w), number_style)
    sheet.height(row, 18.75)


def _notes(sheet: SheetBuilder, row: int, btu_per_w: float, *, auxiliary: bool) -> None:
    lines = [
        "CALCULATIONS:",
        f"1. Unit Heat Dissipation (BTU/Hr) = Unit Power Consumption (W) x {btu_per_w:g}",
        "2. Total Heat Dissipation (BTU/Hr) = Unit Heat Dissipation (BTU/Hr) x Device Quantity",
        "",
        "NOTES:",
        "1. The power values for devices are rated values as specified in manufacturer datasheets",
    ]
    if auxiliary:
        lines.append(
            "2. Heat Dissipation for Auxiliary Equipment is given for information. It is "
            "outside the PSA panels, so it is not included in the PSA panel fan calculation."
        )
    for offset, text in enumerate(lines):
        if text:
            sheet.set(row + offset, 2, text, styles.NOTE)
