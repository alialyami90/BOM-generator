"""Derived parts: an equipment entry's part number, overrides and SFP choice (ADR 0024)."""

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from bomgen.io.derived import derive_parts, derived_id, effective_part_id
from bomgen.io.errors import InputError
from bomgen.io.loader import load_library, load_project
from bomgen.models.library import Library
from bomgen.models.substation import Equipment, Substation

EXAMPLES = Path(__file__).parents[2] / "examples"
LIB = load_library(EXAMPLES / "library.yaml")
EXAMPLE_SUB = load_project(EXAMPLES / "project.yaml").substations[0].substation


def sub_with(*extra: Equipment) -> Substation:
    return EXAMPLE_SUB.model_copy(update={"equipment": [*EXAMPLE_SUB.equipment, *extra]})


def derived(lib: Library, part_id: str) -> Any:
    return next(d for d in lib.devices if d.part_id == part_id)


def ows(**fields: Any) -> Equipment:
    return Equipment(id="ows", part_id="SEL-3355", role="operator_ws", **fields)


OWS_INDEX = len(EXAMPLE_SUB.equipment)


def test_part_number_box_is_the_bom_ordering_code() -> None:
    lib, problems = derive_parts(LIB, sub_with(ows(ordering_code="3355#ABC")))
    part = derived(lib, "SEL-3355+ows")
    assert (part.code, part.derived_from, problems) == ("3355#ABC", "SEL-3355", [])


def test_override_replaces_only_the_values_given() -> None:
    lib, _ = derive_parts(LIB, sub_with(ows(overrides={"unit_power_w": 120})))
    part = derived(lib, "SEL-3355+ows")
    assert (part.unit_power_w, part.height_u, part.code) == (120, 3, "3355#F5P8")


def test_the_sfp_choice_is_carried_on_the_derived_part() -> None:
    l2 = Equipment(
        id="l2b",
        part_id="RST2228-L2",
        role="l2_switch",
        redundant=True,
        sfp=[{"speed": "1G", "media": "MM", "part_id": "FR-TRAN-SX"}],
    )
    lib, _ = derive_parts(LIB, sub_with(l2))
    assert [c.part_id for c in derived(lib, "RST2228-L2+l2b").sfp_choice] == ["FR-TRAN-SX"]


def test_an_override_that_breaks_a_library_rule_is_a_located_problem() -> None:
    _, problems = derive_parts(LIB, sub_with(ows(overrides={"supply_type": "VAC"})))
    assert problems == [
        (("equipment", OWS_INDEX, "overrides"), "power_supplies above 0 needs supply_type VDC")
    ]


def test_a_derived_id_taken_by_a_library_part_is_a_problem() -> None:
    taken = Equipment(id="taken", part_id="SEL-3355", role="other", ordering_code="X")
    clash = LIB.model_copy(update={"devices": [*LIB.devices, derived_for(taken)]})
    lib, problems = derive_parts(clash, sub_with(taken))
    assert lib.part_ids().count("SEL-3355+taken") == 1
    assert problems == [
        (
            ("equipment", OWS_INDEX, "id"),
            "the part id 'SEL-3355+taken' for this entry's overrides is a library "
            "part already; rename the entry",
        )
    ]


def derived_for(entry: Equipment) -> Any:
    base = LIB.get(str(entry.part_id))
    assert base is not None
    return base.model_copy(update={"part_id": derived_id(entry)})


def test_an_unknown_part_is_left_to_the_equipment_check() -> None:
    lib, problems = derive_parts(
        LIB, sub_with(Equipment(id="ows", part_id="NOPE", role="other", ordering_code="X"))
    )
    assert (lib.get("NOPE+ows"), problems) == (None, [])


def test_no_overrides_leaves_the_library_unchanged() -> None:
    lib, problems = derive_parts(LIB, EXAMPLE_SUB)
    assert lib is LIB
    assert problems == []


def test_effective_part_id_is_the_derived_id_only_when_needed() -> None:
    assert effective_part_id(ows()) == "SEL-3355"
    assert effective_part_id(ows(ordering_code="X")) == "SEL-3355+ows"
    assert effective_part_id(Equipment(id="l1", role="l1_switch", redundant=True)) is None


def test_two_substations_get_their_own_derived_parts() -> None:
    first, _ = derive_parts(LIB, sub_with(ows(overrides={"unit_power_w": 50})))
    second, _ = derive_parts(LIB, sub_with(ows(overrides={"unit_power_w": 60})))
    assert derived(first, "SEL-3355+ows").unit_power_w == 50
    assert derived(second, "SEL-3355+ows").unit_power_w == 60
    assert LIB.get("SEL-3355+ows") is None


def example_project(tmp_path: Path, **gw: Any) -> Path:
    shutil.copytree(EXAMPLES, tmp_path, dirs_exist_ok=True)
    file = tmp_path / "substations" / "gis01" / "substation.yaml"
    data = yaml.safe_load(file.read_text(encoding="utf-8"))
    entry = next(e for e in data["equipment"] if e["id"] == "gw")
    entry.update(gw)
    file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return tmp_path / "project.yaml"


def test_the_loader_adds_derived_parts_to_the_substation_library_only(tmp_path: Path) -> None:
    loaded = load_project(example_project(tmp_path, ordering_code="GW-1"))
    assert loaded.substations[0].library.get("SEL-3555-GW+gw") is not None
    assert loaded.library.get("SEL-3555-GW+gw") is None


def test_the_loader_reports_a_broken_override_on_the_equipment_entry(tmp_path: Path) -> None:
    with pytest.raises(InputError) as caught:
        load_project(example_project(tmp_path, overrides={"supply_type": "VAC"}))
    gw = next(i for i, e in enumerate(EXAMPLE_SUB.equipment) if e.id == "gw")
    issue = caught.value.issues[0]
    assert (issue.file.name, issue.location, issue.message) == (
        "substation.yaml",
        f"equipment[{gw}].overrides",
        "power_supplies above 0 needs supply_type VDC",
    )
    assert issue.line is not None


def panel_naming(tmp_path: Path, part_id: str, *, generated: bool) -> Path:
    """The example project with psa3's first row and its port plan renamed to ``part_id``."""
    project_file = example_project(tmp_path)
    file = tmp_path / "substations" / "gis01" / "panels" / "psa3.yaml"
    data = yaml.safe_load(file.read_text(encoding="utf-8"))
    old = data["devices"][0]["part_id"]
    data["devices"][0]["part_id"] = part_id
    if old in data.get("port_plans", {}):
        data["port_plans"][part_id] = data["port_plans"].pop(old)
    data["generated"] = generated
    file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return project_file


def first_row_part(tmp_path: Path) -> str:
    file = tmp_path / "substations" / "gis01" / "panels" / "psa3.yaml"
    return str(yaml.safe_load(file.read_text(encoding="utf-8"))["devices"][0]["part_id"])


def test_a_generated_panel_naming_a_removed_override_falls_back_to_the_library_part(
    tmp_path: Path,
) -> None:
    base = first_row_part(EXAMPLES)
    loaded = load_project(panel_naming(tmp_path, f"{base}+gone", generated=True))
    psa3 = next(p for p in loaded.substations[0].panels if p.id == "psa3")
    assert psa3.devices[0].part_id == base
    assert first_row_part(tmp_path) == f"{base}+gone"  # the file is not written


def test_a_hand_written_panel_naming_a_removed_override_is_an_unknown_part(
    tmp_path: Path,
) -> None:
    base = first_row_part(EXAMPLES)
    with pytest.raises(InputError) as caught:
        load_project(panel_naming(tmp_path, f"{base}+gone", generated=False))
    assert [(i.location, f"'{base}+gone'" in i.message) for i in caught.value.issues] == [
        ("devices[0].part_id", True)
    ]


def test_a_cable_manager_is_only_for_network_devices(tmp_path: Path) -> None:
    file = tmp_path / "substations" / "gis01" / "substation.yaml"
    project_file = example_project(tmp_path)
    data = yaml.safe_load(file.read_text(encoding="utf-8"))
    rtac = next(i for i, e in enumerate(data["equipment"]) if e["id"] == "rtac")
    data["equipment"][rtac]["cable_manager"] = False
    file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(InputError) as caught:
        load_project(project_file)
    assert [(i.location, i.message) for i in caught.value.issues] == [
        (f"equipment[{rtac}].cable_manager", "only network devices have a cable manager")
    ]


def test_a_hand_written_row_with_a_cable_manager_must_be_a_network_device(
    tmp_path: Path,
) -> None:
    project_file = example_project(tmp_path)
    file = tmp_path / "substations" / "gis01" / "panels" / "psa3.yaml"
    data = yaml.safe_load(file.read_text(encoding="utf-8"))
    data["devices"][0]["cable_manager"] = True  # the GPS clock
    file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(InputError) as caught:
        load_project(project_file)
    assert [(i.location, i.message) for i in caught.value.issues] == [
        ("devices[0].cable_manager", "only network devices have a cable manager")
    ]
