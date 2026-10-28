"""Base input types: templates, revisions, quantities and sheet names."""

import re
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from bomgen.models._base import (
    AutoBool,
    ChildQuantity,
    ExcelSheetName,
    Quantity,
    Rev,
    check_template,
    template_fields,
)


def test_template_fields_lists_placeholders() -> None:
    assert template_fields("LAN-{lan} {level}") == {"lan", "level"}


def test_template_fields_rejects_unbalanced_braces() -> None:
    with pytest.raises(ValueError, match="malformed template"):
        template_fields("LAN-{lan")


def test_check_template_returns_valid_template() -> None:
    assert check_template("LAN-{lan}", {"lan", "level"}) == "LAN-{lan}"


def test_check_template_rejects_unknown_placeholder() -> None:
    with pytest.raises(ValueError, match="allowed: lan, level, purpose") as excinfo:
        check_template("{lan} {colour}", {"purpose", "level", "lan"})
    assert "'colour'" in str(excinfo.value)


def test_rev_accepts_unquoted_integer() -> None:
    assert TypeAdapter(Rev).validate_python(0) == "0"
    assert TypeAdapter(Rev).validate_python("A") == "A"


def test_rev_rejects_empty_string() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Rev).validate_python("")


def test_quantity_accepts_int_and_one_lot() -> None:
    adapter = TypeAdapter(Quantity)
    assert adapter.validate_python(3) == 3
    assert adapter.validate_python("1 Lot") == "1 Lot"


def test_quantity_rejects_other_text_with_one_message() -> None:
    with pytest.raises(ValidationError) as excinfo:
        TypeAdapter(Quantity).validate_python("1 lot")
    errors = excinfo.value.errors()
    assert len(errors) == 1
    assert errors[0]["msg"] == "Value error, must be a whole number of at least 1 or '1 Lot'"


@pytest.mark.parametrize("bad", [True, 0, -1, 1.5])
def test_quantity_rejects_bool_and_zero(bad: Any) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Quantity).validate_python(bad)


def test_child_quantity_accepts_int_and_cores_only() -> None:
    adapter = TypeAdapter(ChildQuantity)
    assert adapter.validate_python(2) == 2
    assert adapter.validate_python("cores") == "cores"
    with pytest.raises(ValidationError) as excinfo:
        adapter.validate_python("Cores")
    errors = excinfo.value.errors()
    assert len(errors) == 1
    assert errors[0]["msg"] == "Value error, must be a whole number of at least 1 or 'cores'"


def test_auto_bool_accepts_true_false_auto() -> None:
    adapter = TypeAdapter(AutoBool)
    assert adapter.validate_python(True) is True
    assert adapter.validate_python(False) is False
    assert adapter.validate_python("auto") == "auto"


@pytest.mark.parametrize("bad", ["yes", 1, "Auto"])
def test_auto_bool_rejects_other_values_with_one_message(bad: Any) -> None:
    with pytest.raises(ValidationError) as excinfo:
        TypeAdapter(AutoBool).validate_python(bad)
    errors = excinfo.value.errors()
    assert len(errors) == 1
    assert errors[0]["msg"] == "Value error, must be true, false or 'auto'"


def test_quantity_types_publish_json_schema() -> None:
    assert TypeAdapter(Quantity).json_schema() == {
        "anyOf": [{"type": "integer", "minimum": 1}, {"const": "1 Lot"}]
    }
    assert TypeAdapter(ChildQuantity).json_schema() == {
        "anyOf": [{"type": "integer", "minimum": 1}, {"const": "cores"}]
    }
    assert TypeAdapter(AutoBool).json_schema() == {
        "anyOf": [{"type": "boolean"}, {"const": "auto"}]
    }


def test_rev_and_sheet_name_schemas_accept_string_or_integer() -> None:
    rev = TypeAdapter(Rev).json_schema()
    assert rev == {"type": ["string", "integer"], "minLength": 1}
    sheet = TypeAdapter(ExcelSheetName).json_schema()
    assert sheet["type"] == ["string", "integer"]
    assert (sheet["minLength"], sheet["maxLength"]) == (1, 31)
    pattern = re.compile(sheet["pattern"])
    for good in ("Power Consumption", "a'b", "1"):
        assert pattern.search(good), good
    for bad in ("a/b", "a[1]", "'x", "x'", "a:b", "a*", "a?", "a\\b"):
        assert not pattern.search(bad), bad


@pytest.mark.parametrize(
    "bad", ["x" * 32, "a/b", "'x", "x'", "a[1]", "a:b", "a*", "a?", "a\\b", ""]
)
def test_excel_sheet_name_rejects_long_and_forbidden_chars(bad: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(ExcelSheetName).validate_python(bad)


def test_excel_sheet_name_accepts_31_characters_and_inner_apostrophe() -> None:
    adapter = TypeAdapter(ExcelSheetName)
    assert adapter.validate_python("x" * 31) == "x" * 31
    assert adapter.validate_python("a'b") == "a'b"


def test_excel_sheet_name_accepts_unquoted_integer() -> None:
    assert TypeAdapter(ExcelSheetName).validate_python(1) == "1"
