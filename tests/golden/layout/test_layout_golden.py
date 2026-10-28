"""Golden layout of the example substation (design rule R10, ADR 0013)."""

import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from bomgen.engine.layout import LayoutResult, layout_substation
from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.panel import PortPlan

pytestmark = pytest.mark.golden

ROOT = Path(__file__).parents[3]
EXPECTED: dict[str, Any] = yaml.safe_load(
    (Path(__file__).parent / "expected_panels.yaml").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def example(tmp_path_factory: pytest.TempPathFactory) -> LoadedSubstation:
    # Ali's answer (plan M1c): after a layout the annunciator is fed from panel 001
    # (side A). examples/ keeps psa3 for the hand-written goldens, so feed it from psa1
    # here.
    root = tmp_path_factory.mktemp("layout") / "examples"
    shutil.copytree(ROOT / "examples", root)
    path = root / "substations" / "gis01" / "substation.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("fed_from: psa3", "fed_from: psa1"))
    return load_substation(path)


@pytest.fixture(scope="module")
def result(example: LoadedSubstation) -> LayoutResult:
    return layout_substation(example)


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
            "devices": [[d.part_id, d.qty, d.lan, d.purpose] for d in panel.devices],
        }
        for panel, fill in zip(result.panels, result.fills, strict=True)
    ]
    expected = [{k: p[k] for k in ("id", "used_u", "devices")} for p in EXPECTED["panels"]]
    assert actual == expected


def test_r10_example_substation_port_plans_match_golden(result: LayoutResult) -> None:
    for panel, expected in zip(result.panels, EXPECTED["panels"], strict=True):
        for part_id, plan in expected["port_plans"].items():
            assert panel.port_plans[part_id] == PortPlan.model_validate(plan), part_id


def test_r10_example_substation_has_no_layout_issues(result: LayoutResult) -> None:
    assert result.report.issues == []


def test_r10_generated_psa1_feeds_the_annunciator(
    example: LoadedSubstation, result: LayoutResult
) -> None:
    manual = [p for p in example.panels if p.id in example.manual_panel_ids]
    bom = build(replace(example, panels=(*result.panels, *manual)))
    psa1 = next(p for p in bom.panels if p.panel_id == "psa1")
    qcod = next(line for line in psa1.lines if line.tag == "PSA1-QCOD-1")
    assert qcod.description == "2A, 2P MCB For Annunciator"
