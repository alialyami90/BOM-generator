"""The Spare Parts sheet (ADR 0035, plan M64)."""

from dataclasses import replace
from pathlib import Path

from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.library import Category
from bomgen.models.sheet import Formula, SheetModel
from bomgen.models.substation import DesignBasis, SpareExtra, SparesList, SparesPolicy
from bomgen.sheets.workbook import build_workbook

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"
POLICY = SparesPolicy(percent={Category.SFP: 10}, minimum_per_part=1, categories=[Category.SFP])


def target(
    policy: SparesPolicy | None, edits: SparesList | None = None, summary: bool = False
) -> LoadedSubstation:
    loaded = load_substation(EXAMPLE)
    update: dict[str, object] = {
        "design_basis": DesignBasis(spares_policy=policy) if policy else None,
        "spares_list": edits,
    }
    if summary:
        update["output"] = loaded.substation.output.model_copy(update={"include": {"summary_bom"}})
    return replace(loaded, substation=loaded.substation.model_copy(update=update))


def sheets(loaded: LoadedSubstation) -> dict[str, SheetModel]:
    return {s.name: s for s in build_workbook(loaded, build(loaded)).sheets}


def cell(model: SheetModel, ref: str) -> object:
    found = model.cells.get((int(ref[1:]), ord(ref[0]) - ord("A") + 1))
    return None if found is None else found.value


def test_no_sheet_without_a_policy_or_edits() -> None:
    assert "Spare Parts" not in sheets(target(None))


def test_layout_and_rule_formula_without_the_summary() -> None:
    by_name = sheets(target(POLICY))
    assert list(by_name)[-1] == "Spare Parts"
    m = by_name["Spare Parts"]
    assert cell(m, "A1") == "GIS Substation\nSpare Parts"
    assert [cell(m, f"{c}2") for c in "ABCDEFGH"] == [
        "SR.NO",
        "DESCRIPTION",
        "INSTALLED QTY",
        "SPARE QTY",
        "MAKE",
        "MODEL",
        "ORDERING CODE",
        "BASIS",
    ]
    assert cell(m, "C3") == 4  # the summed value when no Summary BOM is written
    spare = cell(m, "D3")
    assert isinstance(spare, Formula)
    assert spare.text == "=MAX(1,ROUNDUP(C3*10/100,0))"
    assert spare.result == 1
    assert cell(m, "H3") == "10% of 4, min 1 = 1"
    assert m.print_setup.orientation == "landscape"


def test_installed_references_the_summary_when_written() -> None:
    by_name = sheets(target(POLICY, summary=True))
    assert list(by_name)[-2:] == ["Summary BOM", "Spare Parts"]
    installed = cell(by_name["Spare Parts"], "C3")
    assert isinstance(installed, Formula)
    assert installed.text.startswith("='Summary BOM'!C")
    assert installed.result == 4


def test_an_override_and_an_extra_are_values() -> None:
    edits = SparesList(items={"A9F74202": 5}, extra=[SpareExtra(description="Fuse kit", qty=2)])
    m = sheets(target(None, edits))["Spare Parts"]
    assert [cell(m, f"{c}3") for c in "CDH"] == [77, 5, "set to 5"]
    assert [cell(m, f"{c}4") for c in "BCDH"] == ["Fuse kit", None, 2, "added"]


def test_written_workbook_recalculates_the_spare(tmp_path: Path) -> None:
    from pycel import ExcelCompiler

    from bomgen.build import build_substation

    out = build_substation(target(POLICY, summary=True), tmp_path / "s.xlsx", checks=False).path
    excel = ExcelCompiler(filename=str(out))
    assert excel.evaluate("'Spare Parts'!C3") == 4
    assert excel.evaluate("'Spare Parts'!D3") == 1
