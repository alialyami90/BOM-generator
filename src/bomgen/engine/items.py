"""A BOM line with its kit children, and flattening into table order."""

from collections.abc import Iterable
from dataclasses import dataclass

from bomgen.models.bom import BomLine


@dataclass(frozen=True)
class BomItem:
    """A parent line and the child lines printed right under it."""

    line: BomLine
    children: tuple[BomLine, ...] = ()


def flatten(items: Iterable[BomItem]) -> tuple[BomLine, ...]:
    """Lines in order, each child pointing at its parent's index."""
    lines: list[BomLine] = []
    for item in items:
        parent = len(lines)
        lines.append(item.line)
        lines.extend(child.model_copy(update={"parent": parent}) for child in item.children)
    return tuple(lines)
