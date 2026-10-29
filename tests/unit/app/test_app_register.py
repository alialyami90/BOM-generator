"""The project's document register in the app (docs/ui/editing.md, Project > Documents;
plan M17c): what uses each document, assumed dates, Confirm, Add and Remove."""

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
    package = tmp_path / "lib.bomlib"
    pack(EXAMPLES / "library.yaml", package, name="psa-devices", version="1.0.0")
    LibraryStore(tmp_path / "libraries").import_package(package)
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


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope, default=str)
    return envelope["data"]


def refused(envelope: dict[str, object]) -> dict[str, str]:
    assert envelope["ok"] is False, envelope
    return envelope["error"]  # type: ignore[return-value]


def register(app: api.Api, project: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = ok(app.open_project(str(project)))["register"]
    return rows


def test_each_document_lists_what_uses_it_and_its_assumed_fields(
    app: api.Api, project: Path
) -> None:
    rows = register(app, project)
    first = rows[0]
    assert first["index"] == 0
    assert first["used_by"]  # the example's documents are all picked by something
    assert "issue_date" in first["assumed"]


def test_confirming_an_assumed_date_drops_the_mark(app: api.Api, project: Path) -> None:
    ok(app.confirm_project_field(str(project), ["documents", 0, "issue_date"]))
    assert "issue_date" not in register(app, project)[0]["assumed"]


def test_an_added_document_gets_a_free_key_and_blank_number(app: api.Api, project: Path) -> None:
    page = ok(app.add_document(str(project), "gis01", "Cable schedule"))
    added = page["register"][-1]
    assert added["key"] == "gis01-cable-schedule"
    assert added["title"] == "Cable schedule"
    assert added["used_by"] == []
    again = ok(app.add_document(str(project), "gis01", "Cable schedule"))["register"][-1]
    assert again["key"] == "gis01-cable-schedule-2"


def test_an_unused_document_is_removed_and_a_used_one_is_refused(
    app: api.Api, project: Path
) -> None:
    page = ok(app.add_document(str(project), "gis01", "Cable schedule"))
    index = page["register"][-1]["index"]
    removed = ok(app.remove_document(str(project), index))
    keys = [r["key"] for r in removed["page"]["register"]]
    assert "gis01-cable-schedule" not in keys
    assert removed["row"]["key"] == "gis01-cable-schedule"  # as written, for Undo
    back = ok(app.restore_document(str(project), removed["row"], index))
    assert back["register"][index]["key"] == "gis01-cable-schedule"
    ok(app.remove_document(str(project), index))
    error = refused(app.remove_document(str(project), 0))
    assert "used by" in error["message"]
    assert len(read_yaml(project).data["documents"]) == len(keys)


def test_an_issue_date_is_written_as_a_date_not_text(app: api.Api, project: Path) -> None:
    ok(app.set_project_field(str(project), ["documents", 0, "issue_date"], "2026-11-01"))
    assert "issue_date: 2026-11-01" in project.read_text(encoding="utf-8")
    removed = ok(app.add_document(str(project), "gis01", "Cable schedule"))["register"][-1]
    back = ok(app.remove_document(str(project), removed["index"]))
    ok(app.restore_document(str(project), back["row"], removed["index"]))
    assert "'20" not in project.read_text(encoding="utf-8")
