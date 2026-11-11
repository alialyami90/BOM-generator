"""Which Parts rows have a link to the L2 switch (plan M89, M31 design; Q78 (a)).

The rows of a networked category have one, and so does a part that lists a network port
(an IP KVM); a monitor, a keyboard and a plain KVM have none. A link written in the file
always shows. psa-devices ships no KVM, so the test library gets two.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app.parts import parts_page
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"

KVMS = """devices:
  - part_id: KVM-PLAIN  # a desk KVM: no network port
    category: kvm
    height_u: 1
    make: Test
    model: KVM-PLAIN
    description_template: "KVM Switch"
    supply_type: VDC
    voltage_v: 125
    unit_power_w: 10
    load_type: CONTINUOUS
    power_supplies: 1
    min_branch_mcb_a: 2

  - part_id: KVM-IP  # an IP KVM: one RJ45 network port
    category: kvm
    height_u: 1
    make: Test
    model: KVM-IP
    description_template: "IP KVM Switch"
    supply_type: VDC
    voltage_v: 125
    unit_power_w: 10
    load_type: CONTINUOUS
    power_supplies: 1
    min_branch_mcb_a: 2
    ports:
      - { count: 1, speed: 1G, media: RJ45, kind: fixed }

"""
HWIO = "  - { id: hwio, part_id: SEL-2240, role: other }  # Axion I/O, no L2 link\n"
ROWS = """  - { id: mon, part_id: NAP-F23, role: other }
  - { id: kbm, part_id: KEYTEK-KBM, role: other }
  - { id: kvm, part_id: KVM-PLAIN, role: kvm }
  - { id: ipkvm, part_id: KVM-IP, role: kvm }
"""


def edit(file: Path, old: str, new: str) -> None:
    text = file.read_text(encoding="utf-8")
    assert old in text
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """The example with a monitor, a keyboard, a plain KVM and an IP KVM row."""
    root = tmp_path / "workspace" / "jfgp2-pkg3"
    shutil.copytree(EXAMPLES, root)
    edit(root / "library.yaml", "devices:\n", KVMS)
    edit(root / "substations" / "gis01" / "substation.yaml", HWIO, HWIO + ROWS)
    return root / "project.yaml"


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


def link(project: Path, store: LibraryStore, entry_id: str) -> Any:
    found = parts_page(project, "gis01", store)["parts"]
    json.dumps(found)
    return next(r for r in found["rows"] if r["id"] == entry_id)["link"]


def test_m31_a_monitor_row_has_no_l2_link(project: Path, store: LibraryStore) -> None:
    assert link(project, store, "mon") is None


def test_m31_a_keyboard_row_has_no_l2_link(project: Path, store: LibraryStore) -> None:
    assert link(project, store, "kbm") is None


def test_m31_a_kvm_without_a_network_port_has_no_l2_link(
    project: Path, store: LibraryStore
) -> None:
    """Ali, 2026-11-11: his KVM is not an IP KVM, so it is not linked to the switch."""
    assert link(project, store, "kvm") is None


def test_m31_a_part_that_lists_a_network_port_has_an_l2_link(
    project: Path, store: LibraryStore
) -> None:
    found = link(project, store, "ipkvm")
    assert found == {"l2_ports": 0, "l2_speed": "1G", "l2_media": "MM", "no_sfp": False}


def test_m31_a_row_with_a_written_l2_link_still_shows_it(
    project: Path, store: LibraryStore
) -> None:
    """Written data is never hidden: the link adds SFPs to the L2 switch."""
    substation = project.parent / "substations" / "gis01" / "substation.yaml"
    edit(substation, "NAP-F23, role: other }", "NAP-F23, role: other, l2_ports: 1 }")
    assert link(project, store, "mon")["l2_ports"] == 1


def test_m31_the_io_chassis_and_the_ext_switch_keep_their_l2_link(
    project: Path, store: LibraryStore
) -> None:
    """Q78 (a): both may be linked, and the example links neither."""
    for entry_id in ("hwio", "ext-esw"):
        assert link(project, store, entry_id)["l2_ports"] == 0
