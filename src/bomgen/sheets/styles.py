"""Named cell styles from the spec section "Formatting" (the plan's style tokens).

Sizes are points; colours come from the Office 2007 theme the spec names: grey
#A6A6A6 / #D9D9D9 and dark blue #1F497D.
"""

from bomgen.models.sheet import Alignment, Borders, BorderStyle, CellStyle, Font, Margins

GREY_DARK = "#A6A6A6"
GREY_LIGHT = "#D9D9D9"
DARK_BLUE = "#1F497D"
YELLOW = "#FFFF00"
WHITE = "#FFFFFF"

# Page setup margins (Formatting → page setup)
BOM_MARGINS = Margins(left_cm=1.0, right_cm=1.0, top_cm=3.0, bottom_cm=2.0)
CALC_MARGINS = Margins(left_cm=1.8, right_cm=1.8, top_cm=1.9, bottom_cm=1.9)

THIN = Borders.all(BorderStyle.THIN)
MEDIUM = Borders.all(BorderStyle.MEDIUM)

_CENTRE = Alignment(horizontal="center", vertical="center")
_CENTRE_WRAP = Alignment(horizontal="center", vertical="center", wrap=True)
_LEFT_WRAP = Alignment(horizontal="left", vertical="center", wrap=True)

# Panel BOM sheets
BOM_TITLE = CellStyle(
    font=Font(size=24, bold=True), fill=GREY_DARK, alignment=_CENTRE_WRAP, borders=THIN
)
BOM_HEADER = CellStyle(font=Font(size=20, bold=True), alignment=_CENTRE_WRAP, borders=THIN)
BOM_CENTRE = CellStyle(font=Font(size=20), alignment=_CENTRE, borders=THIN)
BOM_CENTRE_WRAP = CellStyle(font=Font(size=20), alignment=_CENTRE_WRAP, borders=THIN)
BOM_DESIGNATION = CellStyle(font=Font(size=20, bold=True), alignment=_LEFT_WRAP, borders=THIN)
BOM_DESCRIPTION = CellStyle(font=Font(size=20), alignment=_LEFT_WRAP, borders=THIN)
BOM_SEPARATOR = CellStyle(borders=THIN)

# Calculation sheets (Power Consumption, Heat Dissipation)
CALC_TITLE = CellStyle(
    font=Font(size=18, bold=True, underline="single", color=DARK_BLUE),
    alignment=Alignment(horizontal="left", vertical="center"),
)
CALC_BLOCK_LABEL = CellStyle(
    font=Font(size=15, bold=True, color=DARK_BLUE),
    fill=GREY_LIGHT,
    alignment=_CENTRE,
    borders=MEDIUM,
)
CALC_HEADER = CellStyle(
    font=Font(size=12, bold=True, color=DARK_BLUE), fill=GREY_LIGHT, alignment=_CENTRE_WRAP
)
CALC_DATA = CellStyle(font=Font(size=12, bold=True), alignment=_CENTRE)
CALC_DATA_TEXT = CellStyle(font=Font(size=12, bold=True), alignment=_LEFT_WRAP)
CALC_TOTAL = CellStyle(
    font=Font(size=12, bold=True, color=DARK_BLUE),
    fill=GREY_LIGHT,
    alignment=_CENTRE,
    borders=MEDIUM,
)
CALC_SUMMARY = CellStyle(font=Font(size=12, bold=True), alignment=_CENTRE, borders=MEDIUM)
CALC_SUMMARY_TEXT = CellStyle(
    font=Font(size=12, bold=True),
    alignment=Alignment(horizontal="left", vertical="center"),
    borders=MEDIUM,
)
CALC_SUMMARY_TOTAL = CALC_SUMMARY.model_copy(update={"fill": GREY_LIGHT})
NOTE = CellStyle()

# Heat Calculations: plain 11 pt text
HEAT_TEXT = CellStyle()
HEAT_TITLE = CellStyle(font=Font(bold=True, underline="single"))
HEAT_NUMBER = CellStyle(number_format="0.00")


def with_fill(style: CellStyle, fill: str) -> CellStyle:
    return style.model_copy(update={"fill": fill})


def with_format(style: CellStyle, number_format: str) -> CellStyle:
    return style.model_copy(update={"number_format": number_format})
