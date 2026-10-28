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

DB_DIR = Path(__file__).resolve().parents[2] / "data" / "device-db"
TIERS = ("low", "mid", "high")
VERIFIED_LEVELS = {"confirmed", "partial", "unverified"}
KINDS = {"device", "catalogue"}

# Every distinct part in the example workbook. Device ids match examples/library.yaml.
EXPECTED_DEVICE_IDS = {
    "FOPP-96SM", "FOPP-SPOOL", "FOPP-SPLICE-HOLDER", "FOPP-PIGTAIL-LC-SM",
    "RST2228-L2", "RST2228-L1-24MM", "SEL-2730M-EXT", "SEL-3555-GW", "FGR-60F",
    "SEL-2488", "SEL-3555-RTAC", "SEL-2240", "SEL-2242", "SEL-2241", "SEL-2243",
    "SEL-2244-2", "SEL-3355", "NAP-F23", "KEYTEK-KBM", "SFP-1G-LX-SM", "SFP-1G-SX-MM",
    "SFP-100M-FX-MM", "FR-TRAN-SX", "PL1U12NEBK", "SEL-C607", "SZ2500-LAMP",
    "SK3243-FAN", "SK3238-FILTER", "SK3110-TH", "IPR-2903685", "IPR-BASE-2900934",
    "IPR-SUPP-2900944", "IPR-BRACKET-2900954", "COD-NEG-IRND150F12",
    "COD-POS-IRMD150F12", "SOCKET-730076", "NAP-K55", "LPA37-696", "ZENON-V12",
    "MS-OFFICE-2021", "ANN-DISPLAY-CABLE-10M", "ANN-USB-CABLE-10M", "MON-DVI-CABLE-3M",
    "MON-USB-CABLE-3M", "FO-PATCH-CORDS", "SEL-9524B", "SEL-C961-050", "SEL-915900139",
    "SEL-C961-025", "SEL-915900043",
}  # fmt: skip

EXPECTED_CATALOGUE_IDS = {
    "ENCL-RAWABI-2100", "ENCL-RITTAL-PC5386",
    "MCB-A9F74201", "MCB-A9F74202", "MCB-A9F74206", "MCB-A9F74210", "MCB-A9F74216",
    "AUX-A9A26924", "TB-UT-16", "TB-UT-2.5-MTD", "TB-UT-2.5-MT",
    "BUSBAR-AC-SAFETY-GND", "BUSBAR-INSTRUMENT-GND",
}  # fmt: skip


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


def test_every_workbook_device_and_commodity_has_a_record() -> None:
    devices = {r["part_id"] for r in RECORDS if r["kind"] == "device"}
    catalogues = {r["part_id"] for r in RECORDS if r["kind"] == "catalogue"}
    assert devices == EXPECTED_DEVICE_IDS
    assert catalogues == EXPECTED_CATALOGUE_IDS


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_kind_and_verified_level_are_known(record: dict[str, Any]) -> None:
    assert record["kind"] in KINDS
    assert record["verified"] in VERIFIED_LEVELS


@pytest.mark.parametrize("record", RECORDS, ids=_ids(RECORDS))
def test_record_names_the_part_it_enriches(record: dict[str, Any]) -> None:
    assert record["description"]
    assert record.get("model") or record.get("ordering_code") or record["kind"] == "catalogue"


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
def test_alternative_brands_differ_from_original_and_each_other(record: dict[str, Any]) -> None:
    makes = [str(alt["make"]).casefold() for alt in record["alternatives"]]
    assert len(set(makes)) == 2
    original = str(record.get("make") or "").casefold()
    if original:
        assert not any(original in make or make in original for make in makes)
