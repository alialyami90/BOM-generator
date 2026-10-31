"""Hand-written panels in the panel editor (plan M32b; the M32 design brief).

The app adds a panel to ``manual_panels``, edits its file one field at a time (the device
list as a whole), and deletes it only when nothing still names it.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.io.yaml_source import read_yaml

EXAMPLES = Path(__file__).parents[3] / "examples"


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
    return api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
            "BOMGEN_APP_HOME": str(tmp_path / "app"),
        }
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


@pytest.fixture
def sub_dir(project: Path) -> Path:
    return project.parent / "substations" / "gis01"


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)
    return envelope["data"]


NEW = {"name": "Telecom Rack", "cabinet_number": "861-GIS01-TEL-0001", "kind": "network"}


def test_a_new_panel_is_written_listed_last_and_opened(
    app: api.Api, project: Path, sub_dir: Path
) -> None:
    reply = ok(app.add_panel(str(project), "gis01", {**NEW, "part_id": "SEL-2488"}))

    assert reply["written"] is True
    assert reply["id"] == "telecom-rack"
    data = read_yaml(sub_dir / "panels" / "telecom-rack.yaml").data
    assert data["cabinet_name"] == "Telecom Rack"
    assert data["cabinet_number"] == "861-GIS01-TEL-0001"
    assert (data["tag_prefix"], data["kind"]) == ("TELECOM", "network")
    assert data["devices"] == [{"part_id": "SEL-2488"}]
    assert data["sheet_name"] == "5"  # after psa1-3 and ws
    assert data["document"] == "gis01-bom"
    assert data["enclosure"]["make"] == "Rawabi"  # as the generated panels
    manual = read_yaml(sub_dir / "substation.yaml").data["manual_panels"]
    assert manual[-1] == "panels/telecom-rack.yaml"
    page = reply["page"]
    assert (page["panel"]["id"], page["panel"]["manual"]) == ("telecom-rack", True)


def test_a_second_panel_with_the_same_name_gets_its_own_id(app: api.Api, project: Path) -> None:
    ok(app.add_panel(str(project), "gis01", {**NEW, "part_id": "SEL-2488"}))
    other = {**NEW, "cabinet_number": "861-GIS01-TEL-0002", "part_id": "SEL-2488"}
    assert ok(app.add_panel(str(project), "gis01", other))["id"] == "telecom-rack-2"


def test_a_new_panel_with_an_unknown_part_is_not_written(
    app: api.Api, project: Path, sub_dir: Path
) -> None:
    reply = ok(app.add_panel(str(project), "gis01", {**NEW, "part_id": "NOPE"}))

    assert reply["written"] is False
    assert any("NOPE" in issue["message"] for issue in reply["issues"])
    assert not (sub_dir / "panels" / "telecom-rack.yaml").exists()


def test_a_field_of_a_hand_written_panel_is_set_checked_and_removed(
    app: api.Api, project: Path, sub_dir: Path
) -> None:
    page = ok(app.set_panel_field(str(project), "gis01", "ws", ["options", "ac_spare_branches"], 3))
    options = {o["key"]: o for o in page["options"]}
    assert (options["ac_spare_branches"]["value"], options["ac_spare_branches"]["own"]) == (3, True)
    assert options["smoke_detector"]["own"] is False
    assert options["smoke_detector"]["shared"] is True  # the default

    message = ok(app.check_panel_field(str(project), "gis01", "ws", ["enclosure", "h_mm"], -1))
    assert message
    assert ok(app.check_panel_field(str(project), "gis01", "ws", ["sheet_name"], "WS")) is None

    page = ok(
        app.set_panel_field(str(project), "gis01", "ws", ["options", "ac_spare_branches"], None)
    )
    assert {o["key"]: o for o in page["options"]}["ac_spare_branches"]["own"] is False
    assert "ac_spare_branches" not in read_yaml(sub_dir / "panels" / "ws.yaml").data["options"]


def test_the_device_list_is_written_as_a_whole(app: api.Api, project: Path) -> None:
    devices = [{"part_id": "NAP-F23"}, {"part_id": "SEL-3355", "qty": 2}]

    page = ok(app.set_panel_field(str(project), "gis01", "ws", ["devices"], devices))
    assert [(d["part_id"], d["qty"]) for d in page["devices"]] == [("NAP-F23", 1), ("SEL-3355", 2)]


def test_a_generated_panel_is_not_edited_as_a_file(app: api.Api, project: Path) -> None:
    file = project.parent / "substations" / "gis01" / "substation.yaml"
    text = file.read_text("utf-8")
    file.write_text(text[: text.index("\nloose_material:") + 1], "utf-8")
    ok(app.generate_panels(str(project), "gis01"))

    envelope = app.set_panel_field(str(project), "gis01", "psa1", ["sheet_name"], "9")
    assert envelope["ok"] is False
    assert envelope["error"]["kind"] == "edit_refused"  # type: ignore[index]


def test_a_panel_something_still_names_is_not_deleted(
    app: api.Api, project: Path, sub_dir: Path
) -> None:
    reply = ok(app.delete_panel(str(project), "gis01", "ws"))

    assert reply["written"] is False
    assert any("ws" in issue["message"] for issue in reply["issues"])  # loose material
    assert (sub_dir / "panels" / "ws.yaml").exists()


def test_a_deleted_panel_can_be_restored(app: api.Api, project: Path, sub_dir: Path) -> None:
    ok(app.add_panel(str(project), "gis01", {**NEW, "part_id": "SEL-2488"}))

    reply = ok(app.delete_panel(str(project), "gis01", "telecom-rack"))
    assert reply["written"] is True
    assert not (sub_dir / "panels" / "telecom-rack.yaml").exists()
    assert "panels/telecom-rack.yaml" not in (
        read_yaml(sub_dir / "substation.yaml").data.get("manual_panels") or []
    )

    restored = ok(app.restore_panel(str(project), "gis01", reply["panel"]))
    assert restored["written"] is True
    assert (
        read_yaml(sub_dir / "panels" / "telecom-rack.yaml").data["cabinet_name"] == "Telecom Rack"
    )


def test_a_hand_written_page_lists_the_library_parts_for_the_picker(
    app: api.Api, project: Path
) -> None:
    page = ok(app.panel_page(str(project), "gis01", "ws"))

    parts = {p["part_id"]: p for p in page["parts"]}
    assert "SEL-2488" in parts
    assert {"part_id", "label", "category"} <= set(parts["SEL-2488"])
    assert page["panel"]["mirror_of"] is None


def test_the_add_dialog_lists_the_library_parts(app: api.Api, project: Path) -> None:
    parts = ok(app.panel_parts(str(project), "gis01"))
    assert "SEL-3355" in [p["part_id"] for p in parts]
