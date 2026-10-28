"""Assembly of a panel's lines (spec: Data model and generation order, step 11).

Lines arrive in group order A-H; separators and SR.NO follow from that order
(``BomTable.separators_before``), merges from ``parent`` and ``merge_fg``.
"""

from collections.abc import Sequence

from bomgen.engine.errors import EngineError
from bomgen.models.bom import BomLine
from bomgen.models.panel import Panel


def mark_revisions(panel: Panel, lines: Sequence[BomLine]) -> tuple[BomLine, ...]:
    """Flag the cells the panel's ``revision.highlight`` lists (OUT-8)."""
    marks: dict[str, set[str]] = {}
    for mark in panel.revision.highlight:
        marks.setdefault(mark.tag, set()).update(mark.columns)
    unknown = sorted(set(marks) - {line.tag for line in lines if line.tag})
    if unknown:
        raise EngineError(f"{panel.id}: revision.highlight names no row: {', '.join(unknown)}")
    return tuple(
        line.model_copy(update={"revised": frozenset(marks[line.tag])})
        if line.tag in marks
        else line
        for line in lines
    )
