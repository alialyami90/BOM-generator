"""Checks on the researched device database in data/device-db/.

The database adds datasheet facts and alternative brands to the parts of the example
project's device library (spec: Inputs the tool needs, 1. Device library). It keys on
the library's part ids and does not repeat library fields. These tests pin its shape so
later edits keep every record complete and sourced.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

TIERS = ("low", "mid", "high")
VERIFIED_LEVELS = {"confirmed", "partial", "unverified"}
KINDS = {"device", "catalogue"}
MOUNTING_KINDS = {"rack", "din_rail", "plug_in", "enclosure", "external"}
PORT_ROLES = {"ied", "uplink", "any"}
PORT_GROUP_KEYS = {"ports", "count", "speed", "media", "kind", "usable_for"}
PORT_SPEEDS = {"100M", "1G", "10G"}
PORT_KINDS = {"fixed", "sfp_slot"}

REPO = Path(__file__).resolve().parents[2]
DB_DIR = REPO / "data" / "device-db"
LIBRARY = yaml.safe_load((REPO / "examples" / "library.yaml").read_text(encoding="utf-8"))

# Catalogue ids are local to the database; each names the library catalogue entries it
# describes in `library_refs`. Enclosures are per panel in the library, so have none.
EXPECTED_CATALOGUE_IDS = {
    "ENCL-RAWABI-2100", "ENCL-RITTAL-PC5386",
    "MCB-A9F74201", "MCB-A9F74202", "MCB-A9F74206", "MCB-A9F74210", "MCB-A9F74216",
    "AUX-A9A26924", "TB-UT-16", "TB-UT-2.5-MTD", "TB-UT-2.5-MT",
    "BUSBAR-AC-SAFETY-GND", "BUSBAR-INSTRUMENT-GND",
}  # fmt: skip


def _originals() -> list[dict[str, Any]]:
    # The parts the device database describes; the alternatives made from its tiers
    # (M14) carry a `tier` and are not records of their own.
    return [d for d in LIBRARY["devices"] if "tier" not in d]


def _library_device_ids() -> set[str]:
    ids: set[str] = set()
    for device in _originals():
        ids.add(device["part_id"])
        ids.update(child["part_id"] for child in device.get("children", []))
        ids.update(item["part_id"] for item in device.get("loose_items", []))
    for entry in LIBRARY["catalogues"]["housekeeping"].values():
        ids.update(v for k, v in entry.items() if k in {"part_id", "negative", "positive"})
    return ids


def _library_switches() -> dict[str, dict[str, Any]]:
    return {d["part_id"]: d for d in _originals() if d["category"] == "network_switch"}


def _library_catalogue_refs() -> set[str]:
    catalogues = LIBRARY["catalogues"]
    refs = {f"mcb.{rating}" for rating in catalogues["mcb"]["ratings_a"]}
    refs.add("aux_contact")
    refs.update(f"terminal_blocks.{key}" for key in catalogues["terminal_blocks"])
    refs.update(f"busbars.{key}" for key in catalogues["busbars"])
    return refs


def _load_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(DB_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        records.extend(doc["records"])
    return records


RECORDS = _load_records()


def _ids(records: list[dict[str, Any]]) -> list[str]:
    return [r["part_id"] for r in records]


def test_part_ids_are_unique() -> None:
    ids = _ids(RECORDS)
    assert len(ids) == len(set(ids))


def test_device_records_match_the_example_library_parts_both_ways() -> None:
    devices = {r["part_id"] for r in RECORDS if r["kind"] == "device"}
    assert devices == _library_device_ids()


def test_catalogue_records_cover_every_library_catalogue_entry() -> None:
    catalogues = [r for r in RECORDS if r["kind"] == "catalogue"]
    assert {r["part_id"] for r in catalogues} == EXPECTED_CATALOGUE_IDS
    refs = [ref for r in catalogues for ref in r.get("library_refs", [])]
    assert len(refs) == len(set(refs))
    assert set(refs) == _library_catalogue_refs()


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_kind_and_verified_level_are_known(record: dict[str, Any]) -> None:
    assert record["kind"] in KINDS
    assert record["verified"] in VERIFIED_LEVELS


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_does_not_repeat_library_fields(record: dict[str, Any]) -> None:
    assert record["description"]
    assert not {"model", "ordering_code", "unit_power_w", "category"} & record.keys()


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_cites_at_least_one_source_url(record: dict[str, Any]) -> None:
    sources = record["sources"]
    assert sources
    assert all(str(url).startswith(("http://", "https://")) for url in sources)


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_two_alternative_brands_each_with_low_mid_high_part(record: dict[str, Any]) -> None:
    alternatives = record["alternatives"]
    assert len(alternatives) == 2
    for alt in alternatives:
        assert alt["make"]
        assert tuple(alt["tiers"]) == TIERS
        for tier in TIERS:
            part = alt["tiers"][tier]
            assert part.get("model"), f"{alt['make']} {tier} has no model"
            assert isinstance(part["verified"], bool)


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_a_tier_repeats_a_lower_tier_part_only_when_marked_same_as(
    record: dict[str, Any],
) -> None:
    for alt in record["alternatives"]:
        seen: dict[tuple[str, str], str] = {}
        for tier in TIERS:
            part = alt["tiers"][tier]
            key = (part["model"], part.get("ordering_code", ""))
            if key in seen:
                assert part.get("same_as") == seen[key], f"{alt['make']} {tier}"
            else:
                assert "same_as" not in part
                seen[key] = tier


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_alternative_brands_differ_from_original_and_each_other(record: dict[str, Any]) -> None:
    makes = [str(alt["make"]).casefold() for alt in record["alternatives"]]
    assert len(set(makes)) == 2
    original = str(record.get("make") or "").casefold()
    if original:
        assert not any(original in make or make in original for make in makes)


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_states_mounting_and_whole_rack_units(record: dict[str, Any]) -> None:
    datasheet = record["datasheet"]
    assert datasheet["mounting_kind"] in MOUNTING_KINDS
    height = datasheet["height_u"]
    assert type(height) is int
    if datasheet["mounting_kind"] == "rack":
        assert height >= 1
    else:
        assert height == 0


@pytest.mark.parametrize("part_id", sorted(_library_switches()))
def test_switch_lists_port_groups_with_a_role_for_the_sizer(part_id: str) -> None:
    record = next(r for r in RECORDS if r["part_id"] == part_id)
    groups = record["datasheet"]["port_groups"]
    assert groups
    for group in groups:
        assert group.keys() >= PORT_GROUP_KEYS, group
        assert group["usable_for"] in PORT_ROLES
        assert group["speed"] in PORT_SPEEDS
        assert group["kind"] in PORT_KINDS
        assert type(group["count"]) is int
        assert group["count"] > 0
    assert any(g["usable_for"] in {"ied", "any"} for g in groups)
    assert any(g["usable_for"] in {"uplink", "any"} for g in groups)


def test_only_switches_carry_port_groups() -> None:
    with_groups = {r["part_id"] for r in RECORDS if "port_groups" in r["datasheet"]}
    assert with_groups == set(_library_switches())


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_datasheet_figures_are_numbers_and_flags_are_booleans(record: dict[str, Any]) -> None:
    datasheet = record["datasheet"]
    assert datasheet["summary"]
    power = datasheet.get("power", {})
    figures = [power.get("typical_w"), power.get("max_w")]
    figures += [datasheet.get("rack_units"), datasheet.get("weight_kg")]
    figures += list(datasheet.get("dimensions_mm", {}).values())
    figures += list(datasheet.get("operating_temp_c", {}).values())
    for alt in record["alternatives"]:
        figures += [part.get("unit_power_w") for part in alt["tiers"].values()]
    assert all(_is_number(v) for v in figures if v is not None)
    assert isinstance(power.get("redundant_psu", False), bool)


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_writes_no_null_values(record: dict[str, Any]) -> None:
    def nulls(node: object, path: str) -> list[str]:
        if node is None:
            return [path]
        if isinstance(node, dict):
            return [p for k, v in node.items() for p in nulls(v, f"{path}.{k}")]
        if isinstance(node, list):
            return [p for i, v in enumerate(node) for p in nulls(v, f"{path}[{i}]")]
        return []

    assert nulls(record, record["part_id"]) == []


SUPPLY_TYPES = {"VDC", "VAC", "none"}
POWER_BASES = {"datasheet_max", "datasheet_typical", "computed", "assumed"}


def _tiers(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [tier for alt in record["alternatives"] for tier in alt["tiers"].values()]


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_every_alternative_states_its_mounting_and_supply(record: dict[str, Any]) -> None:
    for tier in _tiers(record):
        assert tier["mounting_kind"] in MOUNTING_KINDS, tier["model"]
        assert tier["supply_type"] in SUPPLY_TYPES, tier["model"]
        if tier["mounting_kind"] != "rack":
            assert tier["height_u"] == 0, tier["model"]
        elif "height_u" in tier:
            assert tier["height_u"] >= 1, tier["model"]


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_a_powered_alternative_says_where_its_power_figure_comes_from(
    record: dict[str, Any],
) -> None:
    for tier in _tiers(record):
        if tier["supply_type"] == "none":
            assert not {"voltage_v", "inrush_a", "input_v_min"} & tier.keys(), tier["model"]
        elif "unit_power_w" in tier:
            assert tier["power_basis"] in POWER_BASES, tier["model"]
        else:  # finding 30: what was searched, when no figure is published
            assert tier["power_basis"] == "not_given", tier["model"]
            assert tier["power_note"], tier["model"]
        if "inrush_a" in tier:
            assert tier["inrush_basis"] in {"datasheet", "assumed"}, tier["model"]


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_a_dc_input_range_contains_the_nominal_voltage(record: dict[str, Any]) -> None:
    for part in [record["datasheet"], *_tiers(record)]:
        if "input_v_min" in part:
            assert part["input_v_min"] < part["input_v_max"]
            if part.get("supply_type") == "VDC":
                assert part["input_v_min"] <= part["voltage_v"] <= part["input_v_max"]


MCB_RECORDS = [r for r in RECORDS if r["part_id"].startswith("MCB-")]


@pytest.mark.parametrize("record", MCB_RECORDS, ids=_ids(MCB_RECORDS))
def test_every_mcb_states_its_trip_curve_and_dc_magnetic_multiple(record: dict[str, Any]) -> None:
    for ratings in [record["datasheet"]["ratings"], *(t["ratings"] for t in _tiers(record))]:
        assert ratings["trip_curve"] == "C"
        assert ratings["magnetic_trip_multiple_dc"] >= ratings["magnetic_trip_multiple"]
    assert "same_brand_dc_range" in record["datasheet"]["ratings"]


def _tier(part_id: str, make: str, tier: str) -> dict[str, Any]:
    record = next(r for r in RECORDS if r["part_id"] == part_id)
    alternative = next(a for a in record["alternatives"] if a["make"] == make)
    return dict(alternative["tiers"][tier])


def test_finding_30_the_scalance_and_arbiter_tiers_have_their_datasheet_power() -> None:
    scalance = _tier("SEL-2730M-EXT", "Siemens", "low")
    arbiter = _tier("SEL-2488", "Arbiter Systems", "mid")

    assert scalance["ordering_code"] == "6GK5324-4GG10-4JR2"  # the EEC code, finding 27
    assert (scalance["unit_power_w"], scalance["supply_type"], scalance["voltage_v"]) == (
        42,
        "VDC",
        125,
    )
    assert (scalance["input_v_min"], scalance["input_v_max"]) == (60, 250)
    assert (arbiter["unit_power_w"], arbiter["power_basis"]) == (30, "datasheet_max")


def test_finding_31_the_sicam_di_modules_give_16_inputs_each() -> None:
    # SEL-2244-2's Siemens tiers: one DI-8112, two DI-8112, two DI-8113.
    inputs = [_tier("SEL-2244-2", "Siemens", tier).get("di_inputs") for tier in TIERS]

    assert inputs == [16, 32, 32]
