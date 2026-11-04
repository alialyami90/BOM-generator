"""Row notes and the optional Notes sheet (plan M71, ADR 0035 amendment): a note on an
equipment row, a hand-written panel row or a loose item reaches its BOM line, the Notes
sheet when chosen, and nowhere else in the workbook."""

from dataclasses import replace
from pathlib import Path

import pytest

from bomgen.engine.layout import layout_preview
from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.sheet import SheetModel
from bomgen.sheets.workbook import build_workbook

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"
NOTE = "Client asked for the spare port to face the door"


@pytest.fixture(scope="module")
def example() -> LoadedSubstation:
    return load_substation(EXAMPLE)


def noted(loaded: LoadedSubstation, *, include: bool = False) -> LoadedSubstation:
    """The example with a note on psa1's L2 switch row and on the first loose item."""
    first, *rest = loaded.panels
    devices = [
        d.model_copy(update={"note": NOTE}) if d.part_id == "RST2228-L2" else d
        for d in first.devices
    ]
    material = loaded.substation.loose_material
    assert material is not None
    items = [
        material.items[0].model_copy(update={"note": "Ship with the HMI"}),
        *material.items[1:],
    ]
    output = loaded.substation.output
    if include:
        output = output.model_copy(update={"include": {*output.include, "notes"}})
    substation = loaded.substation.model_copy(
        update={"loose_material": material.model_copy(update={"items": items}), "output": output}
    )
    return replace(
        loaded, panels=(first.model_copy(update={"devices": devices}), *rest), substation=substation
    )


def values(model: SheetModel) -> list[object]:
    return [c.value for c in model.cells.values()]


def test_a_panel_row_note_reaches_its_bom_line(example: LoadedSubstation) -> None:
    result = build(noted(example))
    line = next(x for x in result.panels[0].lines if x.part_id == "RST2228-L2")
    assert line.note == NOTE
    assert result.loose is not None
    assert result.loose.lines[0].note == "Ship with the HMI"


def test_an_equipment_note_is_copied_to_the_generated_rows(example: LoadedSubstation) -> None:
    equipment = [
        e.model_copy(update={"note": "Spare unit on site"}) if e.id == "gps" else e
        for e in example.substation.equipment
    ]
    target = replace(
        example, substation=example.substation.model_copy(update={"equipment": equipment})
    )
    rows = [d for p in layout_preview(target).panels for d in p.devices if d.part_id == "SEL-2488"]
    assert rows
    assert {d.note for d in rows} == {"Spare unit on site"}


def test_notes_are_printed_nowhere_unless_the_sheet_is_chosen(example: LoadedSubstation) -> None:
    loaded = noted(example)
    sheets = build_workbook(loaded, build(loaded)).sheets
    assert "Notes" not in [s.name for s in sheets]
    assert not [s.name for s in sheets if NOTE in values(s)]


def test_the_notes_sheet_lists_each_noted_row(example: LoadedSubstation) -> None:
    loaded = noted(example, include=True)
    sheets = build_workbook(loaded, build(loaded)).sheets
    notes = next(s for s in sheets if s.name == "Notes")

    def cell(ref: str) -> object:
        return notes.cells[(int(ref[1:]), ord(ref[0]) - 64)].value

    assert cell("A1") == "GIS Substation\nNotes"
    assert [cell(f"{c}2") for c in "ABCDE"] == ["SR.NO", "SHEET", "TAG", "DESCRIPTION", "NOTE"]
    assert [cell(f"{c}3") for c in "BCE"] == ["1", "PSA1-L2-ESW-A01", NOTE]
    assert [cell(f"{c}4") for c in "BE"] == ["Loose Material", "Ship with the HMI"]
    assert [s.name for s in sheets if NOTE in values(s)] == ["Notes"]


def test_no_notes_sheet_without_a_note(example: LoadedSubstation) -> None:
    output = example.substation.output.model_copy(update={"include": {"notes"}})
    loaded = replace(example, substation=example.substation.model_copy(update={"output": output}))
    assert "Notes" not in [s.name for s in build_workbook(loaded, build(loaded)).sheets]
