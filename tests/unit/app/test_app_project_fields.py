"""Editing the Project page's own fields in the app (plan M17c, ADR 0021).

The field writers are tested in the io tests; these cover the bridge: what is written,
what a refused value leaves, the logo copy and the brand choices the page offers.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.io.yaml_source import read_yaml

EXAMPLES = Path(__file__).parents[3] / "examples"
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


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


def refused(envelope: dict[str, object]) -> dict[str, str]:
    assert envelope["ok"] is False, envelope
    return envelope["error"]  # type: ignore[return-value]


def test_setting_the_client_writes_it_and_returns_the_page(app: api.Api, project: Path) -> None:
    page = ok(app.set_project_field(str(project), ["project", "client"], "Aramco"))
    assert page["client"] == "Aramco"
    assert read_yaml(project).data["project"]["client"] == "Aramco"


def test_an_emptied_field_is_removed(app: api.Api, project: Path) -> None:
    ok(app.set_project_field(str(project), ["project", "client"], "Aramco"))
    ok(app.set_project_field(str(project), ["project", "client"], None))
    assert "client" not in read_yaml(project).data["project"]


def test_a_shared_default_the_model_refuses_is_not_written(app: api.Api, project: Path) -> None:
    before = project.read_text(encoding="utf-8")
    path = ["defaults", "spares", "port_fraction"]
    assert ok(app.check_project_field(str(project), path, 1.5))
    assert ok(app.check_project_field(str(project), path, 0.3)) is None
    assert refused(app.set_project_field(str(project), path, 1.5))["kind"] == "invalid_edit"
    assert project.read_text(encoding="utf-8") == before


def test_a_shared_default_is_written(app: api.Api, project: Path) -> None:
    page = ok(app.set_project_field(str(project), ["defaults", "spares", "ac_branches"], 2))
    assert page["defaults"]["spares"]["ac_branches"] == 2


def test_the_logo_is_copied_into_the_project(app: api.Api, project: Path, tmp_path: Path) -> None:
    source = tmp_path / "Company Logo.png"
    source.write_bytes(PNG)
    page = ok(app.set_project_logo(str(project), str(source)))
    assert page["project"]["logo"] == "assets/company-logo.png"
    assert (project.parent / "assets" / "company-logo.png").read_bytes() == PNG


def test_a_second_logo_with_the_same_file_name_does_not_overwrite_the_first(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    first, second = tmp_path / "a" / "company-logo.png", tmp_path / "b" / "company-logo.png"
    for source, data in ((first, PNG), (second, PNG + b"other")):
        source.parent.mkdir()
        source.write_bytes(data)
    ok(app.set_project_logo(str(project), str(first)))
    page = ok(app.set_project_logo(str(project), str(second)))
    assert page["project"]["logo"] == "assets/company-logo-2.png"
    assert (project.parent / "assets" / "company-logo.png").read_bytes() == PNG
    again = ok(app.set_project_logo(str(project), str(first)))  # the same picture is reused
    assert again["project"]["logo"] == "assets/company-logo.png"


def test_a_logo_that_is_not_a_png_is_refused(app: api.Api, project: Path, tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    source.write_text("not a picture", encoding="utf-8")
    assert refused(app.set_project_logo(str(project), str(source)))["kind"] == "invalid_edit"


def test_the_page_offers_each_catalogues_brands_with_mcb_dc(app: api.Api, project: Path) -> None:
    brands = ok(app.open_project(str(project)))["brands"]
    assert brands["mcb"][0] == {"id": "default", "name": "Library default"}
    assert "siemens-5sy5" in [b["id"] for b in brands["mcb"]]
    # a DC-only family sizes no AC branch, so only the DC MCBs offer it (ADR 0023)
    assert "schneider-c60h-dc" not in [b["id"] for b in brands["mcb"]]
    dc = {b["id"] for b in brands["mcb_dc"]}
    assert dc == {b["id"] for b in brands["mcb"]} | {"schneider-c60h-dc"}
    assert {"aux_contact", "terminal_blocks", "busbars", "housekeeping"} <= set(brands)


def test_a_brand_choice_is_written(app: api.Api, project: Path) -> None:
    path = ["defaults", "catalogue_choice", "mcb_dc"]
    page = ok(app.set_project_field(str(project), path, "schneider-c60h-dc"))
    assert page["defaults"]["catalogue_choice"]["mcb_dc"] == "schneider-c60h-dc"
