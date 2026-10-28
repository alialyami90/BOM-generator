"""Diff of two device libraries by part_id (plan M8: added / changed / removed parts)."""

from typing import Any

import pytest

from bomgen.library_store.diff import diff_libraries, parse_library
from bomgen.library_store.errors import LibraryPackageError


def _library(*devices: dict[str, Any], catalogues: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"devices": list(devices), "catalogues": catalogues or {}}


SWITCH = {"part_id": "RST2228-L1-24MM", "make": "Ruggedcom", "unit_power_w": 77}
FIREWALL = {"part_id": "FW-EXT", "make": "Fortinet", "unit_power_w": 40}
GATEWAY = {"part_id": "GW-DHPCC", "make": "SEL", "unit_power_w": 20}


def test_diff_lists_added_removed_and_changed_parts() -> None:
    old = _library(SWITCH, FIREWALL)
    new = _library({**SWITCH, "unit_power_w": 80, "model": "RST-2228"}, GATEWAY)

    diff = diff_libraries(old, new)

    assert diff.added == ["GW-DHPCC"]
    assert diff.removed == ["FW-EXT"]
    assert diff.changed == {"RST2228-L1-24MM": ["model", "unit_power_w"]}
    assert not diff.is_empty


def test_diff_of_identical_libraries_is_empty() -> None:
    assert diff_libraries(_library(SWITCH), _library(SWITCH)).is_empty


def test_diff_reports_changed_catalogues() -> None:
    old = _library(catalogues={"mcb": {"ratings_a": [1, 2, 6]}, "aux_contact": {"model": "A"}})
    new = _library(catalogues={"mcb": {"ratings_a": [1, 2, 6, 10]}, "aux_contact": {"model": "A"}})

    assert diff_libraries(old, new).catalogues_changed == ["mcb"]


def _with_brands(**brands: list[dict[str, Any]]) -> dict[str, Any]:
    return {"devices": [], "catalogues": {}, "catalogue_brands": brands}


def test_diff_reports_added_changed_and_removed_brand_sets_by_kind_and_id() -> None:
    old = _with_brands(
        mcb=[{"id": "kept", "make": "A"}, {"id": "edited", "make": "A"}, {"id": "gone"}]
    )
    new = _with_brands(
        mcb=[{"id": "kept", "make": "A"}, {"id": "edited", "make": "B"}, {"id": "new"}],
        busbars=[{"id": "extra", "entries": {}}],
    )

    diff = diff_libraries(old, new)

    assert diff.catalogues_changed == ["busbars:extra", "mcb:edited", "mcb:gone", "mcb:new"]
    assert not diff.is_empty


def test_diff_of_identical_brand_sets_is_empty() -> None:
    brands = _with_brands(mcb=[{"id": "kept", "make": "A"}])

    assert diff_libraries(brands, brands).is_empty


def test_diff_against_a_library_without_brand_sets_ignores_the_missing_key() -> None:
    assert diff_libraries(_library(), _with_brands(mcb=[])).is_empty


def test_diff_against_nothing_adds_every_part() -> None:
    diff = diff_libraries(None, _library(SWITCH, FIREWALL))

    assert diff.added == ["FW-EXT", "RST2228-L1-24MM"]
    assert diff.removed == []


def test_diff_lists_changed_extra_files() -> None:
    old_files = {"library.yaml": "a" * 64, "device-db/net.yaml": "b" * 64, "old.txt": "c" * 64}
    new_files = {"library.yaml": "d" * 64, "device-db/net.yaml": "e" * 64, "new.txt": "f" * 64}

    diff = diff_libraries(_library(), _library(), old_files, new_files)

    assert diff.files_added == ["new.txt"]
    assert diff.files_changed == ["device-db/net.yaml"]
    assert diff.files_removed == ["old.txt"]


def test_summary_lines_name_each_change() -> None:
    old = _library(SWITCH, FIREWALL)
    new = _library({**SWITCH, "unit_power_w": 80}, GATEWAY)

    lines = diff_libraries(old, new).summary_lines()

    assert "Added parts (1): GW-DHPCC" in lines
    assert "Removed parts (1): FW-EXT" in lines
    assert "Changed parts (1):" in lines
    assert "  RST2228-L1-24MM: unit_power_w" in lines


def test_summary_of_empty_diff() -> None:
    assert diff_libraries(_library(), _library()).summary_lines() == ["No changes."]


def test_parse_library_reads_devices() -> None:
    library = parse_library(b"devices:\n  - part_id: A\n  - part_id: B\ncatalogues: {}\n")
    assert [d["part_id"] for d in library["devices"]] == ["A", "B"]


def test_parse_library_rejects_duplicate_part_ids() -> None:
    with pytest.raises(LibraryPackageError, match="duplicate part_id 'A'"):
        parse_library(b"devices:\n  - part_id: A\n  - part_id: A\n")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"- a\n- b\n", "mapping"),
        (b"devices: 3\n", "devices"),
        (b"devices:\n  - 3\n", "devices"),
        (b"devices:\n  - make: X\n", "part_id"),
        (b"devices: []\ncatalogues: [1]\n", "catalogues"),
        (b"devices: [\n", "YAML"),
        (b"\xff\xfe", "YAML"),
    ],
)
def test_parse_library_rejects_malformed_documents(data: bytes, message: str) -> None:
    with pytest.raises(LibraryPackageError, match=message):
        parse_library(data)
