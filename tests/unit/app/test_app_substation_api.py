"""Substation endpoints of the desktop app: Settings and the Network inputs (plan M10c)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api

EXAMPLES = Path(__file__).parents[3] / "examples"
SUBSTATION = Path("substations") / "gis01" / "substation.yaml"


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
    json.dumps(envelope)
    return envelope["data"]


def edit(file: Path, old: str, new: str) -> None:
    text = file.read_text(encoding="utf-8")
    assert old in text
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_open_substation_gives_its_name_file_and_project(app: api.Api, project: Path) -> None:
    page = ok(app.open_substation(str(project), "gis01"))

    assert page["id"] == "gis01"
    assert page["name"] == "GIS Substation"
    assert page["file"] == str(project.parent / SUBSTATION)
    assert page["project"]["name"].startswith("JAFURAH JFGP2")
    assert page["problems"] == []


def test_calculation_sheets_print_their_register_documents(app: api.Api, project: Path) -> None:
    page = ok(app.open_substation(str(project), "gis01"))

    sheets = {c["key"]: c for c in page["calculations"]}
    assert sheets["power_consumption"]["document"] == "gis01-power"
    assert sheets["power_consumption"]["entry"]["doc_no"] == "VD-EL0009-861GISPSA-002"
    assert sheets["heat_calculations"]["scope"] == "861-GIS01-PSA-001/002"
    assert [d["key"] for d in page["documents"]] == ["gis01-bom", "gis01-power", "gis01-heat"]


def test_output_gives_the_workbook_file_name_from_the_main_document(
    app: api.Api, project: Path
) -> None:
    output = ok(app.open_substation(str(project), "gis01"))["output"]

    assert output["document"] == "gis01-bom"
    assert output["file_name"] == "{doc_no}_PSA_BOM_Rev{rev}.xlsx"
    assert output["result"] == "VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx"
    assert output["sheet_names"]["heat_dissipation"] == "Heat Dissipation"


def test_constants_show_the_project_default_and_mark_a_changed_one(
    app: api.Api, project: Path
) -> None:
    substation = project.parent / SUBSTATION
    edit(substation, "\nequipment:", "\nconstants: { power_margin: 0.3 }\n\nequipment:")

    page = ok(app.open_substation(str(project), "gis01"))

    constants = {c["key"]: c for c in page["constants"]}
    assert len(constants) == 13
    assert constants["power_margin"] == {
        "key": "power_margin",
        "value": 0.3,
        "default": 0.25,
        "changed": True,
    }
    assert constants["dc_voltage_v"]["changed"] is False
    assert constants["dc_voltage_v"]["value"] == 125


def test_spares_and_network_inputs_are_read(app: api.Api, project: Path) -> None:
    page = ok(app.open_substation(str(project), "gis01"))

    spares = {s["key"]: s for s in page["spares"]}
    assert spares["port_fraction"]["value"] == 0.2
    assert spares["rack_u_reserved"]["changed"] is False
    assert page["network"]["ied_count"] == 40
    assert page["network"]["topology"] == "star"


def test_equipment_rows_carry_the_library_device(app: api.Api, project: Path) -> None:
    page = ok(app.open_substation(str(project), "gis01"))

    rows = {e["id"]: e for e in page["equipment"]}
    assert list(rows)[:3] == ["fopp", "l2", "l1"]
    assert rows["l1"]["role"] == "l1_switch"
    assert rows["l1"]["redundant"] is True
    assert rows["gps"]["l2_ports"] == 1
    assert rows["l2"]["device"]["model"]
    assert rows["l2"]["device"]["known"] is True


def test_loose_material_and_the_yaml_source(app: api.Api, project: Path) -> None:
    page = ok(app.open_substation(str(project), "gis01"))

    assert page["loose_material"]["items"]
    assert page["yaml"].startswith("# yaml-language-server")


def test_a_substation_with_errors_still_opens_with_located_problems(
    app: api.Api, project: Path
) -> None:
    edit(project.parent / SUBSTATION, "ied_count: 40", "ied_count: lots")

    page = ok(app.open_substation(str(project), "gis01"))

    assert page["name"] == "gis01"
    assert page["problems"]
    assert all(p["file"].endswith("substation.yaml") for p in page["problems"])
    assert "ied_count" in page["yaml"]


def test_an_unknown_substation_is_refused(app: api.Api, project: Path) -> None:
    envelope = app.open_substation(str(project), "nope")

    assert envelope["ok"] is False
    assert envelope["error"]["kind"] == "not_found"  # type: ignore[index]


def test_a_constant_the_project_defaults_reject_shows_as_written(
    app: api.Api, project: Path
) -> None:
    edit(project.parent / SUBSTATION, "\nequipment:", "\nconstants: { t_max_c: 1 }\nequipment:")

    page = ok(app.open_substation(str(project), "gis01"))

    t_max = next(c for c in page["constants"] if c["key"] == "t_max_c")
    assert t_max["value"] == 1
    assert t_max["changed"] is True
    assert any(p["location"].startswith("constants") for p in page["problems"])


@pytest.mark.parametrize(
    "damage",
    [
        pytest.param(lambda p: p.unlink(), id="missing"),
        pytest.param(lambda p: edit(p, "\nlibrary:", "\nlibary:"), id="unknown-key"),
        pytest.param(lambda p: shutil.copy(p.parent / SUBSTATION, p), id="a-substation-yaml"),
    ],
)
def test_a_project_that_cannot_be_read_gives_its_own_problems(
    app: api.Api, project: Path, damage: Any
) -> None:
    damage(project)

    envelope = app.open_substation(str(project), "gis01")

    assert envelope["ok"] is False
    assert envelope["error"]["kind"] == "project_invalid"  # type: ignore[index]
    assert "project.yaml" in envelope["error"]["message"]  # type: ignore[index]


def test_a_library_that_is_not_installed_is_a_problem(app: api.Api, project: Path) -> None:
    edit(project, "  file: library.yaml\n", "")

    page = ok(app.open_substation(str(project), "gis01"))

    assert [p["location"] for p in page["problems"]] == ["library"]
    assert page["problems"][0]["file"].endswith("project.yaml")


def test_an_equipment_part_missing_from_the_library_is_marked_unknown(
    app: api.Api, project: Path
) -> None:
    edit(project.parent / SUBSTATION, "part_id: FOPP-96SM", "part_id: NO-SUCH-PART")

    page = ok(app.open_substation(str(project), "gis01"))

    rows = {e["id"]: e for e in page["equipment"]}
    assert rows["fopp"]["device"] == {"known": False}
    assert rows["l2"]["device"]["known"] is True
    assert page["problems"]
