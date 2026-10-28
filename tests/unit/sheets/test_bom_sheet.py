"""Panel BOM sheet layout (spec: Columns of a panel BOM; Formatting → Panel BOM sheets)."""

from typing import Any

import pytest

from bomgen.models.bom import BomLine, Group, LooseTable, PanelBom, QtySum
from bomgen.models.calc import LineRef
from bomgen.models.sheet import Borders, BorderStyle, CellStyle, Formula, SheetModel
from bomgen.sheets import styles
from bomgen.sheets.bom_sheet import bom_sheet


def line(group: Group, tag: str | None, **fields: Any) -> BomLine:
    values: dict[str, Any] = {"description": f"{tag} description", "qty": 1, "make": "Mk"}
    values.update(fields)
    return BomLine(group=group, tag=tag, **values)


def panel(*lines: BomLine) -> PanelBom:
    return PanelBom(
        panel_id="psa1",
        sheet_name="1",
        title=("861-GIS01-PSA-0001", "GIS Substation - PSA Cabinet - 001"),
        lines=lines,
    )


LINES = (
    line(Group.A, "PANEL", description="Cabinet\nBase\nEntry"),  # row 3
    line(Group.B, "FOPP", model="FEUR96", ordering_code="FEUR96", merge_fg=True),  # row 4
    line(Group.B, None, description="Spool", parent=1),  # row 5
    line(Group.B, None, description="Splice", parent=1),  # row 6
    line(Group.B, None, description="Pigtails", qty=96, model="PT", ordering_code="PT", parent=1),
    line(
        Group.B, "L2", ordering_code="6GK6222-6AB00-5CC0-Z A00+B06+C06+D06+E06+F06+G00", hwio=1
    ),  # 8
    line(Group.C, "SFP", qty=QtySum(parts=(24, 3)), revised=frozenset({"D"})),  # row 9
    line(Group.E, "CINC", qty="1 Lot"),  # separator at 10, row 11
    line(Group.H, "GROUND", description="Busbar\nInterface\nWire", make=None, hwio=3),  # 12/13
)


@pytest.fixture
def model() -> SheetModel:
    return bom_sheet(panel(*LINES)).model


def value(model: SheetModel, row: int, col: int) -> object:
    cell = model.cells.get((row, col))
    return None if cell is None else cell.value


def style(model: SheetModel, row: int, col: int) -> CellStyle:
    cell = model.cells[(row, col)]
    assert cell.style is not None
    return cell.style


def test_title_is_two_lines_merged_over_a_to_g(model: SheetModel) -> None:
    assert value(model, 1, 1) == "861-GIS01-PSA-0001\nGIS Substation - PSA Cabinet - 001"
    assert "A1:G1" in [m.name for m in model.merges]
    assert style(model, 1, 1) == styles.BOM_TITLE
    assert model.rows[1].height == 90


def test_header_row_labels(model: SheetModel) -> None:
    labels = [value(model, 2, col) for col in range(1, 9)]
    assert labels == [
        "SR.NO",
        "ITEM DESIGNATION",
        "DESCRIPTION",
        "QUANTITY",
        "MAKE",
        "MODEL",
        "ORDERING CODE",
        "HWIO",
    ]
    assert model.rows[2].height == 26.25


def test_sr_no_is_one_then_formula_skipping_separators(model: SheetModel) -> None:
    assert value(model, 3, 1) == 1
    assert value(model, 4, 1) == Formula(text="=A3+1", result=2)
    assert value(model, 11, 1) == Formula(text="=A9+1", result=8)
    assert value(model, 13, 1) == Formula(text="=A11+1", result=9)


def test_separator_rows_are_blank_and_boxed(model: SheetModel) -> None:
    for row in (10, 12):
        for col in range(1, 8):
            assert value(model, row, col) is None
            assert style(model, row, col).borders == Borders.all(BorderStyle.THIN)


def test_quantity_number_lot_and_sum(model: SheetModel) -> None:
    assert value(model, 7, 4) == 96
    assert value(model, 9, 4) == Formula(text="=24+3", result=27)
    assert value(model, 11, 4) == "1 Lot"


def test_parent_tag_merged_over_children(model: SheetModel) -> None:
    assert "B4:B7" in [m.name for m in model.merges]
    assert value(model, 4, 2) == "FOPP"


def test_model_and_code_merged_over_empty_children_only(model: SheetModel) -> None:
    names = [m.name for m in model.merges]
    assert "F4:F6" in names
    assert "G4:G6" in names
    assert value(model, 7, 6) == "PT"


def test_hwio_column_hidden_with_total(model: SheetModel) -> None:
    assert model.columns[8].hidden is True
    assert value(model, 1, 8) == Formula(text="=SUM(H3:H13)", result=4)
    assert value(model, 8, 8) == 1
    assert (5, 8) not in model.cells


def test_revised_cell_is_yellow(model: SheetModel) -> None:
    assert style(model, 9, 4).fill == "#FFFF00"
    assert style(model, 9, 3).fill is None


def test_row_heights(model: SheetModel) -> None:
    assert model.rows[3].height == 78.75  # three text lines
    assert model.rows[5].height == 30
    assert model.rows[8].height == 52.5  # long ordering code
    assert model.rows[13].height == 131.25  # grounding, three lines


def test_grounding_row_is_white_and_left_wrapped(model: SheetModel) -> None:
    assert style(model, 13, 3).fill == "#FFFFFF"
    assert style(model, 13, 3).alignment.horizontal == "left"
    assert style(model, 13, 3).alignment.wrap


def test_column_widths(model: SheetModel) -> None:
    widths = [model.columns[col].width for col in range(1, 8)]
    assert widths == [12.29, 53.71, 108.71, 23.14, 22.29, 43.43, 60.57]


def test_print_setup(model: SheetModel) -> None:
    setup = model.print_setup
    assert setup.orientation == "portrait"
    assert (setup.fit_to_width, setup.fit_to_height) == (1, 0)
    assert setup.center_horizontally
    m = setup.margins
    assert (m.left_cm, m.right_cm, m.top_cm, m.bottom_cm) == (1.0, 1.0, 3.0, 2.0)
    assert setup.repeat_rows == (1, 2)
    assert setup.print_area is not None
    assert setup.print_area.name == "A1:G13"
    assert setup.page_break_preview
    assert setup.zoom == 60


def test_row_map_covers_every_line() -> None:
    sheet = bom_sheet(panel(*LINES))
    assert sheet.rows[LineRef(panel_id="psa1", line=0)] == 3
    assert sheet.rows[LineRef(panel_id="psa1", line=8)] == 13
    assert len(sheet.rows) == len(LINES)


def test_loose_table_under_the_host_panel() -> None:
    loose = LooseTable(
        title=("GIS Substation", "PSA Panels Loose Material and Auxiliary Equipment"),
        host_panel="psa1",
        lines=(
            line(Group.B, "ANN", merge_fg=True, model="NAP", ordering_code="NAP"),
            line(Group.B, None, description="Mount", parent=0),
            line(Group.B, "FO", qty="1 Lot"),
        ),
    )
    sheet = bom_sheet(panel(*LINES), loose)
    model = sheet.model
    assert model.rows[14].height == 48.75  # gap after row 13
    assert (
        value(model, 15, 1) == "GIS Substation\nPSA Panels Loose Material and Auxiliary Equipment"
    )
    assert "A15:G15" in [m.name for m in model.merges]
    assert value(model, 16, 2) == "ITEM DESIGNATION"
    assert value(model, 17, 1) == 1  # numbering restarts
    assert value(model, 18, 1) == Formula(text="=A17+1", result=2)
    assert "B17:B18" in [m.name for m in model.merges]
    assert sheet.rows[LineRef(panel_id=None, line=2)] == 19
    assert model.print_setup.print_area is not None
    assert model.print_setup.print_area.name == "A1:G19"
    assert model.rows[2].height == 53.1  # header row on the host sheet
    assert value(model, 1, 8) == Formula(text="=SUM(H3:H13)", result=4)
