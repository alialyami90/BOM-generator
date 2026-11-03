"""The Summary BOM sheet (ADR 0035, plan M63)."""

from dataclasses import replace
from pathlib import Path

from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.bom import SummaryLine, SummarySource, SummaryTable
from bomgen.models.calc import LineRef
from bomgen.models.sheet import Formula, SheetModel
from bomgen.sheets.summary_sheet import summary_sheet
from bomgen.sheets.workbook import build_workbook

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"


def with_output(loaded: LoadedSubstation, **update: object) -> LoadedSubstation:
    output = loaded.substation.output.model_copy(update=update)
    return replace(loaded, substation=loaded.substation.model_copy(update={"output": output}))


def test_no_summary_sheet_unless_included() -> None:
    loaded = load_substation(EXAMPLE)
    names = [sheet.name for sheet in build_workbook(loaded, build(loaded)).sheets]
    assert "Summary BOM" not in names


def test_included_summary_comes_after_heat_calculations() -> None:
    loaded = with_output(load_substation(EXAMPLE), include={"summary_bom"})
    names = [sheet.name for sheet in build_workbook(loaded, build(loaded)).sheets]
    assert names[-2:] == ["Heat Calculations", "Summary BOM"]


def test_the_summary_sheet_name_is_an_output_setting() -> None:
    loaded = load_substation(EXAMPLE)
    sheet_names = loaded.substation.output.sheet_names.model_copy(
        update={"summary_bom": "Procurement"}
    )
    loaded = with_output(loaded, include={"summary_bom"}, sheet_names=sheet_names)
    assert build_workbook(loaded, build(loaded)).sheets[-1].name == "Procurement"


# Layout on its own.

P1, P2, LOOSE = "p1", "p2", None
SUMMARY = SummaryTable(
    lines=(
        SummaryLine(
            description="2A,2P MCB",
            qty=4,
            make="Schneider",
            model="A9F74202",
            ordering_code="A9F74202",
            sources=(
                SummarySource(ref=LineRef(panel_id=P1, line=0), tag="P1-Q1", qty=1),
                SummarySource(ref=LineRef(panel_id=P1, line=1), tag="P1-Q2", qty=2),
                SummarySource(ref=LineRef(panel_id=P2, line=0), tag="P2-Q1", qty=1),
            ),
        ),
        SummaryLine(
            description="Patch cords",
            qty="1 Lot",
            sources=(SummarySource(ref=LineRef(panel_id=LOOSE, line=3), tag="FO", qty="1 Lot"),),
        ),
    )
)
CELLS = {
    LineRef(panel_id=P1, line=0): ("1", 20),
    LineRef(panel_id=P1, line=1): ("1", 21),
    LineRef(panel_id=P2, line=0): ("2", 20),
    LineRef(panel_id=LOOSE, line=3): ("Loose Material", 6),
}
SHEETS = {P1: "1", P2: "2", LOOSE: "Loose Material"}


def cell(model: SheetModel, ref: str) -> object:
    found = model.cells.get((int(ref[1:]), ord(ref[0]) - ord("A") + 1))
    return None if found is None else found.value


def sheet() -> SheetModel:
    return summary_sheet("Summary BOM", "GIS Substation", SUMMARY, CELLS, SHEETS)


def test_title_and_header_row() -> None:
    m = sheet()
    assert cell(m, "A1") == "GIS Substation\nSummary BOM"
    assert "A1:G1" in [x.name for x in m.merges]
    assert [cell(m, f"{c}2") for c in "ABCDEFG"] == [
        "SR.NO",
        "DESCRIPTION",
        "QUANTITY",
        "MAKE",
        "MODEL",
        "ORDERING CODE",
        "WHERE USED",
    ]


def test_quantity_sums_the_source_bom_cells() -> None:
    m = sheet()
    assert cell(m, "C3") == Formula(text="=SUM('1'!D20:D21,'2'!D20)", result=4)
    assert [cell(m, f"{c}3") for c in "DEF"] == ["Schneider", "A9F74202", "A9F74202"]
    assert cell(m, "G3") == "1: P1-Q1, P1-Q2 (3); 2: P2-Q1 (1)"


def test_text_quantity_references_its_one_cell() -> None:
    m = sheet()
    assert cell(m, "A4") == Formula(text="=A3+1", result=2)
    assert cell(m, "C4") == Formula(text="='Loose Material'!D6", result="1 Lot")
    assert cell(m, "G4") == "Loose Material: FO (1 Lot)"


def test_landscape_a4_with_repeating_title_rows() -> None:
    setup = sheet().print_setup
    assert setup.orientation == "landscape"
    assert (setup.fit_to_width, setup.fit_to_height) == (1, 0)
    assert setup.repeat_rows == (1, 2)
    assert setup.print_area is not None
    assert setup.print_area.name == "A1:G4"
