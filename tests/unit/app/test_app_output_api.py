"""Checks and Build endpoints of the desktop app (plan M10d)."""

import csv
import io
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
import xlsxwriter.workbook

from bomgen import build
from bomgen.app import api
from bomgen.engine.errors import EngineError
from bomgen.io import lifecycle
from bomgen.io.yaml_source import read_yaml
from bomgen.models.report import CheckItem, CheckReport, CheckStatus

EXAMPLES = Path(__file__).parents[3] / "examples"
LIBRARY = read_yaml(EXAMPLES / "project.yaml").data["library"]  # what the example asks for
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


def test_checks_and_build_are_blocked_until_the_substation_has_parts(
    app: api.Api, project: Path
) -> None:
    """A blank substation must not read "You can build" (audit APP-8)."""
    lifecycle.create_substation(project, "b", "b")

    checks = ok(app.run_checks(str(project), "b"))
    target = ok(app.build_target(str(project), "b"))

    for problems in (checks["problems"], target["problems"]):
        assert [(p["level"], p["location"]) for p in problems] == [("error", "equipment")]
        assert "Parts" in problems[0]["message"]
    assert checks["engine"]["run"] is False


def test_a_link_no_library_sfp_serves_is_a_problem_on_its_parts_row(
    app: api.Api, project: Path
) -> None:
    """M46: not "The engine stopped", but a located problem Where to fix can open."""
    sub = project.parent / SUBSTATION
    edit(sub, "l2_ports: 1, l2_speed: 100M }", "l2_ports: 1, l2_speed: 10G, l2_media: SM }")
    gps = [e["id"] for e in read_yaml(sub).data["equipment"]].index("gps")

    checks = ok(app.run_checks(str(project), "gis01"))
    target = ok(app.build_target(str(project), "gis01"))

    for problems in (checks["problems"], target["problems"]):
        (problem,) = problems
        assert problem["level"] == "error"
        assert problem["location"] == f"equipment[{gps}].l2_speed"
        assert problem["line"] == 70
        assert problem["message"].startswith("no SFP in the library for 10G SM")
    assert checks["engine"]["run"] is False
    assert checks["engine"]["reason"] == checks["problems"][0]["message"]


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
    assert target["library"] == {"name": LIBRARY["name"], "version": LIBRARY["version"]}
    assert target["problems"] == []


def test_build_target_counts_the_engine_flags_checks_shows(app: api.Api, project: Path) -> None:
    """Build's Warnings matches Checks (audit APP-12)."""
    items = ok(app.run_checks(str(project), "gis01"))["engine"]["items"]
    flags = sum(1 for item in items if item["status"] == "warn")

    assert flags
    assert ok(app.build_target(str(project), "gis01"))["flags"] == flags


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


@pytest.mark.parametrize(
    "name",
    [
        "  ",
        ".xlsx",
        "a/b.xlsx",
        "..\\b.xlsx",
        "book.txt",
        "book.xlsx:stream",
        "a:b.xlsx",
        "CON.xlsx",
        "lpt1.xlsx",
        "nul.old.xlsx",
        "a\x00b.xlsx",
        " book.xlsx",
    ],
)
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
    # Excel holds the old workbook: the writer's move onto it is refused
    def held(*args: object, **kwargs: object) -> None:
        raise PermissionError(13, "The process cannot access the file")

    monkeypatch.setattr(os, "replace", held)

    assert refused(app.build_workbook(str(project), "gis01", str(tmp_path))) == "file_open"


@pytest.mark.parametrize("folder", ["", "relative/out"])
def test_build_needs_a_full_folder_path(app: api.Api, project: Path, folder: str) -> None:
    assert refused(app.build_workbook(str(project), "gis01", folder)) == "bad_folder"


def test_a_previous_issue_that_is_not_a_workbook_is_refused(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    previous = tmp_path / "old.xlsx"
    previous.write_text("not a workbook", encoding="utf-8")

    envelope = app.build_workbook(
        str(project), "gis01", str(tmp_path / "out"), compare=str(previous)
    )

    assert refused(envelope) == "bad_previous"


def test_an_engine_failure_is_refused_with_its_message(
    app: api.Api, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def stops(loaded: object) -> object:
        raise EngineError("no rule for this panel")

    monkeypatch.setattr(build, "build_bom", stops)
    envelope = app.build_workbook(str(project), "gis01", str(tmp_path))

    assert refused(envelope) == "engine"
    assert "no rule for this panel" in envelope["error"]["message"]  # type: ignore[index]


def test_a_failed_check_still_writes_the_workbook(
    app: api.Api, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed = CheckReport(
        items=(CheckItem(check="dc_main", status=CheckStatus.FAIL, panel_id="psa1", message="x"),)
    )
    monkeypatch.setattr(build, "check_report", lambda loaded, result: failed)

    result = ok(app.build_workbook(str(project), "gis01", str(tmp_path)))

    assert Path(result["path"]).is_file()
    assert result["checks"]["failed"] is True


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


@pytest.mark.parametrize(("platform", "command"), [("darwin", "open"), ("linux", "xdg-open")])
def test_open_uses_the_systems_default_app(tmp_path: Path, platform: str, command: str) -> None:
    ran: list[list[str]] = []
    api.open_with_default_app(tmp_path / "a.xlsx", platform=platform, run=ran.append)
    assert ran == [[command, str(tmp_path / "a.xlsx")]]


def test_open_on_windows_uses_the_file_association(tmp_path: Path) -> None:
    started: list[str] = []
    target = tmp_path / "a, b.xlsx"
    api.open_with_default_app(
        target, platform="win32", run=lambda c: pytest.fail("ran"), start=started.append
    )
    assert started == [str(target)]


def test_a_read_only_folder_is_not_reported_as_an_open_file(
    app: api.Api, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(xlsxwriter.workbook, "ZipFile", denied)
    monkeypatch.setattr(os, "access", lambda path, mode: False)

    envelope = app.build_workbook(str(project), "gis01", str(tmp_path))

    assert refused(envelope) == "io"
    assert "read-only" in envelope["error"]["message"]  # type: ignore[index]


def test_a_check_report_that_cannot_be_saved_says_the_workbook_was_written(
    app: api.Api, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_text = Path.write_text

    def refuse_json(p: Path, *a: Any, **k: Any) -> int:
        if p.name.endswith(".checks.json"):
            raise OSError(28, "No space left on device")
        return write_text(p, *a, **k)

    monkeypatch.setattr(Path, "write_text", refuse_json)
    envelope = app.build_workbook(str(project), "gis01", str(tmp_path))

    assert refused(envelope) == "io"
    assert "was written" in envelope["error"]["message"]  # type: ignore[index]


# -- Summary BOM (ADR 0035, plan M63) --


def include_summary(project: Path) -> None:
    edit(
        project.parent / SUBSTATION,
        '\n  file_name: "{doc_no}',
        '\n  include: [summary_bom]\n  file_name: "{doc_no}',
    )


def test_build_target_says_whether_the_summary_is_included(app: api.Api, project: Path) -> None:
    assert ok(app.build_target(str(project), "gis01"))["include"] == []
    ok(app.set_substation_field(str(project), "gis01", ["output", "include"], ["summary_bom"]))
    target = ok(app.build_target(str(project), "gis01"))
    assert target["include"] == ["summary_bom"]
    assert target["sheets"][-1] == {"name": "Summary BOM", "cabinet": None}


def test_build_writes_the_summary_when_included(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    include_summary(project)
    result = ok(app.build_workbook(str(project), "gis01", str(tmp_path / "out")))
    assert result["sheets"][-1] == "Summary BOM"


def test_export_summary_csv_writes_the_sheet_rows(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    out = tmp_path / "summary.csv"
    result = ok(app.export_summary_csv(str(project), "gis01", str(out)))
    assert result["path"] == str(out)
    assert result["lines"] == 63
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # Excel reads the BOM as UTF-8
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[0] == [
        "SR.NO",
        "DESCRIPTION",
        "QUANTITY",
        "MAKE",
        "MODEL",
        "ORDERING CODE",
        "WHERE USED",
    ]
    mcb = next(r for r in rows if r[5] == "A9F74202")
    assert mcb[2] == "77"
    assert mcb[6].startswith("1: PSA1-C2")
    assert len(rows) == 64


# -- Recorded issues and accepted warnings (ADR 0036, plan M66b) --


def substation_yaml(project: Path) -> dict[str, Any]:
    return read_yaml(project.parent / SUBSTATION).data


def test_build_target_has_no_record_before_the_first_issue(app: api.Api, project: Path) -> None:
    target = ok(app.build_target(str(project), "gis01"))
    assert target["issue"] == {"refusal": None, "record": None}


def test_build_as_issued_records_the_issue(app: api.Api, project: Path) -> None:
    folder = project.parent / "substations" / "gis01" / "out"
    result = ok(app.build_workbook(str(project), "gis01", str(folder), issue="For review"))

    assert Path(result["path"]).is_file()
    assert result["issued"] == {"rev": "02", "file": f"out/{WORKBOOK}"}
    assert result["not_issued"] is None
    (recorded,) = substation_yaml(project)["issues"]
    assert recorded["rev"] == "02"
    assert recorded["description"] == "For review"
    target = ok(app.build_target(str(project), "gis01"))
    assert target["issue"]["record"] == {"rev": "02", "file": f"out/{WORKBOOK}", "warning": None}
    assert "Rev 02 is already issued" in target["issue"]["refusal"]


def test_a_recorded_rev_is_not_issued_again(app: api.Api, project: Path, tmp_path: Path) -> None:
    ok(app.build_workbook(str(project), "gis01", str(tmp_path / "a"), issue="For review"))
    envelope = app.build_workbook(str(project), "gis01", str(tmp_path / "b"), issue="Again")
    assert refused(envelope) == "already_issued"
    assert not (tmp_path / "b").exists()


def test_build_as_issued_needs_a_description(app: api.Api, project: Path, tmp_path: Path) -> None:
    envelope = app.build_workbook(str(project), "gis01", str(tmp_path), issue="  ")
    assert refused(envelope) == "bad_description"


def test_a_failed_check_writes_the_workbook_but_records_nothing(
    app: api.Api, project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed = CheckReport(
        items=(CheckItem(check="dc_main", status=CheckStatus.FAIL, panel_id="psa1", message="x"),)
    )
    monkeypatch.setattr(build, "check_report", lambda loaded, result: failed)

    result = ok(app.build_workbook(str(project), "gis01", str(tmp_path), issue="For review"))

    assert Path(result["path"]).is_file()
    assert result["issued"] is None
    assert result["not_issued"] == "Not recorded as issued: a check failed."
    assert "issues" not in substation_yaml(project)


def test_the_next_build_compares_with_the_recorded_issue(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    folder = project.parent / "substations" / "gis01" / "out"
    ok(app.build_workbook(str(project), "gis01", str(folder), issue="For review"))

    result = ok(app.build_workbook(str(project), "gis01", str(tmp_path / "next")))

    assert result["revisions"]["previous"] == WORKBOOK
    assert result["record_warning"] is None


def test_a_changed_recorded_file_warns_and_compares_with_nothing(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    folder = project.parent / "substations" / "gis01" / "out"
    ok(app.build_workbook(str(project), "gis01", str(folder), issue="For review"))
    with (folder / WORKBOOK).open("ab") as file:
        file.write(b"edited")

    target = ok(app.build_target(str(project), "gis01"))
    result = ok(app.build_workbook(str(project), "gis01", str(tmp_path / "next")))

    message = f"Rev 02's recorded file out/{WORKBOOK} has changed since it was issued"
    assert target["issue"]["record"]["warning"].startswith(message)
    assert result["record_warning"].startswith(message)
    assert result["revisions"] is None


def test_a_chosen_previous_issue_wins_over_the_record(
    app: api.Api, project: Path, tmp_path: Path
) -> None:
    folder = project.parent / "substations" / "gis01" / "out"
    chosen = ok(app.build_workbook(str(project), "gis01", str(tmp_path / "chosen"), "x.xlsx"))
    ok(app.build_workbook(str(project), "gis01", str(folder), issue="For review"))

    result = ok(
        app.build_workbook(str(project), "gis01", str(tmp_path / "next"), compare=chosen["path"])
    )

    assert result["revisions"]["previous"] == "x.xlsx"


def first_warning(app: api.Api, project: Path) -> dict[str, Any]:
    items = ok(app.run_checks(str(project), "gis01"))["engine"]["items"]
    return next(i for i in items if i["status"] == "warn")


def test_accept_a_warning_with_a_reason(app: api.Api, project: Path) -> None:
    item = first_warning(app, project)

    page = ok(
        app.accept_warning(
            str(project), "gis01", item["check"], item["panel_id"], item["subject"], "Agreed", "Ali"
        )
    )

    key = ("check", "panel_id", "subject")
    same = next(i for i in page["engine"]["items"] if all(i[k] == item[k] for k in key))
    assert same["accepted"] == "Agreed"
    assert page["unused"] == []
    (accepted,) = substation_yaml(project)["checks"]["accepted"]
    assert accepted["reason"] == "Agreed"
    assert accepted["by"] == "Ali"


def test_an_acceptance_needs_a_reason(app: api.Api, project: Path) -> None:
    item = first_warning(app, project)
    envelope = app.accept_warning(
        str(project), "gis01", item["check"], item["panel_id"], item["subject"], " "
    )
    assert refused(envelope) == "invalid_edit"


def test_an_unused_acceptance_is_listed_until_removed(app: api.Api, project: Path) -> None:
    page = ok(app.accept_warning(str(project), "gis01", "dc_main", "psa1", "gone", "Old"))
    assert page["unused"] == [
        {"index": 0, "check": "dc_main", "panel_id": "psa1", "subject": "gone", "reason": "Old"}
    ]

    page = ok(app.remove_acceptance(str(project), "gis01", 0))

    assert page["unused"] == []
    assert "checks" not in substation_yaml(project)


def test_an_accepted_warning_leaves_builds_flag_count(app: api.Api, project: Path) -> None:
    flags = ok(app.build_target(str(project), "gis01"))["flags"]
    item = first_warning(app, project)
    ok(
        app.accept_warning(
            str(project), "gis01", item["check"], item["panel_id"], item["subject"], "Ok"
        )
    )
    assert ok(app.build_target(str(project), "gis01"))["flags"] == flags - 1


# --- override reasons (ADR 0040) ---


def override_items(app: api.Api, project: Path) -> list[dict[str, Any]]:
    items = ok(app.run_checks(str(project), "gis01"))["engine"]["items"]
    return [i for i in items if i["check"] == "override"]


def test_the_checks_list_every_override_with_its_automatic_value(
    app: api.Api, project: Path
) -> None:
    items = override_items(app, project)
    main = next(i for i in items if (i["panel_id"], i["subject"]) == ("psa1", "main_mcb"))
    assert main["status"] == "pass"
    assert main["message"] == "16 A instead of the automatic 10 A"
    assert main["values"] == {"automatic": "10 A", "override": "16 A"}


def test_a_reason_on_a_hand_written_panel_goes_to_its_file(app: api.Api, project: Path) -> None:
    ok(app.set_panel_field(str(project), "gis01", "psa1", ["options", "main_mcb_override_a"], 6))
    (item,) = [
        i
        for i in override_items(app, project)
        if (i["panel_id"], i["subject"]) == ("psa1", "main_mcb")
    ]
    assert item["status"] == "warn"

    page = ok(app.set_override_reason(str(project), "gis01", "psa1", "main_mcb", " Feeder is 6 A "))

    item = next(
        i
        for i in page["engine"]["items"]
        if (i["check"], i["panel_id"], i["subject"]) == ("override", "psa1", "main_mcb")
    )
    assert (item["status"], item["values"]["reason"]) == ("pass", "Feeder is 6 A")
    panel = read_yaml(project.parent / "substations" / "gis01" / "panels" / "psa1.yaml").data
    assert panel["options"]["override_reasons"] == {"main_mcb": "Feeder is 6 A"}
    reasons = ok(app.panel_page(str(project), "gis01", "psa1"))["override_reasons"]
    assert reasons == {"main_mcb": "Feeder is 6 A"}

    ok(app.set_override_reason(str(project), "gis01", "psa1", "main_mcb", ""))
    panel = read_yaml(project.parent / "substations" / "gis01" / "panels" / "psa1.yaml").data
    assert "override_reasons" not in panel["options"]


def test_a_spares_reason_goes_to_the_spares_list(app: api.Api, project: Path) -> None:
    code = "6GK6000-8FG51-0AA0"
    ok(app.set_substation_field(str(project), "gis01", ["spares_list", "items", code], 2))

    page = ok(app.set_override_reason(str(project), "gis01", None, f"spares.{code}", "Client's"))

    assert substation_yaml(project)["spares_list"]["reasons"] == {code: "Client's"}
    item = next(i for i in page["engine"]["items"] if i["subject"] == f"spares.{code}")
    assert item["values"]["reason"] == "Client's"


def test_a_panel_reason_needs_its_panel(app: api.Api, project: Path) -> None:
    envelope = app.set_override_reason(str(project), "gis01", None, "main_mcb", "x")
    assert refused(envelope) == "edit_refused"
    assert "names its panel" in str(envelope["error"])
