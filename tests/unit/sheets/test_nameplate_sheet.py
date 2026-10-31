"""The Nameplates sheet (ADR 0026)."""

from dataclasses import replace
from pathlib import Path

from bomgen.engine.pipeline import build
from bomgen.io.loader import load_substation
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
