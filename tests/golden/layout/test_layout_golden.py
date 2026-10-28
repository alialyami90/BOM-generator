"""Golden layout of the example substation (design rule R10, ADR 0013)."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from bomgen.engine.layout import LayoutResult, layout_substation
from bomgen.io.loader import load_substation
from bomgen.models.panel import PortPlan

pytestmark = pytest.mark.golden

ROOT = Path(__file__).parents[3]
EXPECTED: dict[str, Any] = yaml.safe_load(
    (Path(__file__).parent / "expected_panels.yaml").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def result() -> LayoutResult:
    return layout_substation(
        load_substation(ROOT / "examples" / "substations" / "gis01" / "substation.yaml")
    )


def test_r10_example_substation_sizing_matches_golden(result: LayoutResult) -> None:
    plan = result.plan
    assert (plan.l1_per_side, plan.l2_per_side, plan.l2_demand_per_side) == (
        EXPECTED["l1_per_side"],
        EXPECTED["l2_per_side"],
        EXPECTED["l2_demand_per_side"],
    )


def test_r10_example_substation_layout_matches_golden(result: LayoutResult) -> None:
    actual = [
        {
            "id": panel.id,
            "used_u": fill.used_u(result.rules),
            "devices": [[d.part_id, d.qty, d.lan] for d in panel.devices],
        }
        for panel, fill in zip(result.panels, result.fills, strict=True)
    ]
    expected = [{k: p[k] for k in ("id", "used_u", "devices")} for p in EXPECTED["panels"]]
    assert actual == expected


def test_r10_example_substation_port_plans_match_golden(result: LayoutResult) -> None:
    for panel, expected in zip(result.panels, EXPECTED["panels"], strict=True):
        for part_id, plan in expected["port_plans"].items():
            assert panel.port_plans[part_id] == PortPlan.model_validate(plan), part_id


def test_r10_example_substation_has_no_layout_errors(result: LayoutResult) -> None:
    assert not result.report.has_errors, result.report.lines()
