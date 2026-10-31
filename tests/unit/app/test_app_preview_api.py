"""Preview endpoint of the desktop app (plan M10d)."""

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


@pytest.fixture
def page(app: api.Api, project: Path) -> Any:
    return ok(app.preview_substation(str(project), "gis01"))


def test_preview_lists_one_sheet_per_panel_with_its_cabinet(page: Any) -> None:
    assert [(p["panel_id"], p["sheet"]) for p in page["panels"]] == [
        ("psa1", "1"),
        ("psa2", "2"),
        ("psa3", "3"),
        ("ws", "4"),
    ]
    assert page["panels"][0]["cabinet"] == "PSA Cabinet - 001"
    assert page["panels"][0]["title"] == [
        "861-GIS01-PSA-0001",
        "GIS Substation - PSA Cabinet - 001",
    ]
    assert page["calc_sheets"]["power"] == "Power Consumption"
    assert page["reason"] is None


def test_bom_rows_number_in_order_and_span_parent_tags(page: Any) -> None:
    rows = page["panels"][0]["rows"]
    assert [r["sr"] for r in rows] == list(range(1, len(rows) + 1))
    parents = [r for r in rows if r["tag_rows"] > 1]
    assert parents
    first = parents[0]
    children = [r for r in rows if r["parent"] == first["sr"] - 1]
    assert first["tag_rows"] == children[-1]["sr"] - first["sr"] + 1
    assert any(r["separator_before"] for r in rows)
    assert page["panels"][0]["hwio_total"] == sum(r["hwio"] for r in rows)


def test_a_quantity_written_as_a_sum_keeps_its_parts(page: Any) -> None:
    quantities = [r["qty"] for p in page["panels"] for r in p["rows"]]
    assert any(isinstance(q, str) and "+" in q for q in quantities)


def test_power_totals_are_the_spec_example(page: Any) -> None:
    assert page["power"]["dc_total_w"] == pytest.approx(2177.5)
    assert page["power"]["ac_total_w"] == pytest.approx(1090.3, abs=0.05)
    line = page["power"]["cabinets"][0]["dc"]["lines"][0]
    assert line["description"]
    assert line["total_w"] == pytest.approx(line["qty"] * line["unit_w"])


def test_heat_sheets_carry_the_engine_results(page: Any) -> None:
    dissipation = page["heat_dissipation"]
    assert dissipation[0]["lines"][0]["total_btu_h"] > 0
    calc = page["heat_calculations"]
    assert {c["panel_id"] for c in calc["cabinets"]} == {"psa1", "psa2", "psa3", "ws"}
    assert all(isinstance(c["forced"]["passes"], bool) for c in calc["cabinets"])


def test_loose_material_is_its_own_sheet(page: Any) -> None:
    loose = page["loose"]
    assert loose["sheet"] == "Loose Material"  # ADR 0020 default name
    assert loose["rows"]
    assert loose["title"]
    assert loose["hwio_total"] == sum(r["hwio"] for r in loose["rows"])
    assert all("loose" not in p for p in page["panels"])


def test_the_tabs_follow_the_workbooks_sheet_order(app: api.Api, project: Path, page: Any) -> None:
    target = ok(app.build_target(str(project), "gis01"))

    calc = page["calc_sheets"]
    tabs = [p["sheet"] for p in page["panels"]] + [page["loose"]["sheet"]]
    tabs += [page["nameplates"]["sheet"]]  # ADR 0026
    tabs += [calc["power"], calc["heat_dissipation"], calc["heat_calculations"]]
    assert tabs == [s["name"] for s in target["sheets"]]


def test_a_substation_with_errors_has_no_sheets(app: api.Api, project: Path) -> None:
    file = project.parent / SUBSTATION
    file.write_text(file.read_text().replace("ied_count: 40", "ied_count: lots"))

    page = ok(app.preview_substation(str(project), "gis01"))

    assert page["reason"].startswith("1 error")
    assert "panels" not in page
    assert page["problems"][0]["level"] == "error"


def test_the_page_lists_each_panels_nameplates(page: Any) -> None:
    # ADR 0026: the Nameplates sheet's plates, panel by panel.
    plates = page["nameplates"]["panels"][0]
    assert plates["panel_id"] == "psa1"
    assert plates["plates"][0]["text"] == "FOPP_CCR_A01"
    assert len(plates["plates"]) == 11
