"""Library health: what needs review and what is weak (M68)."""

from pathlib import Path

import pytest

from bomgen.io.loader import load_library
from bomgen.library_store.edit import SetValue, apply_edits
from bomgen.library_store.health import library_health, missing_sources, parts_in_use
from bomgen.models.library import Library

ROOT = Path(__file__).parents[3]
L1, L2 = "RST2228-L1-24MM", "RST2228-L2"
ASSUMED = {"kind": "assumed", "ref": "the spec's example workbook"}


@pytest.fixture(scope="module")
def base() -> Library:
    return load_library(ROOT / "examples" / "library.yaml")


def _edited(base: Library, *edits: tuple[list[object], object]) -> Library:
    result = apply_edits(base, [SetValue(path=path, value=value) for path, value in edits])
    assert result.library is not None, result.problems
    return result.library


def test_counts_parts_by_state_with_every_state_listed(base: Library) -> None:
    library = _edited(base, (["devices", L1, "state"], "draft"))

    states = library_health(library).states

    assert states == {"draft": 1, "reviewed": 0, "released": len(base.devices) - 1, "obsolete": 0}


def test_lists_parts_with_an_assumed_source_and_the_fields(base: Library) -> None:
    library = _edited(base, (["devices", L1, "sources"], {"unit_power_w": ASSUMED}))

    assert library_health(library).assumed == [(L1, ["unit_power_w"])]


def test_lists_parts_without_an_alternative(base: Library) -> None:
    assert L1 not in library_health(base).alone
    library = _edited(base, (["devices", L1, "alt_group"], "ONLY-ONE"))

    alone = library_health(library).alone

    assert L1 in alone
    assert L2 not in alone


def test_lists_obsolete_parts_projects_use_with_where(base: Library) -> None:
    library = _edited(base, (["devices", L2, "state"], "obsolete"))
    used = {L2: ["JFGP2 / GIS Substation"], L1: ["JFGP2 / GIS Substation"]}

    assert library_health(library, used).obsolete_in_use == [(L2, ["JFGP2 / GIS Substation"])]


def test_lists_mcb_brand_sets_missing_a_rating_of_the_default_set(base: Library) -> None:
    brand = {**base.catalogues.mcb.model_dump(mode="json", exclude_none=True), "id": "short"}
    brand["ratings_a"] = [6, 10]
    library = _edited(base, (["catalogue_brands", "mcb"], [brand]))

    gaps = library_health(library).mcb_gaps

    missing = [r for r in base.catalogues.mcb.ratings_a if r not in (6, 10)]
    assert gaps == [("short", missing)]


def test_lists_housekeeping_roles_the_default_fills_and_a_brand_leaves_empty(
    base: Library,
) -> None:
    roles = base.catalogues.housekeeping.model_dump(mode="json", exclude_none=True)
    assert "door_switch" not in roles  # the example's lamp includes it: not a gap
    roles.pop("nameplate")
    library = _edited(base, (["catalogue_brands", "housekeeping"], [{"id": "bare", **roles}]))

    assert library_health(library).housekeeping_gaps == [("bare", ["nameplate"])]


def test_missing_sources_are_the_sized_figures_set_without_one(base: Library) -> None:
    library = _edited(base, (["devices", L1, "sources"], {"unit_power_w": ASSUMED}))
    device = library.get(L1)
    assert device is not None

    missing = missing_sources(device)

    assert "unit_power_w" not in missing
    assert "height_u" in missing


def test_parts_in_use_reads_each_substations_equipment(tmp_path: Path) -> None:
    file = tmp_path / "substation.yaml"
    file.write_text(
        f"equipment:\n  - {{id: l1, part_id: {L1}, role: l1_switch}}\n  - {{id: x, role: other}}\n"
    )
    broken = tmp_path / "broken.yaml"
    broken.write_text("equipment: [unclosed\n")

    used = parts_in_use({"P / S": file, "P / B": broken, "P / gone": tmp_path / "none.yaml"})

    assert used == {L1: ["P / S"]}
