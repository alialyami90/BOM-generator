"""Edit a YAML input file and write it back with its comments, key order and style kept.

ruamel.yaml's round-trip mode, set up so that an unchanged file dumps byte-identical to
the hand-written style of ``examples/`` (ADR 0021): two-space mappings, sequences
indented under their key, ``{ a: 1 }`` flow mappings and ``null`` written out.
"""

from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.emitter import Emitter
from ruamel.yaml.error import CommentMark
from ruamel.yaml.representer import RoundTripRepresenter
from ruamel.yaml.tokens import CommentToken


class _PaddedEmitter(Emitter):
    """Writes flow mappings as ``{ a: 1 }``, as the hand-written files do."""

    def write_indicator(
        self,
        indicator: Any,
        need_whitespace: Any,
        whitespace: bool = False,
        indention: bool = False,
    ) -> None:
        if indicator == "{":
            whitespace = False  # the first key gets a space after the brace
            # ruamel 0.19 keeps the "- " flag through a flow mapping, so after a first list
            # item like `- { a: 1 }  # note` the next block mapping lost its line breaks
            self.no_newline = False
        elif indicator == "}":
            need_whitespace = True
        super().write_indicator(indicator, need_whitespace, whitespace, indention)


class _Representer(RoundTripRepresenter):
    def ignore_aliases(self, data: Any) -> bool:
        """Write a scalar used twice (a writer's ``date``) in full, never as ``&id001``;
        lists and mappings keep the aliases the file has."""
        if isinstance(data, (dict, list)):
            return bool(super().ignore_aliases(data))
        return True


_Representer.add_representer(
    type(None), lambda r, _: r.represent_scalar("tag:yaml.org,2002:null", "null")
)


def _yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096  # never fold a long line
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.Emitter = _PaddedEmitter
    yaml.Representer = _Representer
    return yaml


def load_text(text: str) -> CommentedMap:
    """Parse ``text`` for editing; raise ``ValueError`` unless it is a mapping."""
    data = _yaml().load(text)
    if data is None:
        return CommentedMap()
    if not isinstance(data, CommentedMap):
        raise ValueError("expected a mapping at the top level")
    return data


def dump_text(data: CommentedMap) -> str:
    """The YAML text of ``data``."""
    out = io.StringIO()
    _yaml().dump(data, out)
    return out.getvalue()


Node = CommentedMap | CommentedSeq


def child_map(parent: CommentedMap, key: Any) -> CommentedMap:
    """``parent[key]`` as a mapping, created empty when missing or null."""
    if not isinstance(parent.get(key), CommentedMap):
        set_entry(parent, key, CommentedMap())
    node: CommentedMap = parent[key]
    return node


def set_entry(parent: Node, key: Any, new: Any) -> None:
    """Set ``parent[key]`` to ``new`` built on the old value (see :func:`merge_value`); for
    a sequence, ``key == len(parent)`` appends. The blank lines and comments that end the
    old value (or, for a new last entry, the old last entry) move to the new end."""
    if not len(parent) and parent.fa.flow_style():
        parent.fa.set_block_style()  # a collection that gains its first entry is written out
    if _has(parent, key):
        tail = _take_tail(parent, key)
    elif len(parent):
        tail = _take_tail(parent, _last(parent))
    else:
        tail = ""
    old = parent[key] if _has(parent, key) else None
    value = merge_value(old, new)
    if isinstance(parent, CommentedSeq) and key == len(parent):
        parent.append(value)
    else:
        parent[key] = value
    if _has(parent, key) and _scalar(old) and _scalar(value):
        _shift_comment(parent, key, len(_text(value)) - len(_text(old)))
    if isinstance(value, (CommentedMap, CommentedSeq)) and not value:
        value.fa.set_flow_style()  # a key comment then follows the [] or {}
    _put_tail(parent, key, tail)


def remove_entry(parent: Node, key: Any) -> None:
    """Delete ``parent[key]``; what ended it (the blank line before the next key) moves to
    the entry before it."""
    tail = _take_tail(parent, key)
    keys = list(parent) if isinstance(parent, CommentedMap) else list(range(len(parent)))
    position = keys.index(key)
    del parent[key]
    if position > 0:
        _put_tail(parent, keys[position - 1], tail)
        if isinstance(parent, CommentedMap) and position + 1 < len(keys):
            _drop_blank_lead(parent, keys[position + 1])
    if not parent:
        parent.fa.set_flow_style()  # a key comment then follows the [] or {}


def insert_entry(seq: CommentedSeq, index: int, value: Any) -> None:
    """Insert ``value`` at ``index`` (``len(seq)`` appends), before the list's tail."""
    if index >= len(seq):
        set_entry(seq, len(seq), value)
        return
    seq.insert(index, merge_value(None, value))


def move_entry(seq: CommentedSeq, source: int, target: int) -> None:
    """Move item ``source`` to ``target``; the item keeps its comment and the list's tail
    stays at the list's end."""
    tail = _take_tail(seq, len(seq) - 1)
    comment = seq.ca.items.pop(source, None)
    item = seq[source]
    del seq[source]
    seq.insert(target, item)
    if comment is not None:
        seq.ca.items[target] = comment
    _put_tail(seq, len(seq) - 1, tail)


def comment_of(parent: Node, key: Any) -> str:
    """The end-of-line comment of ``parent[key]`` without its ``#``, or ``""``."""
    entry = parent.ca.items.get(key)
    token = entry[_slot(parent)] if entry else None
    if token is None:
        return ""
    head = str(token.value).partition("\n")[0].strip()
    return head.removeprefix("#").strip()


def set_comment(parent: Node, key: Any, text: str) -> None:
    """Set (``""``: remove) the end-of-line comment of ``parent[key]``, keeping the lines
    after it."""
    entry = parent.ca.items.setdefault(key, [None, None, None, None])
    token = entry[_slot(parent)]
    rest = token.value.partition("\n")[2] if token is not None else ""
    if not text:
        entry[_slot(parent)] = CommentToken("\n" + rest, CommentMark(0), None) if rest else None
    elif token is None:
        parent.yaml_add_eol_comment(f"# {text}", key)
    else:
        token.value = f"# {text}\n{rest}"


def edit_document(data: CommentedMap, change: Callable[[CommentedMap], None]) -> None:
    """Run ``change`` on a parsed file and keep each top-level entry's tail (the blank
    line before the next key) at that entry's end, wherever the change leaves it."""
    tails = {key: _take_tail(data, key) for key in list(data)}
    change(data)
    for key, tail in tails.items():
        if key in data:
            _put_tail(data, key, tail)


def merge_value(old: Any, new: Any) -> Any:
    """``new`` built on ``old`` so unchanged keys and items keep their comments and style:
    a mapping keeps the keys it shares with ``new`` in place, drops the others and adds
    the rest at the end."""
    if isinstance(new, Mapping) and isinstance(old, CommentedMap):
        for key in [k for k in old if k not in new]:
            remove_entry(old, key)
        for key, value in new.items():
            set_entry(old, key, value)
        return old
    if isinstance(new, Sequence) and not isinstance(new, str) and isinstance(old, CommentedSeq):
        while len(old) > len(new):
            remove_entry(old, len(old) - 1)
        for index, value in enumerate(new):
            set_entry(old, index, value)
        return old
    if old == new and isinstance(old, bool) == isinstance(new, bool):
        return old  # keeps a quoted or styled scalar as written
    if isinstance(old, str) and type(old) is not str and isinstance(new, str):
        return type(old)(new)  # a quoted string stays quoted
    return _plain(new)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return CommentedMap((k, _plain(v)) for k, v in value.items())
    if isinstance(value, Sequence) and not isinstance(value, str):
        return CommentedSeq(_plain(v) for v in value)
    return value


# A comment after an entry is a CommentToken in ``ca.items[key]``, at index 2 for a
# mapping and 0 for a sequence. Its text runs from the entry's end-of-line comment through
# any blank and comment lines up to the next entry; on a container's last entry that is
# the container's tail.


def _has(parent: Node, key: Any) -> bool:
    return key in parent if isinstance(parent, CommentedMap) else 0 <= key < len(parent)


def _last(node: Node) -> Any:
    return next(reversed(node)) if isinstance(node, CommentedMap) else len(node) - 1


def _slot(parent: Node) -> int:
    return 2 if isinstance(parent, CommentedMap) else 0


def _block(value: Any) -> bool:
    """A non-empty block collection, whose entries hold its comments; a flow collection's
    comment is its parent's, like a scalar's."""
    return (
        isinstance(value, (CommentedMap, CommentedSeq))
        and bool(value)
        and not (value.fa.flow_style())
    )


def _take_tail(parent: Node, key: Any) -> str:
    """Remove and return the lines after ``parent[key]``'s end-of-line comment."""
    value = parent[key]
    if _block(value):
        return _take_tail(value, _last(value))
    entry = parent.ca.items.get(key)
    token = entry[_slot(parent)] if entry else None
    if token is None:
        return ""
    head, newline, rest = token.value.partition("\n")
    if head.strip():
        token.value = head + newline
    else:
        entry[_slot(parent)] = None
    return str(rest)


def _scalar(value: Any) -> bool:
    return not isinstance(value, (CommentedMap, CommentedSeq, Mapping, list))


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "null" if value is None else str(value)


def _shift_comment(parent: Node, key: Any, by: int) -> None:
    """Keep an end-of-line comment the same distance from a value that grew or shrank."""
    entry = parent.ca.items.get(key)
    token = entry[_slot(parent)] if entry else None
    if by and token is not None and token.value.lstrip().startswith("#"):
        token.column = max(0, token.column + by)


def _drop_blank_lead(parent: CommentedMap, key: Any) -> None:
    """Drop the blank lines ruamel keeps before ``key`` (``ca.items[key][1]``) when they
    separated it from an entry that was removed; the entry before keeps its own."""
    entry = parent.ca.items.get(key)
    lead = entry[1] if entry else None
    if lead and all(not token.value.strip() for token in lead):
        entry[1] = None


def _put_tail(parent: Node, key: Any, tail: str) -> None:
    if not tail:
        return
    value = parent[key]
    if _block(value):
        _put_tail(value, _last(value), tail)
        return
    entry = parent.ca.items.setdefault(key, [None, None, None, None])
    token = entry[_slot(parent)]
    if token is None:
        entry[_slot(parent)] = CommentToken("\n" + tail, CommentMark(0), None)
    else:
        token.value += tail


def write_atomic(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` through a temporary file in the same folder, so a
    failed write leaves the old file whole."""
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644  # mkstemp makes 0600
    path.parent.mkdir(parents=True, exist_ok=True)  # a new panel may start the folder
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
            out.write(text)
        os.chmod(temp, mode)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
