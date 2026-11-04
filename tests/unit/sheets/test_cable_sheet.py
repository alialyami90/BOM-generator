"""The Cable Schedule sheet (ADR 0035, plan M65): loose rows that carry cable data."""

from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.library import Media, PortSpeed
from bomgen.models.project import CableRef, LooseExtra
from bomgen.models.sheet import Formula, SheetModel
from bomgen.sheets.workbook import build_workbook

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"
CORD = CableRef(
    from_tag="L2-ESW-A01", to_tag="L1-ESW-A11", length_m=2, media=Media.MM, speed=PortSpeed.G1
)


def with_items(loaded: LoadedSubstation, *items: LooseExtra) -> LoadedSubstation:
    material = loaded.substation.loose_material
    assert material is not None
    material = material.model_copy(update={"items": [*material.items, *items]})
    return replace(
        loaded, substation=loaded.substation.model_copy(update={"loose_material": material})
    )


def cell(model: SheetModel, ref: str) -> object:
    found = model.cells.get((int(ref[1:]), ord(ref[0]) - ord("A") + 1))
    return None if found is None else found.value


def test_a_cable_needs_both_ends() -> None:
    with pytest.raises(ValidationError):
        CableRef(from_tag=" ", to_tag="L1-ESW-A11")


def test_no_cable_schedule_without_cable_data() -> None:
    loaded = load_substation(EXAMPLE)
    names = [s.name for s in build_workbook(loaded, build(loaded)).sheets]
    assert "Cable Schedule" not in names


def test_a_loose_row_with_cable_data_writes_the_sheet() -> None:
    cord = LooseExtra(description="LC-LC duplex patch cord", qty=4, cable=CORD)
    loaded = with_items(load_substation(EXAMPLE), cord)
    result = build(loaded)
    sheets = build_workbook(loaded, result).sheets
    assert [s.name for s in sheets][-1] == "Cable Schedule"
    m = sheets[-1]
    assert cell(m, "A1") == "GIS Substation\nCable Schedule"
    assert [cell(m, f"{c}2") for c in "ABCDEFGHI"] == [
        "SR.NO",
        "FROM",
        "TO",
        "TYPE",
        "LENGTH (m)",
        "QUANTITY",
        "MAKE",
        "MODEL",
        "ORDERING CODE",
    ]
    assert [cell(m, f"{c}3") for c in "ABCDE"] == [
        1,
        "L2-ESW-A01",
        "L1-ESW-A11",
        "LC-LC duplex patch cord (1G MM)",
        2,
    ]
    qty = cell(m, "F3")
    assert isinstance(qty, Formula)
    assert result.loose is not None
    line = next(i for i, x in enumerate(result.loose.lines) if x.cable is not None)
    assert qty.text.startswith("='Loose Material'!D")
    assert qty.result == 4
    assert result.loose.lines[line].cable == CORD
    assert m.print_setup.orientation == "landscape"
    assert m.print_setup.repeat_rows == (1, 2)


def test_cable_schedule_comes_before_revision_history() -> None:
    cord = LooseExtra(description="LC-LC duplex patch cord", qty=4, cable=CORD)
    loaded = with_items(load_substation(EXAMPLE), cord)
    key = loaded.substation.document
    documents = dict(loaded.documents)
    documents[key] = documents[key].model_copy(update={"prepared": "A. Eng"})
    loaded = replace(loaded, documents=documents)
    names = [s.name for s in build_workbook(loaded, build(loaded)).sheets]
    assert names[-2:] == ["Cable Schedule", "Revision History"]


def test_written_workbook_keeps_the_quantity_formula(tmp_path: Path) -> None:
    import shutil

    import openpyxl

    from bomgen.build import build_substation

    shutil.copytree(EXAMPLE.parents[2], tmp_path / "p")
    file = tmp_path / "p" / "substations" / "gis01" / "substation.yaml"
    text = file.read_text(encoding="utf-8")
    cord = (
        "    - description: LC-LC duplex patch cord\n"
        "      qty: 4\n"
        "      cable: { from_tag: L2-ESW-A01, to_tag: CCR, length_m: 5, media: SM }\n"
    )
    file.write_text(text.replace('      qty: "1 Lot"\n', '      qty: "1 Lot"\n' + cord, 1))
    loaded = load_substation(file)
    out = build_substation(loaded, tmp_path / "out.xlsx", checks=False).path
    sheet = openpyxl.load_workbook(out)["Cable Schedule"]
    assert sheet["B3"].value == "L2-ESW-A01"
    assert sheet["D3"].value == "LC-LC duplex patch cord (SM)"
    assert str(sheet["F3"].value).startswith("='Loose Material'!D")
    assert sheet.print_title_rows == "$1:$2"
