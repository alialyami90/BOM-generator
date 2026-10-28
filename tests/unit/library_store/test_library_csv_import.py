"""Importing a library from CSV tables: the dry-run, the rows, and the saved version (ADR 0018)."""

import csv
import io
from collections.abc import Callable
from pathlib import Path

import pytest

from bomgen.bundle.checks import Check, CheckStatus
from bomgen.io.loader import load_library
from bomgen.library_store.csv_export import CHILD_TABLES, TABLES, export_csv
from bomgen.library_store.csv_import import CsvPreview, import_csv, preview_csv_import
from bomgen.library_store.edit import Insert, Remove, SetValue, apply_edits
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.local import save_local_version
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore
from bomgen.models.library import DeviceType, Library

ROOT = Path(__file__).parents[3]
EXAMPLE_LIBRARY = ROOT / "examples" / "library.yaml"
SWITCH = "RST2228-L1-24MM"
RTAC = "SEL-3555-RTAC"
IDS = ["files", "encoding", "columns", "rows", "links", "cells", "library", "base", "changes"]

Rows = list[dict[str, str]]
Edit = Callable[[Rows], Rows]


@pytest.fixture
def store(tmp_path: Path) -> LibraryStore:
    store = LibraryStore(tmp_path / "libraries")
    package = tmp_path / "psa-1.0.0.bomlib"
    pack(EXAMPLE_LIBRARY, package, name="psa", version="1.0.0")
    store.import_package(package)
    return store


@pytest.fixture
def base(store: LibraryStore) -> Library:
    return load_library(store.library_file("psa"))


@pytest.fixture
def folder(tmp_path: Path, base: Library) -> Path:
    out = tmp_path / "csv"
    export_csv(base, out, name="psa", based_on="1.0.0")
    return out


def _device(library: Library, part_id: str) -> DeviceType:
    device = library.get(part_id)
    assert device is not None
    return device


def _read(folder: Path, file: str) -> Rows:
    return list(csv.DictReader(io.StringIO((folder / file).read_text("utf-8-sig"), newline="")))


def _write(folder: Path, file: str, rows: Rows, delimiter: str = ",") -> None:
    columns = list(TABLES[file])
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\r\n", delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    (folder / file).write_bytes(buffer.getvalue().encode("utf-8-sig"))


def _edit(folder: Path, file: str, change: Edit) -> None:
    _write(folder, file, change(_read(folder, file)))


def _preview(store: LibraryStore, source: Path, skip_invalid: bool = False) -> CsvPreview:
    return preview_csv_import(source, store, "psa", skip_invalid=skip_invalid)


def _by_id(preview: CsvPreview) -> dict[str, Check]:
    return {check.id: check for check in preview.checks}


def _set(file_rows: Rows, part_id: str, **cells: str) -> Rows:
    for row in file_rows:
        if row["part_id"] == part_id:
            row.update(cells)
    return file_rows


def test_an_untouched_export_imports_as_no_change(
    store: LibraryStore, folder: Path, base: Library
) -> None:
    preview = _preview(store, folder)

    assert [c.id for c in preview.checks] == IDS
    checks = _by_id(preview)
    assert all(checks[i].status is CheckStatus.OK for i in IDS if i != "changes"), [
        c for c in preview.checks if c.status is not CheckStatus.OK
    ]
    assert checks["changes"].status is CheckStatus.WARNING
    assert "nothing" in checks["changes"].detail.lower()
    assert preview.library == base
    assert preview.problems == []
    assert preview.edits == []
    assert preview.diff is not None
    assert preview.diff.is_empty


def test_the_round_trip_keeps_every_field_and_the_order(
    tmp_path: Path, store: LibraryStore, base: Library
) -> None:
    # A library with every kind of row: brands, codes and a rearranged device order.
    mcb = base.catalogues.mcb.model_dump(mode="json", exclude_none=True)
    mcb.pop("code_pattern")
    mcb["codes"] = {str(a): f"X{a}" for a in mcb["ratings_a"]}
    types = {k: v.model_dump(mode="json") for k, v in base.catalogues.terminal_blocks.items()}
    busbars = {k: v.model_dump(mode="json") for k, v in base.catalogues.busbars.items()}
    housekeeping = base.catalogues.housekeeping.model_dump(mode="json", exclude_none=True)
    edited = apply_edits(
        base,
        [
            Insert(
                path=["catalogue_brands", "mcb"], value={**mcb, "id": "abb-s200", "name": "ABB"}
            ),
            Insert(
                path=["catalogue_brands", "terminal_blocks"],
                value={"id": "alt-blocks", "name": "Alt", "types": types},
            ),
            Insert(
                path=["catalogue_brands", "busbars"],
                value={"id": "alt", "entries": busbars},
            ),
            Insert(
                path=["catalogue_brands", "housekeeping"],
                value={**housekeeping, "id": "alt-hk", "name": "Alt"},
            ),
            Insert(
                path=["catalogue_brands", "aux_contact"],
                value={**base.catalogues.aux_contact.model_dump(mode="json"), "id": "alt-aux"},
            ),
            SetValue(path=["devices", SWITCH, "alt_group"], value="L1-SWITCH"),
            SetValue(path=["devices", RTAC, "inrush_a"], value=12.5),
            SetValue(path=["catalogues", "enclosure_u"], value=45),
        ],
    ).library
    assert edited is not None
    data = edited.model_dump(mode="json")
    data["devices"].reverse()
    edited = Library.model_validate(data)
    out = tmp_path / "full.zip"
    export_csv(edited, out, name="psa", based_on="1.0.0")

    preview = _preview(store, out)

    assert preview.problems == []
    assert preview.library == edited
    assert preview.library is not None
    assert preview.library.part_ids() == edited.part_ids()


def test_a_zip_and_a_folder_read_the_same(
    tmp_path: Path, store: LibraryStore, folder: Path, base: Library
) -> None:
    out = tmp_path / "x.zip"
    export_csv(base, out, name="psa", based_on="1.0.0")

    assert _preview(store, out).library == _preview(store, folder).library == base


def test_a_changed_cell_is_a_changed_device(store: LibraryStore, folder: Path) -> None:
    _edit(folder, "devices.csv", lambda rows: _set(rows, SWITCH, make="Acme"))

    preview = _preview(store, folder)

    assert preview.can_import
    assert preview.diff is not None
    assert preview.diff.changed == {SWITCH: ["make"]}
    assert [(c.key, c.field, c.new) for c in preview.changes] == [(SWITCH, "make", "Acme")]
    assert preview.changes[0].old != "Acme"
    assert [type(e) for e in preview.edits] == [SetValue]
    assert preview.edits[0].path == ["devices", SWITCH]


def test_a_new_device_row_with_its_child_rows_is_added(store: LibraryStore, folder: Path) -> None:
    new = {c: "" for c in TABLES["devices.csv"]}
    new.update(part_id="NEW-1", category="component", description_template="New {lan}")
    _edit(folder, "devices.csv", lambda rows: [*rows, new])
    port = {c: "" for c in TABLES["device_ports.csv"]}
    port.update(part_id="NEW-1", seq="1", count="4", speed="1G", media="RJ45", kind="fixed")
    _edit(folder, "device_ports.csv", lambda rows: [*rows, port])

    preview = _preview(store, folder)

    assert preview.can_import
    assert preview.diff is not None
    assert preview.diff.added == ["NEW-1"]
    assert preview.library is not None
    assert _device(preview.library, "NEW-1").ports[0].count == 4
    assert [type(e) for e in preview.edits] == [Insert]


def test_a_missing_device_row_is_a_removed_device(store: LibraryStore, folder: Path) -> None:
    used = {r["child_part_id"] for r in _read(folder, "device_children.csv")}
    used |= {r["item_part_id"] for r in _read(folder, "device_loose_items.csv")}
    used |= {r["part_id"] for r in _read(folder, "housekeeping.csv")}
    unused = next(r["part_id"] for r in _read(folder, "devices.csv") if r["part_id"] not in used)
    for file in ("devices.csv", *CHILD_TABLES.values()):
        _edit(folder, file, lambda rows: [r for r in rows if r["part_id"] != unused])

    preview = _preview(store, folder)

    assert preview.can_import
    assert preview.diff is not None
    assert preview.diff.removed == [unused]
    assert Remove(path=["devices", unused]) in preview.edits


def test_removing_a_device_another_part_uses_fails_the_library_check(
    store: LibraryStore, folder: Path
) -> None:
    used = _read(folder, "device_children.csv")[0]["child_part_id"]
    _edit(folder, "devices.csv", lambda rows: [r for r in rows if r["part_id"] != used])

    preview = _preview(store, folder)

    check = _by_id(preview)["library"]
    assert check.status is CheckStatus.FAILED
    assert f"unknown part_id '{used}'" in check.detail
    assert not preview.can_import


def test_a_file_saved_by_excel_with_semicolons_and_decimal_commas_is_read(
    store: LibraryStore, folder: Path, base: Library
) -> None:
    rows = _read(folder, "devices.csv")
    powered = next(r for r in rows if r["unit_power_w"] not in ("", "0"))
    powered["unit_power_w"] = "12,5"
    _write(folder, "devices.csv", rows, delimiter=";")
    for file in ("device_ports.csv", "device_children.csv", "mcb.csv"):
        _write(folder, file, _read(folder, file), delimiter=";")

    preview = _preview(store, folder)

    assert preview.problems == []
    assert preview.library is not None
    assert _device(preview.library, powered["part_id"]).unit_power_w == 12.5


def test_text_that_is_not_utf8_is_refused_with_the_remedy(
    store: LibraryStore, folder: Path
) -> None:
    text = (folder / "devices.csv").read_text("utf-8-sig").replace("Hubbell", "Hübbell")
    (folder / "devices.csv").write_bytes(text.encode("cp1252"))

    preview = _preview(store, folder)

    check = _by_id(preview)["encoding"]
    assert check.status is CheckStatus.FAILED
    assert "devices.csv" in check.detail
    assert "CSV UTF-8" in check.detail
    assert [c.status for c in preview.checks if c.id == "columns"] == [CheckStatus.SKIPPED]
    assert preview.library is None


def test_a_missing_required_column_fails_the_columns_check(
    store: LibraryStore, folder: Path
) -> None:
    text = (folder / "devices.csv").read_text("utf-8-sig")
    (folder / "devices.csv").write_text(text.replace("category", "kategorie", 1), "utf-8-sig")

    check = _by_id(_preview(store, folder))["columns"]

    assert check.status is CheckStatus.FAILED
    assert "devices.csv" in check.detail
    assert "category" in check.detail


def test_an_unknown_column_is_ignored_with_a_warning(
    store: LibraryStore, folder: Path, base: Library
) -> None:
    text = (folder / "devices.csv").read_text("utf-8-sig")
    lines = text.splitlines()
    lines = [lines[0] + ",notes", *(line + ",remember" for line in lines[1:])]
    (folder / "devices.csv").write_text("\r\n".join(lines) + "\r\n", "utf-8-sig")

    preview = _preview(store, folder)

    check = _by_id(preview)["columns"]
    assert check.status is CheckStatus.WARNING
    assert "notes" in check.detail
    assert preview.library == base


def test_a_column_the_file_lacks_keeps_the_values_the_library_has(
    store: LibraryStore, folder: Path, base: Library
) -> None:
    data = base.model_dump(mode="json")
    data["devices"][0]["inrush_a"] = 9.5
    save_local_version(store, "psa", Library.model_validate(data))
    columns = [c for c in TABLES["devices.csv"] if c != "inrush_a"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=columns, lineterminator="\r\n", extrasaction="ignore"
    )
    writer.writeheader()
    writer.writerows(_read(folder, "devices.csv"))
    (folder / "devices.csv").write_bytes(buffer.getvalue().encode("utf-8-sig"))

    preview = _preview(store, folder)

    check = _by_id(preview)["columns"]
    assert check.status is CheckStatus.WARNING
    assert "inrush_a" in check.detail
    assert preview.library is not None
    assert preview.library.devices[0].inrush_a == 9.5


def test_a_table_the_file_lacks_is_left_as_it_is(
    tmp_path: Path, store: LibraryStore, base: Library
) -> None:
    only_devices = tmp_path / "devices-only"
    export_csv(base, only_devices, name="psa", based_on="1.0.0", include=("devices",))
    only_catalogues = tmp_path / "catalogues-only"
    export_csv(base, only_catalogues, name="psa", based_on="1.0.0", include=("catalogues",))

    assert _preview(store, only_devices).library == base
    assert _preview(store, only_catalogues).library == base


def test_a_row_with_a_bad_cell_is_a_problem_with_table_row_and_column(
    store: LibraryStore, folder: Path
) -> None:
    rows = _read(folder, "devices.csv")
    target = rows[2]["part_id"]
    _edit(folder, "devices.csv", lambda rows: _set(rows, target, voltage_v="abc"))

    preview = _preview(store, folder)

    assert [(p.table, p.row, p.column) for p in preview.problems] == [
        ("devices.csv", 4, "voltage_v")
    ]
    assert "voltage_v" in preview.problems[0].message or "integer" in preview.problems[0].message
    assert preview.problems[0].key == target
    assert _by_id(preview)["rows"].status is CheckStatus.FAILED
    assert not preview.can_import


def test_skipping_invalid_rows_imports_the_rest_and_keeps_the_old_device(
    store: LibraryStore, folder: Path
) -> None:
    rows = _read(folder, "devices.csv")
    bad, good = rows[2]["part_id"], rows[3]["part_id"]
    _edit(folder, "devices.csv", lambda r: _set(_set(r, bad, voltage_v="abc"), good, make="Acme"))

    preview = _preview(store, folder, True)

    assert preview.can_import
    assert _by_id(preview)["rows"].status is CheckStatus.WARNING
    assert preview.diff is not None
    assert preview.diff.changed == {good: ["make"]}
    assert len(preview.problems) == 1


def test_a_child_row_problem_is_reported_on_the_child_table(
    store: LibraryStore, folder: Path
) -> None:
    rows = _read(folder, "device_ports.csv")
    first = rows[0]
    _edit(folder, "device_ports.csv", lambda r: [{**r[0], "count": "0"}, *r[1:]])

    preview = _preview(store, folder)

    assert [(p.table, p.row, p.column) for p in preview.problems] == [
        ("device_ports.csv", 2, "count")
    ]
    assert preview.problems[0].key == first["part_id"]


def test_two_rows_for_one_part_fail_the_links_check(store: LibraryStore, folder: Path) -> None:
    _edit(folder, "devices.csv", lambda rows: [*rows, dict(rows[0])])

    check = _by_id(_preview(store, folder))["links"]

    assert check.status is CheckStatus.FAILED
    assert "duplicate part_id" in check.detail


def test_child_rows_for_a_part_without_a_device_row_fail_the_links_check(
    store: LibraryStore, folder: Path
) -> None:
    ghost = {**_read(folder, "device_ports.csv")[0], "part_id": "GHOST"}
    _edit(folder, "device_ports.csv", lambda rows: [*rows, ghost])

    check = _by_id(_preview(store, folder))["links"]

    assert check.status is CheckStatus.FAILED
    assert "GHOST" in check.detail


def test_a_position_used_twice_or_not_a_number_fails_the_links_check(
    store: LibraryStore, folder: Path
) -> None:
    rows = _read(folder, "device_children.csv")
    dup = {**rows[0]}
    _edit(folder, "device_children.csv", lambda r: [*r, dup])

    assert _by_id(_preview(store, folder))["links"].status is CheckStatus.FAILED

    _edit(folder, "device_children.csv", lambda r: [{**r[0], "seq": "x"}, *r[1:]])
    assert _by_id(_preview(store, folder))["links"].status is CheckStatus.FAILED


def test_children_are_ordered_by_their_position_not_their_row(
    store: LibraryStore, folder: Path, base: Library
) -> None:
    rows = _read(folder, "device_children.csv")
    part = next(p for p in {r["part_id"] for r in rows} if sum(r["part_id"] == p for r in rows) > 1)
    mine = [r for r in rows if r["part_id"] == part]
    others = [r for r in rows if r["part_id"] != part]
    _edit(folder, "device_children.csv", lambda _: [*reversed(mine), *others])

    preview = _preview(store, folder)

    assert preview.library == base


def test_text_that_excel_may_have_changed_is_a_warning(store: LibraryStore, folder: Path) -> None:
    target = _read(folder, "devices.csv")[0]["part_id"]
    _edit(
        folder,
        "devices.csv",
        lambda rows: _set(rows, target, ordering_code="1.5E+03", model="2-Jan"),
    )

    preview = _preview(store, folder)

    check = _by_id(preview)["cells"]
    assert check.status is CheckStatus.WARNING
    assert "1.5E+03" in check.detail
    assert "2-Jan" in check.detail
    assert preview.can_import


def test_text_starting_like_a_formula_is_a_warning(store: LibraryStore, folder: Path) -> None:
    target = _read(folder, "devices.csv")[0]["part_id"]
    _edit(folder, "devices.csv", lambda rows: _set(rows, target, make="=SUM(A1)"))

    assert _by_id(_preview(store, folder))["cells"].status is CheckStatus.WARNING


@pytest.mark.parametrize("cell", ["=B2*2", "+A1", "-A1", "@SUM(B2)"])
def test_a_bad_cell_starting_like_a_formula_is_named_as_probably_an_excel_formula(
    store: LibraryStore, folder: Path, cell: str
) -> None:
    target = _read(folder, "devices.csv")[0]["part_id"]
    _edit(folder, "devices.csv", lambda rows: _set(rows, target, voltage_v=cell))

    problems = _preview(store, folder).problems

    assert [p.column for p in problems] == ["voltage_v"]
    assert problems[0].message.endswith("(probably an Excel formula)")


def test_a_bad_cell_that_is_not_a_formula_gets_no_formula_hint(
    store: LibraryStore, folder: Path
) -> None:
    target = _read(folder, "devices.csv")[0]["part_id"]
    _edit(folder, "devices.csv", lambda rows: _set(rows, target, voltage_v="abc"))

    assert "formula" not in _preview(store, folder).problems[0].message


def test_booleans_are_read_in_any_case(store: LibraryStore, folder: Path) -> None:
    _edit(folder, "devices.csv", lambda rows: _set(rows, SWITCH, alarm_on_branch_mcb="TRUE"))

    preview = _preview(store, folder)

    assert preview.problems == []
    assert preview.library is not None
    assert _device(preview.library, SWITCH).alarm_on_branch_mcb is True


def test_blank_rows_are_ignored(store: LibraryStore, folder: Path, base: Library) -> None:
    blank = {c: "" for c in TABLES["devices.csv"]}
    _edit(folder, "devices.csv", lambda rows: [blank, *rows, blank])

    assert _preview(store, folder).library == base


def test_a_newer_csv_format_is_refused(store: LibraryStore, folder: Path) -> None:
    rows = [{"key": "csv_format", "value": "2"}, {"key": "enclosure_u", "value": "42"}]
    _write(folder, "library.csv", rows)

    check = _by_id(_preview(store, folder))["files"]

    assert check.status is CheckStatus.FAILED
    assert "format" in check.detail


def test_an_export_of_another_version_warns_on_the_base_check(
    store: LibraryStore, folder: Path
) -> None:
    _write(
        folder,
        "library.csv",
        [
            {"key": "csv_format", "value": "1"},
            {"key": "library_name", "value": "psa"},
            {"key": "based_on_version", "value": "0.9.0"},
            {"key": "enclosure_u", "value": "42"},
        ],
    )

    check = _by_id(_preview(store, folder))["base"]

    assert check.status is CheckStatus.WARNING
    assert "0.9.0" in check.detail
    assert "1.0.0" in check.detail


def test_a_folder_without_tables_or_a_missing_path_fails_the_files_check(
    tmp_path: Path, store: LibraryStore
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    assert _by_id(_preview(store, empty))["files"].status is CheckStatus.FAILED
    assert _by_id(_preview(store, tmp_path / "nothing"))["files"].status is CheckStatus.FAILED
    notzip = tmp_path / "x.zip"
    notzip.write_text("not a zip")
    assert _by_id(_preview(store, notzip))["files"].status is CheckStatus.FAILED


def test_child_tables_without_the_device_table_fail_the_files_check(
    tmp_path: Path, store: LibraryStore, folder: Path
) -> None:
    (folder / "devices.csv").unlink()

    check = _by_id(_preview(store, folder))["files"]

    assert check.status is CheckStatus.FAILED
    assert "devices.csv" in check.detail


def test_a_failed_check_skips_the_rest_and_gives_no_library(
    store: LibraryStore, tmp_path: Path
) -> None:
    preview = _preview(store, tmp_path / "nothing")

    assert [c.status for c in preview.checks[1:]] == [CheckStatus.SKIPPED] * (len(IDS) - 1)
    assert preview.library is None
    assert preview.diff is None
    assert preview.edits == []


def test_the_preview_writes_nothing(store: LibraryStore, folder: Path) -> None:
    _edit(folder, "devices.csv", lambda rows: _set(rows, SWITCH, make="Acme"))

    _preview(store, folder)

    assert store.versions("psa") == ["1.0.0"]


def test_importing_saves_the_rows_as_the_next_local_version(
    store: LibraryStore, folder: Path
) -> None:
    _edit(folder, "devices.csv", lambda rows: _set(rows, SWITCH, make="Acme"))

    saved = import_csv(folder, store, "psa", note="from Excel")

    assert saved.manifest.version == "1.0.0+local.1"
    assert store.active_version("psa") == "1.0.0+local.1"
    assert _device(load_library(store.library_file("psa")), SWITCH).make == "Acme"
    assert "from Excel" in saved.manifest.release_notes


def test_importing_a_file_with_row_problems_is_refused_unless_they_are_skipped(
    store: LibraryStore, folder: Path
) -> None:
    rows = _read(folder, "devices.csv")
    bad, good = rows[2]["part_id"], rows[3]["part_id"]
    _edit(folder, "devices.csv", lambda r: _set(_set(r, bad, voltage_v="abc"), good, make="Acme"))

    with pytest.raises(LibraryPackageError) as caught:
        import_csv(folder, store, "psa")

    assert caught.value.kind is RefusalKind.VALIDATION_FAILED
    assert "devices.csv" in str(caught.value)
    assert "voltage_v" in str(caught.value)
    assert store.versions("psa") == ["1.0.0"]

    saved = import_csv(folder, store, "psa", skip_invalid=True)
    assert saved.diff.changed == {good: ["make"]}


def test_importing_without_a_change_is_refused(store: LibraryStore, folder: Path) -> None:
    with pytest.raises(LibraryPackageError) as caught:
        import_csv(folder, store, "psa")

    assert caught.value.kind is RefusalKind.NO_CHANGES


def test_the_export_and_import_of_an_edited_version_continue_from_it(
    tmp_path: Path, store: LibraryStore, folder: Path
) -> None:
    _edit(folder, "devices.csv", lambda rows: _set(rows, SWITCH, make="One"))
    import_csv(folder, store, "psa")
    out = tmp_path / "second"
    export_csv(load_library(store.library_file("psa")), out, name="psa", based_on="1.0.0+local.1")
    _edit(out, "devices.csv", lambda rows: _set(rows, SWITCH, make="Two"))

    preview = _preview(store, out)

    assert _by_id(preview)["base"].status is CheckStatus.OK
    assert preview.diff is not None
    assert preview.diff.changed == {SWITCH: ["make"]}


def test_a_device_with_every_field_set_survives_the_round_trip(
    tmp_path: Path, store: LibraryStore, base: Library
) -> None:
    full = {
        "part_id": "FULL-1",
        "category": "rtac",
        "make": "Acme",
        "model": "M-1",
        "ordering_code": "0123-A",
        "description_template": 'Full, with "quotes" for {lan}',
        "tag_type": "RTAC",
        "purdue_level": "L2",
        "tag_pattern": "{prefix}-{type}{nn}",
        "supply_type": "VDC",
        "voltage_v": 125,
        "unit_power_w": 22.5,
        "load_type": "CONTINUOUS",
        "power_supplies": 2,
        "min_branch_mcb_a": 6,
        "alarm_on_branch_mcb": True,
        "hwio_points": 8,
        "di_inputs": 4,
        "ports": [
            {"count": 4, "speed": "1G", "media": "RJ45", "kind": "fixed", "usable_for": "ied"},
            {"count": 2, "speed": "10G", "kind": "sfp_slot", "usable_for": "uplink"},
        ],
        "cores": 12,
        "height_u": 2,
        "children": [
            {"part_id": "FOPP-SPOOL", "qty": "cores"},
            {"part_id": "FOPP-96SM", "qty": 3},
        ],
        "terminals": [
            {
                "strip": "X{slot}",
                "block": "UT-2.5-MT",
                "count": 6,
                "per": "serial_port",
                "first_slot": "A",
                "description": "Strip {slot}",
            }
        ],
        "loose_items": [
            {"part_id": "FOPP-SPOOL", "qty": "1 Lot", "tag": "LOOSE-1"},
            {"part_id": "FOPP-96SM", "qty": 2},
        ],
        "excluded_from_power": False,
        "alt_group": "RTAC-LIST",
        "tier": "mid",
        "inrush_a": 30.5,
        "inrush_ms": 12.0,
    }
    edited = apply_edits(base, [Insert(path=["devices"], value=full)]).library
    assert edited is not None
    out = tmp_path / "full.zip"
    export_csv(edited, out, name="psa", based_on="1.0.0")

    preview = _preview(store, out)

    assert preview.problems == []
    assert preview.library == edited
    assert preview.library.get("FULL-1") == edited.get("FULL-1")
