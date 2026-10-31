"""The Device preview page of the desktop app (plan M24 Task 5; docs/ui/screens.md)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.app.device_preview import device_preview_page
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"


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


def unit(page: Any, tag: str) -> Any:
    return next(u for p in page["panels"] for u in p["units"] if u["tag"] == tag)


def test_device_preview_page_labels_each_unit_by_its_row(tmp_path: Path, project: Path) -> None:
    page = device_preview_page(project, "gis01", LibraryStore(tmp_path / "libraries"))
    json.dumps(page)

    assert unit(page, "PSA1-GPS")["label"] == "Time server clock"
    assert unit(page, "PSA1-L2-ESW-A01")["label"] == "L2 switch"
    assert page["waist_u"] == 18
    assert page["saved_at"]


def test_a_pin_by_top_u_is_written_and_the_page_shows_it_pinned(
    app: api.Api, project: Path
) -> None:
    ok(
        app.set_layout_overrides(
            str(project), "gis01", [{"device": "rtac", "panel": 2, "top_u": 10}]
        )
    )

    rtac = unit(ok(app.device_preview(str(project), "gis01")), "PSA2-RTAC")

    assert (rtac["pinned"], rtac["top_u"]) == (True, 10)


def test_unpin_removes_only_that_override(app: api.Api, project: Path) -> None:
    pins = [
        {"device": "rtac", "panel": 2, "top_u": 10},
        {"device": "hwio", "panel": 1, "top_u": 8},
    ]
    ok(app.set_layout_overrides(str(project), "gis01", pins))

    ok(app.set_layout_overrides(str(project), "gis01", pins[1:]))

    page = ok(app.device_preview(str(project), "gis01"))
    assert unit(page, "PSA2-RTAC")["pinned"] is False
    assert (unit(page, "PSA1-HWIO")["pinned"], unit(page, "PSA1-HWIO")["top_u"]) == (True, 8)


def test_check_layout_refuses_a_top_u_that_overlaps_with_the_layout_sentence(
    app: api.Api, project: Path
) -> None:
    both = [
        {"device": "gps", "panel": 1, "top_u": 32},
        {"device": "hwio", "panel": 1, "top_u": 32},  # the I/O rack is 5 U: U32 to U28
    ]

    check = ok(app.check_layout(str(project), "gis01", both, []))

    assert check["fits"] is False
    assert "overlaps" in check["issues"][0]["message"]


def test_the_page_says_whether_the_panels_are_generated(tmp_path: Path, project: Path) -> None:
    page = device_preview_page(project, "gis01", LibraryStore(tmp_path / "libraries"))

    assert (
        page["generated"] is False
    )  # the example's panels are hand-written: pins do not reach Build


def test_an_issue_about_an_equipment_row_can_go_to_that_row(tmp_path: Path, project: Path) -> None:
    page = device_preview_page(project, "gis01", LibraryStore(tmp_path / "libraries"))

    no_number = next(i for i in page["issues"] if i["kind"] == "part_number")
    assert no_number["device"] == "hwio"  # its subject is the equipment id
    assert no_number["message"] == "I/O rack: no part number; the BOM prints the library model"


def test_an_ac_unit_shows_its_ac_branch_mcb(tmp_path: Path, project: Path) -> None:
    """ADR 0025: each VAC unit gets its own AC branch MCB, shown as its PS1."""
    yaml = project.parent / "substations" / "gis01" / "substation.yaml"
    text = yaml.read_text("utf-8")
    old = "    part_id: SEL-3555-GW\n"
    assert old in text
    ac = old + "    overrides: { supply_type: VAC, voltage_v: 230, power_supplies: 0 }\n"
    yaml.write_text(text.replace(old, ac, 1), "utf-8")

    page = device_preview_page(project, "gis01", LibraryStore(tmp_path / "libraries"))

    gw = next(u for p in page["panels"] for u in p["units"] if u["device"] == "gw")
    assert gw["supply"] == "230 VAC"
    assert gw["ps1"]["tag"].startswith("PSA1-C")
    assert gw["ps2"] is None
