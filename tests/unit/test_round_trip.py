"""Round-trip YAML editing keeps the hand-written files as they are (ADR 0021)."""

from collections.abc import Callable
from pathlib import Path

import pytest
from ruamel.yaml.comments import CommentedMap

from bomgen.io.round_trip import (
    dump_text,
    edit_document,
    load_text,
    merge_value,
    remove_entry,
    set_entry,
    write_atomic,
)

EXAMPLES = Path(__file__).parents[2] / "examples"


@pytest.mark.parametrize(
    "path", sorted(EXAMPLES.rglob("*.yaml")), ids=lambda p: p.relative_to(EXAMPLES).as_posix()
)
def test_an_unchanged_example_file_dumps_byte_identical(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert dump_text(load_text(text)) == text


def test_merge_keeps_comments_of_unchanged_keys_and_quoting() -> None:
    data = load_text(
        'enclosure:  # as psa1\n  make: Rawabi  # maker\n  model: "Fixed Frame"\n  h_mm: 2100\n'
    )
    new = {"make": "Rawabi", "model": "Other", "h_mm": 2200, "w_mm": 800}
    data["enclosure"] = merge_value(data["enclosure"], new)
    assert dump_text(data) == (
        'enclosure:  # as psa1\n  make: Rawabi  # maker\n  model: "Other"\n  h_mm: 2200\n'
        "  w_mm: 800\n"
    )


def test_merge_drops_keys_the_new_value_lacks() -> None:
    data = load_text("a: { x: 1, y: 2 }\n")
    data["a"] = merge_value(data["a"], {"x": 1})
    assert dump_text(data) == "a: { x: 1 }\n"


def test_merge_keeps_a_true_value_apart_from_one() -> None:
    data = load_text("a: 1\n")
    data["a"] = merge_value(data["a"], True)
    assert dump_text(data) == "a: true\n"


def test_null_is_written_out() -> None:
    data = load_text("a: 1\n")
    data["a"] = merge_value(data["a"], None)
    assert dump_text(data) == "a: null\n"


def test_atomic_write_replaces_the_file(tmp_path: Path) -> None:
    path = tmp_path / "s.yaml"
    path.write_text("old\n", encoding="utf-8")
    write_atomic(path, "new: 1\n")
    assert path.read_text(encoding="utf-8") == "new: 1\n"
    assert [p.name for p in tmp_path.iterdir()] == ["s.yaml"]


def test_atomic_write_keeps_the_file_mode(tmp_path: Path) -> None:
    path = tmp_path / "s.yaml"
    path.write_text("old\n", encoding="utf-8")
    path.chmod(0o640)
    write_atomic(path, "new: 1\n")
    assert path.stat().st_mode & 0o777 == 0o640
    fresh = tmp_path / "new.yaml"
    write_atomic(fresh, "a: 1\n")
    assert fresh.stat().st_mode & 0o777 == 0o644


TEXT = """a:  # key comment
  - x  # cx
  - y  # cy

b:
  k: 1  # kc
  m: 2

c: 1
"""


def edited(change: Callable[[CommentedMap], None]) -> str:
    data = load_text(TEXT)
    edit_document(data, change)
    return dump_text(data)


def test_removing_the_last_item_keeps_the_blank_line() -> None:
    assert edited(lambda d: remove_entry(d["a"], 1)) == TEXT.replace("  - y  # cy\n", "")


def test_emptying_a_list_writes_it_inline_with_its_comment() -> None:
    def change(d: CommentedMap) -> None:
        remove_entry(d["a"], 1)
        remove_entry(d["a"], 0)

    assert edited(change).startswith("a: [] # key comment\n\nb:\n")


def test_appending_puts_the_new_item_before_the_blank_line() -> None:
    assert edited(lambda d: set_entry(d["a"], 2, "z")) == TEXT.replace(
        "  - y  # cy\n", "  - y  # cy\n  - z\n"
    )


def test_removing_a_top_level_key_keeps_one_blank_line() -> None:
    assert (
        edited(lambda d: remove_entry(d, "b"))
        == "a:  # key comment\n  - x  # cx\n  - y  # cy\n\nc: 1\n"
    )


def test_an_end_of_line_comment_keeps_its_distance() -> None:
    assert "  k: 1234  # kc\n" in edited(lambda d: set_entry(d["b"], "k", 1234))


def test_a_commented_flow_item_first_in_a_commented_list_keeps_the_next_items_lines() -> None:
    # ruamel 0.19 joined "id: a" and "x: 1" onto one line here (found moving a Parts row up)
    text = "k:  # head\n  - { id: b, x: 2 }  # bee\n  - id: a\n    x: 1\n"

    assert dump_text(load_text(text)) == text
