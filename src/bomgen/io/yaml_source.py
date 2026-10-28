"""Read a YAML input file, keeping the line of every key and sequence item."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bomgen.io.errors import InputError, Issue, Loc, format_location

_MERGE_TAG = "tag:yaml.org,2002:merge"
_INT_TAG = "tag:yaml.org,2002:int"
_FLOAT_TAG = "tag:yaml.org,2002:float"

# PyYAML follows YAML 1.1, where 02 is an int (2), 010 is octal (8) and 1:30 is
# sexagesimal (90). Revisions such as ``rev: 02`` must stay text, so numbers with a
# leading zero and sexagesimal forms are left as strings.
_INT_PATTERN = re.compile(r"^[-+]?(?:0|[1-9][0-9_]*)$")
_FLOAT_PATTERN = re.compile(
    r"""^(?:[-+]?(?:0|[1-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
    |\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
    |[-+]?\.(?:inf|Inf|INF)
    |\.(?:nan|NaN|NAN))$""",
    re.X,
)


class _InputLoader(yaml.SafeLoader):
    """``SafeLoader`` whose int and float resolvers skip leading-zero and sexagesimal text."""


_InputLoader.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers if tag not in (_INT_TAG, _FLOAT_TAG)]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_InputLoader.add_implicit_resolver(_INT_TAG, _INT_PATTERN, list("-+0123456789"))
_InputLoader.add_implicit_resolver(_FLOAT_TAG, _FLOAT_PATTERN, list("-+0123456789."))


@dataclass(frozen=True)
class YamlSource:
    """Parsed YAML plus the 1-based line of each mapping key and sequence item, by path."""

    path: Path
    data: dict[str, Any]
    lines: Mapping[Loc, int]

    def line_for(self, loc: Loc) -> int | None:
        """Line of the longest prefix of ``loc`` that was recorded (so a missing key reports
        its parent's line); ``None`` when no prefix is known."""
        for length in range(len(loc), 0, -1):
            line = self.lines.get(loc[:length])
            if line is not None:
                return line
        return None


_PENDING: ContextVar[Mapping[Path, str] | None] = ContextVar("pending_texts", default=None)


@contextmanager
def pending_texts(texts: Mapping[Path, str]) -> Iterator[None]:
    """Inside the block, :func:`read_yaml` reads ``texts`` in place of those files, so an
    edit can be loaded and checked before it is written (ADR 0021)."""
    token = _PENDING.set({path.resolve(): text for path, text in texts.items()})
    try:
        yield
    finally:
        _PENDING.reset(token)


def read_yaml(path: Path) -> YamlSource:
    """Read ``path`` into a :class:`YamlSource`, or raise :class:`InputError`."""

    def fail(message: str, line: int | None = None) -> InputError:
        return InputError([Issue(path, "", message, line)])

    pending = (_PENDING.get() or {}).get(path.resolve())
    try:
        text = pending if pending is not None else path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise fail("file not found") from None
    except OSError as exc:
        raise fail(f"cannot read file: {exc.strerror or exc}") from None
    except UnicodeDecodeError:
        raise fail("not valid UTF-8 text") from None

    try:
        root = yaml.compose(text, Loader=_InputLoader)
        if not isinstance(root, yaml.MappingNode):
            raise fail("expected a mapping at the top level")
        lines: dict[Loc, int] = {}
        duplicates: list[Issue] = []
        _walk(root, (), path, lines, duplicates)
        if duplicates:
            raise InputError(duplicates)
        data = yaml.load(text, Loader=_InputLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        problem = getattr(exc, "problem", None) or str(exc)
        raise fail(problem, mark.line + 1 if mark is not None else None) from None
    return YamlSource(path, data, lines)


def _walk(
    node: yaml.Node,
    loc: Loc,
    path: Path,
    lines: dict[Loc, int],
    duplicates: list[Issue],
    active: frozenset[int] = frozenset(),
) -> None:
    """Record lines for ``node``'s children and collect duplicate mapping keys."""
    if id(node) in active:  # recursive alias
        return
    active = active | {id(node)}
    if isinstance(node, yaml.MappingNode):
        constructor = _InputLoader("")
        first_lines: dict[Any, int] = {}
        for key_node, value_node in node.value:
            if not isinstance(key_node, yaml.ScalarNode):
                continue  # safe_load reports unhashable keys
            if key_node.tag == _MERGE_TAG:
                continue  # merged keys are checked where their anchor is defined
            key = constructor.construct_object(key_node, deep=True)
            line = key_node.start_mark.line + 1
            child = (*loc, key)
            if key in first_lines:
                duplicates.append(
                    Issue(
                        path,
                        format_location(child),
                        f"duplicate key '{key}' (first at line {first_lines[key]})",
                        line,
                    )
                )
                continue
            first_lines[key] = line
            lines[child] = line
            _walk(value_node, child, path, lines, duplicates, active)
    elif isinstance(node, yaml.SequenceNode):
        for index, item in enumerate(node.value):
            child = (*loc, index)
            lines[child] = item.start_mark.line + 1
            _walk(item, child, path, lines, duplicates, active)
