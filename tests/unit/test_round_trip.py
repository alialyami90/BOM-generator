"""Round-trip YAML editing keeps the hand-written files as they are (ADR 0021)."""

from pathlib import Path

import pytest

from bomgen.io.round_trip import dump_text, load_text, merge_value, write_atomic

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
