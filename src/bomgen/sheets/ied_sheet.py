"""The IED Schedule reference sheet: the schedule's rows and the ports they take per speed,
media and side, so the switch count can be audited (plan M80, ADR 0035 amendment). Written
only when ``output.include`` names it and the network has a schedule.

One row per schedule row and port need; the side columns are formulas on QTY and PORTS PER
IED (OUT-5), and a totals block sums them per speed, media and landing with SUMIFS.
"""

from collections.abc import Sequence
from typing import Any

from bomgen.models.sheet import CellRange, CellValue, Formula, HeaderFooter, PrintSetup, SheetModel
from bomgen.models.substation import IedRow
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder
from bomgen.sheets.summary_sheet import CENTRE, HEADER, TEXT, TITLE_HEIGHT, TITLE_STYLE

HEADERS = (
    "SR.NO",
    "BAY",
    "IED",
    "QTY",
    "PORTS PER IED",
    "SPEED",
    "MEDIA",
    "ATTACHMENT",
    "LANDS ON",
    "SIDE A PORTS",
    "SIDE B PORTS",
)
WIDTHS = (8.0, 14.0, 28.0, 8.0, 14.0, 10.0, 10.0, 18.0, 12.0, 14.0, 14.0)
CELL_STYLES = (CENTRE, TEXT, TEXT, CENTRE, CENTRE, CENTRE, CENTRE, TEXT, CENTRE, CENTRE, CENTRE)
TITLE = "IED Schedule"
ATTACHMENT = {"dual": "Dual (A and B)", "single_a": "Side A only", "single_b": "Side B only"}
TOTAL_HEADERS = {6: "SPEED", 7: "MEDIA", 9: "LANDS ON", 10: "SIDE A PORTS", 11: "SIDE B PORTS"}


def schedule_lines(rows: Sequence[IedRow]) -> list[dict[str, Any]]:
    """One line per schedule row and port need, with the ports it takes on each side."""
    lines = []
    for ied in rows:
        for need in ied.ports:
            ports = ied.qty * need.count
            lines.append(
                {
                    "bay": ied.bay,
                    "ied": ied.name,
                    "qty": ied.qty,
                    "ports": need.count,
                    "speed": need.speed.value,
                    "media": need.media.value,
                    "attachment": ATTACHMENT[ied.attachment],
                    "lands_on": ied.lands_on.upper(),
                    "side_a": ports if ied.attachment != "single_b" else 0,
                    "side_b": ports if ied.attachment != "single_a" else 0,
                }
            )
    return lines


def ied_sheet(
    name: str,
    substation: str,
    rows: Sequence[IedRow],
    header_footer: HeaderFooter | None = None,
) -> SheetModel:
    sheet = SheetBuilder(name)
    for col, width in enumerate(WIDTHS, start=1):
        sheet.width(col, width)
    last_col = len(HEADERS)
    sheet.merge(1, 1, 1, last_col, f"{substation}\n{TITLE}", TITLE_STYLE)
    sheet.height(1, TITLE_HEIGHT)
    for col, label in enumerate(HEADERS, start=1):
        sheet.set(2, col, label, HEADER)
    row = 2
    totals: dict[tuple[str, str, str], list[int]] = {}
    for line in schedule_lines(rows):
        row += 1
        sr_no: CellValue = 1 if row == 3 else Formula(text=f"=A{row - 1}+1", result=row - 2)
        sums = totals.setdefault((line["speed"], line["media"], line["lands_on"]), [0, 0])
        sums[0] += line["side_a"]
        sums[1] += line["side_b"]
        side = Formula(text=f"=D{row}*E{row}", result=line["qty"] * line["ports"])
        values = (
            sr_no,
            *(line[k] for k in ("bay", "ied", "qty", "ports", "speed", "media")),
            line["attachment"],
            line["lands_on"],
            side if line["side_a"] else 0,
            side if line["side_b"] else 0,
        )
        for col, (value, style) in enumerate(zip(values, CELL_STYLES, strict=True), 1):
            sheet.set(row, col, value, style)
    last = row
    row += 2
    for col, label in TOTAL_HEADERS.items():
        sheet.set(row, col, label, HEADER)
    for (speed, media, landing), (side_a, side_b) in totals.items():
        row += 1
        for col, value in ((6, speed), (7, media), (9, landing)):
            sheet.set(row, col, value, CENTRE)
        for col, letter, result in ((10, "J", side_a), (11, "K", side_b)):
            text = (
                f"=SUMIFS({letter}$3:{letter}${last},F$3:F${last},F{row},"
                f"G$3:G${last},G{row},I$3:I${last},I{row})"
            )
            sheet.set(row, col, Formula(text=text, result=result), CENTRE)
    setup = PrintSetup(
        orientation="landscape",
        fit_to_width=1,
        fit_to_height=0,
        margins=styles.BOM_MARGINS,
        center_horizontally=True,
        print_area=CellRange(first_row=1, first_col=1, last_row=row, last_col=last_col),
        repeat_rows=(1, 2),
    )
    return sheet.build(setup, header_footer)
