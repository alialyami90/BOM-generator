"""Device-database records inside a `.bomlib` and the loader that reads them (ADR 0008)."""

from pathlib import Path

import pytest
import yaml

from bomgen.library_store.device_db import (
    DEVICE_DB_DIR,
    DeviceRecord,
    load_device_records,
    parse_device_records,
)
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.package import pack, read_package
from bomgen.library_store.store import LibraryStore

ROOT = Path(__file__).parents[3]
EXAMPLE_LIBRARY = ROOT / "examples" / "library.yaml"
DEVICE_DB = ROOT / "data" / "device-db"

MINIMAL = """\
schema_version: 1
area: test
title: Test
records:
  - part_id: SW-1
    kind: device
    description: A switch
    verified: confirmed
    datasheet:
      summary: s
      notes: n
      mounting_kind: rack
      height_u: 1
    alternatives:
      - make: Moxa
        manufacturer: Moxa Inc.
        tiers:
          low: {model: A, description: a, verified: true}
          mid: {model: B, description: b, verified: false}
          high: {model: B, description: b, verified: false, same_as: mid}
    sources: [https://example.com]
"""


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    return LibraryStore(tmp_path / "libraries")


def _device_db(tmp_path: Path, **files: str) -> Path:
    folder = tmp_path / DEVICE_DB_DIR
    folder.mkdir()
    for name, text in files.items():
        (folder / name).write_text(text)
    return folder


def _install(tmp_path: Path, store: LibraryStore, *extra: Path) -> None:
    package = tmp_path / "psa-1.0.0.bomlib"
    pack(EXAMPLE_LIBRARY, package, name="psa", version="1.0.0", extra_dirs=list(extra))
    store.import_package(package)


def test_the_researched_database_loads_and_keys_on_part_id() -> None:
    files = {f"{DEVICE_DB_DIR}/{p.name}": p.read_bytes() for p in DEVICE_DB.glob("*.yaml")}

    records = parse_device_records(files)

    expected = sum(len(yaml.safe_load(data)["records"]) for data in files.values())
    assert len(records) == expected == 64
    switch = records["RST2228-L1-24MM"]
    assert isinstance(switch, DeviceRecord)
    assert switch.kind == "device"
    assert switch.datasheet.mounting_kind == "rack"
    assert switch.datasheet.port_groups
    assert switch.datasheet.port_groups[0].usable_for in {"ied", "uplink", "any"}
    assert {a.make for a in switch.alternatives}
    catalogue = [r for r in records.values() if r.kind == "catalogue"]
    assert catalogue
    assert all(r.library_refs is not None or r.part_id.startswith("ENCL") for r in catalogue)


def test_a_packed_database_is_installed_and_loaded(tmp_path: Path, store: LibraryStore) -> None:
    _install(tmp_path, store, DEVICE_DB)

    records = load_device_records(store, "psa", "1.0.0")

    assert "RST2228-L1-24MM" in records
    installed = store.root / "psa" / "1.0.0" / DEVICE_DB_DIR
    assert sorted(p.name for p in installed.iterdir()) == sorted(
        p.name for p in DEVICE_DB.glob("*.yaml")
    )


def test_a_package_without_a_database_loads_nothing(tmp_path: Path, store: LibraryStore) -> None:
    _install(tmp_path, store)

    assert load_device_records(store, "psa", "1.0.0") == {}


def test_an_uninstalled_version_is_refused(store: LibraryStore) -> None:
    with pytest.raises(LibraryPackageError) as caught:
        load_device_records(store, "psa", "9.9.9")

    assert caught.value.kind is RefusalKind.NOT_INSTALLED


def test_pack_refuses_a_malformed_record_and_names_the_file(tmp_path: Path) -> None:
    folder = _device_db(tmp_path, **{"bad.yaml": MINIMAL.replace("kind: device", "kind: gadget")})

    with pytest.raises(LibraryPackageError) as caught:
        pack(
            EXAMPLE_LIBRARY, tmp_path / "x.bomlib", name="psa", version="1.0.0", extra_dirs=[folder]
        )

    assert caught.value.kind is RefusalKind.VALIDATION_FAILED
    assert "device-db/bad.yaml" in str(caught.value)
    assert "records[0].kind" in str(caught.value)


def test_pack_refuses_an_unknown_key(tmp_path: Path) -> None:
    text = MINIMAL.replace(
        "    description: A switch\n", "    description: A switch\n    colour: red\n"
    )
    folder = _device_db(tmp_path, **{"bad.yaml": text})

    with pytest.raises(LibraryPackageError, match=r"records\[0\]\.colour"):
        pack(
            EXAMPLE_LIBRARY, tmp_path / "x.bomlib", name="psa", version="1.0.0", extra_dirs=[folder]
        )


def test_pack_refuses_the_same_part_id_in_two_files(tmp_path: Path) -> None:
    folder = _device_db(tmp_path, **{"a.yaml": MINIMAL, "b.yaml": MINIMAL})

    with pytest.raises(LibraryPackageError, match=r"SW-1.*a\.yaml.*b\.yaml"):
        pack(
            EXAMPLE_LIBRARY, tmp_path / "x.bomlib", name="psa", version="1.0.0", extra_dirs=[folder]
        )


def test_pack_refuses_a_file_that_is_not_yaml(tmp_path: Path) -> None:
    folder = _device_db(tmp_path, **{"bad.yaml": "records: [unclosed"})

    with pytest.raises(LibraryPackageError, match=r"device-db/bad\.yaml"):
        pack(
            EXAMPLE_LIBRARY, tmp_path / "x.bomlib", name="psa", version="1.0.0", extra_dirs=[folder]
        )


def test_other_extra_folders_are_not_checked(tmp_path: Path) -> None:
    other = tmp_path / "notes"
    other.mkdir()
    (other / "bad.yaml").write_text("kind: gadget\n")

    pack(EXAMPLE_LIBRARY, tmp_path / "x.bomlib", name="psa", version="1.0.0", extra_dirs=[other])


def test_loading_a_damaged_installed_database_raises(tmp_path: Path, store: LibraryStore) -> None:
    folder = _device_db(tmp_path, **{"ok.yaml": MINIMAL})
    _install(tmp_path, store, folder)
    (store.root / "psa" / "1.0.0" / DEVICE_DB_DIR / "ok.yaml").write_text("kind: gadget\n")

    with pytest.raises(LibraryPackageError) as caught:
        load_device_records(store, "psa", "1.0.0")

    assert caught.value.kind is RefusalKind.STORE_DAMAGED


def test_the_package_reader_still_accepts_the_folder(tmp_path: Path) -> None:
    folder = _device_db(tmp_path, **{"ok.yaml": MINIMAL})
    package = tmp_path / "x.bomlib"
    pack(EXAMPLE_LIBRARY, package, name="psa", version="1.0.0", extra_dirs=[folder])

    assert f"{DEVICE_DB_DIR}/ok.yaml" in read_package(package).files


def test_the_loader_is_a_public_entry_point() -> None:
    from bomgen import library_store

    assert library_store.load_device_records is load_device_records
    assert library_store.DeviceRecord is DeviceRecord


def _bad(text: str) -> dict[str, bytes]:
    return {f"{DEVICE_DB_DIR}/bad.yaml": text.encode()}


def test_notes_are_optional() -> None:
    parse_device_records(_bad(MINIMAL.replace("      notes: n\n", "")))


def test_height_is_above_zero_exactly_for_rack_parts() -> None:
    with pytest.raises(LibraryPackageError, match="height_u is above 0 exactly when"):
        parse_device_records(
            _bad(MINIMAL.replace("mounting_kind: rack", "mounting_kind: din_rail"))
        )
    with pytest.raises(LibraryPackageError, match="height_u is above 0 exactly when"):
        parse_device_records(_bad(MINIMAL.replace("height_u: 1", "height_u: 0")))


def test_a_boolean_is_not_a_height_or_a_figure() -> None:
    with pytest.raises(LibraryPackageError, match=r"datasheet\.height_u"):
        parse_device_records(_bad(MINIMAL.replace("height_u: 1", "height_u: true")))
    with pytest.raises(LibraryPackageError, match=r"datasheet\.weight_kg"):
        parse_device_records(
            _bad(
                MINIMAL.replace("      height_u: 1\n", "      height_u: 1\n      weight_kg: true\n")
            )
        )


def test_port_groups_use_the_library_vocabulary() -> None:
    group = (
        "      port_groups:\n"
        "        - {ports: p, count: 4, speed: 5G, media: SFP,"
        " kind: sfp_slot, usable_for: uplink}\n"
    )
    text = MINIMAL.replace("      height_u: 1\n", "      height_u: 1\n" + group)

    with pytest.raises(LibraryPackageError, match=r"port_groups\[0\]\.speed"):
        parse_device_records(_bad(text))
    parse_device_records(_bad(text.replace("5G", "10G")))


LOW = "low: {model: A, description: a, verified: true}"


def _tier(extra: str) -> dict[str, bytes]:
    """MINIMAL with `extra` keys added to the low tier."""
    return _bad(MINIMAL.replace(LOW, LOW[:-1] + ", " + extra + "}"))


def _datasheet(extra: str) -> dict[str, bytes]:
    """MINIMAL with `extra` keys added to the original part's datasheet."""
    return _bad(MINIMAL.replace("      height_u: 1\n", f"      height_u: 1\n      {extra}\n"))


def _refused(files: dict[str, bytes], field: str) -> None:
    """The records fail on `field` itself, not because the key is unknown."""
    with pytest.raises(LibraryPackageError) as caught:
        parse_device_records(files)
    assert field in str(caught.value)
    assert f"{field}: unknown key" not in str(caught.value)


def test_a_tier_may_carry_its_own_mounting_and_height() -> None:
    parse_device_records(_tier("mounting_kind: rack, height_u: 2"))
    parse_device_records(_tier("mounting_kind: din_rail, height_u: 0"))
    parse_device_records(_tier("height_u: 1"))


def test_a_tier_height_is_above_zero_exactly_for_rack_parts() -> None:
    with pytest.raises(LibraryPackageError, match="height_u is above 0 exactly when"):
        parse_device_records(_tier("mounting_kind: din_rail, height_u: 1"))
    with pytest.raises(LibraryPackageError, match="height_u is above 0 exactly when"):
        parse_device_records(_tier("mounting_kind: rack, height_u: 0"))


def test_a_tier_mounting_kind_and_height_use_the_datasheet_vocabulary() -> None:
    _refused(_tier("mounting_kind: shelf"), "low.mounting_kind")
    _refused(_tier("height_u: true"), "low.height_u")
    _refused(_tier("height_u: -1"), "low.height_u")


def test_a_tier_may_describe_its_supply() -> None:
    parse_device_records(
        _tier(
            "supply_type: VDC, voltage_v: 125, supply_option: HV, supply_ok: true,"
            " power_supplies: 2, power_basis: datasheet_max, power_note: n"
        )
    )
    parse_device_records(_tier("supply_type: none, supply_ok: false, power_basis: assumed"))
    parse_device_records(_tier("supply_type: VAC, voltage_v: 230.5, power_supplies: 1"))


@pytest.mark.parametrize(
    ("extra", "field"),
    [
        ("supply_type: AC", "supply_type"),
        ("voltage_v: '125'", "voltage_v"),
        ("voltage_v: true", "voltage_v"),
        ("supply_ok: 'yes'", "supply_ok"),
        ("power_supplies: 3", "power_supplies"),
        ("power_supplies: 0", "power_supplies"),
        ("power_supplies: true", "power_supplies"),
        ("power_basis: guessed", "power_basis"),
    ],
)
def test_a_tier_supply_value_outside_its_rule_is_refused(extra: str, field: str) -> None:
    _refused(_tier(extra), f"low.{field}")


def test_a_tier_may_carry_inrush_figures() -> None:
    parse_device_records(
        _tier("inrush_a: 12.5, inrush_ms: 3, inrush_basis: datasheet, inrush_note: n")
    )
    parse_device_records(_tier("inrush_basis: not_given"))
    parse_device_records(_tier("inrush_basis: assumed"))


@pytest.mark.parametrize(
    ("extra", "field"),
    [
        ("inrush_a: '12'", "inrush_a"),
        ("inrush_a: true", "inrush_a"),
        ("inrush_ms: '3'", "inrush_ms"),
        ("inrush_basis: measured", "inrush_basis"),
    ],
)
def test_a_tier_inrush_value_outside_its_rule_is_refused(extra: str, field: str) -> None:
    _refused(_tier(extra), f"low.{field}")


def test_the_original_part_may_carry_inrush_figures() -> None:
    text = MINIMAL.replace(
        "      height_u: 1\n",
        "      height_u: 1\n      inrush_a: 30\n      inrush_ms: 2.5\n"
        "      inrush_basis: datasheet\n      inrush_note: n\n",
    )
    parse_device_records(_bad(text))


def test_the_original_part_inrush_follows_the_same_rules() -> None:
    _refused(_datasheet("inrush_a: '30'"), "datasheet.inrush_a")
    _refused(_datasheet("inrush_basis: measured"), "datasheet.inrush_basis")


def test_a_tier_may_list_port_groups() -> None:
    group = "{ports: p, count: 4, speed: 10G, media: SFP, kind: sfp_slot, usable_for: uplink}"
    parse_device_records(_tier(f"port_groups: [{group}]"))
    _refused(_tier(f"port_groups: [{group.replace('10G', '5G')}]"), "low.port_groups[0].speed")


def test_a_tier_may_carry_fan_airflow_ratings_and_sources() -> None:
    parse_device_records(
        _tier("airflow_m3h: 120, ratings: {trip_curve: C, dc_v: 125}, sources: [https://x.test]")
    )
    _refused(_tier("airflow_m3h: '120'"), "low.airflow_m3h")
    _refused(_tier("sources: https://x.test"), "low.sources")


def test_a_tier_still_refuses_an_unknown_key() -> None:
    with pytest.raises(LibraryPackageError, match=r"low\.colour: unknown key"):
        parse_device_records(_tier("colour: red"))


def test_a_tier_and_the_datasheet_may_give_the_dc_input_range() -> None:
    parse_device_records(_tier("input_v_min: 88, input_v_max: 300.5"))
    parse_device_records(_tier("input_v_min: 24"))
    parse_device_records(_datasheet("input_v_min: 18\n      input_v_max: 60"))
    parse_device_records(_tier("input_v_min: 48, input_v_max: 48"))


@pytest.mark.parametrize("field", ["input_v_min", "input_v_max"])
def test_a_dc_input_figure_is_a_number(field: str) -> None:
    _refused(_tier(f"{field}: '24'"), f"low.{field}")
    _refused(_tier(f"{field}: true"), f"low.{field}")
    _refused(_datasheet(f"{field}: '24'"), f"datasheet.{field}")


def test_the_dc_input_minimum_is_not_above_the_maximum() -> None:
    with pytest.raises(LibraryPackageError, match="input_v_min must not be above input_v_max"):
        parse_device_records(_tier("input_v_min: 60, input_v_max: 18"))
    with pytest.raises(LibraryPackageError, match="input_v_min must not be above input_v_max"):
        parse_device_records(_datasheet("input_v_min: 60\n      input_v_max: 18"))
