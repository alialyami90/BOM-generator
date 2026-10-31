"""Power Consumption sheet (spec: Power Consumption sheet; plan M5, step 12).

Every row references its BOM row for description, quantity, make and model, so the
BOM and the calculation always describe the same equipment (OUT-5).
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from bomgen.models.bom import BomLine, QtySum
from bomgen.models.calc import LineRef, PowerBlock, PowerConsumption, PowerLine
from bomgen.models.library import SupplyType
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

WIDTHS = {
    1: 8.29, 2: 10.86, 3: 13.86, 4: 12.0, 5: 65.57, 6: 7.29, 7: 25.0, 8: 33.0,
    9: 34.29, 10: 25.57, 11: 19.29, 12: 8.71, 15: 22.0, 16: 22.0, 17: 22.0, 18: 22.0,
}  # fmt: skip
HIDDEN = (13, 14)  # M-N
LAST_PRINTED_COL = 12  # L
SCALE = 49
ZOOM = 70

HEADERS = (
    "S.NO",
    "POWER SUPPLY",
    "INPUT\nTYPE",
    "COMPONENT DESCRIPTION",
    "QTY",
    "MAKE",
    "MODEL NUMBER",
    "UNIT POWER CONSUMPTION (W)",
    "TOTAL POWER (W)",
    "TYPE OF LOAD",
)
SIZING_HEADERS = (
    "Required Load",
    "Required Load +30%",
    "MCB rating per device",
    "For Main MCB Calculation",
    "Continuous Current Flow for COR Selection (A)",
)
BLOCK_LABELS = {SupplyType.VDC: "DC LOAD", SupplyType.VAC: "AUX AC LOAD"}

TITLE_HEIGHT = 23.25
GAP_HEIGHT = 18.0
LABEL_HEIGHT = 20.25
HEADER_HEIGHT = 32.25
ROW_HEIGHT = 18.75
AFTER_BLOCK_HEIGHT = 15.75
FOOTNOTE_LINE_HEIGHT = 15.0  # per line; Excel doesn't fit a merged cell's height
FOOTNOTE_GAP = 2  # blank rows between the NOTES and the footnotes, as in the reference

# columns
B, C, D, E, F, G, H, I, J, K = range(2, 12)  # noqa: E741 - column letters
N, O, P, Q, R = range(14, 19)  # noqa: E741


@dataclass(frozen=True)
class BomSource:
    """Where a BOM line was written, and the line itself (for cached results)."""

    sheet: str
    row: int
    line: BomLine


@dataclass(frozen=True)
class PowerSheet:
    model: SheetModel
    rows: dict[LineRef, int]  # Power Consumption row of every power line


def power_sheet(
    name: str,
    power: PowerConsumption,
    sources: Mapping[LineRef, BomSource],
    cabinet_names: Mapping[str, str],
    constants: DesignConstants,
    header_footer: HeaderFooter | None = None,
    footnotes: Sequence[str] = (),
) -> PowerSheet:
    layout = _Layout(SheetBuilder(name), sources)
    sheet = layout.sheet
    for col, width in WIDTHS.items():
        sheet.width(col, width)
    for col in HIDDEN:
        sheet.width(col, hidden=True)
    sheet.height(1, 19.5)

    row = 2
    for cabinet in power.cabinets:
        title = f"Power Consumption for {cabinet_names[cabinet.panel_id]}"
        row = layout.cabinet(row, title, (cabinet.dc, cabinet.ac))
    if power.external is not None:
        row = layout.cabinet(row, "Power Consumption for External Equipment", (power.external,))
    row = layout.summary(row, constants, power)
    row = _notes(sheet, row + 1, constants)
    _footnotes(sheet, row + FOOTNOTE_GAP, footnotes)

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
    return PowerSheet(model=sheet.build(setup, header_footer), rows=layout.rows)


class _Layout:
    def __init__(self, sheet: SheetBuilder, sources: Mapping[LineRef, BomSource]) -> None:
        self.sheet = sheet
        self.sources = sources
        self.rows: dict[LineRef, int] = {}
        self.dc_totals: list[tuple[int, float]] = []  # (row of J total, value)
        self.ac_totals: list[tuple[int, float]] = []
        self._sizing_headers_written = False

    def cabinet(self, row: int, title: str, blocks: tuple[PowerBlock | None, ...]) -> int:
        """Title and blocks from ``row``; return the next free row."""
        self.sheet.merge(row, 1, row, LAST_PRINTED_COL, title, styles.CALC_TITLE)
        self.sheet.height(row, TITLE_HEIGHT)
        self.sheet.height(row + 1, GAP_HEIGHT)
        row += 2
        for block in blocks:
            if block is not None and block.lines:
                row = self._block(row, block)
        return row

    def _block(self, row: int, block: PowerBlock) -> int:
        sheet = self.sheet
        sheet.merge(row, B, row, C, BLOCK_LABELS[block.supply_type], styles.CALC_BLOCK_LABEL)
        sheet.height(row, LABEL_HEIGHT)
        sheet.height(row + 1, GAP_HEIGHT)
        header = row + 2
        for col, label in enumerate(HEADERS, start=B):
            sheet.set(header, col, label, styles.CALC_HEADER)
        if not self._sizing_headers_written:
            for col, label in enumerate(SIZING_HEADERS, start=N):
                sheet.set(header, col, label, styles.CALC_HEADER)
            self._sizing_headers_written = True
        sheet.height(header, HEADER_HEIGHT)

        first = header + 1
        for number, line in enumerate(block.lines, start=1):
            self._line(first + number - 1, number, line)
        last = first + len(block.lines) - 1
        sheet.box(header, B, last, K, outer=BorderStyle.MEDIUM, inner=BorderStyle.THIN)

        total = last + 1
        sheet.set(total, I, "TOTAL POWER (W)", styles.CALC_TOTAL)
        factor = 1 + block.margin
        text = f"=SUM(J{first}:J{last})*{factor:g}"
        sheet.set(total, J, Formula(text=text, result=block.total_w), styles.CALC_TOTAL)
        sheet.height(total, ROW_HEIGHT)
        sheet.height(total + 1, AFTER_BLOCK_HEIGHT)
        totals = self.dc_totals if block.supply_type is SupplyType.VDC else self.ac_totals
        totals.append((total, block.total_w))
        return total + 2

    def _line(self, row: int, number: int, line: PowerLine) -> None:
        sheet, source = self.sheet, self.sources[line.source]
        self.rows[line.source] = row
        bom = source.line
        data, text = styles.CALC_DATA, styles.CALC_DATA_TEXT

        def bom_ref(col: int, result: CellValue) -> Formula:
            value = result if not isinstance(result, Formula) else result.result
            return Formula(text="=" + ref(source.sheet, source.row, col), result=value)

        qty: CellValue = bom.qty.value if isinstance(bom.qty, QtySum) else bom.qty
        sheet.set(row, B, number, data)
        sheet.set(row, C, line.supply_label, data)
        sheet.set(row, D, line.supply_type.value, data)
        sheet.set(row, E, bom_ref(3, bom.description), text)
        sheet.set(row, F, bom_ref(4, qty), data)
        sheet.set(row, G, bom_ref(5, bom.make), data)
        sheet.set(row, H, bom_ref(6, bom.model), data)
        sheet.set(row, I, line.unit_w, data)
        sheet.set(row, J, Formula(text=f"=F{row}*I{row}", result=line.total_w), data)
        sheet.set(row, K, line.load_type.value, data)
        volts = f"{line.voltage_v:g}"
        factor = f"{line.current_factor:g}"
        sheet.set(row, N, Formula(text=f"=I{row}/{volts}", result=line.current_a), data)
        o = Formula(text=f"=N{row}*{factor}", result=line.current_with_margin_a)
        sheet.set(row, O, o, data)
        p: CellValue = line.branch_mcb_a  # ADR 0028: the row's own branch MCB
        if p is None:
            p = Formula(text=f"=ROUNDUP(O{row},0)", result=line.device_mcb_a)
        sheet.set(row, P, p, data)
        sheet.set(row, Q, Formula(text=f"=O{row}*F{row}", result=line.main_contribution_a), data)
        sheet.set(row, R, Formula(text=f"=Q{row}", result=line.main_contribution_a), data)
        sheet.height(row, ROW_HEIGHT)

    def summary(self, row: int, constants: DesignConstants, power: PowerConsumption) -> int:
        sheet = self.sheet
        sheet.merge(
            row, 1, row, LAST_PRINTED_COL, "TOTAL POWER CONSUMPTION SUMMARY", styles.CALC_TITLE
        )
        sheet.height(row, TITLE_HEIGHT)
        sheet.height(row + 1, LABEL_HEIGHT)
        header = row + 2
        sheet.set(header, B, "S.NO", styles.CALC_SUMMARY)
        sheet.merge(header, C, header, F, "LOAD TYPE", styles.CALC_SUMMARY)
        sheet.set(header, G, "POWER CONSUMED (W)", styles.CALC_SUMMARY)
        rows = (
            (f"{constants.dc_voltage_v:g}V DC LOAD", self.dc_totals, power.dc_total_w),
            (f"{constants.ac_voltage_v:g}V AUX AC LOAD", self.ac_totals, power.ac_total_w),
        )
        for offset, (label, totals, total_w) in enumerate(rows, start=1):
            r = header + offset
            sheet.set(r, B, offset, styles.CALC_SUMMARY)
            sheet.merge(r, C, r, F, label, styles.CALC_SUMMARY_TEXT)
            sheet.set(r, G, _sum([f"J{t}" for t, _w in totals], total_w), styles.CALC_SUMMARY)
        total = header + len(rows) + 1
        sheet.merge(total, E, total, F, "TOTAL POWER (W)", styles.CALC_SUMMARY_TOTAL)
        text = f"=SUM(G{header + 1}:G{total - 1})"
        sheet.set(total, G, Formula(text=text, result=power.total_w), styles.CALC_SUMMARY_TOTAL)
        for r in range(header, total + 1):
            sheet.height(r, 16.5)
        return total + 1


def _sum(cells: list[str], result: float) -> CellValue:
    if not cells:
        return 0
    return Formula(text=f"=SUM({','.join(cells)})", result=result)


def _notes(sheet: SheetBuilder, row: int, constants: DesignConstants) -> int:
    notes = (
        "NOTES:",
        f"1. Total power calculation is inclusive of {constants.power_margin * 100:g}% margin "
        "to accommodate for scalability and expandability requirements",
        "2. The power values for devices are rated values as specified in manufacturer datasheets",
    )
    for offset, note in enumerate(notes):
        sheet.set(row + offset, B, note, styles.NOTE)
    return row + len(notes)


def _footnotes(sheet: SheetBuilder, row: int, footnotes: Sequence[str]) -> None:
    """One row per footnote, merged across the printed columns and wrapped."""
    width = sum(WIDTHS.get(col, 0) for col in range(B, LAST_PRINTED_COL + 1))
    for offset, footnote in enumerate(footnotes):
        lines = sum(max(1, math.ceil(len(line) / width)) for line in footnote.split("\n"))
        sheet.merge(row + offset, B, row + offset, LAST_PRINTED_COL, footnote, styles.FOOTNOTE)
        sheet.height(row + offset, lines * FOOTNOTE_LINE_HEIGHT)
