"""Assembly of a panel's lines (spec: Data model and generation order, step 11).

Lines arrive in group order A-H; separators and SR.NO follow from that order
(``BomTable.separators_before``), merges from ``parent`` and ``merge_fg``.
"""

from collections.abc import Sequence

from bomgen.engine.errors import EngineError
from bomgen.models.bom import BomLine, BuildResult
from bomgen.models.panel import Panel
from bomgen.models.substation import RowMark


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


def mark_rows(result: BuildResult, marks: Sequence[RowMark]) -> BuildResult:
    """Flag the cells of the rows marked as revised for the next issue (plan M79); a mark
    whose row is gone is left for the change list to report."""
    if not marks:
        return result
    wanted: dict[tuple[str | None, str], set[str]] = {}
    for mark in marks:
        wanted.setdefault((mark.panel_id, mark.tag), set()).update(mark.columns)

    def lines(panel_id: str | None, table: Sequence[BomLine]) -> tuple[BomLine, ...]:
        return tuple(
            line.model_copy(update={"revised": line.revised | wanted[(panel_id, line.tag)]})
            if line.tag is not None and (panel_id, line.tag) in wanted
            else line
            for line in table
        )

    panels = tuple(
        p.model_copy(update={"lines": lines(p.panel_id, p.lines)}) for p in result.panels
    )
    loose = result.loose
    if loose is not None:
        loose = loose.model_copy(update={"lines": lines(None, loose.lines)})
    return result.model_copy(update={"panels": panels, "loose": loose})
