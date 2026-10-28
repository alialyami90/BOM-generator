"""Writer: print setup and sheet view per OUT-7."""

import pytest
from writer_helpers import WriteAndOpen

from bomgen.models.sheet import CellRange, Margins, PrintSetup, SheetModel

CM = 1 / 2.54


def test_a4_portrait_fit_to_one_page_wide(write_and_open: WriteAndOpen) -> None:
    setup = PrintSetup(orientation="portrait", fit_to_width=1, fit_to_height=0)
    ws = write_and_open(SheetModel(name="1", print_setup=setup))["1"]
    assert ws.page_setup.paperSize == 9
    assert ws.page_setup.orientation == "portrait"
    pr = ws.sheet_properties.pageSetUpPr
    assert pr is not None
    assert pr.fitToPage is True
    assert ws.page_setup.fitToWidth in (1, None)  # 1 is the default openpyxl omits
    assert ws.page_setup.fitToHeight == 0


def test_landscape_with_scale(write_and_open: WriteAndOpen) -> None:
    setup = PrintSetup(orientation="landscape", scale=50)
    ws = write_and_open(SheetModel(name="Power Consumption", print_setup=setup))[
        "Power Consumption"
    ]
    assert ws.page_setup.orientation == "landscape"
    assert ws.page_setup.scale == 50
    pr = ws.sheet_properties.pageSetUpPr
    assert pr is None or not pr.fitToPage


def test_margins_in_cm(write_and_open: WriteAndOpen) -> None:
    margins = Margins(
        left_cm=1.8, right_cm=1.8, top_cm=1.9, bottom_cm=1.9, header_cm=0.5, footer_cm=0.6
    )
    ws = write_and_open(SheetModel(name="1", print_setup=PrintSetup(margins=margins)))["1"]
    assert ws.page_margins.left == pytest.approx(1.8 * CM)
    assert ws.page_margins.right == pytest.approx(1.8 * CM)
    assert ws.page_margins.top == pytest.approx(1.9 * CM)
    assert ws.page_margins.bottom == pytest.approx(1.9 * CM)
    assert ws.page_margins.header == pytest.approx(0.5 * CM)
    assert ws.page_margins.footer == pytest.approx(0.6 * CM)


def test_default_margins_are_the_bom_sheet_margins(write_and_open: WriteAndOpen) -> None:
    ws = write_and_open(SheetModel(name="1"))["1"]
    assert ws.page_margins.left == pytest.approx(1.0 * CM)
    assert ws.page_margins.top == pytest.approx(3.0 * CM)
    assert ws.page_margins.bottom == pytest.approx(2.0 * CM)


def test_centred_horizontally(write_and_open: WriteAndOpen) -> None:
    setup = PrintSetup(center_horizontally=True)
    ws = write_and_open(SheetModel(name="1", print_setup=setup))["1"]
    assert ws.print_options.horizontalCentered is True
    assert not ws.print_options.verticalCentered


def test_print_area_and_repeat_rows(write_and_open: WriteAndOpen) -> None:
    setup = PrintSetup(
        print_area=CellRange(first_row=1, first_col=1, last_row=71, last_col=7),
        repeat_rows=(1, 2),
    )
    ws = write_and_open(SheetModel(name="1", print_setup=setup))["1"]
    assert ws.print_area == "'1'!$A$1:$G$71"
    assert ws.print_title_rows == "$1:$2"


def test_page_break_preview_with_zoom(write_and_open: WriteAndOpen) -> None:
    setup = PrintSetup(page_break_preview=True, zoom=60)
    ws = write_and_open(SheetModel(name="1", print_setup=setup))["1"]
    assert ws.sheet_view.view == "pageBreakPreview"
    assert ws.sheet_view.zoomScale == 60


def test_normal_view_when_preview_is_off(write_and_open: WriteAndOpen) -> None:
    setup = PrintSetup(page_break_preview=False)
    ws = write_and_open(SheetModel(name="1", print_setup=setup))["1"]
    assert ws.sheet_view.view in (None, "normal")
