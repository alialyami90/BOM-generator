"""Checks and Build endpoints of the desktop app (plan M10d)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api, output
from bomgen.writer import WriterError

EXAMPLES = Path(__file__).parents[3] / "examples"
SUBSTATION = Path("substations") / "gis01" / "substation.yaml"
WORKBOOK = "VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx"


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


def refused(envelope: dict[str, object]) -> str:
    assert envelope["ok"] is False, envelope
    return envelope["error"]["kind"]  # type: ignore[index,no-any-return]


def edit(file: Path, old: str, new: str) -> None:
    text = file.read_text(encoding="utf-8")
    assert old in text
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


# -- Checks --


def test_checks_on_a_clean_substation_run_the_engine_checks(app: api.Api, project: Path) -> None:
    page = ok(app.run_checks(str(project), "gis01"))

    assert page["problems"] == []
    assert page["engine"]["run"] is True
    items = page["engine"]["items"]
    assert items
    assert {"check", "status", "panel_id", "subject", "message", "values"} <= set(items[0])
    assert {i["status"] for i in items} <= {"pass", "warn", "fail"}
    assert page["engine"]["failed"] is any(i["status"] == "fail" for i in items)


def test_checks_list_input_errors_and_do_not_run_the_engine(app: api.Api, project: Path) -> None:
    edit(project.parent / SUBSTATION, "ied_count: 40", "ied_count: lots")

    page = ok(app.run_checks(str(project), "gis01"))

    assert page["problems"]
    assert {p["level"] for p in page["problems"]} == {"error"}
    assert page["problems"][0]["file"].endswith("substation.yaml")
    assert page["engine"]["run"] is False
    assert "error" in page["engine"]["reason"]


def test_checks_of_an_unknown_substation_are_refused(app: api.Api, project: Path) -> None:
    assert refused(app.run_checks(str(project), "nope")) == "not_found"


# -- Build --


def test_build_writes_the_workbook_and_its_check_report(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    result = ok(app.build_workbook(str(project), "gis01", str(tmp_path / "out")))

    path = Path(result["path"])
    assert path == tmp_path / "out" / WORKBOOK
    assert path.is_file()
    assert result["size"] == path.stat().st_size
    assert result["sheets"][-3:] == ["Power Consumption", "Heat Dissipation", "Heat Calculations"]
    assert result["checks"]["items"]
    report = json.loads(path.with_suffix(".checks.json").read_text(encoding="utf-8"))
    assert len(report["items"]) == len(result["checks"]["items"])
    assert result["revisions"] is None


def test_build_target_gives_the_file_name_and_default_folder(app: api.Api, project: Path) -> None:
    target = ok(app.build_target(str(project), "gis01"))

    assert target["file_name"] == WORKBOOK
    assert target["folder"] == str(project.parent / "substations" / "gis01" / "out")
    assert target["exists"] is False
    assert target["sheets"][0] == {"name": "1", "cabinet": "PSA Cabinet - 001"}
    assert target["sheets"][-1] == {"name": "Heat Calculations", "cabinet": None}
    assert target["revision"] == "02"
    assert target["library"] == {"name": "psa-devices", "version": "1.0.0"}
    assert target["problems"] == []


def test_build_does_not_replace_a_file_unless_asked(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    out = str(tmp_path / "out")
    ok(app.build_workbook(str(project), "gis01", out))

    assert refused(app.build_workbook(str(project), "gis01", out)) == "file_exists"
    assert ok(app.build_workbook(str(project), "gis01", out, replace=True))["path"]


def test_build_under_another_name(app: api.Api, project: Path, tmp_path: Path) -> None:
    result = ok(app.build_workbook(str(project), "gis01", str(tmp_path), "gis01 copy.xlsx"))

    assert Path(result["path"]) == tmp_path / "gis01 copy.xlsx"


@pytest.mark.parametrize("name", ["  ", "a/b.xlsx", "..\\b.xlsx", "book.txt"])
def test_build_refuses_a_bad_file_name(
    app: api.Api, project: Path, tmp_path: Path, name: str
) -> None:
    assert refused(app.build_workbook(str(project), "gis01", str(tmp_path), name)) == "bad_name"


def test_build_is_blocked_by_input_errors(app: api.Api, project: Path, tmp_path: Path) -> None:
    edit(project.parent / SUBSTATION, "ied_count: 40", "ied_count: lots")

    assert refused(app.build_workbook(str(project), "gis01", str(tmp_path))) == "has_errors"


def test_a_workbook_open_in_excel_is_reported_as_open(
    app: api.Api, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def locked(workbook: object, path: Path) -> Path:
        try:
            raise PermissionError(13, "Permission denied", str(path))
        except PermissionError as exc:
            raise WriterError(f"could not write {path}: {exc}") from exc

    monkeypatch.setattr(output, "write_workbook", locked)

    assert refused(app.build_workbook(str(project), "gis01", str(tmp_path))) == "file_open"


def test_build_compares_with_a_previous_issue(app: api.Api, project: Path, tmp_path: Path) -> None:
    first = ok(app.build_workbook(str(project), "gis01", str(tmp_path / "rev01")))

    result = ok(
        app.build_workbook(str(project), "gis01", str(tmp_path / "rev02"), compare=first["path"])
    )

    assert result["revisions"]["previous"]
    assert isinstance(result["revisions"]["changes"], list)


def test_a_built_workbook_can_be_opened_and_shown(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    opened: list[Path] = []
    app._open = opened.append
    app._reveal = opened.append
    result = ok(app.build_workbook(str(project), "gis01", str(tmp_path)))

    ok(app.open_file(result["path"]))
    ok(app.show_in_folder(result["path"]))

    assert opened == [Path(result["path"])] * 2


def test_only_listed_files_are_opened(app: api.Api, tmp_path: Path) -> None:
    other = tmp_path / "other.xlsx"
    other.write_bytes(b"x")

    assert refused(app.open_file(str(other))) == "not_listed"


@pytest.mark.parametrize(
    ("platform", "command"),
    [("win32", ["explorer"]), ("darwin", ["open"]), ("linux", ["xdg-open"])],
)
def test_open_uses_the_systems_default_app(
    tmp_path: Path, platform: str, command: list[str]
) -> None:
    ran: list[list[str]] = []
    api.open_with_default_app(tmp_path / "a.xlsx", platform=platform, run=ran.append)
    assert ran == [[*command, str(tmp_path / "a.xlsx")]]
