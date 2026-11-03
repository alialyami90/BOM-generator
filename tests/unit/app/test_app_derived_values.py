"""Pages carry each derived value with its rule (plan M48, the override contract)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

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
