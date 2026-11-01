"""The Library's Catalogues tab: brand sets per catalogue, edited as pending changes (M36).

docs/ui/editing.md "Catalogues tab": one tab per brand with the default marked, rows edited
in place, Add brand and Make default; every edit is a pending entry, never a write.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import api
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

EXAMPLES = Path(__file__).parents[3] / "examples"
NAME = "psa-devices"


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


def brand(page: dict[str, Any], kind: str, brand_id: str) -> dict[str, Any]:
    return next(b for b in page["kinds"][kind] if b["id"] == brand_id)


def test_each_catalogue_lists_its_brands_with_the_default_first(app: api.Api) -> None:
    page = ok(app.library_catalogues())

    assert list(page["kinds"]) == [
        "mcb",
        "aux_contact",
        "terminal_blocks",
        "busbars",
        "housekeeping",
    ]
    mcbs = page["kinds"]["mcb"]
    assert [b["id"] for b in mcbs] == [
        "default",
        "schneider-c60h-dc",
        "abb-s200m-uc",
        "siemens-5sy5",
    ]
    assert (mcbs[0]["default"], mcbs[1]["default"]) == (True, False)
    assert mcbs[0]["label"] == "Schneider Acti9 2P"
    assert mcbs[0]["value"]["rows"][2] == {"rating_a": 6, "code": "A9F74206"}
    assert brand(page, "mcb", "schneider-c60h-dc")["ac_rated"] is False
    assert brand(page, "terminal_blocks", "wago")["label"] == "WAGO"
    assert brand(page, "terminal_blocks", "default")["value"]["rows"][0] == {
        "key": "UT-16",
        "make": "Phoenix",
        "ordering_code": "3044199",
    }
    assert brand(page, "busbars", "default")["value"]["rows"][1]["tag"] == "INSTRUMENT-GROUND"
    roles = brand(page, "housekeeping", "default")["value"]["rows"]
    assert {"role": "fan", "part_id": "SK3243-FAN"} in roles
    assert {"role": "door_switch", "part_id": None} in roles  # optional, not set
    assert "SZ2500-LAMP" in page["parts"]
    assert brand(page, "housekeeping", "default")["label"] == "Standard kit"


def test_an_mcb_code_edit_is_a_pending_change_and_keeps_the_other_codes(app: api.Api) -> None:
    value = brand(ok(app.library_catalogues()), "mcb", "default")["value"]
    value["rows"][2]["code"] = "A9F99906"

    reply = ok(app.set_library_catalogue("mcb", "default", value))
    mcb = brand(reply["catalogues"], "mcb", "default")
    assert mcb["value"]["rows"][2]["code"] == "A9F99906"
    assert mcb["value"]["rows"][3]["code"] == "A9F74210"
    assert mcb["changed"] is True
    assert reply["pending"]["count"] == 1
    assert reply["pending"]["entries"][0]["area"] == "Catalogue"


def test_setting_a_catalogue_back_to_its_saved_value_leaves_no_pending_change(
    app: api.Api,
) -> None:
    saved = brand(ok(app.library_catalogues()), "aux_contact", "abb-s2c-h6r")["value"]
    ok(app.set_library_catalogue("aux_contact", "abb-s2c-h6r", {**saved, "model": "S2C-H6R x"}))

    reply = ok(app.set_library_catalogue("aux_contact", "abb-s2c-h6r", saved))
    assert reply["pending"]["count"] == 0
    assert brand(reply["catalogues"], "aux_contact", "abb-s2c-h6r")["changed"] is False


def test_a_row_the_library_cannot_take_is_refused_with_the_reason(app: api.Api) -> None:
    value = brand(ok(app.library_catalogues()), "terminal_blocks", "default")["value"]
    value["rows"].append({"key": "UT-4", "make": "Phoenix", "ordering_code": "3044102"})

    error = refused(app.set_library_catalogue("terminal_blocks", "default", value))
    assert error["kind"] == "invalid_edit"
    assert "weidmuller" in error["message"]
    assert "UT-4" in error["message"]
    assert ok(app.library_pending())["count"] == 0


def test_add_brand_copies_the_rows_of_the_brand_it_starts_from(app: api.Api) -> None:
    reply = ok(app.add_catalogue_brand("terminal_blocks", "phoenix-pt", "Phoenix PT", "default"))

    new = brand(reply["catalogues"], "terminal_blocks", "phoenix-pt")
    assert new["label"] == "Phoenix PT"
    assert [r["key"] for r in new["value"]["rows"]] == ["UT-16", "UT-2.5-MTD", "UT-2.5-MT"]
    assert reply["pending"]["entries"][0]["area"] == "Catalogue brand"
    taken = refused(app.add_catalogue_brand("terminal_blocks", "wago", "", "default"))
    assert "wago" in taken["message"]


def test_make_default_swaps_the_brand_with_the_default_set(app: api.Api) -> None:
    reply = ok(app.make_default_brand("mcb", "abb-s200m-uc"))

    mcbs = reply["catalogues"]["kinds"]["mcb"]
    assert mcbs[0]["label"] == "ABB S200M UC 2P"
    assert mcbs[0]["value"]["rows"][0]["code"] == "2CDS272061R0014"
    assert "abb-s200m-uc" not in [b["id"] for b in mcbs]
    old = brand(reply["catalogues"], "mcb", "schneider")
    assert old["value"]["rows"][0]["code"] == "A9F74201"


def test_a_dc_only_mcb_brand_cannot_be_the_default(app: api.Api) -> None:
    error = refused(app.make_default_brand("mcb", "schneider-c60h-dc"))
    assert "DC only" in error["message"]


def test_a_housekeeping_role_points_to_another_part(app: api.Api) -> None:
    value = brand(ok(app.library_catalogues()), "housekeeping", "default")["value"]
    for row in value["rows"]:
        if row["role"] == "lamp":
            row["part_id"] = "SZ2500-LAMP.STEGO-MID"

    reply = ok(app.set_library_catalogue("housekeeping", "default", value))
    rows = brand(reply["catalogues"], "housekeeping", "default")["value"]["rows"]
    assert {"role": "lamp", "part_id": "SZ2500-LAMP.STEGO-MID"} in rows
    assert {"role": "fan", "part_id": "SK3243-FAN"} in rows  # its airflow is kept


def test_an_mcb_code_set_back_leaves_no_pending_change(app: api.Api) -> None:
    saved = brand(ok(app.library_catalogues()), "mcb", "default")["value"]
    changed = json.loads(json.dumps(saved))
    changed["rows"][0]["code"] = "X1"
    ok(app.set_library_catalogue("mcb", "default", changed))

    assert ok(app.set_library_catalogue("mcb", "default", saved))["pending"]["count"] == 0


def test_applying_a_catalogue_edit_makes_a_version_with_it(app: api.Api) -> None:
    ok(app.add_catalogue_brand("aux_contact", "phoenix", "Phoenix", "default"))

    version = ok(app.apply_library_edits("New aux brand"))["version"]
    assert version == "1.0.0+local.1"
    assert brand(ok(app.library_catalogues()), "aux_contact", "phoenix")["changed"] is False
