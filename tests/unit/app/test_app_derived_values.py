"""Pages carry each derived value with its rule (plan M48, the override contract)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from bomgen.app import api
from bomgen.models.output import Derived

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
def generated(app: api.Api, project: Path) -> Path:
    """The example laid out: psa1 and psa2 generated (its loose material is dropped)."""
    file = project.parent / "substations" / "gis01" / "substation.yaml"
    text = file.read_text("utf-8")
    file.write_text(text[: text.index("\nloose_material:") + 1], "utf-8")
    ok(app.generate_panels(str(project), "gis01"))
    return project


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)
    return envelope["data"]


def test_a_derived_value_is_from_the_engine_until_overridden() -> None:
    auto = Derived[int](value=16, rule="16 A: next standard size above 7.1 A")
    assert (auto.override, auto.source) == (None, "engine")
    assert Derived[int](value=16, rule="r", override=20).source == "override"


def test_panel_page_carries_the_main_mcb_with_its_rule(app: api.Api, project: Path) -> None:
    """Cabinet 001 sizes to 10 A from 7.1 A; the example's override gives the 16 A (plan Q3)."""
    page = ok(app.panel_page(str(project), "gis01", "psa1"))

    assert page["derived"]["main_mcb_a"] == {
        "value": 10,
        "rule": "10 A: next standard size above 7.1 A, minimum 6 A",
        "override": 16,
        "source": "override",
        "unit": "A",
    }


def test_a_main_mcb_without_override_comes_from_the_engine(app: api.Api, generated: Path) -> None:
    ok(app.remove_panel_option(str(generated), "gis01", "main_mcb_override_a", None))

    main = ok(app.panel_page(str(generated), "gis01", "psa1"))["derived"]["main_mcb_a"]
    assert (main["override"], main["source"]) == (None, "engine")
    assert main["rule"].startswith(f"{main['value']} A: ")


def test_panel_page_carries_the_spare_ratings_with_their_rules(
    app: api.Api, generated: Path
) -> None:
    """Plan M58: each spare breaker rating is a derived value the panel may override."""
    ok(app.set_panel_option(str(generated), "gis01", "dc_spare_rating_a", 6, 1))
    derived = ok(app.panel_page(str(generated), "gis01", "psa1"))["derived"]

    assert derived["ac_spare_a"] == {
        "value": 2,
        "rule": "2 A: the largest housekeeping branch",
        "override": None,
        "source": "engine",
        "unit": "A",
    }
    dc = derived["dc_spare_a"]
    assert (dc["value"], dc["override"], dc["source"]) == (2, 6, "override")
    assert dc["rule"].startswith("2 A: the largest of ")


def _dc_aux(app: api.Api, project: Path) -> tuple[int, int]:
    """psa1's DC aux contact row (quantity, HWIO) and its HWIO total."""
    sheet = ok(app.preview_substation(str(project), "gis01"))["panels"][0]
    row = next(r for r in sheet["rows"] if r["description"].startswith("DC Auxiliary Contacts"))
    return row["qty"], sheet["hwio_total"]


def test_turning_the_firewalls_alarm_off_drops_its_dc_aux_contacts(
    app: api.Api, generated: Path
) -> None:
    """Plan M58 acceptance: Q1.n/Q2.n of the firewall leave the DC aux contacts. The DC
    HWIO counts the mains only (Columns of a panel BOM, HWIO), so the HWIO stays."""
    file = generated.parent / "substations" / "gis01" / "substation.yaml"
    ids = [x["id"] for x in yaml.safe_load(file.read_text("utf-8"))["equipment"]]
    path: list[str | int] = ["equipment", ids.index("ext-fw"), "alarm_on_branch_mcb"]

    before = _dc_aux(app, generated)
    ok(app.set_substation_field(str(generated), "gis01", path, False))
    assert before[0] == 4
    assert _dc_aux(app, generated) == (2, before[1])


def _strip(page: dict[str, Any], code: str) -> dict[str, Any]:
    return next(s for s in page["terminals"] if s["code"] == code)


def test_terminals_tab_carries_each_strip_with_its_rule(app: api.Api, project: Path) -> None:
    """ADR 0033: each strip's quantity is a derived value with the rule that gave it."""
    page = ok(app.panel_page(str(project), "gis01", "psa1"))

    x3 = _strip(page, "X3-AC")
    assert x3["qty"] == {
        "value": 12,
        "rule": "2 x 6 AC MCBs = 12",
        "override": None,
        "source": "engine",
        "unit": None,
    }
    assert (x3["block"], x3["block_override"], x3["spared"]) == ("UT-2.5-MTD", None, True)
    assert _strip(page, "X4-DC1")["qty"]["value"] == 32
    assert "UT-16" in page["terminal_blocks"]


def test_spare_terminals_and_overrides_keep_the_rule(app: api.Api, project: Path) -> None:
    """Plan M57 acceptance on Cabinet 001: 10% spare makes X3-AC 14 and X4-DC1 36; an XIP
    override of 60 keeps the rule shown; a block type override changes the strip's type."""
    ok(app.set_project_field(str(project), ["defaults", "spares", "terminals_fraction"], 0.1))
    options: list[str | int] = ["options", "terminal_overrides", "XIP"]
    ok(app.set_panel_field(str(project), "gis01", "psa1", options, 60))
    blocks: list[str | int] = ["options", "terminal_block_overrides", "X3-AC"]
    page = ok(app.set_panel_field(str(project), "gis01", "psa1", blocks, "UT-16"))
    page = ok(app.panel_page(str(project), "gis01", "psa1"))

    assert _strip(page, "X3-AC")["qty"]["value"] == 14
    assert _strip(page, "X3-AC")["block_override"] == "UT-16"
    assert _strip(page, "X4-DC1")["qty"]["value"] == 36
    xip = _strip(page, "XIP")["qty"]
    assert (xip["override"], xip["source"]) == (60, "override")
    assert xip["rule"].endswith("% spare = " + str(xip["value"]))


def test_generated_panels_share_terminal_overrides(app: api.Api, generated: Path) -> None:
    path: list[str | int] = ["generated_panels", "options", "terminal_overrides", "X3-AC"]
    ok(app.set_substation_field(str(generated), "gis01", path, 20))

    qty = _strip(ok(app.panel_page(str(generated), "gis01", "psa1")), "X3-AC")["qty"]
    assert (qty["value"], qty["override"]) == (12, 20)


def test_panel_page_carries_the_housekeeping_kit_with_its_rules(
    app: api.Api, project: Path
) -> None:
    """ADR 0032: each housekeeping load's breaker is a derived value; the counts default
    to the spec's kit."""
    kit = ok(app.panel_page(str(project), "gis01", "psa1"))["housekeeping"]

    assert kit["defaults"]["fans"] == 2
    fan = kit["ratings"]["fan"]
    assert (fan["value"], fan["override"], fan["source"]) == (2, None, "engine")
    assert fan["rule"].startswith("2 A: the spec's fan rating")
    assert [b["load"] for b in kit["branches"]][:2] == ["Illumination Lamp", "Fan-1 and TH-1"]


def test_housekeeping_counts_and_ratings_round_trip(app: api.Api, project: Path) -> None:
    fans: list[str | int] = ["options", "housekeeping", "fans"]
    rating: list[str | int] = ["options", "housekeeping", "branch_ratings", "fan"]
    ok(app.set_panel_field(str(project), "gis01", "psa1", fans, 3))
    kit = ok(app.set_panel_field(str(project), "gis01", "psa1", rating, 6))["housekeeping"]

    assert [b["key"] for b in kit["branches"]].count("fan") == 3
    fan = kit["ratings"]["fan"]
    assert (fan["value"], fan["override"]) == (2, 6)

    ok(app.set_panel_field(str(project), "gis01", "psa1", rating, None))
    page = ok(app.panel_page(str(project), "gis01", "psa1"))
    assert page["housekeeping"]["ratings"]["fan"]["override"] is None


def test_generated_panels_share_a_housekeeping_count(app: api.Api, generated: Path) -> None:
    path: list[str | int] = ["generated_panels", "options", "housekeeping", "lamps"]
    ok(app.set_substation_field(str(generated), "gis01", path, 2))

    sheet = ok(app.preview_substation(str(generated), "gis01"))["panels"][0]
    lamp = next(r for r in sheet["rows"] if r["description"].startswith("Illumination Lamp"))
    assert lamp["qty"] == 2
