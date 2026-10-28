"""Exporting a library as CSV tables for Excel (ADR 0018)."""

import csv
import io
import zipfile
from collections.abc import Mapping
from pathlib import Path

import pytest

from bomgen.io.loader import load_library
from bomgen.library_store.csv_export import (
    CHILD_TABLES,
    TABLES,
    export_csv,
    library_tables,
)
from bomgen.library_store.edit import Insert, apply_edits
from bomgen.models.library import DeviceType, Library

EXAMPLE_LIBRARY = Path(__file__).parents[3] / "examples" / "library.yaml"
SWITCH = "RST2228-L1-24MM"
RTAC = "SEL-3555-RTAC"
ALL_FILES = {
    "library.csv",
    "devices.csv",
    "device_ports.csv",
    "device_children.csv",
    "device_terminals.csv",
    "device_loose_items.csv",
    "mcb.csv",
    "mcb_codes.csv",
    "aux_contacts.csv",
    "terminal_blocks.csv",
    "busbars.csv",
    "housekeeping.csv",
}


@pytest.fixture(scope="module")
def library() -> Library:
    return load_library(EXAMPLE_LIBRARY)


def _rows(text: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text.decode("utf-8-sig"), newline="")))


def _read_zip(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_the_export_has_one_table_per_file(library: Library) -> None:
    assert set(TABLES) == ALL_FILES
    assert set(library_tables(library)) == ALL_FILES


def test_every_device_field_is_a_column_or_a_child_table() -> None:
    nested = {
        name
        for name, info in DeviceType.model_fields.items()
        if str(info.annotation).startswith("list[")
    }
    columns = set(TABLES["devices.csv"])

    assert nested == set(CHILD_TABLES)
    assert columns | nested == set(DeviceType.model_fields)
    assert columns.isdisjoint(nested)


def test_a_device_is_one_row_with_its_part_id_first_and_in_library_order(
    library: Library,
) -> None:
    table = library_tables(library)["devices.csv"]

    assert table[0]["part_id"] == library.devices[0].part_id
    assert [row["part_id"] for row in table] == library.part_ids()
    assert TABLES["devices.csv"][0] == "part_id"


def test_cells_are_written_the_way_excel_shows_them(library: Library) -> None:
    row = next(r for r in library_tables(library)["devices.csv"] if r["part_id"] == SWITCH)
    device = library.get(SWITCH)
    assert device is not None

    assert row["category"] == device.category.value
    assert row["alarm_on_branch_mcb"] in ("true", "false")
    assert row["excluded_from_power"] == "false"
    assert row["voltage_v"] == str(device.voltage_v)
    assert row["alt_group"] == device.alt_group
    assert row["tier"] == ""  # not given is a blank cell
    assert row["make"] == device.make


def test_nested_lists_are_child_tables_keyed_by_part_id_and_position(library: Library) -> None:
    tables = library_tables(library)
    device = library.get(SWITCH)
    assert device is not None

    ports = [r for r in tables["device_ports.csv"] if r["part_id"] == SWITCH]

    assert [r["seq"] for r in ports] == [str(i) for i in range(1, len(device.ports) + 1)]
    assert ports[0]["count"] == str(device.ports[0].count)
    assert ports[0]["speed"] == device.ports[0].speed.value
    assert set(ports[0]) == {"part_id", "seq", "count", "speed", "media", "kind", "usable_for"}


def test_child_rows_name_the_referenced_part_in_their_own_column(library: Library) -> None:
    tables = library_tables(library)

    children = [r for r in tables["device_children.csv"] if r["part_id"] == RTAC]
    loose = tables["device_loose_items.csv"]
    terminals = [r for r in tables["device_terminals.csv"] if r["part_id"] == RTAC]

    assert set(tables["device_children.csv"][0]) == {"part_id", "seq", "child_part_id", "qty"}
    assert all(r["child_part_id"] for r in children)
    assert not loose or set(loose[0]) == {"part_id", "seq", "item_part_id", "qty", "tag"}
    assert terminals[0]["block"] == "UT-2.5-MT"
    assert terminals[0]["seq"] == "1"


def test_a_core_count_quantity_is_written_as_the_word(library: Library) -> None:
    rows = library_tables(library)["device_children.csv"]

    assert any(r["qty"] == "cores" for r in rows)


def test_the_default_catalogue_is_the_brand_default(library: Library) -> None:
    tables = library_tables(library)

    mcb = tables["mcb.csv"]
    brands = [b.id for b in library.catalogue_brands.mcb]
    assert [r["catalogue_id"] for r in mcb] == ["default", *brands]
    assert mcb[0]["ratings_a"] == "|".join(str(a) for a in library.catalogues.mcb.ratings_a)
    assert mcb[0]["family"] == library.catalogues.mcb.family
    blocks = [r for r in tables["terminal_blocks.csv"] if r["catalogue_id"] == "default"]
    assert len(blocks) == len(library.catalogues.terminal_blocks)
    assert {r["role"] for r in tables["busbars.csv"]} == set(library.catalogues.busbars)
    assert tables["library.csv"][-1] == {"key": "enclosure_u", "value": "42"}


def test_housekeeping_is_a_row_per_role_with_the_fan_and_socket_figures(library: Library) -> None:
    rows = {
        r["role"]: r
        for r in library_tables(library)["housekeeping.csv"]
        if r["catalogue_id"] == "default"
    }

    assert set(rows) >= {"lamp", "fan", "vent_filter", "thermostat", "ipr_kit", "socket"}
    assert {"change_over_diode_negative", "change_over_diode_positive"} <= set(rows)
    assert rows["fan"]["airflow_m3h"] == str(library.catalogues.housekeeping.fan.airflow_m3h)
    assert rows["socket"]["rating_a"] == str(library.catalogues.housekeeping.socket.rating_a)
    assert rows["lamp"]["airflow_m3h"] == ""
    assert rows["lamp"]["part_id"] == library.catalogues.housekeeping.lamp.part_id


def test_brand_sets_are_rows_of_their_catalogue_table(library: Library) -> None:
    mcb = library.catalogues.mcb.model_dump(mode="json", exclude_none=True)
    mcb.pop("code_pattern")
    mcb["codes"] = {str(a): f"X{a}" for a in mcb["ratings_a"]}
    brand = {**mcb, "id": "abb-s200", "name": "ABB S200"}
    edited = apply_edits(library, [Insert(path=["catalogue_brands", "mcb"], value=brand)]).library
    assert edited is not None

    tables = library_tables(edited)

    shipped = [b.id for b in library.catalogue_brands.mcb]
    assert [r["catalogue_id"] for r in tables["mcb.csv"]] == ["default", *shipped, "abb-s200"]
    assert tables["mcb.csv"][-1]["name"] == "ABB S200"
    assert tables["mcb.csv"][-1]["code_pattern"] == ""
    codes = [r for r in tables["mcb_codes.csv"] if r["catalogue_id"] == "abb-s200"]
    assert {r["code"] for r in codes} == {f"X{a}" for a in mcb["ratings_a"]}


def test_a_dc_only_brand_is_marked_in_the_last_mcb_column(library: Library) -> None:
    mcb = library.catalogues.mcb.model_dump(mode="json", exclude_none=True)
    brand = {**mcb, "id": "dc-only", "ac_rated": False}
    edited = apply_edits(library, [Insert(path=["catalogue_brands", "mcb"], value=brand)]).library
    assert edited is not None

    rows = library_tables(edited)["mcb.csv"]

    assert TABLES["mcb.csv"][-1] == "ac_rated"
    by_id = {r["catalogue_id"]: r for r in rows}
    assert by_id["default"]["ac_rated"] == ""  # the default catalogue has no such flag
    assert by_id["dc-only"]["ac_rated"] == "false"
    assert {by_id[b.id]["ac_rated"] for b in library.catalogue_brands.mcb} == {"true"}


def test_the_zip_holds_every_table_as_utf8_with_a_byte_order_mark(
    tmp_path: Path, library: Library
) -> None:
    out = tmp_path / "psa-1.0.0-csv.zip"

    export_csv(library, out, name="psa", based_on="1.0.0")

    files = _read_zip(out)
    assert set(files) == ALL_FILES
    assert all(data.startswith(b"\xef\xbb\xbf") for data in files.values())
    assert all(b"\r\n" in data for data in files.values())
    assert [r["part_id"] for r in _rows(files["devices.csv"])] == library.part_ids()


def test_the_library_table_says_where_the_export_came_from(
    tmp_path: Path, library: Library
) -> None:
    out = tmp_path / "x.zip"

    export_csv(library, out, name="psa", based_on="1.0.0+local.2")

    settings = {r["key"]: r["value"] for r in _rows(_read_zip(out)["library.csv"])}
    assert settings["csv_format"] == "1"
    assert settings["library_name"] == "psa"
    assert settings["based_on_version"] == "1.0.0+local.2"
    assert settings["enclosure_u"] == "42"


def test_accents_and_arabic_text_survive_the_file(tmp_path: Path, library: Library) -> None:
    data = library.model_dump(mode="json")
    data["devices"][0]["make"] = "Société — شركة"
    edited = Library.model_validate(data)
    out = tmp_path / "x.zip"

    export_csv(edited, out, name="psa", based_on="1.0.0")

    assert _rows(_read_zip(out)["devices.csv"])[0]["make"] == "Société — شركة"


def test_commas_quotes_and_line_breaks_in_text_are_quoted(tmp_path: Path, library: Library) -> None:
    data = library.model_dump(mode="json")
    data["devices"][0]["description_template"] = 'Switch, "managed"\nsecond line'
    edited = Library.model_validate(data)
    out = tmp_path / "x.zip"

    export_csv(edited, out, name="psa", based_on="1.0.0")

    row = _rows(_read_zip(out)["devices.csv"])[0]
    assert row["description_template"] == 'Switch, "managed"\nsecond line'


def test_the_export_is_the_same_bytes_every_time(tmp_path: Path, library: Library) -> None:
    export_csv(library, tmp_path / "a.zip", name="psa", based_on="1.0.0")
    export_csv(library, tmp_path / "b.zip", name="psa", based_on="1.0.0")

    assert (tmp_path / "a.zip").read_bytes() == (tmp_path / "b.zip").read_bytes()


def test_a_folder_gets_one_file_per_table(tmp_path: Path, library: Library) -> None:
    folder = tmp_path / "csv"

    written = export_csv(library, folder, name="psa", based_on="1.0.0")

    assert {p.name for p in folder.iterdir()} == ALL_FILES
    assert sorted(written) == sorted(ALL_FILES)
    assert (folder / "devices.csv").read_bytes().startswith(b"\xef\xbb\xbf")


def test_the_person_can_choose_which_tables_to_write(tmp_path: Path, library: Library) -> None:
    folder = tmp_path / "devices-only"

    export_csv(library, folder, name="psa", based_on="1.0.0", include=("devices",))

    assert {p.name for p in folder.iterdir()} == {
        "library.csv",
        "devices.csv",
        "device_ports.csv",
        "device_children.csv",
        "device_terminals.csv",
        "device_loose_items.csv",
    }
    only_catalogues = tmp_path / "catalogues-only"
    export_csv(library, only_catalogues, name="psa", based_on="1.0.0", include=("catalogues",))
    assert "devices.csv" not in {p.name for p in only_catalogues.iterdir()}
    assert "mcb.csv" in {p.name for p in only_catalogues.iterdir()}


def test_an_unknown_table_group_is_refused(tmp_path: Path, library: Library) -> None:
    with pytest.raises(ValueError, match="unknown"):
        export_csv(library, tmp_path / "x", name="psa", based_on="1.0.0", include=("nonsense",))


def test_the_table_columns_are_exactly_the_documented_ones() -> None:
    expected: Mapping[str, tuple[str, ...]] = {
        "device_ports.csv": ("part_id", "seq", "count", "speed", "media", "kind", "usable_for"),
        "device_children.csv": ("part_id", "seq", "child_part_id", "qty"),
        "device_terminals.csv": (
            "part_id",
            "seq",
            "strip",
            "block",
            "count",
            "per",
            "first_slot",
            "description",
        ),
        "device_loose_items.csv": ("part_id", "seq", "item_part_id", "qty", "tag"),
        "mcb_codes.csv": ("catalogue_id", "rating_a", "code"),
        "aux_contacts.csv": ("catalogue_id", "name", "make", "model", "ordering_code"),
        "terminal_blocks.csv": ("catalogue_id", "name", "type", "make", "ordering_code"),
        "busbars.csv": ("catalogue_id", "name", "role", "description", "tag"),
        "housekeeping.csv": (
            "catalogue_id",
            "name",
            "role",
            "part_id",
            "airflow_m3h",
            "rating_a",
        ),
    }
    for name, columns in expected.items():
        assert tuple(TABLES[name]) == columns, name
    assert tuple(TABLES["mcb.csv"])[:5] == ("catalogue_id", "name", "family", "make", "poles")
