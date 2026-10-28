"""The app's editing endpoints over the substation writers (plan M17, ADR 0021).

The writers themselves are tested in tests/unit/test_edit.py; these tests cover what
the page gets back: whether the file was written, the problems, and the refreshed board.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api

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


def refused(envelope: dict[str, object]) -> dict[str, str]:
    assert envelope["ok"] is False, envelope
    return envelope["error"]  # type: ignore[return-value]


def test_a_pin_is_written_and_the_board_comes_back(
    app: api.Api, project: Path, substation: Path
) -> None:
    pin = {"device": "gps", "panel": 2, "unit": None, "side": None, "position": None}

    reply = ok(app.set_layout_overrides(str(project), "gis01", [pin]))

    assert reply["written"] is True
    assert "- { device: gps, panel: 2 }" in substation.read_text("utf-8")
    [panel] = [p for p in reply["page"]["panels"] if any(u["device"] == "gps" for u in p["units"])]
    assert panel["number"] == 2
    assert [u["pinned"] for u in panel["units"] if u["device"] == "gps"] == [True]
    assert reply["page"]["overrides"] == [pin]


def test_an_edit_that_breaks_the_files_is_not_written(
    app: api.Api, project: Path, substation: Path
) -> None:
    before = substation.read_text("utf-8")

    reply = ok(app.set_layout_removed(str(project), "gis01", [{"device": "nope"}]))

    assert reply["written"] is False
    assert reply["page"] is None
    assert reply["issues"]
    assert {"file", "location", "message", "line"} <= set(reply["issues"][0])
    assert substation.read_text("utf-8") == before


def test_removed_units_are_written(app: api.Api, project: Path) -> None:
    reply = ok(app.set_layout_removed(str(project), "gis01", [{"device": "gps"}]))

    assert reply["written"] is True
    assert reply["page"]["removed"][0]["device"] == "gps"
    assert not any(u["device"] == "gps" for p in reply["page"]["panels"] for u in p["units"])


def test_panel_options_are_read_set_and_removed(app: api.Api, project: Path) -> None:
    options = {o["key"]: o for o in ok(app.panel_options(str(project), "gis01", 1))}
    assert options["inter_panel_terminals"]["value"] == 40
    assert options["inter_panel_terminals"]["own"] is False

    assert ok(app.set_panel_option(str(project), "gis01", "aux_socket_a", 16, 1))["written"]
    options = {o["key"]: o for o in ok(app.panel_options(str(project), "gis01", 1))}
    assert (options["aux_socket_a"]["value"], options["aux_socket_a"]["own"]) == (16, True)

    assert ok(app.remove_panel_option(str(project), "gis01", "aux_socket_a", 1))["written"]
    options = {o["key"]: o for o in ok(app.panel_options(str(project), "gis01", 1))}
    assert options["aux_socket_a"]["own"] is False


def test_a_shared_option_applies_to_every_generated_panel(app: api.Api, project: Path) -> None:
    reply = ok(app.set_panel_option(str(project), "gis01", "inter_panel_terminals", 44, None))

    assert reply["written"] is True
    for panel in (1, 2):
        options = {o["key"]: o for o in ok(app.panel_options(str(project), "gis01", panel))}
        assert options["inter_panel_terminals"]["shared"] == 44


def test_enclosure_document_and_port_plan_are_written(app: api.Api, project: Path) -> None:
    enclosure = {
        "make": "Rittal",
        "model": "TS 8",
        "ordering_code": "8886.000",
        "h_mm": 2200,
        "d_mm": 800,
        "w_mm": 800,
        "cable_entry": "top",
    }
    assert ok(app.set_enclosure(str(project), "gis01", enclosure))["written"]
    assert not ok(app.set_generated_document(str(project), "gis01", "nope-bom"))["written"]
    plan = {"uplinks": [{"count": 2, "speed": "1G", "media": "SM"}], "serial_ports": 2}
    assert ok(app.set_port_plan(str(project), "gis01", "gw", plan))["written"]
    assert ok(app.set_port_plan(str(project), "gis01", "gw", None))["written"]


def test_an_edit_naming_something_that_is_not_there_is_refused(app: api.Api, project: Path) -> None:
    assert refused(app.set_port_plan(str(project), "gis01", "xx", None))["kind"] == "edit_refused"
    assert refused(app.set_panel_option(str(project), "gis01", "colour", 1, None))["kind"] == (
        "edit_refused"
    )
    assert refused(app.panel_options(str(project), "gis99", 1))["kind"] == "not_found"


BAD_MOVE = {"pair": "gw", "panel": [9, 10]}  # panels 9 and 10 do not follow the last pair


def test_a_move_the_layout_cannot_take_is_refused_and_not_written(
    app: api.Api, project: Path, substation: Path
) -> None:
    before = substation.read_text("utf-8")

    reply = ok(app.set_layout_overrides(str(project), "gis01", [BAD_MOVE]))

    assert reply["written"] is False
    assert reply["page"] is None
    assert reply["issues"]
    assert all(i["location"].startswith("layout: ") for i in reply["issues"])
    assert substation.read_text("utf-8") == before


def test_check_layout_says_whether_a_move_fits_without_writing(
    app: api.Api, project: Path, substation: Path
) -> None:
    before = substation.read_text("utf-8")
    gps = {"device": "gps", "panel": 2}

    assert ok(app.check_layout(str(project), "gis01", [gps], []))["fits"] is True
    refused_move = ok(app.check_layout(str(project), "gis01", [BAD_MOVE], []))
    assert refused_move["fits"] is False
    assert refused_move["issues"][0]["message"]
    assert substation.read_text("utf-8") == before
