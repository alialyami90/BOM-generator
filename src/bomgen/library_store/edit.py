"""Edit a library by path: set, insert and remove (ADR 0018).

An edit names a place in the library by a path of segments and says what to do there. A
string segment is a key of a mapping, or, in a list, the `part_id` (devices) or `id` (catalogue
brands) of the item; an integer segment is a position in a list. So
``["devices", "PSU-24", "voltage_v"]`` is a device's voltage and ``["devices", "SW-1", "ports",
0, "count"]`` the count of its first port group. Edits are plain JSON, so the app can send
them as they are, and every field of the model is reachable without a function per field.

The edited library is checked as a whole with the same rules the loader applies, so an edit
that would leave a dangling reference (deleting a part another part uses) is a problem, not
a surprise at build time.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    TypeAdapter,
    ValidationError,
)

from bomgen.io.errors import Loc, issues_from_validation_error
from bomgen.io.references import library_issues
from bomgen.io.yaml_source import YamlSource
from bomgen.library_store.manifest import LIBRARY_FILE
from bomgen.models.library import Library

Segment = StrictStr | StrictInt
_IDENTITY_KEYS = ("part_id", "id")


class _Edit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Annotated[list[Segment], Field(min_length=1)]


class SetValue(_Edit):
    """Put `value` at `path`: a field, a mapping key (new or existing) or a whole list item."""

    op: Literal["set"] = "set"
    value: Any


class Insert(_Edit):
    """Add `value` to the list at `path`, at the end or before position `index`."""

    op: Literal["insert"] = "insert"
    value: Any
    index: Annotated[int, Field(ge=0)] | None = None


class Remove(_Edit):
    """Delete the field, mapping key or list item at `path`."""

    op: Literal["remove"] = "remove"


Edit = Annotated[SetValue | Insert | Remove, Field(discriminator="op")]
_EDITS = TypeAdapter(list[Edit])


def parse_edits(raw: Sequence[object]) -> list[SetValue | Insert | Remove]:
    """Edits from plain JSON; raises pydantic's `ValidationError` for a malformed one."""
    return _EDITS.validate_python(list(raw))


@dataclass(frozen=True)
class Problem:
    """Something wrong with the edited library, at `location` (e.g. ``devices[SW-1].ports[0]``)."""

    location: str
    message: str


@dataclass(frozen=True)
class EditResult:
    """The edited library, or `None` and every problem that stops it from being one."""

    library: Library | None
    problems: list[Problem] = field(default_factory=list)


class _PathError(Exception):
    pass


def apply_edits(library: Library, edits: Sequence[SetValue | Insert | Remove]) -> EditResult:
    """Apply `edits` in order to a copy of `library`; the argument is never changed."""
    data = copy.deepcopy(library.model_dump(mode="json"))
    for edit in edits:
        try:
            _apply(data, edit)
        except _PathError as exc:
            return EditResult(None, [Problem(_describe(edit.path), str(exc))])
    problems = _problems(data)
    if problems:
        return EditResult(None, problems)
    return EditResult(Library.model_validate(data))


def check_field(library: Library, path: Sequence[str | int], value: object) -> str | None:
    """The message for setting `path` to `value`, or `None` when the library stays valid.

    Only problems the change causes count; ones the library already had are not blamed on it.
    """
    data = copy.deepcopy(library.model_dump(mode="json"))
    before = {(p.location, p.message) for p in _problems(data)}
    try:
        _apply(data, SetValue(path=list(path), value=value))
    except _PathError as exc:
        return str(exc)
    for problem in _problems(data):
        if (problem.location, problem.message) not in before:
            return problem.message
    return None


# -- applying -----------------------------------------------------------------------------


def _apply(data: dict[str, Any], edit: SetValue | Insert | Remove) -> None:
    path = edit.path
    if isinstance(edit, Insert):
        target = _walk(data, path)
        if not isinstance(target, list):
            raise _PathError(f"{_describe(path)} is not a list, so nothing can be inserted")
        if edit.index is not None and edit.index > len(target):
            raise _PathError(f"{_describe(path)} has {len(target)} items; no position {edit.index}")
        position = len(target) if edit.index is None else edit.index
        target.insert(position, copy.deepcopy(edit.value))
        return
    parent = _walk(data, path[:-1])
    last = path[-1]
    if isinstance(parent, dict):
        if not isinstance(last, str):
            raise _PathError(f"{_describe(path[:-1])} is a mapping; {last!r} is not a key")
        if isinstance(edit, Remove):
            if last not in parent:
                raise _PathError(f"{_describe(path)} does not exist")
            del parent[last]
        else:
            parent[last] = copy.deepcopy(edit.value)
    elif isinstance(parent, list):
        index = _index(parent, last, path)
        if isinstance(edit, Remove):
            del parent[index]
        else:
            parent[index] = copy.deepcopy(edit.value)
    else:
        raise _PathError(f"{_describe(path[:-1])} holds a single value, not fields")


def _walk(node: Any, path: Sequence[str | int]) -> Any:
    for depth, segment in enumerate(path):
        if isinstance(node, dict):
            if not isinstance(segment, str) or segment not in node:
                raise _PathError(f"{_describe(path[: depth + 1])} does not exist")
            node = node[segment]
        elif isinstance(node, list):
            node = node[_index(node, segment, path[: depth + 1])]
        else:
            raise _PathError(f"{_describe(path[:depth])} holds a single value, not fields")
    return node


def _index(items: list[Any], segment: str | int, path: Sequence[str | int]) -> int:
    if isinstance(segment, int):
        if 0 <= segment < len(items):
            return segment
        raise _PathError(f"{_describe(path)} does not exist (the list has {len(items)} items)")
    for index, item in enumerate(items):
        if isinstance(item, dict) and segment in (item.get(key) for key in _IDENTITY_KEYS):
            return index
    raise _PathError(f"{_describe(path)} does not exist: no item {segment!r}")


def _describe(path: Sequence[str | int]) -> str:
    text = ""
    for segment in path:
        text += f"[{segment}]" if isinstance(segment, int) else f".{segment}" if text else segment
    return text


# -- checking -----------------------------------------------------------------------------


@dataclass(frozen=True)
class _Located(YamlSource):
    """Records the location of every issue made from it (they ask for its line, in order)."""

    locs: list[Loc] = field(default_factory=list)

    def line_for(self, loc: Loc) -> int | None:
        self.locs.append(loc)
        return None


def _problems(data: dict[str, Any]) -> list[Problem]:
    source = _Located(Path(LIBRARY_FILE), data, {})
    try:
        library = Library.model_validate(data)
    except ValidationError as exc:
        issues = issues_from_validation_error(exc, source)
    else:
        issues = library_issues(library, source)
    return [
        Problem(_named(loc, data), issue.message)
        for loc, issue in zip(source.locs, issues, strict=True)
    ]


def _named(loc: Loc, data: dict[str, Any]) -> str:
    """`devices[SW-1].ports[0].count` for a location, naming list items by their id."""
    text = ""
    node: Any = data
    for segment in loc:
        if isinstance(segment, int) and isinstance(node, list) and segment < len(node):
            item = node[segment]
            name = next(
                (item[k] for k in _IDENTITY_KEYS if isinstance(item, dict) and k in item), None
            )
            text += f"[{name if name is not None else segment}]"
            node = item
        elif isinstance(segment, int):
            text += f"[{segment}]"
            node = None
        else:
            text += f".{segment}" if text else segment
            node = node.get(segment) if isinstance(node, dict) else None
    return text
