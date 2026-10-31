"""The Nameplates sheet (ADR 0026)."""

from dataclasses import replace
from pathlib import Path

from bomgen.engine.pipeline import build
from bomgen.io.loader import load_substation
from bomgen.models.bom import Nameplate, PanelNameplates
from bomgen.models.sheet import Formula, SheetModel
from bomgen.sheets.nameplate_sheet import nameplate_sheet
from bomgen.sheets.workbook import build_workbook

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"


def test_no_plates_means_no_nameplates_sheet() -> None:
    loaded = load_substation(EXAMPLE)
    result = build(loaded).model_copy(update={"nameplates": ()})
    names = [sheet.name for sheet in build_workbook(loaded, result).sheets]
    assert "Nameplates" not in names
    assert names[4:6] == ["Loose Material", "Power Consumption"]


def test_the_sheet_name_is_an_output_setting() -> None:
    loaded = load_substation(EXAMPLE)
    output = loaded.substation.output
    names = output.sheet_names.model_copy(update={"nameplates": "Plates"})
    substation = loaded.substation.model_copy(
        update={"output": output.model_copy(update={"sheet_names": names})}
    )
    sheets = build_workbook(replace(loaded, substation=substation), build(loaded)).sheets
    assert sheets[5].name == "Plates"


# Nameplates sheet layout, on its own (spec: Nameplates sheet, ADR 0026).

PLATES = (
    PanelNameplates(
        panel_id="psa1",
        plates=(
            Nameplate(text="L2_ESW_A01", device="LAN-A switch"),
            Nameplate(text="DHPCC_GW_1", device="Gateway"),
        ),
    ),
    PanelNameplates(panel_id="ws", plates=(Nameplate(text="MONITOR", device="Monitor"),)),
)
NUMBERS = {"psa1": "861-GIS01-PSA-0001", "ws": "861-GIS01-WS-0001"}


def cell(model: SheetModel, ref: str) -> object:
    found = model.cells.get((int(ref[1:]), ord(ref[0]) - ord("A") + 1))
    return None if found is None else found.value


def test_title_and_header_row() -> None:
    m = nameplate_sheet("Nameplates", "GIS Substation", PLATES, NUMBERS)
    assert cell(m, "A1") == "GIS Substation\nDevice Nameplates"
    assert "A1:D1" in [x.name for x in m.merges]
    assert [cell(m, f"{c}2") for c in "ABCD"] == ["SR.NO", "PANEL", "PLATE TEXT", "DEVICE"]


def test_one_row_per_plate_with_sr_no_continuing_across_panels() -> None:
    m = nameplate_sheet("Nameplates", "GIS Substation", PLATES, NUMBERS)
    assert [cell(m, f"{c}3") for c in "ABCD"] == [1, NUMBERS["psa1"], "L2_ESW_A01", "LAN-A switch"]
    assert cell(m, "A4") == Formula(text="=A3+1", result=2)
    assert [cell(m, f"{c}5") for c in "ABC"] == [
        Formula(text="=A4+1", result=3),
        NUMBERS["ws"],
        "MONITOR",
    ]


def test_columns_and_print_setup() -> None:
    m = nameplate_sheet("Nameplates", "GIS Substation", PLATES, NUMBERS)
    assert [m.columns[c].width for c in (1, 2, 3, 4)] == [12.29, 43.43, 53.71, 108.71]
    setup = m.print_setup
    assert setup.orientation == "portrait"
    assert (setup.fit_to_width, setup.fit_to_height) == (1, 0)
    assert setup.repeat_rows == (1, 2)
    assert setup.print_area is not None
    assert setup.print_area.name == "A1:D5"
