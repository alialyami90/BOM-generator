"""Shared base class and field types for the input models.

Templates and quantity notations follow the spec section "Inputs the tool needs";
the YAML-typing leniencies (unquoted ``rev: 0`` and ``sheet_name: 1``) follow
ADR 0010.
"""

from string import Formatter
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    PlainValidator,
    StringConstraints,
    WithJsonSchema,
)


class InputModel(BaseModel):
    """Base for every input model: unknown keys are errors and instances are immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def template_fields(template: str) -> set[str]:
    """Return the placeholder names used by a ``str.format`` template."""
    try:
        parsed = list(Formatter().parse(template))
    except ValueError as exc:
        raise ValueError(f"malformed template: {exc}") from exc
    names: set[str] = set()
    for _literal, field_name, format_spec, _conversion in parsed:
        if field_name is not None:
            names.add(field_name.split(".")[0].split("[")[0])
        if format_spec:
            names |= template_fields(format_spec)
    return names


def check_template(template: str, allowed: set[str]) -> str:
    """Return ``template`` if it only uses ``allowed`` placeholders, else raise ``ValueError``."""
    unknown = sorted(template_fields(template) - allowed)
    if unknown:
        names = ", ".join(f"'{name}'" for name in unknown)
        raise ValueError(f"unknown placeholder(s) {names}; allowed: {', '.join(sorted(allowed))}")
    return template


def _int_to_str(value: Any) -> Any:
    """Accept an unquoted YAML integer where a string is expected."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return value


Rev = Annotated[
    str,
    BeforeValidator(_int_to_str),
    StringConstraints(min_length=1),
    WithJsonSchema({"type": ["string", "integer"], "minLength": 1}),
]


def _is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _validate_quantity(value: object) -> int | Literal["1 Lot"]:
    if _is_count(value):
        assert isinstance(value, int)
        return value
    if value == "1 Lot":
        return "1 Lot"
    raise ValueError("must be a whole number of at least 1 or '1 Lot'")


def _validate_child_quantity(value: object) -> int | Literal["cores"]:
    if _is_count(value):
        assert isinstance(value, int)
        return value
    if value == "cores":
        return "cores"
    raise ValueError("must be a whole number of at least 1 or 'cores'")


def _validate_auto_bool(value: object) -> bool | Literal["auto"]:
    if isinstance(value, bool):
        return value
    if value == "auto":
        return "auto"
    raise ValueError("must be true, false or 'auto'")


Quantity = Annotated[
    int | Literal["1 Lot"],
    PlainValidator(_validate_quantity),
    WithJsonSchema({"anyOf": [{"type": "integer", "minimum": 1}, {"const": "1 Lot"}]}),
]
ChildQuantity = Annotated[
    int | Literal["cores"],
    PlainValidator(_validate_child_quantity),
    WithJsonSchema({"anyOf": [{"type": "integer", "minimum": 1}, {"const": "cores"}]}),
]
AutoBool = Annotated[
    bool | Literal["auto"],
    PlainValidator(_validate_auto_bool),
    WithJsonSchema({"anyOf": [{"type": "boolean"}, {"const": "auto"}]}),
]

_SHEET_NAME_FORBIDDEN = set("[]:*?/\\")


def _check_sheet_name(name: str) -> str:
    if not 1 <= len(name) <= 31:
        raise ValueError("sheet name must be 1 to 31 characters")
    bad = sorted(set(name) & _SHEET_NAME_FORBIDDEN)
    if bad:
        raise ValueError(f"sheet name must not contain any of {' '.join(bad)}")
    if name.startswith("'") or name.endswith("'"):
        raise ValueError("sheet name must not start or end with an apostrophe")
    return name


ExcelSheetName = Annotated[
    str,
    BeforeValidator(_int_to_str),
    AfterValidator(_check_sheet_name),
    WithJsonSchema(
        {
            "type": ["string", "integer"],
            "minLength": 1,
            "maxLength": 31,
            "pattern": r"^(?!')(?:[^\[\]:*?/\\']|'(?!$))*$",
        }
    ),
]

PartId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")]
