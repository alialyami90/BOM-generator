"""Editing a substation's Network inputs in the app (plan M17c, ADR 0021).

The field writers are tested in the io tests; these cover the bridge: the substation the
edit goes to, what a refused value leaves and the page that comes back.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.io.yaml_source import read_yaml

EXAMPLES = Path(__file__).parents[3] / "examples"
SUB = "gis01"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


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
    json.dumps(envelope, default=str)
    return envelope["data"]


def refused(envelope: dict[str, object]) -> dict[str, str]:
    assert envelope["ok"] is False, envelope
    return envelope["error"]  # type: ignore[return-value]


def substation_yaml(project: Path) -> dict[str, Any]:
    return read_yaml(project.parent / "substations" / SUB / "substation.yaml").data


def test_setting_the_ied_count_writes_the_substation_and_returns_its_page(
    app: api.Api, project: Path
) -> None:
    page = ok(app.set_substation_field(str(project), SUB, ["network", "ied_count"], 41))
    assert page["id"] == SUB
    assert substation_yaml(project)["network"]["ied_count"] == 41


def test_an_emptied_spare_is_removed_so_the_project_default_applies(
    app: api.Api, project: Path
) -> None:
    ok(app.set_substation_field(str(project), SUB, ["spares", "sfp_per_l1"], 5))
    assert substation_yaml(project)["spares"]["sfp_per_l1"] == 5
    ok(app.set_substation_field(str(project), SUB, ["spares", "sfp_per_l1"], None))
    assert "sfp_per_l1" not in (substation_yaml(project).get("spares") or {})


def test_a_refused_value_leaves_the_file_and_names_the_problem(app: api.Api, project: Path) -> None:
    before = (project.parent / "substations" / SUB / "substation.yaml").read_text()
    error = refused(app.set_substation_field(str(project), SUB, ["network", "ied_count"], -1))
    assert error["kind"] in {"invalid_edit", "edit_refused"}
    assert (project.parent / "substations" / SUB / "substation.yaml").read_text() == before


def test_checking_a_field_gives_the_models_message_or_none(app: api.Api, project: Path) -> None:
    assert ok(app.check_substation_field(str(project), SUB, ["network", "ied_count"], 12)) is None
    message = ok(app.check_substation_field(str(project), SUB, ["network", "topology"], "mesh"))
    assert message
    assert "Value error, " not in message


def test_an_added_equipment_row_is_written_at_the_end(app: api.Api, project: Path) -> None:
    row = {"id": "gps-2", "part_id": "SEL-2488", "role": "other", "l2_ports": 1}
    page = ok(app.add_equipment(str(project), SUB, row, None))
    assert page["equipment"][-1]["id"] == "gps-2"
    assert substation_yaml(project)["equipment"][-1]["part_id"] == "SEL-2488"


def test_a_removed_row_comes_back_at_its_place_on_undo(app: api.Api, project: Path) -> None:
    before = substation_yaml(project)["equipment"]
    at = [e["id"] for e in before].index("gps")
    removed = ok(app.remove_equipment(str(project), SUB, at))
    page = removed["page"]
    assert [e["id"] for e in page["equipment"]] == [e["id"] for e in before if e["id"] != "gps"]
    assert removed["row"] == page_row(before[at])  # as written, for Undo
    ok(app.add_equipment(str(project), SUB, removed["row"], at))
    assert [e["id"] for e in substation_yaml(project)["equipment"]] == [e["id"] for e in before]


def test_an_equipment_row_with_a_taken_id_is_refused(app: api.Api, project: Path) -> None:
    taken = substation_yaml(project)["equipment"][0]["id"]
    row = {"id": taken, "part_id": "SEL-2488", "role": "other"}
    assert refused(app.add_equipment(str(project), SUB, row, None))["kind"] == "invalid_edit"


def page_row(row: Any) -> dict[str, Any]:
    plain: dict[str, Any] = json.loads(json.dumps(dict(row), default=str))
    return plain


def test_a_row_the_substation_needs_is_not_removed_and_the_reason_is_plain(
    app: api.Api, project: Path
) -> None:
    ids = [e["id"] for e in substation_yaml(project)["equipment"]]
    error = refused(app.remove_equipment(str(project), SUB, ids.index("l2")))
    assert error["message"].startswith("equipment needs")


def test_the_page_lists_the_brands_and_whose_choice_applies(app: api.Api, project: Path) -> None:
    page = ok(app.open_substation(str(project), SUB))
    assert page["catalogue_choice"] == {}  # nothing chosen by the substation itself
    assert set(page["brands"]) >= {"mcb", "mcb_dc", "aux_contact", "terminal_blocks"}
    ok(app.set_substation_field(str(project), SUB, ["catalogue_choice", "mcb"], "default"))
    page = ok(app.open_substation(str(project), SUB))
    assert page["catalogue_choice"] == {"mcb": "default"}
    assert "project_choice" in page
