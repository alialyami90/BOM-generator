"""Project model: project info, library, document register, defaults; shared settings models."""

import re
from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.models.library import LooseItem
from bomgen.models.project import (
    ConstantOverrides,
    DesignConstants,
    LibrarySelection,
    LooseExtra,
    OutputSettings,
    Project,
    SheetNames,
    Spares,
    merge_defaults,
)


def project_dict() -> dict[str, Any]:
    """The design's project file (section 2), with one substation."""
    return {
        "project": {"id": "jfgp2", "name": "JAFURAH JFGP2", "client": "Aramco"},
        "library": {"name": "psa-devices", "version": "1.0.0"},
        "documents": [
            {
                "key": "s1-bom",
                "substation": "s1",
                "doc_no": "DOC-1",
                "rev": "02",
                "issue_date": "2026-10-28",
            },
            {
                "key": "s1-power",
                "substation": "s1",
                "doc_no": "DOC-2",
                "rev": 0,
                "issue_date": "2026-10-28",
            },
        ],
        "substations": ["substations/s1/substation.yaml"],
    }


def test_project_from_design_example_validates() -> None:
    project = Project.model_validate(project_dict())
    assert project.project.id == "jfgp2"
    assert project.library.file is None
    assert [entry.key for entry in project.documents] == ["s1-bom", "s1-power"]
    assert project.documents[1].rev == "0"
    assert project.defaults.constants == DesignConstants()
    assert project.defaults.spares == Spares()


def test_register_keys_must_be_unique() -> None:
    data = project_dict()
    data["documents"][1]["key"] = "s1-bom"
    with pytest.raises(ValidationError, match="duplicate document key 's1-bom'"):
        Project.model_validate(data)


@pytest.mark.parametrize("good", ["1.0.0", "12.3.40", "1.4.0+local.1", "1.4.0+local.12"])
def test_library_version_must_be_semver(good: str) -> None:
    assert LibrarySelection(name="lib", version=good).version == good
    for bad in ["one", "1.0", "01.0.0", "1.0.0+local.0", "1.0.0+local", "1.0.0+x.1"]:
        with pytest.raises(ValidationError, match="version"):
            LibrarySelection(name="lib", version=bad)


def test_spares_defaults_are_design_values() -> None:
    spares = Spares()
    assert spares.port_fraction == 0.20
    assert spares.sfp_per_l1 == 3
    assert spares.dc_branches_per_feed == 3
    assert spares.ac_branches == 1
    assert spares.rack_u_reserved == 10


@pytest.mark.parametrize("bad", [1, 1.5, -0.1])
def test_port_fraction_must_be_below_one(bad: float) -> None:
    with pytest.raises(ValidationError, match="port_fraction"):
        Spares(port_fraction=bad)


def test_merge_defaults_overrides_only_written_keys() -> None:
    base = DesignConstants(t_max_c=40)
    merged = merge_defaults(base, ConstantOverrides(dc_voltage_v=110))
    assert (merged.dc_voltage_v, merged.t_max_c) == (110, 40)
    assert merge_defaults(base, None) == base


def test_constant_overrides_are_checked_after_the_merge() -> None:
    assert merge_defaults(DesignConstants(t_max_c=45), ConstantOverrides(t_int_c=40)).t_int_c == 40
    with pytest.raises(ValidationError, match="t_max_c must be greater than t_int_c"):
        merge_defaults(DesignConstants(), ConstantOverrides(t_int_c=40))


def test_project_lists_substations_but_a_new_one_may_have_none() -> None:
    data = project_dict()
    data["substations"] = []
    assert Project.model_validate(data).substations == []  # ADR 0021 (M17d)
    del data["substations"]
    with pytest.raises(ValidationError, match="substations"):
        Project.model_validate(data)


def test_project_rejects_unknown_key() -> None:
    data = project_dict()
    data["panels"] = ["panels/p1.yaml"]
    with pytest.raises(ValidationError, match="panels"):
        Project.model_validate(data)


def test_design_constants_default_to_spec_values() -> None:
    constants = DesignConstants()
    assert constants.dc_voltage_v == 125
    assert constants.ac_voltage_v == 230
    assert constants.power_margin == 0.25
    assert constants.current_factor == 1.3
    assert constants.btu_per_w == 3.41
    assert constants.t_max_c == 35
    assert constants.t_int_c == 25
    assert constants.air_constant_m3k_per_wh == 4.1
    assert constants.steel_coefficient_w_per_m2c == 5.5
    assert constants.min_main_mcb_a == 6


def test_t_max_must_exceed_t_int() -> None:
    with pytest.raises(ValidationError, match="t_max_c"):
        DesignConstants(t_max_c=25, t_int_c=25)
    with pytest.raises(ValidationError, match="t_max_c"):
        DesignConstants(t_max_c=20, t_int_c=25)


def test_design_constants_reject_non_positive_voltage() -> None:
    with pytest.raises(ValidationError):
        DesignConstants(dc_voltage_v=0)


def test_default_file_name_pattern() -> None:
    assert OutputSettings().resolve_file_name("DOC-1", "0") == "DOC-1_PSA_BOM_Rev0.xlsx"


@pytest.mark.parametrize(
    "name",
    ["{project}.xlsx", "a/b_{rev}.xlsx", "x.xls", "a:b.xlsx", "a?{doc_no}.xlsx", "{rev"],
)
def test_file_name_rejects_unknown_placeholder_and_bad_characters(name: str) -> None:
    with pytest.raises(ValidationError):
        OutputSettings(file_name=name)


@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("{doc_no.x}.xlsx", "doc_no.x"),
        ("{doc_no[0]}.xlsx", "doc_no[0]"),
        ("{doc_no!r}.xlsx", "doc_no"),
        ("{doc_no!z}.xlsx", "doc_no"),
        ("{doc_no:/<5}.xlsx", "doc_no"),
        ("{doc_no}_{rev:>3}.xlsx", "rev"),
    ],
)
def test_file_name_rejects_attribute_index_conversion_and_format_spec(
    name: str, field: str
) -> None:
    with pytest.raises(ValidationError, match=f"'{re.escape(field)}'"):
        OutputSettings(file_name=name)


def test_file_name_accepts_custom_template() -> None:
    settings = OutputSettings(file_name="BOM_{doc_no}_{rev}.xlsx")
    assert settings.resolve_file_name("D1", "B") == "BOM_D1_B.xlsx"


def test_default_calc_sheet_names() -> None:
    names = SheetNames()
    assert names.power_consumption == "Power Consumption"
    assert names.heat_dissipation == "Heat Dissipation"
    assert names.heat_calculations == "Heat Calculations"


def test_loose_material_sheet_name_defaults_and_is_configurable() -> None:
    # ADR 0020 (Q36): loose material has its own sheet, named like the calculation sheets.
    assert SheetNames().loose_material == "Loose Material"
    assert SheetNames(loose_material="Loose").loose_material == "Loose"
    with pytest.raises(ValidationError):
        SheetNames(loose_material="a/b")


def test_sheet_names_follow_excel_rules() -> None:
    with pytest.raises(ValidationError):
        SheetNames(power_consumption="a/b")


def test_loose_extra_accepts_one_lot() -> None:
    assert LooseExtra(part_id="CABLE-1", qty="1 Lot").qty == "1 Lot"
    assert LooseExtra(part_id="CABLE-1").qty == 1


def test_loose_item_and_extra_accept_tag() -> None:
    assert LooseItem(part_id="TS-ACC", tag="Time Server Accessories").tag == (
        "Time Server Accessories"
    )
    assert LooseItem(part_id="TS-ACC").tag is None
    assert LooseExtra(part_id="FO-1", tag="FO").tag == "FO"
    assert LooseExtra(part_id="FO-1").tag is None


def test_loose_extra_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        LooseExtra(part_id="CABLE-1", qty=0)


def test_free_text_loose_item_has_a_description_and_no_part() -> None:
    item = LooseExtra(description="Cable tray, 300 mm", qty="1 Lot", tag="Tray")
    assert item.part_id is None
    assert item.description == "Cable tray, 300 mm"


@pytest.mark.parametrize(
    "fields",
    [{}, {"part_id": "FO-1", "description": "FO patch cords"}, {"description": "  "}],
)
def test_loose_item_names_a_part_or_a_description_not_both(fields: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="part_id or a description"):
        LooseExtra.model_validate(fields)


@pytest.mark.parametrize(("key", "value"), [("children", ["LPA37-696"]), ("fed_from", "psa3")])
def test_free_text_loose_item_brings_no_children_and_is_not_fed(key: str, value: Any) -> None:
    with pytest.raises(ValidationError, match=f"{key} needs a library part"):
        LooseExtra.model_validate({"description": "Cable tray", key: value})


@pytest.mark.parametrize("bad", ["../x", "a/b", "", ".hidden"])
def test_library_name_is_a_plain_folder_name(bad: str) -> None:
    with pytest.raises(ValidationError, match="name"):
        LibrarySelection(name=bad, version="1.0.0")


def test_dc_float_voltage_defaults_to_140() -> None:
    assert DesignConstants().dc_float_v == 140
