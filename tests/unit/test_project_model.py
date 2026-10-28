"""Project model: project info, documents, output settings, constants, loose material."""

import re
from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.models.library import LooseItem
from bomgen.models.project import (
    DesignConstants,
    LooseExtra,
    OutputSettings,
    Project,
    SheetNames,
)


def project_dict() -> dict[str, Any]:
    calc = {
        "doc_no": "DOC-9",
        "rev": 0,
        "issue_date": "2026-10-28",
        "scope": "Whole substation",
    }
    return {
        "project": {"name": "GIS 01", "substation": "Dhahran", "doc_no": "DOC-1"},
        "library": "library.yaml",
        "panels": ["panels/psa1.yaml"],
        "documents": {
            "power_consumption": calc,
            "heat_dissipation": calc,
            "heat_calculations": calc,
        },
    }


def test_project_from_minimal_dict_validates() -> None:
    project = Project.model_validate(project_dict())
    assert project.project.rev == "0"
    assert project.output == OutputSettings()
    assert project.constants == DesignConstants()
    assert project.loose_material is None
    assert project.documents.heat_calculations.scope == "Whole substation"


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


def test_sheet_names_follow_excel_rules() -> None:
    with pytest.raises(ValidationError):
        SheetNames(power_consumption="a/b")


def test_project_requires_at_least_one_panel() -> None:
    data = project_dict()
    data["panels"] = []
    with pytest.raises(ValidationError):
        Project.model_validate(data)


def test_project_rejects_unknown_key() -> None:
    data = project_dict()
    data["extras"] = 1
    with pytest.raises(ValidationError, match="extras"):
        Project.model_validate(data)


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


def test_loose_material_from_project_dict() -> None:
    data = project_dict()
    data["loose_material"] = {
        "host_panel": "psa1",
        "items": [{"part_id": "CABLE-1", "qty": 2, "children": ["LUG-1"], "fed_from": "psa1"}],
    }
    project = Project.model_validate(data)
    assert project.loose_material is not None
    assert project.loose_material.items[0].children == ["LUG-1"]
