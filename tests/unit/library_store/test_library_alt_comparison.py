"""The comparison list of a device and its alternatives (ADR 0017; design: Library editing)."""

from pathlib import Path

import pytest

from bomgen.io.loader import load_library
from bomgen.library_store.alternatives import compare_alternatives
from bomgen.library_store.device_db import DeviceRecord, parse_device_records
from bomgen.library_store.edit import SetValue, apply_edits
from bomgen.models.library import Library

ROOT = Path(__file__).parents[3]
FIRST = "RST2228-L1-24MM"
SECOND = "RST2228-L2"


def _grouped(base: Library, **second: object) -> Library:
    edits = [
        SetValue(path=["devices", FIRST, "alt_group"], value="L1-SWITCH"),
        SetValue(path=["devices", SECOND, "alt_group"], value="L1-SWITCH"),
        SetValue(path=["devices", SECOND, "tier"], value="high"),
        SetValue(path=["devices", FIRST, "tier"], value="mid"),
        *(SetValue(path=["devices", SECOND, key], value=value) for key, value in second.items()),
    ]
    result = apply_edits(base, edits)
    assert result.library is not None, result.problems
    return result.library


@pytest.fixture(scope="module")
def base() -> Library:
    return load_library(ROOT / "examples" / "library.yaml")


@pytest.fixture(scope="module")
def records() -> dict[str, DeviceRecord]:
    files = {
        f"device-db/{p.name}": p.read_bytes() for p in (ROOT / "data" / "device-db").glob("*.yaml")
    }
    return parse_device_records(files)


def test_the_device_comes_first_then_its_alternatives_in_library_order(base: Library) -> None:
    rows = compare_alternatives(_grouped(base), FIRST)

    assert [r.part_id for r in rows] == [FIRST, SECOND]
    assert [r.is_self for r in rows] == [True, False]
    assert [r.tier for r in rows] == ["mid", "high"]


def test_the_list_is_the_same_from_either_member(base: Library) -> None:
    library = _grouped(base)

    rows = compare_alternatives(library, SECOND)

    assert [r.part_id for r in rows] == [SECOND, FIRST]


def test_a_row_shows_the_comparison_fields(base: Library) -> None:
    library = _grouped(base)
    device = library.get(SECOND)
    assert device is not None

    row = compare_alternatives(library, FIRST)[1]

    assert row.model == device.model
    assert row.make == device.make
    assert row.unit_power_w == device.unit_power_w
    assert row.height_u == device.height_u
    assert device.ports
    assert row.first_port_group == device.ports[0]


def test_power_inrush_and_height_are_compared_with_the_device(base: Library) -> None:
    library = _grouped(base, inrush_a=30.0, unit_power_w=50.0, height_u=3)
    first = library.get(FIRST)
    assert first is not None
    assert first.unit_power_w is not None

    rows = compare_alternatives(library, FIRST)

    assert rows[0].power_delta_w == 0
    assert rows[1].power_delta_w == pytest.approx(50.0 - first.unit_power_w)
    assert rows[1].height_delta_u == 3 - (first.height_u or 0)
    assert rows[1].inrush_delta_a is None  # the device itself gives no inrush figure


def test_a_missing_figure_has_no_delta(base: Library) -> None:
    rows = compare_alternatives(_grouped(base), FIRST)

    assert rows[1].inrush_a is None
    assert rows[1].inrush_delta_a is None


def test_the_data_quality_comes_from_the_device_database(
    base: Library, records: dict[str, DeviceRecord]
) -> None:
    rows = compare_alternatives(_grouped(base), FIRST, records)

    assert rows[0].data_quality == records[FIRST].verified
    assert rows[1].data_quality == records[SECOND].verified


def test_without_a_database_the_data_quality_is_not_given(base: Library) -> None:
    assert [r.data_quality for r in compare_alternatives(_grouped(base), FIRST)] == [None, None]


def test_a_device_without_a_group_is_alone(base: Library) -> None:
    rows = compare_alternatives(base, FIRST)

    assert [r.part_id for r in rows] == [FIRST]
    assert rows[0].tier is None


def test_an_unknown_part_is_refused(base: Library) -> None:
    with pytest.raises(KeyError, match="NO-SUCH"):
        compare_alternatives(base, "NO-SUCH")
