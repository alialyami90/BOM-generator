"""The panel editor's page (plan M32a; the M32 design brief in docs/superpowers/specs).

``panel_page`` gives one panel: its header facts, enclosure, document, options, devices
with where they came from, the port plans and what the engine made of them, and its YAML.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

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
    """The example with hand-written panels (its loose material is hosted on ws)."""
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


@pytest.fixture
def generated(app: api.Api, project: Path) -> Path:
    """The example laid out: psa1 and psa2 generated, ws hand-written (manual)."""
    file = project.parent / "substations" / "gis01" / "substation.yaml"
    text = file.read_text("utf-8")
    file.write_text(text[: text.index("\nloose_material:") + 1], "utf-8")  # fed from psa3
    ok(app.generate_panels(str(project), "gis01"))
    return project


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)
    return envelope["data"]


def test_a_generated_panel_page_gives_its_header_facts(app: api.Api, generated: Path) -> None:
    page = ok(app.panel_page(str(generated), "gis01", "psa2"))

    assert page["reason"] is None
    head = page["panel"]
    assert (head["id"], head["number"], head["side"], head["pair"]) == ("psa2", 2, "B", 1)
    assert head["cabinet_number"] == "861-GIS01-PSA-0002"
    assert head["cabinet_name"] == "PSA Cabinet - 002"
    assert (head["kind"], head["generated"], head["manual"]) == ("network", True, False)
    assert head["file"].endswith("psa2.yaml")
    assert page["yaml"].startswith("#") or "psa2" in page["yaml"]


def test_enclosure_document_and_register_come_with_the_page(app: api.Api, generated: Path) -> None:
    page = ok(app.panel_page(str(generated), "gis01", "psa1"))

    assert page["enclosure"]["make"] == "Rawabi"
    assert page["enclosure"]["h_mm"] == 2100
    assert page["document"] == "gis01-bom"
    assert "gis01-bom" in [d["key"] for d in page["documents"]]


def test_options_of_a_generated_panel_say_which_are_its_own(app: api.Api, generated: Path) -> None:
    ok(app.set_panel_option(str(generated), "gis01", "aux_socket_a", 10, 2))

    options = {o["key"]: o for o in ok(app.panel_page(str(generated), "gis01", "psa2"))["options"]}
    assert (options["aux_socket_a"]["value"], options["aux_socket_a"]["own"]) == (10, True)
    assert options["smoke_detector"]["own"] is False
    first = {o["key"]: o for o in ok(app.panel_page(str(generated), "gis01", "psa1"))["options"]}
    assert first["aux_socket_a"]["own"] is False


def test_devices_of_a_generated_panel_say_where_they_came_from(
    app: api.Api, generated: Path
) -> None:
    pin = {"device": "gps", "panel": 1, "unit": None, "side": None, "position": None, "top_u": None}
    ok(app.set_layout_overrides(str(generated), "gis01", [pin]))

    devices = ok(app.panel_page(str(generated), "gis01", "psa1"))["devices"]
    origin = {d["device"]: d["origin"] for d in devices}
    assert origin["gps"] == "pinned"
    assert origin["l2"] == "layout"
    assert {"part_id", "label", "role", "side", "n", "height_u"} <= set(devices[0])


def test_port_plans_are_editable_except_for_the_sized_switches(
    app: api.Api, generated: Path
) -> None:
    ports = {p["device"]: p for p in ok(app.panel_page(str(generated), "gis01", "psa2"))["ports"]}

    assert ports["l2"]["editable"] is False
    assert ports["l1"]["editable"] is False
    assert ports["l2"]["used"]["uplinks_l3"] == [
        {"count": 2, "speed": "1G", "media": "SM", "spare": 0}
    ]
    rtac = ports["rtac"]
    assert rtac["editable"] is True
    assert rtac["equipment"] == 7  # its index in substation.yaml equipment
    assert rtac["own"]["serial_ports"] == 6
    assert ports["gw"]["own"] is None
    assert rtac["l2"] == {"ports": 2, "speed": "1G", "media": "MM"}


def test_port_plans_show_the_engine_result_lines(app: api.Api, generated: Path) -> None:
    ports = {p["device"]: p for p in ok(app.panel_page(str(generated), "gis01", "psa1"))["ports"]}

    sfps = {(line["part_id"], line["qty"]) for line in ports["l2"]["lines"]}
    assert ("SFP-1G-LX-SM", "2") in sfps
    assert ("SFP-1G-SX-MM", "7") in sfps
    assert [line["part_id"] for line in ports["ext-fw"]["lines"]] == ["FR-TRAN-SX"]
    assert ports["gw"]["lines"] == []


def test_an_engine_error_still_gives_the_panel_and_says_why(app: api.Api, generated: Path) -> None:
    ok(app.set_panel_option(str(generated), "gis01", "aux_socket_a", 16, 2))

    page = ok(app.panel_page(str(generated), "gis01", "psa2"))
    assert page["panel"]["id"] == "psa2"
    assert "aux_socket_a is 16 A" in page["engine_error"]
    assert all(p["lines"] == [] for p in page["ports"])


def test_a_hand_written_panel_page_lists_its_file_devices(app: api.Api, generated: Path) -> None:
    page = ok(app.panel_page(str(generated), "gis01", "ws"))

    head = page["panel"]
    assert (head["generated"], head["manual"], head["number"]) == (False, True, None)
    assert head["kind"] == "console"
    assert [d["part_id"] for d in page["devices"]] == ["SEL-3355", "NAP-F23", "KEYTEK-KBM"]
    assert page["ports"] == []


def test_a_substation_with_errors_gives_the_problems_and_no_panel(
    app: api.Api, project: Path
) -> None:
    file = project.parent / "substations" / "gis01" / "substation.yaml"
    file.write_text(file.read_text("utf-8").replace("part_id: SEL-2488", "part_id: NOPE"), "utf-8")

    page = ok(app.panel_page(str(project), "gis01", "psa1"))
    assert page["panel"] is None
    assert page["reason"]
    assert any("NOPE" in p["message"] for p in page["problems"])


def test_a_panel_that_is_not_there_is_refused(app: api.Api, generated: Path) -> None:
    envelope = app.panel_page(str(generated), "gis01", "psa9")
    assert envelope["ok"] is False
    assert "psa9" in envelope["error"]["message"]  # type: ignore[index]


def test_an_unknown_part_names_the_installed_library_not_its_file(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    """APP-7: "not in psa-devices x.y.z" when the project uses the installed library."""
    package = tmp_path / "lib.bomlib"
    library = read_yaml(project).data["library"]
    pack(EXAMPLES / "library.yaml", package, name=library["name"], version=library["version"])
    LibraryStore(tmp_path / "libraries").import_package(package)
    text = project.read_text("utf-8")
    project.write_text(text.replace("  file: library.yaml\n", "", 1), "utf-8")
    file = project.parent / "substations" / "gis01" / "substation.yaml"
    file.write_text(file.read_text("utf-8").replace("part_id: SEL-2488", "part_id: NOPE"), "utf-8")

    problems = ok(app.panel_page(str(project), "gis01", "psa1"))["problems"]
    [message] = [p["message"] for p in problems if "NOPE" in p["message"]]
    assert message == f"unknown part_id 'NOPE' (not in {library['name']} {library['version']})"


def test_a_generated_panel_page_gives_the_shared_numbering_patterns(
    app: api.Api, generated: Path
) -> None:
    """ALI-5/ALI-13: the generated-panel template is edited in the app, not only in YAML."""
    page = ok(app.panel_page(str(generated), "gis01", "psa2"))
    assert page["template"] == {
        "cabinet_name": "PSA Cabinet - {n:03d}",
        "cabinet_number": "861-GIS01-PSA-{n:04d}",
        "tag_prefix": "PSA{n}",
        "sheet_name": "{n}",
    }
    path = ["generated_panels", "cabinet_number"]
    ok(app.set_substation_field(str(generated), "gis01", path, "861-GIS01-XYZ-{n:04d}"))
    page = ok(app.panel_page(str(generated), "gis01", "psa2"))
    assert page["panel"]["cabinet_number"] == "861-GIS01-XYZ-0002"
    assert ok(app.panel_page(str(generated), "gis01", "ws"))["template"] is None


def test_an_edited_numbering_pattern_drops_its_assumed_mark(app: api.Api, generated: Path) -> None:
    """Pre-release finding 6: an edit is a confirmation, as for a project.yaml field."""
    file = generated.parent / "substations" / "gis01" / "substation.yaml"
    text = file.read_text("utf-8")
    old = 'cabinet_number: "861-GIS01-PSA-{n:04d}"'
    file.write_text(text.replace(old, f"{old}  # ASSUMED"), "utf-8")

    path = ["generated_panels", "cabinet_number"]
    ok(app.set_substation_field(str(generated), "gis01", path, "861-GIS01-XYZ-{n:04d}"))
    line = next(x for x in file.read_text("utf-8").splitlines() if "cabinet_number" in x)
    assert line.strip() == 'cabinet_number: "861-GIS01-XYZ-{n:04d}"'
