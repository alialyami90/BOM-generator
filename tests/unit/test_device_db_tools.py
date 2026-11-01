"""The M14 generator in data/device-db/tools/ (alternatives as library parts)."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "data" / "device-db" / "tools" / "library_entries.py"


@pytest.fixture(scope="module")
def tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("library_entries", TOOL)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _original() -> dict[str, Any]:
    return {
        "part_id": "SW-1",
        "category": "network_switch",
        "description_template": "Switch",
        "tag_type": "ESW",
        "purdue_level": "L1",
        "load_type": "CONTINUOUS",
        "hwio_points": 1,
    }


def _record(**mid: Any) -> dict[str, Any]:
    low = {"model": "Low 1", "mounting_kind": "din_rail", "supply_type": "none"}
    return {
        "part_id": "SW-1",
        "alternatives": [
            {
                "make": "Maker Co",
                "tiers": {"low": low, "mid": {"model": "Mid 1", **mid}, "high": {"same_as": "mid"}},
            }
        ],
    }


def test_each_distinct_tier_becomes_a_part_in_its_originals_group(tool: ModuleType) -> None:
    mid = {
        "mounting_kind": "rack",
        "height_u": 1,
        "supply_type": "VDC",
        "voltage_v": 125.0,
        "unit_power_w": 12.0,
        "power_supplies": 2,
        "inrush_a": 8,
    }

    parts, skipped = tool.alternative_parts([_original()], {"SW-1": _record(**mid)}, set())

    assert skipped == []
    assert [p["part_id"] for p in parts] == ["SW-1.MAKER-CO-LOW", "SW-1.MAKER-CO-MID"]
    low, power = parts
    assert (low["height_u"], low["alt_group"], low["tier"]) == (0, "SW-1", "low")
    assert "unit_power_w" not in low
    assert (power["voltage_v"], power["unit_power_w"], power["power_supplies"]) == (125, 12, 2)
    assert (power["inrush_a"], power["tag_type"], power["hwio_points"]) == (8, "ESW", 1)


def test_a_part_the_library_has_is_not_added_again(tool: ModuleType) -> None:
    parts, _ = tool.alternative_parts(
        [_original()], {"SW-1": _record(supply_type="none")}, {"SW-1.MAKER-CO-LOW"}
    )

    assert [p["part_id"] for p in parts] == ["SW-1.MAKER-CO-MID"]


def test_a_powered_tier_without_a_power_figure_is_skipped(tool: ModuleType) -> None:
    parts, skipped = tool.alternative_parts(
        [_original()], {"SW-1": _record(supply_type="VAC", voltage_v=230)}, set()
    )

    assert [p["part_id"] for p in parts] == ["SW-1.MAKER-CO-LOW"]
    assert skipped == ["SW-1 Maker Co mid Mid 1: no power figure"]


def test_the_shipped_library_has_every_powered_alternative_but_the_unpowered_figures(
    tool: ModuleType,
) -> None:
    # Finding 30: the nine powered tiers that publish no figure are the only ones left out.
    parts, skipped = tool.alternative_parts(*tool.inputs(ROOT))

    assert parts == []
    assert len(skipped) == 9


def test_the_generator_reproduces_the_examples_alternatives(tool: ModuleType) -> None:
    originals, records, _ = tool.inputs(ROOT)
    text = (ROOT / "examples" / "library.yaml").read_text(encoding="utf-8")
    example = {d["part_id"]: d for d in yaml.safe_load(text)["devices"]}

    parts, _ = tool.alternative_parts(originals, records, set())
    made = {p["part_id"]: p for p in parts if p["part_id"] in example}

    assert len(made) == 279
    for part_id, part in made.items():
        assert part == example[part_id], part_id
