"""Located input errors: formatting and conversion from pydantic validation errors."""

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, PositiveInt, ValidationError, field_validator
from pydantic_core import InitErrorDetails

from bomgen.io.errors import InputError, Issue, format_location, issues_from_validation_error
from bomgen.io.yaml_source import read_yaml


class _Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_id: str
    qty: PositiveInt


class _Doc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    devices: list[_Item]


def _validate(tmp_path: Path, text: str) -> list[Issue]:
    path = tmp_path / "doc.yaml"
    path.write_text(text, encoding="utf-8")
    source = read_yaml(path)
    with pytest.raises(ValidationError) as error:
        _Doc.model_validate(source.data)
    return issues_from_validation_error(error.value, source)


def test_format_location_uses_brackets_for_indices() -> None:
    assert format_location(("devices", 2, "part_id")) == "devices[2].part_id"
    assert format_location((0,)) == "[0]"
    assert format_location(()) == ""


def test_issue_str_with_and_without_line() -> None:
    path = Path("a") / "b.yaml"
    assert str(Issue(path, "devices[0].qty", "bad", 4)) == "a/b.yaml:4: devices[0].qty: bad"
    assert str(Issue(path, "devices[0].qty", "bad")) == "a/b.yaml: devices[0].qty: bad"
    assert str(Issue(path, "", "file not found")) == "a/b.yaml: file not found"
    assert str(Issue(path, "", "bad", 7)) == "a/b.yaml:7: bad"


def test_input_error_lists_every_issue() -> None:
    first = Issue(Path("a.yaml"), "x", "one", 1)
    second = Issue(Path("b.yaml"), "", "two")
    error = InputError([first, second])
    assert error.issues == (first, second)
    assert str(error) == "a.yaml:1: x: one\nb.yaml: two"


def test_validation_error_becomes_located_issue(tmp_path: Path) -> None:
    issues = _validate(
        tmp_path,
        "devices:\n  - part_id: X\n    qty: 0\n",
    )
    assert len(issues) == 1
    issue = issues[0]
    assert issue.file == tmp_path / "doc.yaml"
    assert issue.location == "devices[0].qty"
    assert issue.line == 3
    assert issue.message == "Input should be greater than 0"


def test_value_error_prefix_is_stripped_and_prefix_loc_applied(tmp_path: Path) -> None:
    class _Checked(BaseModel):
        part_id: str

        @field_validator("part_id")
        @classmethod
        def _reject(cls, value: str) -> str:
            raise ValueError("nope")

    path = tmp_path / "doc.yaml"
    path.write_text("devices:\n  - part_id: X\n", encoding="utf-8")
    source = read_yaml(path)
    with pytest.raises(ValidationError) as error:
        _Checked.model_validate({"part_id": "X"})
    issues = issues_from_validation_error(error.value, source, prefix=("devices", 0))
    assert [(i.location, i.message, i.line) for i in issues] == [("devices[0].part_id", "nope", 2)]


def test_unknown_key_message_suggests_spelling(tmp_path: Path) -> None:
    issues = _validate(tmp_path, "devices: []\nbogus: 1\n")
    assert [(i.location, i.message, i.line) for i in issues] == [
        ("bogus", "unknown key (check spelling)", 2)
    ]


def test_missing_key_reports_parent_line(tmp_path: Path) -> None:
    issues = _validate(tmp_path, "devices:\n  - qty: 1\n")
    assert [(i.location, i.message, i.line) for i in issues] == [
        ("devices[0].part_id", "required key is missing", 2)
    ]


def test_duplicate_messages_at_one_location_are_dropped(tmp_path: Path) -> None:
    path = tmp_path / "doc.yaml"
    path.write_text("devices: []\n", encoding="utf-8")
    source = read_yaml(path)
    line_error: InitErrorDetails = {"type": "int_type", "loc": ("devices",), "input": []}
    error = ValidationError.from_exception_data("_Doc", [line_error, line_error])
    issues = issues_from_validation_error(error, source)
    assert [(i.location, i.line) for i in issues] == [("devices", 1)]
