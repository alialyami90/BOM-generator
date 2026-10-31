"""Project endpoints of the desktop app: Home, Project page, Backup and share (plan M10b)."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.io.yaml_source import read_yaml

EXAMPLES = Path(__file__).parents[3] / "examples"
LIBRARY = read_yaml(EXAMPLES / "project.yaml").data["library"]  # what the example asks for
EXAMPLE_ID = "jfgp2-pkg3"
EXAMPLE_NAME = "JAFURAH JFGP2 PKG.3 UTILITIES, SULFUR and INTERCONNECTING SYSTEMS"


class FakeWindow:
    def __init__(self) -> None:
        self.answers: list[tuple[str, ...] | None] = []
        self.asked: list[dict[str, Any]] = []

    def create_file_dialog(self, dialog_type: int = 10, **options: Any) -> tuple[str, ...] | None:
        self.asked.append({"dialog_type": dialog_type, **options})
        return self.answers.pop(0)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture
def window() -> FakeWindow:
    return FakeWindow()


@pytest.fixture
def app(tmp_path: Path, workspace: Path, window: FakeWindow) -> api.Api:
    instance = api.Api(
        env={
            "BOMGEN_LIBRARY_HOME": str(tmp_path / "libraries"),
            "BOMGEN_WORKSPACE": str(workspace),
            "BOMGEN_APP_HOME": str(tmp_path / "app"),
        }
    )
    instance._set_window(window)
    return instance


def copy_example(folder: Path) -> Path:
    shutil.copytree(EXAMPLES, folder)
    return folder / "project.yaml"


@pytest.fixture
def example(workspace: Path) -> Path:
    return copy_example(workspace / EXAMPLE_ID)


def ok(envelope: dict[str, object]) -> Any:
    assert envelope["ok"] is True, envelope
    json.dumps(envelope)  # pywebview sends it to the page as JSON
    return envelope["data"]


def error_kind(envelope: dict[str, object]) -> str:
    assert envelope["ok"] is False, envelope
    return envelope["error"]["kind"]  # type: ignore[index,no-any-return]


# -- Home: the projects on this PC --


def test_no_projects_in_an_empty_workspace(app: api.Api) -> None:
    assert ok(app.list_projects()) == []


def test_projects_in_the_workspace_are_listed_with_their_substations(
    app: api.Api, example: Path
) -> None:
    (project,) = ok(app.list_projects())

    assert project["id"] == EXAMPLE_ID
    assert project["name"] == EXAMPLE_NAME
    assert project["file"] == str(example)
    assert project["library"]["name"] == LIBRARY["name"]
    assert project["library"]["version"] == LIBRARY["version"]
    assert [(s["id"], s["panels"]) for s in project["substations"]] == [("gis01", 4)]
    assert project["status"] == {"level": "ok", "text": "Ready", "errors": 0}


def test_a_project_with_errors_is_listed_with_the_count(app: api.Api, example: Path) -> None:
    text = example.read_text(encoding="utf-8")
    example.write_text(text.replace("doc_no: VD-EL0009-861GISPSA-001", "doc_no: 7"), "utf-8")
    (example.parent / "substations" / "gis01" / "substation.yaml").write_text(
        "substation: {id: gis01}\n", "utf-8"
    )

    (project,) = ok(app.list_projects())

    assert project["status"]["level"] == "bad"
    assert project["status"]["errors"] >= 1
    assert project["status"]["text"].endswith(("error", "errors"))


def test_an_unreadable_project_file_is_listed_not_hidden(app: api.Api, workspace: Path) -> None:
    broken = workspace / "broken"
    broken.mkdir(parents=True)
    (broken / "project.yaml").write_text("project: [", "utf-8")

    (project,) = ok(app.list_projects())

    assert project["file"] == str(broken / "project.yaml")
    assert project["name"] == "broken"
    assert project["status"]["level"] == "bad"


def test_a_project_opened_from_another_folder_is_remembered(app: api.Api, tmp_path: Path) -> None:
    elsewhere = copy_example(tmp_path / "D" / "Projects" / "jafurah")

    ok(app.open_project(str(elsewhere)))

    assert [p["file"] for p in ok(app.list_projects())] == [str(elsewhere)]


def test_a_remembered_project_that_was_deleted_is_dropped(app: api.Api, tmp_path: Path) -> None:
    elsewhere = copy_example(tmp_path / "elsewhere")
    ok(app.open_project(str(elsewhere)))
    shutil.rmtree(elsewhere.parent)

    assert ok(app.list_projects()) == []


# -- Project page --


def test_open_project_returns_the_project_page(app: api.Api, example: Path) -> None:
    page = ok(app.open_project(str(example)))

    assert page["project"]["name"] == EXAMPLE_NAME
    assert page["defaults"]["constants"]["dc_voltage_v"] == 125
    assert page["defaults"]["spares"]["rack_u_reserved"] == 10
    assert [d["key"] for d in page["documents"]] == ["gis01-bom", "gis01-power", "gis01-heat"]
    assert page["substations"][0]["name"]
    assert page["substations"][0]["file"].endswith("substation.yaml")
    assert page["problems"] == []


def test_open_project_with_errors_returns_located_problems(app: api.Api, example: Path) -> None:
    substation = example.parent / "substations" / "gis01" / "substation.yaml"
    substation.write_text("substation: {id: gis01}\n", "utf-8")

    page = ok(app.open_project(str(example)))

    assert page["project"]["name"] == EXAMPLE_NAME
    assert page["problems"]
    problem = page["problems"][0]
    assert set(problem) == {"file", "line", "location", "message"}
    assert problem["file"] == str(substation)


def test_a_substation_that_does_not_load_keeps_its_name(app: api.Api, example: Path) -> None:
    """Audit 2026-10-31 APP-14: the top bar and the switcher show the name, not the folder."""
    file = example.parent / "substations" / "gis01" / "substation.yaml"
    text = file.read_text("utf-8")
    file.write_text(text.replace("part_id: RST2228-L2,", "part_id: NOPE,"), "utf-8")

    page = ok(app.open_project(str(example)))

    assert page["problems"]
    (row,) = page["substations"]
    assert row["id"] == "gis01"
    assert row["name"] == "GIS Substation"


def test_layout_heights_are_assumed_until_written_or_confirmed(app: api.Api, example: Path) -> None:
    """Audit 2026-10-31 APP-19: waist height and rack start on the project Overview."""
    layout = ["defaults", "layout"]
    page = ok(app.open_project(str(example)))
    assert page["defaults"]["layout"] == {"waist_height_mm": 1000, "rack_start_mm": 200}
    assert page["layout_assumed"] == {"waist_height_mm": "default", "rack_start_mm": "default"}

    page = ok(app.set_project_field(str(example), [*layout, "waist_height_mm"], 1100))
    assert page["defaults"]["layout"]["waist_height_mm"] == 1100
    assert page["layout_assumed"] == {"rack_start_mm": "default"}

    text = example.read_text("utf-8")
    marked = "    waist_height_mm: 1100\n    rack_start_mm: 250  # ASSUMED"
    example.write_text(text.replace("    waist_height_mm: 1100", marked), "utf-8")
    page = ok(app.open_project(str(example)))
    assert page["layout_assumed"] == {"rack_start_mm": "marked"}

    page = ok(app.confirm_project_field(str(example), [*layout, "rack_start_mm"]))
    assert page["layout_assumed"] == {}


def test_open_project_on_a_missing_file_is_an_io_error(app: api.Api, tmp_path: Path) -> None:
    assert error_kind(app.open_project(str(tmp_path / "nowhere" / "project.yaml"))) == "io"


def test_choose_project_folder_returns_its_project_file(
    app: api.Api, window: FakeWindow, example: Path
) -> None:
    window.answers.append((str(example.parent),))

    assert ok(app.choose_project_folder()) == str(example)
    assert window.asked[0]["dialog_type"] == 20  # folder


def test_choose_project_folder_without_a_project_file_says_so(
    app: api.Api, window: FakeWindow, tmp_path: Path
) -> None:
    window.answers.append((str(tmp_path),))

    assert error_kind(app.choose_project_folder()) == "not_a_project"


def test_choose_project_folder_cancelled_is_none(app: api.Api, window: FakeWindow) -> None:
    window.answers.append(None)

    assert ok(app.choose_project_folder()) is None


# -- Backup and share --


def test_export_writes_where_the_save_dialog_says(
    app: api.Api, window: FakeWindow, example: Path, tmp_path: Path
) -> None:
    target = tmp_path / "out" / "shared.bomproj"
    target.parent.mkdir()
    window.answers.append((str(target),))

    exported = ok(app.export_project(str(example)))

    assert exported["path"] == str(target)
    assert exported["size"] == target.stat().st_size > 0
    assert window.asked[0]["dialog_type"] == 30  # save
    assert window.asked[0]["save_filename"].startswith(EXAMPLE_ID)
    assert window.asked[0]["save_filename"].endswith(".bomproj")


def test_export_cancelled_writes_nothing(app: api.Api, window: FakeWindow, example: Path) -> None:
    window.answers.append(None)

    assert ok(app.export_project(str(example))) is None


def test_back_up_now_then_list_backups(app: api.Api, example: Path) -> None:
    saved = ok(app.backup_project(str(example)))

    (backup,) = ok(app.list_backups(str(example)))
    assert backup["path"] == saved["path"]
    assert backup["project_id"] == EXAMPLE_ID
    assert backup["library_version"] == LIBRARY["version"]
    assert backup["size"] > 0
    assert backup["problem"] is None


def test_import_review_of_a_project_already_on_this_pc_warns_and_can_replace(
    app: api.Api, window: FakeWindow, example: Path, tmp_path: Path
) -> None:
    target = tmp_path / "shared.bomproj"
    window.answers.append((str(target),))
    ok(app.export_project(str(example)))

    preview = ok(app.preview_project_import(str(target)))

    assert preview["can_import"] is True
    assert preview["exists"] is True
    assert preview["project_id"] == EXAMPLE_ID
    assert preview["file_name"] == "shared.bomproj"
    assert error_kind(app.import_project(str(target))) == "project_exists"
    result = ok(app.import_project(str(target), True))
    assert result["replaced"] is True
    assert result["backup"]
    assert result["project_file"] == str(example)


def test_import_review_offers_a_free_id_to_keep_both(
    app: api.Api, window: FakeWindow, example: Path, tmp_path: Path
) -> None:
    target = tmp_path / "shared.bomproj"
    window.answers.append((str(target),))
    ok(app.export_project(str(example)))

    preview = ok(app.preview_project_import(str(target)))
    result = ok(app.import_project(str(target), False, preview["suggested_id"]))

    assert preview["suggested_id"]
    assert preview["suggested_id"] != EXAMPLE_ID
    assert result["replaced"] is False
    assert result["manifest"]["project_id"] == preview["suggested_id"]
    ids = sorted(p["id"] for p in ok(app.list_projects()))
    assert ids == sorted([EXAMPLE_ID, preview["suggested_id"]])


def test_keep_both_under_an_id_that_is_taken_is_refused(
    app: api.Api, window: FakeWindow, example: Path, tmp_path: Path
) -> None:
    target = tmp_path / "shared.bomproj"
    window.answers.append((str(target),))
    ok(app.export_project(str(example)))

    assert error_kind(app.import_project(str(target), False, EXAMPLE_ID)) == "project_exists"


def test_import_into_an_empty_workspace(app: api.Api, window: FakeWindow, tmp_path: Path) -> None:
    source = copy_example(tmp_path / "colleague" / EXAMPLE_ID)
    target = tmp_path / "from-colleague.bomproj"
    window.answers.append((str(target),))
    ok(app.export_project(str(source)))
    shutil.rmtree(source.parent)

    preview = ok(app.preview_project_import(str(target)))
    result = ok(app.import_project(str(target)))

    assert preview["exists"] is False
    assert result["replaced"] is False
    assert [p["id"] for p in ok(app.list_projects())] == [EXAMPLE_ID]


def test_restore_a_backup(app: api.Api, example: Path) -> None:
    saved = ok(app.backup_project(str(example)))
    (example.parent / "notes.txt").write_text("changed after the backup", "utf-8")

    preview = ok(app.preview_backup_restore(saved["path"]))
    result = ok(app.restore_backup(saved["path"]))

    assert preview["can_import"] is True
    assert preview["exists"] is True
    assert result["replaced"] is True
    assert not (example.parent / "notes.txt").exists()


def test_restore_review_refuses_a_backup_outside_its_backups_folder(
    app: api.Api, example: Path, tmp_path: Path
) -> None:
    saved = ok(app.backup_project(str(example)))
    moved = tmp_path / "moved.bomproj"
    shutil.copy(saved["path"], moved)

    preview = ok(app.preview_backup_restore(str(moved)))

    assert preview["can_import"] is False
    assert preview["checks"][0]["id"] == "location"
    assert preview["checks"][0]["status"] == "failed"


def test_show_in_folder_selects_the_file_in_explorer_on_windows(tmp_path: Path) -> None:
    target = tmp_path / "a backup.bomproj"
    target.write_bytes(b"x")
    ran: list[list[str]] = []
    api.reveal(target, platform="win32", run=ran.append)
    assert ran == [["explorer", f"/select,{target}"]]


@pytest.mark.parametrize(("platform", "opener"), [("darwin", "open"), ("linux", "xdg-open")])
def test_show_in_folder_opens_the_folder_elsewhere(
    tmp_path: Path, platform: str, opener: str
) -> None:
    target = tmp_path / "x.bomproj"
    target.write_bytes(b"x")
    ran: list[list[str]] = []
    api.reveal(target, platform=platform, run=ran.append)
    assert ran == [[opener, str(tmp_path)]]


def test_show_in_folder_refuses_a_backup_deleted_since_it_was_listed(
    app: api.Api, example: Path
) -> None:
    ran: list[Path] = []
    app._reveal = ran.append
    saved = ok(app.backup_project(str(example)))
    Path(saved["path"]).unlink()

    envelope = app.show_in_folder(saved["path"])

    assert envelope["ok"] is False
    assert envelope["error"]["kind"] == "io"  # type: ignore[index]
    assert ran == []


def test_show_in_folder_reveals_the_files_the_app_listed(app: api.Api, example: Path) -> None:
    ran: list[Path] = []
    app._reveal = ran.append
    saved = ok(app.backup_project(str(example)))
    (listed,) = ok(app.list_backups(str(example)))
    ok(app.list_projects())

    for path in (saved["path"], listed["path"], str(example)):
        ok(app.show_in_folder(path))

    assert ran == [Path(saved["path"]), Path(listed["path"]), example]


def test_show_in_folder_refuses_a_path_the_app_did_not_list(app: api.Api, tmp_path: Path) -> None:
    ran: list[Path] = []
    app._reveal = ran.append
    other = tmp_path / "anything.exe"
    other.write_bytes(b"x")

    envelope = app.show_in_folder(str(other))

    assert envelope["ok"] is False
    assert envelope["error"]["kind"] == "not_listed"  # type: ignore[index]
    assert ran == []


def test_recent_projects_live_in_the_app_home(app: api.Api, tmp_path: Path) -> None:
    elsewhere = copy_example(tmp_path / "elsewhere")

    ok(app.open_project(str(elsewhere)))

    assert (tmp_path / "app" / "recent-projects.json").is_file()


def test_app_home_defaults_next_to_the_libraries_not_beside_an_overridden_one() -> None:
    windows = {"LOCALAPPDATA": r"C:\Users\ali\AppData\Local", "BOMGEN_LIBRARY_HOME": r"D:\libs"}

    assert api.default_app_home(windows, platform="win32") == Path(
        windows["LOCALAPPDATA"], "bomgen", "app"
    )
    assert api.default_app_home({"BOMGEN_APP_HOME": "/x"}) == Path("/x")
    assert api.default_app_home({"XDG_DATA_HOME": "/d"}, platform="linux") == Path("/d/bomgen/app")


def test_a_project_opens_when_the_recent_list_cannot_be_written(
    app: api.Api, tmp_path: Path
) -> None:
    (tmp_path / "app").write_text("a file where the folder should be", "utf-8")
    elsewhere = copy_example(tmp_path / "elsewhere")

    page = ok(app.open_project(str(elsewhere)))

    assert page["id"] == EXAMPLE_ID
