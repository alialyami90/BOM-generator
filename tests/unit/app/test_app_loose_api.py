"""The app's Loose material page over the loose-material writers (plan M18, ADR 0022).

The writers themselves are tested in tests/unit/test_loose_edit.py; these tests cover
what the page gets: the list with its parts, whether an edit was written, the problems,
and the refreshed list.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"
FREE = {"description": "Fibre patch cords, LC to LC", "qty": "1 Lot", "tag": "FO cords"}


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES, tmp_path / "workspace" / "jfgp2-pkg3")
    return tmp_path / "workspace" / "jfgp2-pkg3" / "project.yaml"


@pytest.fixture
def substation(project: Path) -> Path:
    return project.parent / "substations" / "gis01" / "substation.yaml"


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


def test_loose_material_lists_the_items_with_their_library_parts(
    app: api.Api, project: Path
) -> None:
    page = ok(app.loose_material(str(project), "gis01"))

    assert page["reason"] is None
    assert page["sheet_name"] == "Loose Material"
    assert page["host_panel"] == "ws"
    assert [i["part_id"] for i in page["items"]][:3] == ["NAP-K55", "ZENON-V12", "MS-OFFICE-2021"]
    first = page["items"][0]
    assert first["children"] == ["LPA37-696"]
    assert first["fed_from"] == "psa3"
    assert first["tag"] == '55" LCD Alarm Annunciator'
    assert first["make"]
    assert first["model"]
    assert page["items"][-1]["qty"] == "1 Lot"
    assert {"id": "ws"}.items() <= page["host_options"][-1].items()
    assert "psa3" in [p["id"] for p in page["fed_options"]]
    assert {"part_id": "ZENON-V12"}.items() <= next(
        p for p in page["parts"] if p["part_id"] == "ZENON-V12"
    ).items()


def test_a_free_text_item_is_added_and_the_list_comes_back(
    app: api.Api, project: Path, substation: Path
) -> None:
    reply = ok(app.add_loose_item(str(project), "gis01", FREE, None, None))

    assert reply["written"] is True
    item = reply["page"]["items"][-1]
    assert item["part_id"] is None
    assert item["description"] == FREE["description"]
    assert item["make"] is None
    assert "Fibre patch cords, LC to LC" in substation.read_text("utf-8")


def test_an_item_is_edited_moved_and_removed(app: api.Api, project: Path) -> None:
    item = {"part_id": "ZENON-V12", "tag": "HMI Software"}

    edited = ok(app.set_loose_item(str(project), "gis01", 1, item))
    moved = ok(app.move_loose_item(str(project), "gis01", 1, 0))
    removed = ok(app.remove_loose_item(str(project), "gis01", 0))

    assert edited["page"]["items"][1]["tag"] == "HMI Software"
    assert moved["page"]["items"][0]["part_id"] == "ZENON-V12"
    assert removed["page"]["items"][0]["part_id"] == "NAP-K55"


def test_a_free_text_item_fed_from_a_panel_is_refused_and_not_written(
    app: api.Api, project: Path, substation: Path
) -> None:
    before = substation.read_text("utf-8")

    reply = ok(app.add_loose_item(str(project), "gis01", FREE | {"fed_from": "psa1"}, None, None))

    assert reply["written"] is False
    assert reply["page"] is None
    assert "needs a library part" in reply["issues"][0]["message"]
    assert substation.read_text("utf-8") == before


def test_the_host_panel_names_the_document_the_sheet_is_issued_under(
    app: api.Api, project: Path
) -> None:
    reply = ok(app.set_loose_host_panel(str(project), "gis01", "psa1"))

    assert reply["page"]["host_panel"] == "psa1"


def test_validate_loose_item_gives_the_engines_messages_by_field(
    app: api.Api, project: Path, substation: Path
) -> None:
    before = substation.read_text("utf-8")

    unknown = ok(app.validate_loose_item(str(project), "gis01", None, {"part_id": "NO-SUCH"}))
    empty = ok(app.validate_loose_item(str(project), "gis01", 0, {"qty": 1}))
    fine = ok(app.validate_loose_item(str(project), "gis01", None, FREE))

    assert "part_id" in unknown
    assert "" in empty
    assert fine == {}
    assert substation.read_text("utf-8") == before


def test_an_edit_of_an_item_that_is_not_there_is_refused(app: api.Api, project: Path) -> None:
    error = refused(app.remove_loose_item(str(project), "gis01", 99))

    assert error["kind"] == "edit_refused"


def test_library_parts_carry_their_data_quality_from_the_installed_library(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    package = tmp_path / "lib.bomlib"
    db = Path(__file__).parents[3] / "data" / "device-db"
    pack(EXAMPLES / "library.yaml", package, name="psa-devices", version="1.1.0", extra_dirs=[db])
    LibraryStore(tmp_path / "libraries").import_package(package)
    text = project.read_text(encoding="utf-8").replace("  file: library.yaml\n", "")
    project.write_text(text, encoding="utf-8")

    parts = ok(app.loose_material(str(project), "gis01"))["parts"]

    rtac = next(p for p in parts if p["part_id"] == "SEL-3555-RTAC")
    assert rtac["data_quality"] == "partial"


def test_parts_from_a_library_file_have_no_data_quality(app: api.Api, project: Path) -> None:
    parts = ok(app.loose_material(str(project), "gis01"))["parts"]
    assert {p["data_quality"] for p in parts} == {None}
