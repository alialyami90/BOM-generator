"""Edit a YAML input file and write it back with its comments, key order and style kept.

ruamel.yaml's round-trip mode, set up so that an unchanged file dumps byte-identical to
the hand-written style of ``examples/`` (ADR 0021): two-space mappings, sequences
indented under their key, ``{ a: 1 }`` flow mappings and ``null`` written out.
"""

from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.emitter import Emitter
from ruamel.yaml.representer import RoundTripRepresenter


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
        elif indicator == "}":
            need_whitespace = True
        super().write_indicator(indicator, need_whitespace, whitespace, indention)


class _Representer(RoundTripRepresenter):
    pass


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


def child_map(parent: CommentedMap, key: Any) -> CommentedMap:
    """``parent[key]`` as a mapping, created empty when missing or null."""
    node = parent.get(key)
    if not isinstance(node, CommentedMap):
        node = CommentedMap()
        parent[key] = node
    return node


def merge_value(old: Any, new: Any) -> Any:
    """``new`` built on ``old`` so unchanged keys and items keep their comments and style:
    a mapping keeps the keys it shares with ``new`` in place, drops the others and adds
    the rest at the end."""
    if isinstance(new, Mapping) and isinstance(old, CommentedMap):
        for key in [k for k in old if k not in new]:
            del old[key]
        for key, value in new.items():
            old[key] = merge_value(old.get(key), value) if key in old else _plain(value)
        return old
    if isinstance(new, Sequence) and not isinstance(new, str) and isinstance(old, CommentedSeq):
        items = [merge_value(old[i], v) if i < len(old) else _plain(v) for i, v in enumerate(new)]
        del old[len(new) :]
        for index, item in enumerate(items):
            if index < len(old):
                old[index] = item
            else:
                old.append(item)
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


def write_atomic(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` through a temporary file in the same folder, so a
    failed write leaves the old file whole."""
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
            out.write(text)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
