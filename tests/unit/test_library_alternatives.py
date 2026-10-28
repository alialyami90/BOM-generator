"""Alternatives as parts, catalogue brands and the MCB sizing fields (ADR 0017)."""

import copy
from typing import Any

import pytest
from pydantic import ValidationError
from test_library_model import minimal_library_dict, switch_dict

from bomgen.models.library import (
    DEFAULT_BRAND,
    CatalogueChoice,
    DeviceType,
    Library,
    McbBrand,
    McbCatalogue,
    resolve_catalogues,
)

ABB_MCB = {
    "id": "abb-s200m",
    "family": "S200M 2P",
    "make": "ABB",
    "ratings_a": [1, 2, 6, 10, 16],
    "code_pattern": "2CDS272{rating:03d}R0014",
    "trip_curve": "C",
    "magnetic_trip_multiple": 5,
}


def library_with_brands() -> dict[str, Any]:
    data = minimal_library_dict()
    data["catalogue_brands"] = {
        "mcb": [dict(ABB_MCB)],
        "aux_contact": [{"id": "abb", "make": "ABB", "model": "S2C-H6R", "ordering_code": "X1"}],
        "terminal_blocks": [
            {
                "id": "weidmuller",
                "name": "Weidmüller",
                "types": {"UT-16": {"make": "W", "ordering_code": "1"}},
            }
        ],
        "busbars": [
            {"id": "copper", "name": "Copper", "entries": {"PE": {"description": "Cu PE"}}}
        ],
        "housekeeping": [
            {"id": "rittal", "name": "Rittal", **copy.deepcopy(data["catalogues"]["housekeeping"])}
        ],
    }
    return data


def test_alternative_group_and_tier_are_device_fields() -> None:
    d = DeviceType.model_validate({**switch_dict(), "alt_group": "L1-SWITCH-24P", "tier": "mid"})
    assert (d.alt_group, d.tier) == ("L1-SWITCH-24P", "mid")
    plain = DeviceType.model_validate(switch_dict())
    assert (plain.alt_group, plain.tier, plain.inrush_a) == (None, None, None)


@pytest.mark.parametrize("bad", ["l1-switch", "L1 SWITCH", "-L1", ""])
def test_alternative_group_key_is_upper_case_with_dashes(bad: str) -> None:
    with pytest.raises(ValidationError, match="alt_group"):
        DeviceType.model_validate({**switch_dict(), "alt_group": bad})


def test_inrush_current_is_positive() -> None:
    assert DeviceType.model_validate({**switch_dict(), "inrush_a": 12.5}).inrush_a == 12.5
    with pytest.raises(ValidationError, match="inrush_a"):
        DeviceType.model_validate({**switch_dict(), "inrush_a": 0})


def test_library_lists_a_devices_alternatives_in_file_order() -> None:
    data = minimal_library_dict()
    first = {**switch_dict(), "alt_group": "L1-SWITCH-24P", "tier": "high"}
    second = {**switch_dict(), "part_id": "PT-7528", "alt_group": "L1-SWITCH-24P", "tier": "low"}
    data["devices"] = [first, data["devices"][1], second]
    library = Library.model_validate(data)
    assert [d.part_id for d in library.alternatives("RST2228-L1-24MM")] == ["PT-7528"]
    assert library.alternatives("LAMP-1") == []
    assert [d.part_id for d in library.alt_group("L1-SWITCH-24P")] == ["RST2228-L1-24MM", "PT-7528"]


def test_an_alternative_group_shares_one_category() -> None:
    data = minimal_library_dict()
    for device in data["devices"]:
        device["alt_group"] = "MIXED"
    with pytest.raises(ValidationError, match="alt group 'MIXED' mixes categories"):
        Library.model_validate(data)


def mcb(**overrides: Any) -> McbCatalogue:
    return McbCatalogue.model_validate({k: v for k, v in ABB_MCB.items() if k != "id"} | overrides)


def test_mcb_trip_curve_and_magnetic_multiple() -> None:
    assert (mcb().trip_curve, mcb(magnetic_trip_multiple=7.5).magnetic_trip_multiple) == ("C", 7.5)
    with pytest.raises(ValidationError, match="a C curve trips magnetically at 5 to 10"):
        mcb(magnetic_trip_multiple=12)
    with pytest.raises(ValidationError, match="trip_curve"):
        mcb(trip_curve="X")


def test_magnetic_multiple_falls_back_to_the_curves_lower_bound() -> None:
    assert mcb(magnetic_trip_multiple=None).magnetic_multiple == 5
    assert mcb(trip_curve="D", magnetic_trip_multiple=None).magnetic_multiple == 10
    assert mcb(trip_curve=None, magnetic_trip_multiple=None).magnetic_multiple is None


def test_dc_magnetic_multiple_is_outside_the_ac_band_but_not_below_it() -> None:
    assert mcb(magnetic_trip_multiple_dc=14).magnetic_trip_multiple_dc == 14
    with pytest.raises(ValidationError, match="must not be below magnetic_trip_multiple"):
        mcb(magnetic_trip_multiple_dc=4)


def test_mcb_dc_rating_and_inrush_duration() -> None:
    assert mcb(dc_rating_v=125).dc_rating_v == 125
    assert DeviceType.model_validate({**switch_dict(), "inrush_ms": 2}).inrush_ms == 2
    with pytest.raises(ValidationError, match="dc_rating_v"):
        mcb(dc_rating_v=0)


def test_mcb_codes_map_replaces_the_pattern() -> None:
    codes = {1: "A1", 2: "A2", 6: "A6", 10: "A10", 16: "A16"}
    assert mcb(code_pattern=None, codes=codes).code_for(6) == "A6"
    with pytest.raises(ValidationError, match="exactly one of code_pattern and codes"):
        mcb(codes=codes)
    with pytest.raises(ValidationError, match="exactly one of code_pattern and codes"):
        mcb(code_pattern=None)
    with pytest.raises(ValidationError, match="exactly the ratings in ratings_a"):
        mcb(code_pattern=None, codes={1: "A1"})


def test_brands_need_unique_ids_other_than_default() -> None:
    data = library_with_brands()
    data["catalogue_brands"]["mcb"].append(dict(ABB_MCB))
    with pytest.raises(ValidationError, match="duplicate mcb brand id 'abb-s200m'"):
        Library.model_validate(data)
    data = library_with_brands()
    data["catalogue_brands"]["mcb"][0]["id"] = DEFAULT_BRAND
    with pytest.raises(ValidationError, match="'default' names the catalogues entry"):
        Library.model_validate(data)


@pytest.mark.parametrize(
    ("kind", "field", "message"),
    [
        ("terminal_blocks", "types", "terminal_blocks brand 'weidmuller' lacks UT-16"),
        ("busbars", "entries", "busbars brand 'copper' lacks PE"),
    ],
)
def test_keyed_brands_cover_every_default_key(kind: str, field: str, message: str) -> None:
    data = library_with_brands()
    data["catalogue_brands"][kind][0][field] = {
        "OTHER": data["catalogue_brands"][kind][0][field].popitem()[1]
    }
    with pytest.raises(ValidationError, match=message):
        Library.model_validate(data)


def test_no_choice_keeps_the_default_catalogues() -> None:
    library = Library.model_validate(library_with_brands())
    assert resolve_catalogues(library, CatalogueChoice()) is library
    assert resolve_catalogues(library, CatalogueChoice(mcb=DEFAULT_BRAND)) is library


def test_a_choice_swaps_in_the_chosen_brand() -> None:
    library = Library.model_validate(library_with_brands())
    choice = CatalogueChoice(mcb="abb-s200m", terminal_blocks="weidmuller", housekeeping="rittal")
    resolved = resolve_catalogues(library, choice)
    assert resolved.catalogues.mcb.make == "ABB"
    assert resolved.catalogues.mcb.code_for(6) == "2CDS272006R0014"
    assert not isinstance(resolved.catalogues.mcb, McbBrand)  # engines see a plain catalogue
    assert resolved.catalogues.terminal_blocks["UT-16"].make == "W"
    assert resolved.catalogues.aux_contact == library.catalogues.aux_contact
    assert resolved.catalogues.busbars == library.catalogues.busbars
    assert resolved.devices == library.devices


def test_an_unknown_choice_names_the_brands() -> None:
    library = Library.model_validate(library_with_brands())
    message = r"no mcb brand 'siemens' \(the library has: default, abb-s200m\)"
    with pytest.raises(ValueError, match=message):
        resolve_catalogues(library, CatalogueChoice(mcb="siemens"))


def test_input_voltage_range_is_optional_and_ordered() -> None:
    d = DeviceType.model_validate({**switch_dict(), "input_v_min": 12, "input_v_max": 125})
    assert (d.input_v_min, d.input_v_max) == (12, 125)
    with pytest.raises(ValidationError, match="input_v_min must not be above input_v_max"):
        DeviceType.model_validate({**switch_dict(), "input_v_min": 150, "input_v_max": 125})


def test_mcb_brands_are_ac_rated_by_default() -> None:
    library = Library.model_validate(library_with_brands())
    assert library.catalogue_brands.mcb[0].ac_rated is True
    dc_only = McbBrand.model_validate({**ABB_MCB, "id": "dc-only", "ac_rated": False})
    assert dc_only.ac_rated is False


def test_a_dc_only_choice_still_resolves_to_a_plain_catalogue() -> None:
    data = library_with_brands()
    data["catalogue_brands"]["mcb"][0]["ac_rated"] = False
    library = Library.model_validate(data)
    resolved = resolve_catalogues(library, CatalogueChoice(mcb="abb-s200m"))
    assert type(resolved.catalogues.mcb) is McbCatalogue


DC_MCB = {
    "id": "c60h-dc",
    "family": "C60H-DC 2P",
    "make": "Schneider",
    "ratings_a": [1, 2, 6, 10, 16],
    "code_pattern": "A9N615{rating:02d}",
    "dc_rating_v": 440,
}


def library_with_a_dc_brand() -> Library:
    data = library_with_brands()
    data["catalogue_brands"]["mcb"].append(dict(DC_MCB))
    return Library.model_validate(data)


def test_without_a_dc_choice_the_dc_set_is_the_mcb_set() -> None:
    library = library_with_a_dc_brand()
    assert library.catalogues.dc_mcb is library.catalogues.mcb
    resolved = resolve_catalogues(library, CatalogueChoice(mcb="abb-s200m"))
    assert resolved.catalogues.dc_mcb.make == "ABB"


def test_mcb_dc_picks_the_dc_set_and_mcb_keeps_the_ac_set() -> None:
    library = library_with_a_dc_brand()
    resolved = resolve_catalogues(library, CatalogueChoice(mcb="abb-s200m", mcb_dc="c60h-dc"))
    assert resolved.catalogues.mcb.make == "ABB"
    assert resolved.catalogues.dc_mcb.family == "C60H-DC 2P"
    assert type(resolved.catalogues.dc_mcb) is McbCatalogue


def test_mcb_dc_default_keeps_the_default_set_for_dc_when_mcb_is_a_brand() -> None:
    library = library_with_a_dc_brand()
    resolved = resolve_catalogues(library, CatalogueChoice(mcb="abb-s200m", mcb_dc=DEFAULT_BRAND))
    assert resolved.catalogues.mcb.make == "ABB"
    assert resolved.catalogues.dc_mcb == library.catalogues.mcb


def test_mcb_dc_default_with_no_other_choice_keeps_the_library() -> None:
    library = library_with_a_dc_brand()
    assert resolve_catalogues(library, CatalogueChoice(mcb_dc=DEFAULT_BRAND)) is library


def test_mcb_dc_names_an_mcb_brand() -> None:
    library = library_with_a_dc_brand()
    assert library.brand_ids("mcb_dc") == library.brand_ids("mcb")
    message = r"no mcb_dc brand 'siemens' \(the library has: default, abb-s200m, c60h-dc\)"
    with pytest.raises(ValueError, match=message):
        resolve_catalogues(library, CatalogueChoice(mcb_dc="siemens"))


def test_a_library_may_give_its_own_default_dc_set() -> None:
    data = library_with_brands()
    data["catalogues"]["mcb_dc"] = {k: v for k, v in DC_MCB.items() if k != "id"}
    library = Library.model_validate(data)
    assert library.catalogues.dc_mcb.family == "C60H-DC 2P"
    assert library.catalogues.mcb.family != "C60H-DC 2P"


def test_the_librarys_default_dc_set_needs_a_dc_rating() -> None:
    data = library_with_brands()
    data["catalogues"]["mcb_dc"] = {k: v for k, v in ABB_MCB.items() if k != "id"}
    with pytest.raises(ValidationError, match=r"catalogues\.mcb_dc needs dc_rating_v"):
        Library.model_validate(data)
