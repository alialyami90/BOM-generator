"""The parts a Parts row offers (plan M83, Q74 (a), Q82).

A row offers its role's category, at the role's Purdue level for the L1, L2 and EXT
switches, the alternatives of its own part only, no obsolete part, and its current part
always. The whole category stays in ``options`` for *Search all parts*.
"""

import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from bomgen.app.parts import ADD_CATEGORIES, ADD_ROLE, ROLE_CATEGORY, parts_page, row_choices
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.store import LibraryStore
from bomgen.models.library import Category, Library
from bomgen.models.substation import EquipmentRole

REPO = Path(__file__).parents[3]
EXAMPLES = REPO / "examples"
SHIPPED = REPO / "data" / "library" / "psa-devices.yaml"

L2_GROUP = {
    "RST2228-L2",
    "RST2228-L2.MOXA-LOW",
    "RST2228-L2.MOXA-MID",
    "RST2228-L2.MOXA-HIGH",
    "RST2228-L2.CISCO-LOW",
    "RST2228-L2.CISCO-MID",
    "RST2228-L2.CISCO-HIGH",
}


def _project(root: Path, library: Path | None = None) -> Path:
    shutil.copytree(EXAMPLES, root / "workspace" / "jfgp2-pkg3")
    project = root / "workspace" / "jfgp2-pkg3"
    if library is not None:
        shutil.copyfile(library, project / "library.yaml")
    return project / "project.yaml"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return _project(tmp_path)


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


@pytest.fixture(scope="module")
def shipped(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """The Parts page of the example with the shipped library (as test_engine_shipped_library)."""
    root = tmp_path_factory.mktemp("shipped")
    found = parts_page(_project(root, SHIPPED), "gis01", LibraryStore(root / "libraries"))
    json.dumps(found["parts"])
    return found["parts"]


@pytest.fixture(scope="module")
def shipped_library() -> Library:
    return Library.model_validate(read_yaml(SHIPPED).data)


def edit(file: Path, old: str, new: str) -> None:
    text = file.read_text(encoding="utf-8")
    assert old in text
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def parts(project: Path, store: LibraryStore) -> Any:
    found = parts_page(project, "gis01", store)["parts"]
    json.dumps(found)
    return found


def row(found: Any, entry_id: str) -> Any:
    return next(r for r in found["rows"] if r["id"] == entry_id)


def ids(choices: list[dict[str, Any]]) -> list[str]:
    return [c["part_id"] for c in choices]


def test_the_l1_row_offers_only_l1_switches(project: Path, store: LibraryStore) -> None:
    offered = ids(row(parts(project, store), "l1")["choices"])

    assert set(offered) == {
        "RST2228-L1-24MM",
        "RST2228-L1-24MM.MOXA-LOW",
        "RST2228-L1-24MM.MOXA-MID",
        "RST2228-L1-24MM.MOXA-HIGH",
        "RST2228-L1-24MM.CISCO-LOW",
        "RST2228-L1-24MM.CISCO-MID",
        "RST2228-L1-24MM.CISCO-HIGH",
    }
    assert len(offered) == len(set(offered))


def test_the_l2_row_offers_only_l2_switches(project: Path, store: LibraryStore) -> None:
    assert set(ids(row(parts(project, store), "l2")["choices"])) == L2_GROUP


def test_the_ext_row_offers_only_ext_switches(project: Path, store: LibraryStore) -> None:
    offered = ids(row(parts(project, store), "ext-esw")["choices"])

    assert set(offered) == {
        "SEL-2730M-EXT",
        "SEL-2730M-EXT.MOXA-LOW",
        "SEL-2730M-EXT.MOXA-MID",
        "SEL-2730M-EXT.MOXA-HIGH",
        "SEL-2730M-EXT.SIEMENS-MID",
        "SEL-2730M-EXT.SIEMENS-HIGH",
    }


def test_the_shipped_library_offers_9_l1_10_l2_and_7_ext_switches(shipped: Any) -> None:
    """Plan M83 acceptance (psa-devices, Q74 (a))."""
    assert len(row(shipped, "l1")["choices"]) == 9
    assert len(row(shipped, "l2")["choices"]) == 10
    assert len(row(shipped, "ext-esw")["choices"]) == 7


def test_a_row_offers_no_alternative_of_another_part(
    shipped: Any, shipped_library: Library
) -> None:
    for r in shipped["rows"]:
        own = shipped_library.get(r["part_id"]) if r["part_id"] else None
        group = own.alt_group if own is not None else None
        for choice in r["choices"]:
            part = shipped_library.get(choice["part_id"])
            assert part is not None
            if part.tier is not None:
                assert part.alt_group == group, (r["id"], part.part_id)


def test_the_current_part_is_always_offered(project: Path, store: LibraryStore) -> None:
    substation = project.parent / "substations" / "gis01" / "substation.yaml"
    # an L1 switch's alternative on the L2 row: off level, and an alternative of no L2 part
    edit(
        substation,
        "{ id: l2, part_id: RST2228-L2,",
        "{ id: l2, part_id: RST2228-L1-24MM.MOXA-LOW,",
    )

    offered = ids(row(parts(project, store), "l2")["choices"])

    assert "RST2228-L1-24MM.MOXA-LOW" in offered
    assert "RST2228-L2" in offered  # the L2 originals stay
    assert "RST2228-L1-24MM" not in offered  # still the L1 level
    assert "RST2228-L2.MOXA-LOW" not in offered  # no alternative of another part


def test_obsolete_parts_are_not_offered(project: Path, store: LibraryStore) -> None:
    library = project.parent / "library.yaml"
    old = "  - part_id: RST2228-L2.MOXA-LOW\n"
    edit(library, old, old + "    state: obsolete\n")

    found = parts(project, store)

    assert set(ids(row(found, "l2")["choices"])) == L2_GROUP - {"RST2228-L2.MOXA-LOW"}
    assert "RST2228-L2.MOXA-LOW" in ids(found["options"]["network_switch"])  # searchable


def test_an_obsolete_current_part_is_still_offered(project: Path, store: LibraryStore) -> None:
    library = project.parent / "library.yaml"
    edit(library, "  - part_id: RST2228-L2  #", "  - state: obsolete\n    part_id: RST2228-L2  #")

    assert "RST2228-L2" in ids(row(parts(project, store), "l2")["choices"])


def test_every_part_of_the_category_stays_searchable(
    shipped: Any, shipped_library: Library
) -> None:
    switches = [d.part_id for d in shipped_library.devices if d.category is Category.NETWORK_SWITCH]

    assert sorted(ids(shipped["options"]["network_switch"])) == sorted(switches)
    assert len(switches) == 26


def test_an_alternative_names_its_tier_and_the_part_it_replaces(
    project: Path, store: LibraryStore
) -> None:
    found = parts(project, store)
    choices = {c["part_id"]: c for c in row(found, "l2")["choices"]}

    assert choices["RST2228-L2.MOXA-LOW"]["tier"] == "low"
    assert choices["RST2228-L2.MOXA-LOW"]["replaces"] == {
        "part_id": "RST2228-L2",
        "make": "Ruggedcom",
        "model": "RST-2228",
    }
    assert choices["RST2228-L2"]["tier"] is None
    assert choices["RST2228-L2"]["replaces"] is None
    searchable = {o["part_id"]: o for o in found["options"]["network_switch"]}
    assert searchable["RST2228-L1-24MM.CISCO-HIGH"]["tier"] == "high"
    assert searchable["RST2228-L1-24MM.CISCO-HIGH"]["replaces"]["model"] == "RST-2228"


def test_a_new_substations_rows_offer_their_roles_originals(
    project: Path, store: LibraryStore
) -> None:
    rows = {d["role"]: d for d in parts(project, store)["default_rows"]}

    assert ids(rows["l1_switch"]["choices"]) == ["RST2228-L1-24MM"]
    assert ids(rows["l2_switch"]["choices"]) == ["RST2228-L2"]
    assert all(c["tier"] is None for d in rows.values() for c in d["choices"])


def test_add_a_switch_offers_ext_switches_only(project: Path, store: LibraryStore) -> None:
    """Add a device > Switch makes an ext_switch row (plan M83)."""
    added = {c["category"]: c for c in parts(project, store)["add_categories"]}

    assert added["network_switch"]["role"] == "ext_switch"
    assert ids(added["network_switch"]["choices"]) == ["SEL-2730M-EXT"]
    assert added["firewall"]["role"] == "firewall"
    assert added["gateway"]["role"] == "other"


# Choices that share a make and model in one row's list (plan M83 point 3, Q82). Neither
# a distinguishing text nor the ordering code is added; the lead decides. Each pair or
# triple differs by its tier only. Key: (role, the row's current part).
SAME_NAME = {
    ("l1_switch", "RST2228-L1-24MM"): {
        ("Cisco", "Catalyst IE9320"): ["high", "low", "mid"],
        ("Moxa", "PT-7528 series"): ["low", "mid"],
    },
    ("l2_switch", "RST2228-L2"): {("Cisco", "Catalyst IE9320"): ["high", "low", "mid"]},
    ("ext_switch", "SEL-2730M-EXT"): {("Moxa", "PT-7528 series"): ["low", "mid"]},
    ("firewall", "FGR-60F"): {
        ("Cisco", "Secure Firewall ISA3000"): ["low", "mid"],
        ("Moxa", "EDR-G9010 series"): ["low", "mid"],
    },
}


def _same_name(choices: list[Any]) -> dict[tuple[str | None, str | None], list[str]]:
    names = Counter((d.make, d.model) for d in choices)
    return {
        name: sorted(str(d.tier) for d in choices if (d.make, d.model) == name)
        for name, n in names.items()
        if n > 1
    }


def test_choices_sharing_a_make_and_model_in_the_shipped_library(
    shipped_library: Library,
) -> None:
    # every row the app makes: the role rows, and Add a device's "other" rows
    others = ((EquipmentRole.OTHER, c) for c in ADD_CATEGORIES if c not in ADD_ROLE)
    rows = [*ROLE_CATEGORY.items(), *others]
    found = {}
    for role, category in rows:
        starts = row_choices(shipped_library, role, category, None)
        for current in [None, *(d.part_id for d in starts)]:
            same = _same_name(row_choices(shipped_library, role, category, current))
            if same:
                found[(role.value, current)] = same

    assert found == SAME_NAME
    # the shared names never share a tier, so the tier line tells each apart
    assert all(len(set(t)) == len(t) for v in found.values() for t in v.values())


def test_a_switch_option_says_its_level(project: Path, store: LibraryStore) -> None:
    # plan M83, Q82: two switches may share a make and model (the two RST-2228); in the whole
    # category their level tells them apart, not the library id or the ordering code.
    options = parts(project, store)["options"]
    level = {o["part_id"]: o["level"] for o in options["network_switch"]}

    assert level["RST2228-L2"] == "L2 switch"
    assert level["RST2228-L1-24MM"] == "L1 switch"
    assert level["SEL-2730M-EXT"] == "EXT switch"
    assert {o["level"] for o in options["firewall"]} == {None}
