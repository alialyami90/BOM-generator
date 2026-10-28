"""Revision comparison with the previous issue (spec: Output requirements, OUT-8; plan
M7, Q10; ADR 0016).

Reads the BOM tables of a previously issued workbook and marks the cells of the new
build whose written value differs, as yellow highlighting on top of the panel files'
``revision.highlight``. Rows match by tag; rows without one match under the tag above
them, first by description, then in order.
"""

import zipfile
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

from bomgen.io.errors import InputError, Issue
from bomgen.models.bom import BomLine, BomTable, BuildResult, Column, QtySum
from bomgen.models.report import (
    PreviousIssue,
    PreviousTable,
    RevisionChange,
    RevisionKind,
    RevisionReport,
)

# The panel BOM column headers A-G (spec: Columns of a panel BOM).
BOM_HEADERS = (
    "SR.NO",
    "ITEM DESIGNATION",
    "DESCRIPTION",
    "QUANTITY",
    "MAKE",
    "MODEL",
    "ORDERING CODE",
)
COLUMNS: tuple[Column, ...] = ("B", "C", "D", "E", "F", "G", "H")

Cells = dict[Column, str]
_Key = Callable[[Cells, str], tuple[str, ...] | None]


def read_previous_issue(path: Path) -> PreviousIssue:
    """Every BOM table of the workbook at ``path``, from the values Excel last saved."""
    try:
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except (OSError, KeyError, zipfile.BadZipFile, InvalidFileException) as error:
        message = f"not a readable .xlsx workbook ({error})"
        raise InputError([Issue(file=path, location="", message=message)]) from None
    try:
        sheets = {}
        for sheet in book.worksheets:
            tables = tuple(_tables(sheet.iter_rows(max_col=8, values_only=True)))
            if tables:
                sheets[sheet.title] = tables
    finally:
        book.close()
    return PreviousIssue(source=path.name, sheets=sheets)


def _tables(rows: Iterator[tuple[object, ...]]) -> Iterator[PreviousTable]:
    """A table starts at a BOM header row; its rows are those with a description."""
    current: list[Cells] | None = None
    for values in rows:
        text = [_text(value) for value in (*values, *(None,) * 8)[:8]]
        if tuple(text[:7]) == BOM_HEADERS:
            if current is not None:
                yield PreviousTable(rows=tuple(current))
            current = []
        elif current is not None and text[2]:
            current.append(dict(zip(COLUMNS, text[1:], strict=True)))
    if current is not None:
        yield PreviousTable(rows=tuple(current))


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).replace("\r\n", "\n").strip()


def compare_with_previous(
    result: BuildResult, previous: PreviousIssue
) -> tuple[BuildResult, RevisionReport]:
    """``result`` with changed and added cells marked, and the list of changes."""
    sheets = {panel.panel_id: panel.sheet_name for panel in result.panels}
    changes: list[RevisionChange] = []
    used: set[tuple[str, int]] = set()

    def against(table: BomTable, sheet: str, index: int) -> tuple[BomLine, ...]:
        tables = previous.sheets.get(sheet, ())
        before = tables[index].rows if index < len(tables) else ()
        used.add((sheet, index))
        lines, found = _compare_table(table.lines, before, sheet)
        changes.extend(found)
        return lines

    panels = tuple(
        panel.model_copy(update={"lines": against(panel, panel.sheet_name, 0)})
        for panel in result.panels
    )
    loose = result.loose
    if loose is not None:
        loose = loose.model_copy(update={"lines": against(loose, sheets[loose.host_panel], 1)})
    for sheet, tables in previous.sheets.items():
        for index, table in enumerate(tables):
            if (sheet, index) not in used:
                changes.extend(_removed(sheet, table.rows, range(len(table.rows))))
    marked = result.model_copy(update={"panels": panels, "loose": loose})
    return marked, RevisionReport(previous=previous.source, changes=tuple(changes))


def _compare_table(
    lines: Sequence[BomLine], before: Sequence[Cells], sheet: str
) -> tuple[tuple[BomLine, ...], list[RevisionChange]]:
    now = [_cells(line) for line in lines]
    pairs = _match(now, before)
    out: list[BomLine] = []
    changes: list[RevisionChange] = []
    anchors = _anchors(now)
    for index, (line, cells) in enumerate(zip(lines, now, strict=True)):
        old = pairs.get(index)
        if old is None:
            kind, columns = RevisionKind.ADDED, frozenset(COLUMNS)
        else:
            columns = frozenset(c for c in COLUMNS if cells[c] != before[old][c])
            kind = RevisionKind.CHANGED
        if columns:
            out.append(line.model_copy(update={"revised": line.revised | columns}))
            change = RevisionChange(
                sheet=sheet,
                kind=kind,
                tag=anchors[index] or None,
                description=line.description,
                columns=columns if kind is RevisionKind.CHANGED else frozenset(),
            )
            changes.append(change)
        else:
            out.append(line)
    gone = sorted(set(range(len(before))) - set(pairs.values()))
    changes.extend(_removed(sheet, before, gone))
    return tuple(out), changes


def _removed(sheet: str, rows: Sequence[Cells], indexes: Sequence[int]) -> list[RevisionChange]:
    anchors = _anchors(rows)
    return [
        RevisionChange(
            sheet=sheet,
            kind=RevisionKind.REMOVED,
            tag=anchors[i] or None,
            description=rows[i]["C"],
        )
        for i in indexes
    ]


def _cells(line: BomLine) -> Cells:
    """The B-H text the writer puts on ``line``'s row; a kit child's tag cell is merged
    under its parent's."""
    qty = line.qty
    return {
        "B": "" if line.parent is not None else _text(line.tag),
        "C": _text(line.description),
        "D": _text(qty.value if isinstance(qty, QtySum) else qty),
        "E": _text(line.make),
        "F": _text(line.model),
        "G": _text(line.ordering_code),
        "H": _text(line.hwio or None),
    }


def _anchors(rows: Sequence[Cells]) -> list[str]:
    """Each row's own tag, or the last tag above it."""
    anchors, tag = [], ""
    for cells in rows:
        tag = cells["B"] or tag
        anchors.append(tag)
    return anchors


def _match(now: Sequence[Cells], before: Sequence[Cells]) -> dict[int, int]:
    """Current row → previous row: tagged rows by tag and occurrence; untagged rows
    under the same tag by description and occurrence, then the rest in order."""
    pairs: dict[int, int] = {}
    for key in (_tag_key, _description_key, _order_key):
        free = defaultdict(list)
        for index, key_value in _keys(before, key, set(pairs.values())):
            free[key_value].append(index)
        for index, key_value in _keys(now, key, set(pairs)):
            if free.get(key_value):
                pairs[index] = free[key_value].pop(0)
    return pairs


def _keys(
    rows: Sequence[Cells], key: _Key, taken: set[int]
) -> Iterator[tuple[int, tuple[str, ...]]]:
    seen: defaultdict[tuple[str, ...], int] = defaultdict(int)
    anchors = _anchors(rows)
    for index, cells in enumerate(rows):
        if index in taken:
            continue
        base = key(cells, anchors[index])
        if base is None:
            continue
        seen[base] += 1
        yield index, (*base, str(seen[base]))


def _tag_key(cells: Cells, anchor: str) -> tuple[str, ...] | None:
    return ("tag", cells["B"]) if cells["B"] else None


def _description_key(cells: Cells, anchor: str) -> tuple[str, ...] | None:
    return None if cells["B"] else ("description", anchor, cells["C"])


def _order_key(cells: Cells, anchor: str) -> tuple[str, ...] | None:
    return None if cells["B"] else ("order", anchor)


def render_revisions(report: RevisionReport) -> str:
    """One line per change, then the counts."""
    lines = []
    for change in report.changes:
        parts = [
            change.sheet,
            change.tag or "",
            change.description,
            ",".join(sorted(change.columns)),
        ]
        lines.append(f"{change.kind.value:<7}  " + "  ".join(p for p in parts if p))
    counts = ", ".join(
        f"{sum(1 for c in report.changes if c.kind is kind)} {kind.value}" for kind in RevisionKind
    )
    lines.append(f"against {report.previous}: {counts}")
    return "\n".join(lines)
