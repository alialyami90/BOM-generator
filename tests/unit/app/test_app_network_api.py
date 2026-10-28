"""The Network result, the L1 ranking and the Panels board of the desktop app (plan M10c).

The expected values are the example substation's layout golden (tests/golden/layout).
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bomgen.app import api
from bomgen.cli import app as cli
from bomgen.engine.layout import l1_candidates
from bomgen.io.loader import load_substation

EXAMPLES = Path(__file__).parents[3] / "examples"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


@pytest.fixture
def substation(project: Path) -> Path:
    return project.parent / "substations" / "gis01" / "substation.yaml"


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
    return api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
            "BOMGEN_APP_HOME": str(tmp_path / "app"),
        }
    )


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)
    return envelope["data"]


def edit(file: Path, old: str, new: str) -> None:
    text = file.read_text(encoding="utf-8")
    assert old in text
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def page(app: api.Api, project: Path) -> Any:
    return ok(app.substation_layout(str(project), "gis01"))


def test_the_result_card_is_the_engines_network_plan(app: api.Api, project: Path) -> None:
    plan = page(app, project)["plan"]

    assert plan["ied_count"] == 40
    assert plan["topology"] == "star"
    assert (plan["l1_per_side"], plan["l2_per_side"], plan["l2_demand_per_side"]) == (3, 1, 8)
    assert plan["l1_usable_ports"] == 19
    assert plan["l2_usable_ports"] == 16
    assert plan["l1_part_id"] == "RST2228-L1-24MM"
    assert plan["l1_pinned"] is True  # the example names its L1 part


def test_the_l1_ranking_is_in_the_engines_order(
    app: api.Api, project: Path, substation: Path
) -> None:
    ranking = page(app, project)["l1_ranking"]

    expected = l1_candidates(load_substation(substation))
    assert [r["part_id"] for r in ranking] == [c.ports.part_id for c in expected]
    assert [r["per_side"] for r in ranking] == [c.per_side for c in expected]
    assert [r["usable_ports"] for r in ranking] == [c.usable_ports for c in expected]
    assert {"make", "model", "ports"} <= set(ranking[0])


def test_an_unpinned_l1_uses_the_tools_pick(app: api.Api, project: Path, substation: Path) -> None:
    edit(substation, "part_id: RST2228-L1-24MM, ", "")

    data = page(app, project)

    assert data["plan"]["l1_pinned"] is False
    assert data["plan"]["l1_part_id"] == data["l1_ranking"][0]["part_id"]


def test_the_board_has_the_golden_panels(app: api.Api, project: Path) -> None:
    panels = page(app, project)["panels"]

    assert [(p["id"], p["number"], p["side"], p["pair"]) for p in panels] == [
        ("psa1", 1, "A", 1),
        ("psa2", 2, "B", 1),
    ]
    first = panels[0]
    assert (first["used_u"], first["capacity_u"], first["free_u"]) == (29, 32, 3)
    assert first["cabinet_name"] == "PSA Cabinet - 001"
    devices = [u["device"] for u in first["units"]]
    assert devices[:3] == ["fopp", "l2", "l1"]
    assert devices.count("l1") == 3
    assert first["blank_plates"] == sum(1 for u in first["units"] if u["block_u"]) - 1
    firewall = next(u for u in first["units"] if u["device"] == "ext-fw")
    assert firewall["block_u"] == 0  # DIN rail
    assert first["din_rail"] >= 1
    l2 = next(u for u in first["units"] if u["device"] == "l2")
    assert l2["cable_manager_u"] == 1
    assert l2["block_u"] == l2["height_u"] + 1
    assert {"key", "n", "part_id", "label", "moved"} <= set(l2)
    l1 = [u for u in first["units"] if u["device"] == "l1"]
    assert [(u["role"], u["n"], u["of"]) for u in l1] == [("l1_switch", n, 3) for n in (1, 2, 3)]


def test_a_moved_device_is_marked(app: api.Api, project: Path, substation: Path) -> None:
    edit(substation, "  overrides: []", "  overrides: [{device: gps, panel: 2}]")

    panels = page(app, project)["panels"]

    gps = next(u for p in panels for u in p["units"] if u["device"] == "gps")
    assert gps["moved"] is True
    assert next(p for p in panels if any(u is gps for u in p["units"]))["number"] == 2
    assert not any(u["moved"] for p in panels for u in p["units"] if u["device"] != "gps")
    assert page(app, project)["overrides"] == [
        {"device": "gps", "unit": None, "side": None, "panel": 2}
    ]


def test_hand_written_panels_are_listed_and_the_board_is_what_the_layout_would_write(
    app: api.Api, project: Path
) -> None:
    data = page(app, project)

    # the example still feeds the annunciator from psa3, which the layout does not write
    [issue] = data["issues"]
    assert issue["subject"] == "loose_material.items[0].fed_from"
    assert issue["message"].startswith("names panel 'psa3'")
    assert data["generated"] is False
    assert [(p["id"], p["generated"]) for p in data["list"]] == [
        ("psa1", False),
        ("psa2", False),
        ("psa3", False),
        ("ws", False),
    ]
    assert data["list"][0]["sheet"] == "1"
    assert data["list"][0]["cabinet_number"] == "861-GIS01-PSA-0001"
    assert data["list"][3]["manual"] is True


def test_layout_errors_show_on_the_board(app: api.Api, project: Path, substation: Path) -> None:
    edit(substation, "  overrides: []", "  overrides: [{pair: gw, panel: [9, 10]}]")

    data = page(app, project)

    assert data["panels"]
    errors = [i for i in data["issues"] if i["level"] == "error"]
    assert any(i["subject"].startswith("gw") for i in errors)


def test_a_substation_without_equipment_has_no_network_yet(
    app: api.Api, project: Path, substation: Path
) -> None:
    text = substation.read_text(encoding="utf-8")
    start = text.index("equipment:")
    end = text.index("\nnetwork:")
    substation.write_text(text[:start] + "equipment: []\n" + text[end:], encoding="utf-8")

    data = page(app, project)

    assert data["plan"] is None
    assert data["l1_ranking"] == []
    assert data["panels"] == []
    assert data["reason"] is None


def test_a_substation_with_input_errors_gives_the_reason(
    app: api.Api, project: Path, substation: Path
) -> None:
    edit(substation, "ied_count: 40", "ied_count: lots")

    data = page(app, project)

    assert data["reason"]
    assert data["plan"] is None
    assert data["problems"]


def test_generated_panels_with_a_layout_error_still_show_the_board(
    app: api.Api, project: Path, substation: Path
) -> None:
    edit(substation, "fed_from: psa3", "fed_from: psa1")
    result = CliRunner().invoke(cli, ["layout", "--substation", str(substation), "--force"])
    assert result.exit_code == 0, result.output
    edit(substation, "  overrides: []", "  overrides: [{pair: gw, panel: [9, 10]}]")

    data = page(app, project)

    assert data["generated"] is True
    assert data["reason"] is None
    assert data["panels"]
    assert any(i["level"] == "error" for i in data["issues"])
    assert any(p["level"] == "error" for p in data["problems"])  # Build is blocked
