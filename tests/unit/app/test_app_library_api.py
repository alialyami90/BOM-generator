"""Library endpoints of the desktop app: browse, import review, import, versions (plan M10b)."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from bomgen.app import api
from bomgen.library_store.package import pack

REPO = Path(__file__).parents[3]
EXAMPLE_LIBRARY = REPO / "examples" / "library.yaml"
DEVICE_DB = REPO / "data" / "device-db"
EXAMPLE_PART_IDS = [d["part_id"] for d in yaml.safe_load(EXAMPLE_LIBRARY.read_text())["devices"]]


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
    return api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(tmp_path / "workspace"),
        }
    )


@pytest.fixture
def package(tmp_path: Path) -> Any:
    def make(version: str, notes: str = "", device_db: bool = False) -> Path:
        out = tmp_path / f"psa-{version}.bomlib"
        extra = [DEVICE_DB] if device_db else []
        pack(
            EXAMPLE_LIBRARY, out, name="psa", version=version, release_notes=notes, extra_dirs=extra
        )
        return out

    return make


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)  # pywebview sends it to the page as JSON
    return envelope["data"]


def failed_checks(preview: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in preview["checks"] if c["status"] == "failed"]


class FakeWindow:
    def __init__(self, answer: tuple[str, ...] | None) -> None:
        self.answer = answer
        self.asked: dict[str, Any] = {}

    def create_file_dialog(self, dialog_type: int = 10, **options: Any) -> tuple[str, ...] | None:
        self.asked = {"dialog_type": dialog_type, **options}
        return self.answer


def test_library_overview_with_nothing_installed(app: api.Api) -> None:
    assert ok(app.library_overview()) == {
        "library": None,
        "devices": [],
        "records": {},
        "records_problem": None,
    }


def test_library_overview_lists_the_active_library_devices(app: api.Api, package: Any) -> None:
    ok(app.import_library(str(package("1.0.0", "First release"))))

    overview = ok(app.library_overview())

    assert overview["library"]["name"] == "psa"
    assert overview["library"]["version"] == "1.0.0"
    assert overview["library"]["notes"] == "First release"
    assert overview["library"]["created"]
    assert [d["part_id"] for d in overview["devices"]] == EXAMPLE_PART_IDS
    switch = next(d for d in overview["devices"] if d["part_id"] == "RST2228-L1-24MM")
    assert switch["category"] == "network_switch"


def test_library_overview_without_a_device_database_has_no_records(
    app: api.Api, package: Any
) -> None:
    ok(app.import_library(str(package("1.0.0"))))

    overview = ok(app.library_overview())

    assert overview["records"] == {}
    assert overview["records_problem"] is None


def test_library_overview_joins_the_device_database_records(app: api.Api, package: Any) -> None:
    ok(app.import_library(str(package("1.0.0", device_db=True))))

    records = ok(app.library_overview())["records"]

    switch = records["RST2228-L1-24MM"]
    assert switch["verified"] in {"confirmed", "partial", "unverified"}
    assert switch["datasheet"]["summary"]
    assert len(switch["alternatives"]) == 2
    assert set(switch["alternatives"][0]["tiers"]) == {"low", "mid", "high"}


def test_a_damaged_device_database_does_not_hide_the_library(
    app: api.Api, package: Any, tmp_path: Path
) -> None:
    ok(app.import_library(str(package("1.0.0", device_db=True))))
    damaged = tmp_path / "libraries" / "psa" / "1.0.0" / "device-db" / "network.yaml"
    damaged.write_text("records: [")

    overview = ok(app.library_overview())

    assert [d["part_id"] for d in overview["devices"]] == EXAMPLE_PART_IDS
    assert overview["records"] == {}
    assert "network.yaml" in overview["records_problem"]


def test_preview_of_a_new_library_can_be_imported(app: api.Api, package: Any) -> None:
    preview = ok(app.preview_library_import(str(package("1.0.0"))))

    assert preview["can_import"] is True
    assert preview["manifest"]["version"] == "1.0.0"
    assert preview["previous"] is None
    assert preview["package_size"] > 0
    assert sorted(preview["diff"]["added"]) == sorted(set(EXAMPLE_PART_IDS))
    assert {c["id"] for c in preview["checks"]} >= {"library", "validation", "version", "signature"}


def test_preview_installs_nothing(app: api.Api, package: Any) -> None:
    ok(app.preview_library_import(str(package("1.0.0"))))

    assert ok(app.library_overview())["library"] is None


def test_preview_of_the_installed_version_is_refused_unless_forced(
    app: api.Api, package: Any
) -> None:
    file = str(package("1.0.0"))
    ok(app.import_library(file))

    refused = ok(app.preview_library_import(file))
    forced = ok(app.preview_library_import(file, True))

    assert refused["can_import"] is False
    assert [c["kind"] for c in failed_checks(refused)] == ["already_installed"]
    assert forced["can_import"] is True


def test_preview_of_a_damaged_file_reports_a_failed_check(app: api.Api, tmp_path: Path) -> None:
    junk = tmp_path / "junk.bomlib"
    junk.write_bytes(b"not a zip")

    preview = ok(app.preview_library_import(str(junk)))

    assert preview["can_import"] is False
    assert failed_checks(preview)


def test_import_reports_the_previous_version_and_the_changes(app: api.Api, package: Any) -> None:
    ok(app.import_library(str(package("1.0.0"))))

    result = ok(app.import_library(str(package("1.1.0"))))

    assert result["manifest"]["version"] == "1.1.0"
    assert result["previous"] == "1.0.0"
    assert ok(app.library_overview())["library"]["version"] == "1.1.0"


def test_import_of_the_installed_version_is_a_refusal(app: api.Api, package: Any) -> None:
    file = str(package("1.0.0"))
    ok(app.import_library(file))

    result = app.import_library(file)

    assert result["ok"] is False
    assert result["error"]["kind"] == "already_installed"  # type: ignore[index]


def test_versions_list_every_installed_version_with_the_active_one(
    app: api.Api, package: Any
) -> None:
    ok(app.import_library(str(package("1.0.0", "First release"))))
    ok(app.import_library(str(package("1.1.0", "Adds firewall"))))

    versions = ok(app.library_versions())

    assert versions["name"] == "psa"
    assert [(v["version"], v["active"], v["notes"]) for v in versions["versions"]] == [
        ("1.1.0", True, "Adds firewall"),
        ("1.0.0", False, "First release"),
    ]


def test_versions_of_a_library_with_no_active_version_can_be_made_active(
    app: api.Api, package: Any, tmp_path: Path
) -> None:
    ok(app.import_library(str(package("1.0.0"))))
    (tmp_path / "libraries" / "psa" / "active").write_text("9.9.9")

    versions = ok(app.library_versions())

    assert ok(app.library_overview())["library"] is None
    assert [(v["version"], v["active"]) for v in versions["versions"]] == [("1.0.0", False)]
    assert ok(app.activate_library_version("psa", "1.0.0")) == "1.0.0"


def test_versions_with_nothing_installed(app: api.Api) -> None:
    assert ok(app.library_versions()) == {"name": None, "versions": []}


def test_activate_an_older_version(app: api.Api, package: Any) -> None:
    ok(app.import_library(str(package("1.0.0"))))
    ok(app.import_library(str(package("1.1.0"))))

    assert ok(app.activate_library_version("psa", "1.0.0")) == "1.0.0"
    assert ok(app.library_overview())["library"]["version"] == "1.0.0"


def test_choose_file_opens_a_dialog_filtered_to_the_kind(app: api.Api) -> None:
    window = FakeWindow((r"C:\Users\ali\Downloads\psa-1.2.0.bomlib",))
    app._set_window(window)

    assert ok(app.choose_file("bomlib")) == r"C:\Users\ali\Downloads\psa-1.2.0.bomlib"
    assert window.asked["dialog_type"] == 10  # open file
    assert window.asked["file_types"] == ("Library packages (*.bomlib)",)


def test_choose_file_cancelled_is_none(app: api.Api) -> None:
    app._set_window(FakeWindow(None))

    assert ok(app.choose_file("bomproj")) is None


def test_choose_file_of_an_unknown_kind_is_an_error(app: api.Api) -> None:
    app._set_window(FakeWindow(None))

    assert app.choose_file("exe")["ok"] is False
