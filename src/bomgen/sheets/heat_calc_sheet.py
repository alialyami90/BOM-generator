"""Heat Calculations sheet (spec: Heat Dissipation and Heat Calculations sheets; plan M5).

Plain 11 pt worked equations: forced-ventilation airflow for the fan-cooled cabinets,
the line-up check, then natural convection for the others. Heat, airflow, area and
temperature rise are live formulas (OUT-5); the conclusions are ``IF`` formulas.
"""

from collections.abc import Mapping

from bomgen.models.calc import CabinetThermal, HeatResult, LineUpCheck
from bomgen.models.panel import Ventilation
from bomgen.models.project import DesignConstants
from bomgen.models.sheet import (
    BorderStyle,
    CellRange,
    CellStyle,
    CellValue,
    Formula,
    HeaderFooter,
    PrintSetup,
    SheetModel,
)
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder, ref

WIDTHS = {3: 14.43, 4: 26.0, 9: 6.86, 10: 12.57, 11: 12.86, 12: 12.0}
LAST_PRINTED_COL = 14  # N
SCALE = 78
ZOOM = 85
TMAX, TINT, K_AIR = "$K$3", "$K$4", "$K$5"

B, C, D, E, F, G, H = range(2, 9)
TEXT, TITLE, NUMBER = styles.HEAT_TEXT, styles.HEAT_TITLE, styles.HEAT_NUMBER


def heat_calculations_sheet(
    name: str,
    heat: HeatResult,
    dissipation_sheet: str,
    totals: Mapping[str | None, int],
    cabinet_names: Mapping[str, str],
    constants: DesignConstants,
    header_footer: HeaderFooter | None = None,
) -> SheetModel:
    sheet = SheetBuilder(name)
    for col, width in WIDTHS.items():
        sheet.width(col, width)
    _constants_box(sheet, constants)
    btu_h = {block.panel_id: block.total_btu_h for block in heat.dissipation}
    calc = _Calc(sheet, dissipation_sheet, totals, btu_h, cabinet_names, constants)

    forced = [c for c in heat.cabinets if c.ventilation is Ventilation.FORCED]
    # A natural block's coefficient box (I:M) on rows 3-5 would run into the constants box.
    row = 3 if forced else 7
    for cabinet in forced:
        row = calc.forced(row, cabinet)
    if heat.line_up is not None:
        row = calc.line_up(row, heat.line_up)
    for cabinet in heat.cabinets:
        if cabinet.ventilation is not Ventilation.FORCED:
            row = calc.natural(row, cabinet)

    setup = PrintSetup(
        orientation="landscape",
        scale=SCALE,
        margins=styles.CALC_MARGINS,
        print_area=CellRange(
            first_row=1, first_col=1, last_row=max(sheet.last_row, 5), last_col=LAST_PRINTED_COL
        ),
        zoom=ZOOM,
    )
    return sheet.build(setup, header_footer)


def _constants_box(sheet: SheetBuilder, constants: DesignConstants) -> None:
    rows = (
        ("TMax =", constants.t_max_c, "°C"),
        ("TInt =", constants.t_int_c, "°C"),
        ("k =", constants.air_constant_m3k_per_wh, "m³K/Wh"),
    )
    for offset, (label, value, unit) in enumerate(rows):
        sheet.set(3 + offset, 10, label, TEXT)
        sheet.set(3 + offset, 11, value, TEXT)
        sheet.set(3 + offset, 12, unit, TEXT)
    sheet.box(3, 10, 5, 12, outer=BorderStyle.MEDIUM)


def _if(test: str, passes: bool, yes: str, no: str) -> Formula:
    return Formula(text=f'=IF({test},"{yes}","{no}")', result=yes if passes else no)


class _Calc:
    def __init__(
        self,
        sheet: SheetBuilder,
        dissipation_sheet: str,
        totals: Mapping[str | None, int],
        btu_h: Mapping[str | None, float],
        cabinet_names: Mapping[str, str],
        constants: DesignConstants,
    ) -> None:
        self.sheet = sheet
        self.dissipation_sheet = dissipation_sheet
        self.totals = totals
        self.btu_h = btu_h
        self.names = cabinet_names
        self.constants = constants
        self.required: dict[str, str] = {}  # panel id -> cell holding its required airflow
        self.fans: dict[str, str] = {}  # panel id -> cell holding its fan throughput

    def _put(self, row: int, col: int, value: CellValue, style: CellStyle = TEXT) -> None:
        self.sheet.set(row, col, value, style)

    def _heat_loss(self, row: int, panel_id: str, heat_w: float) -> str:
        """'Total Heat Loss' from ``row``: BTU/h from Heat Dissipation and W; return W cell.

        A cabinet with no powered device has no Heat Dissipation block, so its loss is 0.
        """
        btu = self.constants.btu_per_w
        total = self.totals.get(panel_id)
        loss: CellValue = 0
        if total is not None:
            source = "=" + ref(self.dissipation_sheet, total, 11)
            loss = Formula(text=source, result=self.btu_h[panel_id])
        self._put(row, C, "=")
        self._put(row, D, loss, NUMBER)
        self._put(row, E, "BTU/HR")
        self._put(row, F, "or")
        self._put(row, G, Formula(text=f"=D{row}/{btu:g}", result=heat_w), NUMBER)
        self._put(row, H, "W")
        return f"G{row}"

    def forced(self, row: int, cabinet: CabinetThermal) -> int:
        check = cabinet.forced
        name = self.names[cabinet.panel_id]
        self._put(row, B, f"TOTAL HEAT DISSIPATION FOR {name.upper()}", TITLE)
        self._put(row + 2, B, "Total Heat Loss")
        watts = self._heat_loss(row + 3, cabinet.panel_id, check.heat_w)
        self._put(row + 5, B, "Air Flow Rate in m³/h =")
        self._put(row + 5, D, "(Total Heat Loss (W) x k) / (TMax - TInt)")
        airflow = Formula(text=f"={watts}*{K_AIR}/({TMAX}-{TINT})", result=check.required_m3h)
        self._put(row + 6, C, "=")
        self._put(row + 6, E, airflow, NUMBER)
        self._put(row + 6, F, "m³/h")
        self._put(row + 7, B, "Volumetric air flow that the installed fans must generate")
        self._put(row + 8, B, "Selected fan air throughput capacity")
        self._put(row + 8, C, "=")
        self._put(row + 8, E, check.fan_m3h, NUMBER)
        self._put(row + 8, F, "m³/h")
        self.required[cabinet.panel_id] = f"E{row + 6}"
        self.fans[cabinet.panel_id] = f"E{row + 8}"
        sentence = _if(
            f"E{row + 8}>=E{row + 6}",
            check.passes,
            "Selected fan throughput is sufficient for this cabinet.",
            "Selected fan throughput is NOT sufficient for this cabinet.",
        )
        self._put(row + 9, B, sentence)
        self.sheet.box(row, B, row + 9, H, outer=BorderStyle.MEDIUM)
        return row + 11

    def line_up(self, row: int, check: LineUpCheck) -> int:
        count = len(check.panel_ids)
        required = [self.required[p] for p in check.panel_ids]
        fans = [self.fans[p] for p in check.panel_ids]
        self._put(row, B, f"TOTAL HEAT DISSIPATION FOR {count} INTERNALLY OPEN PANELS", TITLE)
        self._put(row + 2, B, "Total required air flow =")
        self._put(row + 2, D, "Sum of the air flow required in each panel")
        self._put(row + 3, C, "=")
        total = Formula(text=f"=SUM({','.join(required)})", result=check.required_m3h)
        self._put(row + 3, D, total, NUMBER)
        self._put(row + 3, E, "m³/h")
        self._put(row + 5, B, "Total fans capacity =")
        self._put(row + 6, C, "=")
        self._put(row + 6, D, Formula(text=f"=SUM({','.join(fans)})", result=check.fan_m3h), NUMBER)
        self._put(row + 6, E, "m³/h")
        sentence = _if(
            f"D{row + 6}>=D{row + 3}",
            check.passes,
            "Total fan capacity is more than the total required air flow. Hence, the selected "
            "fan configuration is sufficient for temperature control.",
            "Total fan capacity is less than the total required air flow. The selected fan "
            "configuration is NOT sufficient.",
        )
        self._put(row + 7, B, sentence)
        self.sheet.box(row, B, row + 7, H, outer=BorderStyle.MEDIUM)
        return row + 9

    def natural(self, row: int, cabinet: CabinetThermal) -> int:
        check = cabinet.natural
        name = self.names[cabinet.panel_id]
        self._put(row, B, f"TOTAL HEAT DISSIPATION FOR {name.upper()}", TITLE)
        self._put(row, 9, "Heat transfer coefficient for sheet steel (W/m²°C) =")
        self._put(row, 13, self.constants.steel_coefficient_w_per_m2c)
        self.sheet.box(row, 9, row, 13, outer=BorderStyle.MEDIUM)
        coefficient = f"$M${row}"
        self._put(row + 1, B, "Total Heat Loss =")
        watts = self._heat_loss(row + 2, cabinet.panel_id, check.heat_w)
        dims = row + 4
        self._put(dims, B, "Cabinet H, W, D (m) =")
        self._put(dims, D, check.h_m)
        self._put(dims, E, check.w_m)
        self._put(dims, F, check.d_m)
        self._put(row + 5, B, "Surface area of panel =")
        self._put(row + 5, D, "1.8 x H x (W + D) + 1.4 x W x D")
        area = Formula(
            text=f"=1.8*D{dims}*(E{dims}+F{dims})+1.4*E{dims}*F{dims}", result=check.area_m2
        )
        self._put(row + 6, C, "=")
        self._put(row + 6, D, area, NUMBER)
        self._put(row + 6, E, "m²")
        self._put(row + 8, B, "Heat rise inside the panel =")
        self._put(row + 8, D, "Heat Loss (W) / (Surface area (m²) x Heat transfer coefficient)")
        rise = Formula(text=f"={watts}/(D{row + 6}*{coefficient})", result=check.delta_t_c)
        self._put(row + 9, C, "=")
        self._put(row + 9, D, rise, NUMBER)
        self._put(row + 9, E, "°C")
        sentence = _if(
            f"D{row + 9}<={TMAX}-{TINT}",
            check.passes,
            "Heat rise inside the cabinet is within the limit, so natural convection is "
            "sufficient.",
            "Heat rise inside the cabinet exceeds the limit; natural convection is NOT sufficient.",
        )
        self._put(row + 10, B, sentence)
        self.sheet.box(row + 1, B, row + 10, H, outer=BorderStyle.MEDIUM)
        return row + 12
