"""A Parts row shows only the controls that change the BOM (plan M90, Ali's v0.5.0 point 6).

Each rule follows the engine: the layout gives a cable manager only to a part taller than
0 U, skips an annunciator row (its loose item takes the part and quantity only), needs
both sized switch rows redundant, and gives a branch MCB from the derived part's supply.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app.parts import parts_page
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


@pytest.fixture
def substation(project: Path) -> Path:
    return project.parent / "substations" / "gis01" / "substation.yaml"


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


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


FW = "  - id: ext-fw\n"  # FGR-60F: a firewall, 0 U (DIN rail), DC with two supplies
NETWORK = "\nnetwork:\n"


def add_row(substation: Path, line: str) -> None:
    """``line`` as the last equipment row."""
    edit(substation, NETWORK, f"  - {line}\n{NETWORK}")


# finding 1: the layout adds a cable manager only under a part taller than 0 U


def test_a_din_rail_network_part_offers_no_cable_manager(
    project: Path, store: LibraryStore
) -> None:
    found = parts(project, store)

    assert row(found, "ext-fw")["cable_manager"] is None  # FGR-60F, height_u 0
    assert row(found, "l2")["cable_manager"] == {"on": True, "default": True, "zero_u": False}


def test_a_height_override_decides_the_cable_manager_toggle(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(substation, FW, f"{FW}    overrides: {{ height_u: 1 }}\n")
    edit(
        substation,
        "{ id: l2, part_id: RST2228-L2,",
        "{ id: l2, overrides: { height_u: 0 }, part_id: RST2228-L2,",
    )

    found = parts(project, store)

    assert row(found, "ext-fw")["cable_manager"] == {"on": True, "default": True, "zero_u": False}
    assert row(found, "l2")["cable_manager"] is None


def test_a_cable_manager_written_on_a_0u_part_shows_and_says_the_bom_has_none(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    edit(substation, FW, f"{FW}    cable_manager: false\n")

    assert row(parts(project, store), "ext-fw")["cable_manager"] == {
        "on": False,
        "default": True,
        "zero_u": True,
    }


# finding 2: the layout skips an annunciator row; its loose item takes part and qty only


def test_an_annunciator_row_offers_no_rack_controls(
    project: Path, substation: Path, store: LibraryStore
) -> None:
    # an AC annunciator, so it has a branch MCB of its own part
    add_row(substation, "{ id: ann, part_id: NAP-K55.ADVANTECH-LOW, role: annunciator }")

    ann = row(parts(project, store), "ann")

    assert ann["ab"] is False  # one loose item of qty units, A and B or not
    assert ann["placement"] is None  # no panel, no rack priority
    assert ann["bom_text"] is None  # no tag, purpose, type code, number, HWIO or note
    assert ann["alarm"] is None  # no branch MCB in any panel
    assert ann["link"] is None  # M89
    # what does reach its loose item stays: the part, its part number, qty and values
    assert (ann["part_id"], ann["qty"], ann["sized"]) == ("NAP-K55.ADVANTECH-LOW", 1, False)
    assert ann["library"] is not None


def test_a_default_annunciator_row_offers_no_a_and_b_box(
    project: Path, store: LibraryStore
) -> None:
    defaults = {d["role"]: d for d in parts(project, store)["default_rows"]}

    assert defaults["annunciator"]["ab"] is False
    assert defaults["operator_ws"]["ab"] is True


# finding 3: the model needs both sized switch rows redundant


def test_a_sized_switch_row_offers_no_a_and_b_box(project: Path, store: LibraryStore) -> None:
    found = parts(project, store)

    assert row(found, "l1")["ab"] is False
    assert row(found, "l2")["ab"] is False
    assert row(found, "ext-esw")["ab"] is True  # an external switch may be single
    assert row(found, "gps")["ab"] is True
    defaults = {d["role"]: d for d in found["default_rows"]}
    assert defaults["l1_switch"]["ab"] is False
    assert defaults["l2_switch"]["ab"] is False


# finding 4: the engine sizes the branch MCB from the derived part's supply (ADR 0024)


@pytest.mark.parametrize(
    "overrides",
    ["{ power_supplies: 1 }", "{ power_supplies: 0 }"],
)
def test_m58_the_alarm_toggle_follows_the_rows_supply_overrides(
    project: Path, substation: Path, store: LibraryStore, overrides: str
) -> None:
    edit(substation, FW, f"{FW}    overrides: {overrides}\n")

    assert row(parts(project, store), "ext-fw")["alarm"] is None  # no branch MCB left


@pytest.mark.parametrize(
    "overrides",
    ["{ power_supplies: 2 }", "{ supply_type: VAC, voltage_v: 230, power_supplies: 0 }"],
)
def test_m58_a_supply_override_that_gives_a_branch_mcb_offers_the_alarm(
    project: Path, substation: Path, store: LibraryStore, overrides: str
) -> None:
    clock = "{ id: clock, part_id: SEL-2488.MEINBERG-LOW, role: other"
    add_row(substation, f"{clock} }}")  # a single-fed DC clock: no branch MCB of its own
    assert row(parts(project, store), "clock")["alarm"] is None

    edit(substation, f"{clock} }}", f"{clock}, overrides: {overrides} }}")

    assert row(parts(project, store), "clock")["alarm"] == {"on": False, "default": False}
