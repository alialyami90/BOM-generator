"""The Spares page endpoint (plan M64, ADR 0035)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api

EXAMPLES = Path(__file__).parents[3] / "examples"
SX = "6GK6000-8FG51-0AA0"
POLICY = {"percent": {"sfp": 10}, "minimum_per_part": 1, "categories": ["sfp"]}


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


def test_no_policy_means_no_lines(app: api.Api, project: Path) -> None:
    page = ok(app.spares(str(project), "gis01"))
    assert page["reason"] is None
    assert page["policy"] is None
    assert page["lines"] == []
    assert page["sheet_name"] == "Spare Parts"
    assert any(p["part_id"] == "SK3243-FAN" for p in page["parts"])


def test_policy_lines_carry_the_key_an_override_names(app: api.Api, project: Path) -> None:
    ok(app.set_substation_field(str(project), "gis01", ["design_basis", "spares_policy"], POLICY))
    page = ok(app.spares(str(project), "gis01"))
    assert page["policy"] == POLICY
    sx = next(line for line in page["lines"] if line["key"] == SX)
    assert (sx["spare"], sx["overridden"]) == (9, False)


def test_override_exclude_and_extra_through_substation_fields(app: api.Api, project: Path) -> None:
    file, sub = str(project), "gis01"
    ok(app.set_substation_field(file, sub, ["design_basis", "spares_policy"], POLICY))
    ok(app.set_substation_field(file, sub, ["spares_list", "items", SX], 12))
    ok(app.set_substation_field(file, sub, ["spares_list", "excluded"], ["FR-TRAN-SX"]))
    extra = [{"description": "Fuse kit", "qty": 2}]
    ok(app.set_substation_field(file, sub, ["spares_list", "extra"], extra))
    page = ok(app.spares(file, sub))
    keys = [line["key"] for line in page["lines"]]
    assert "FR-TRAN-SX" not in keys
    sx = next(line for line in page["lines"] if line["key"] == SX)
    assert (sx["spare"], sx["overridden"]) == (12, True)
    assert page["lines"][-1]["description"] == "Fuse kit"
    assert page["excluded"] == ["FR-TRAN-SX"]
    assert page["extra"] == extra

    ok(app.set_substation_field(file, sub, ["spares_list", "items", SX], None))
    sx = next(line for line in ok(app.spares(file, sub))["lines"] if line["key"] == SX)
    assert sx["spare"] == 9
