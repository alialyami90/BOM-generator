"""Sheet model: accepted defaults and the inputs it rejects before anything is written."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from bomgen.models.sheet import (
    Borders,
    BorderStyle,
    Cell,
    CellRange,
    CellStyle,
    Font,
    Formula,
    HeaderFooter,
    HFZone,
    Merge,
    PrintSetup,
    SheetModel,
    WorkbookModel,
)


def test_defaults_describe_a_plain_portrait_a4_sheet() -> None:
    sheet = SheetModel(name="1")
    assert sheet.cells == {}
    assert sheet.print_setup.paper == "A4"
    assert sheet.print_setup.orientation == "portrait"
    assert sheet.print_setup.page_break_preview is True
    assert sheet.header_footer is None


def test_cell_style_is_hashable_and_equal_by_value() -> None:
    a = CellStyle(font=Font(size=20, bold=True), fill="#a6a6a6")
    b = CellStyle(font=Font(size=20, bold=True), fill="#A6A6A6")
    assert a == b
    assert hash(a) == hash(b)


def test_borders_all_sets_every_side() -> None:
    borders = Borders.all(BorderStyle.THIN)
    assert {borders.left, borders.right, borders.top, borders.bottom} == {BorderStyle.THIN}


def test_formula_must_start_with_equals() -> None:
    assert Formula(text="=A3+1").text == "=A3+1"
    with pytest.raises(ValidationError, match="start with '='"):
        Formula(text="A3+1")


def test_formula_needs_an_expression_after_equals() -> None:
    with pytest.raises(ValidationError, match="expression after '='"):
        Formula(text="=")


@pytest.mark.parametrize("value", [True, float("nan"), float("inf")])
def test_cell_rejects_bool_and_non_finite_numbers(value: object) -> None:
    with pytest.raises(ValidationError):
        Cell.model_validate({"value": value})


def test_colour_must_be_hex_rgb() -> None:
    with pytest.raises(ValidationError, match="#RRGGBB"):
        CellStyle(fill="grey")


@pytest.mark.parametrize("key", [(0, 1), (1, 0), (1_048_577, 1), (1, 16_385)])
def test_cell_address_must_be_inside_excel_limits(key: tuple[int, int]) -> None:
    with pytest.raises(ValidationError, match="outside the sheet"):
        SheetModel(name="1", cells={key: Cell(value=1)})


def test_merge_must_span_two_or_more_cells() -> None:
    with pytest.raises(ValidationError, match="at least two cells"):
        Merge(first_row=1, first_col=1, last_row=1, last_col=1)


def test_merge_corners_must_be_ordered() -> None:
    with pytest.raises(ValidationError, match="first row/column"):
        Merge(first_row=4, first_col=2, last_row=2, last_col=2)


def test_overlapping_merges_are_rejected() -> None:
    with pytest.raises(ValidationError, match="overlap"):
        SheetModel(
            name="1",
            merges=(
                Merge(first_row=1, first_col=1, last_row=1, last_col=7),
                Merge(first_row=1, first_col=7, last_row=3, last_col=7),
            ),
        )


def test_covered_cells_of_a_merge_must_be_empty() -> None:
    with pytest.raises(ValidationError, match=r"B5 is covered by merge B4:B7"):
        SheetModel(
            name="1",
            cells={(4, 2): Cell(value="PSA1-FOPP-CCR-A01"), (5, 2): Cell(value="x")},
            merges=(Merge(first_row=4, first_col=2, last_row=7, last_col=2),),
        )


def test_scale_and_fit_to_page_are_exclusive() -> None:
    with pytest.raises(ValidationError, match="either scale or fit"):
        PrintSetup(scale=50, fit_to_width=1)


@pytest.mark.parametrize("field", ["scale", "zoom"])
def test_scale_and_zoom_are_10_to_400(field: str) -> None:
    with pytest.raises(ValidationError):
        PrintSetup.model_validate({field: 5})


def test_repeat_rows_must_be_ordered() -> None:
    with pytest.raises(ValidationError, match="repeat_rows"):
        PrintSetup(repeat_rows=(2, 1))


def test_print_area_must_be_ordered() -> None:
    with pytest.raises(ValidationError, match="first row/column"):
        CellRange(first_row=10, first_col=1, last_row=1, last_col=7)


def test_only_one_header_zone_may_hold_the_picture() -> None:
    logo = Path("logo.png")
    with pytest.raises(ValidationError, match="one picture"):
        HeaderFooter(header_left=HFZone(image=logo), header_right=HFZone(image=logo))


def test_workbook_needs_a_sheet() -> None:
    with pytest.raises(ValidationError):
        WorkbookModel(sheets=())


def test_sheet_names_are_unique_ignoring_case() -> None:
    with pytest.raises(ValidationError, match="duplicate sheet name"):
        WorkbookModel(sheets=(SheetModel(name="Heat"), SheetModel(name="HEAT")))


def test_sheet_name_follows_excel_rules() -> None:
    with pytest.raises(ValidationError):
        SheetModel(name="a/b")
