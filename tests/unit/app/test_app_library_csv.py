"""Library export and CSV import in the app (M16 b, ADR 0018).

The CSV tables and the dry run are tested in the library store's own tests; these cover the
bridge: where files go, what the review gets, and that accepted rows land in the pending set.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"
NAME = "psa-devices"
PART = "SEL-3555-RTAC"


@pytest.fixture
def app(tmp_path: Path) -> api.Api:
    package = tmp_path / "lib.bomlib"
    pack(EXAMPLES / "library.yaml", package, name=NAME, version="1.0.0")
    LibraryStore(tmp_path / "libraries").import_package(package)
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


def edit_devices(folder: Path, part: str, column: str, value: str) -> None:
    """Change one cell of devices.csv the way Excel would save it (UTF-8 with BOM)."""
    path = folder / "devices.csv"
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
    for row in rows:
        if row["part_id"] == part:
            row[column] = value
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(out.getvalue(), encoding="utf-8-sig")


def test_csv_export_writes_one_file_per_table_in_its_own_folder(
    app: api.Api, tmp_path: Path
) -> None:
    reply = ok(app.export_library_csv(["devices"], str(tmp_path / "out")))
    folder = Path(reply["folder"])
    assert folder.parent == tmp_path / "out"
    assert folder.name == f"{NAME}-1.0.0-csv"
    assert "devices.csv" in reply["files"]
    assert "mcb.csv" not in reply["files"]
    assert (folder / "devices.csv").read_bytes().startswith(b"\xef\xbb\xbf")


def test_csv_export_refuses_an_unknown_table_group(app: api.Api, tmp_path: Path) -> None:
    assert refused(app.export_library_csv(["nope"], str(tmp_path)))["kind"] == "invalid_request"


def test_a_cancelled_export_writes_nothing(app: api.Api) -> None:
    assert ok(app.export_library_csv(["devices"])) is None
    assert ok(app.export_library_package()) is None


def test_backup_package_is_written_where_chosen(app: api.Api, tmp_path: Path) -> None:
    target = tmp_path / "backup.bomlib"
    reply = ok(app.export_library_package(str(target)))
    assert reply["file"] == str(target)
    assert target.is_file()


def test_csv_preview_lists_the_changed_cell_without_writing(app: api.Api, tmp_path: Path) -> None:
    folder = Path(ok(app.export_library_csv(["devices", "catalogues"], str(tmp_path)))["folder"])
    edit_devices(folder, PART, "unit_power_w", "80")
    preview = ok(app.preview_library_csv(str(folder / "devices.csv")))
    assert preview["can_import"] is True
    assert preview["rows"]["devices.csv"] > 0
    assert preview["changed"] == [PART]
    change = {"area": "devices", "key": PART, "field": "unit_power_w", "from": "62", "to": "80"}
    assert change in preview["changes"]
    assert all({"label", "status", "detail"} <= set(c) for c in preview["checks"])
    assert ok(app.library_pending())["count"] == 0


def test_a_row_with_a_problem_is_listed_and_skipped(app: api.Api, tmp_path: Path) -> None:
    folder = Path(ok(app.export_library_csv(["devices", "catalogues"], str(tmp_path)))["folder"])
    edit_devices(folder, PART, "unit_power_w", "lots")
    preview = ok(app.preview_library_csv(str(folder)))
    problem = preview["problems"][0]
    assert (problem["table"], problem["column"]) == ("devices.csv", "unit_power_w")
    assert problem["row"] >= 2
    assert PART not in preview["changed"]


def test_accepted_rows_go_to_the_pending_set(app: api.Api, tmp_path: Path) -> None:
    folder = Path(ok(app.export_library_csv(["devices", "catalogues"], str(tmp_path)))["folder"])
    edit_devices(folder, PART, "unit_power_w", "80")
    page = ok(app.add_library_csv(str(folder / "devices.csv")))
    assert page["count"] >= 1
    assert ok(app.library_device(PART))["device"]["unit_power_w"] == 80
    applied = ok(app.apply_library_edits("csv"))
    assert applied["version"] == "1.0.0+local.1"


def test_a_csv_with_no_changes_adds_nothing(app: api.Api, tmp_path: Path) -> None:
    folder = Path(ok(app.export_library_csv(["devices", "catalogues"], str(tmp_path)))["folder"])
    assert ok(app.preview_library_csv(str(folder)))["changes"] == []
    assert ok(app.add_library_csv(str(folder)))["count"] == 0


def test_a_missing_csv_source_is_refused(app: api.Api, tmp_path: Path) -> None:
    assert refused(app.preview_library_csv(str(tmp_path / "gone.zip")))["kind"] == "not_found"
