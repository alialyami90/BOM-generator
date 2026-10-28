"""YAML reader: line tracking, syntax and structure errors."""

from pathlib import Path

import pytest

from bomgen.io.errors import InputError, Issue
from bomgen.io.yaml_source import read_yaml


def write(tmp_path: Path, text: str, name: str = "in.yaml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def only_issue(error: pytest.ExceptionInfo[InputError]) -> Issue:
    assert len(error.value.issues) == 1
    return error.value.issues[0]


def test_read_yaml_records_line_of_each_key_and_item(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        "name: a\n"
        "devices:\n"
        "  - part_id: X\n"
        "    qty: 1\n"
        "  - part_id: Y\n"
        "nested:\n"
        "  inner:\n"
        "    deep: 1\n",
    )
    source = read_yaml(path)
    assert source.path == path
    assert source.data["name"] == "a"
    assert source.lines[("name",)] == 1
    assert source.lines[("devices",)] == 2
    assert source.lines[("devices", 0)] == 3
    assert source.lines[("devices", 0, "part_id")] == 3
    assert source.lines[("devices", 0, "qty")] == 4
    assert source.lines[("devices", 1)] == 5
    assert source.lines[("devices", 1, "part_id")] == 5
    assert source.lines[("nested", "inner", "deep")] == 8


def test_read_yaml_accepts_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.yaml"
    path.write_bytes(b"\xef\xbb\xbfname: a\n")
    assert read_yaml(path).data == {"name": "a"}


def test_missing_file_is_an_issue(tmp_path: Path) -> None:
    path = tmp_path / "nope.yaml"
    with pytest.raises(InputError) as error:
        read_yaml(path)
    issue = only_issue(error)
    assert issue.file == path
    assert issue.location == ""
    assert issue.message == "file not found"
    assert issue.line is None


def test_file_that_is_not_utf8_is_an_issue(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_bytes(b"name: \xff\xfe\n")
    with pytest.raises(InputError) as error:
        read_yaml(path)
    assert only_issue(error).message == "not valid UTF-8 text"


def test_syntax_error_reports_line(tmp_path: Path) -> None:
    path = write(tmp_path, "name: a\nitems: [1, 2\nother: 3\n")
    with pytest.raises(InputError) as error:
        read_yaml(path)
    issue = only_issue(error)
    assert issue.line == 3
    assert issue.location == ""
    assert issue.message


def test_top_level_list_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InputError) as error:
        read_yaml(write(tmp_path, "- a\n- b\n"))
    assert only_issue(error).message == "expected a mapping at the top level"


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(InputError) as error:
        read_yaml(write(tmp_path, ""))
    assert only_issue(error).message == "expected a mapping at the top level"


def test_duplicate_key_is_rejected_with_both_lines(tmp_path: Path) -> None:
    path = write(tmp_path, "name: a\nother: 1\nname: b\n")
    with pytest.raises(InputError) as error:
        read_yaml(path)
    issue = only_issue(error)
    assert issue.location == "name"
    assert issue.message == "duplicate key 'name' (first at line 1)"
    assert issue.line == 3


def test_duplicate_key_in_nested_mapping_inside_sequence_is_rejected(tmp_path: Path) -> None:
    path = write(tmp_path, "devices:\n  - part_id: X\n    qty: 1\n    qty: 2\n")
    with pytest.raises(InputError) as error:
        read_yaml(path)
    issue = only_issue(error)
    assert issue.location == "devices[0].qty"
    assert issue.message == "duplicate key 'qty' (first at line 3)"
    assert issue.line == 4


def test_line_for_falls_back_to_parent(tmp_path: Path) -> None:
    source = read_yaml(write(tmp_path, "devices:\n  - part_id: X\n"))
    assert source.line_for(("devices", 0, "part_id")) == 2
    assert source.line_for(("devices", 0, "qty")) == 2
    assert source.line_for(("devices", 5)) == 1
    assert source.line_for(("unknown",)) is None
    assert source.line_for(()) is None


def test_merge_key_is_accepted(tmp_path: Path) -> None:
    path = write(tmp_path, "b: &b {a: 1}\nx:\n  <<: *b\n  c: 2\n")
    source = read_yaml(path)
    assert source.data["x"] == {"a": 1, "c": 2}
    assert source.lines[("x", "c")] == 4


def test_rev_keeps_leading_zero_when_unquoted(tmp_path: Path) -> None:
    source = read_yaml(write(tmp_path, "a:\n  rev: 02\n  b: 00\n  c: 010\n  d: -07\n"))
    assert source.data["a"] == {"rev": "02", "b": "00", "c": "010", "d": "-07"}


def test_plain_integers_still_load_as_int(tmp_path: Path) -> None:
    source = read_yaml(
        write(tmp_path, "qty: 6\ncount: 24\nzero: 0\nneg: -3\nplus: +5\nrate: 1.5\n")
    )
    assert source.data == {"qty": 6, "count": 24, "zero": 0, "neg": -3, "plus": 5, "rate": 1.5}
    assert all(type(source.data[key]) is int for key in ("qty", "count", "zero", "neg", "plus"))


def test_sexagesimal_is_not_an_int(tmp_path: Path) -> None:
    source = read_yaml(write(tmp_path, "rev: 1:30\nratio: 1:30.5\n"))
    assert source.data == {"rev": "1:30", "ratio": "1:30.5"}


def test_directory_path_is_an_issue(tmp_path: Path) -> None:
    with pytest.raises(InputError) as error:
        read_yaml(tmp_path)
    issue = only_issue(error)
    assert issue.file == tmp_path
    assert issue.message.startswith("cannot read file: ")
    assert issue.line is None
