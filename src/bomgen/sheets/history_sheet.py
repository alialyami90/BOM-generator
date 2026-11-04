"""The Revision History sheet: one row per recorded issue, then the current revision,
after the Summary BOM (ADR 0035, ADR 0036, plan M66; the OVERRIDES column, ADR 0040).

Laid out like the Summary BOM sheet, A4 portrait. Written when the substation has a
recorded issue or its main document has prepared, checked or approved names.
"""

from collections.abc import Sequence
from datetime import date
from typing import NamedTuple

from bomgen.io.loader import LoadedSubstation
from bomgen.models.sheet import CellRange, HeaderFooter, PrintSetup, SheetModel
from bomgen.models.substation import OverrideNote
from bomgen.sheets import styles
from bomgen.sheets.grid import SheetBuilder
from bomgen.sheets.summary_sheet import CENTRE, HEADER, TEXT, TITLE_HEIGHT, TITLE_STYLE

HEADERS = ("REV", "DATE", "DESCRIPTION", "PREPARED", "CHECKED", "APPROVED", "OVERRIDES")
WIDTHS = (8.0, 14.0, 50.0, 20.0, 20.0, 20.0, 50.0)
CELL_STYLES = (CENTRE, CENTRE, TEXT, TEXT, TEXT, TEXT, TEXT)
TITLE = "Revision History"


class HistoryRow(NamedTuple):
    rev: str
    date: date
    description: str
    prepared: str | None
    checked: str | None
    approved: str | None
    overrides: str = ""  # the risky overrides recorded with the issue, one per line (ADR 0040)


def override_lines(notes: Sequence[OverrideNote]) -> str:
    """What the OVERRIDES cell says: where, what, instead of what, and why."""
    lines = []
    for note in notes:
        where = f"{note.panel_id} " if note.panel_id else ""
        line = f"{where}{note.subject}: {note.override} instead of {note.automatic}"
        lines.append(line + (f": {note.reason}" if note.reason else " (no reason given)"))
    return "\n".join(lines)


def history_rows(loaded: LoadedSubstation) -> list[HistoryRow]:
    """The recorded issues, then the main document's current revision unless recorded;
    empty when there is nothing to show."""
    document = loaded.documents[loaded.substation.document]
    records = loaded.substation.issues
    names = (document.prepared, document.checked, document.approved)
    if not records and not any(names):
        return []
    rows = [
        HistoryRow(
            r.rev,
            r.date,
            r.description,
            r.prepared,
            r.checked,
            r.approved,
            override_lines(r.overrides),
        )
        for r in records
    ]
    if document.rev not in {r.rev for r in records}:
        rows.append(HistoryRow(document.rev, document.issue_date, "", *names))
    return rows


def history_sheet(
    name: str,
    substation: str,
    rows: Sequence[HistoryRow],
    header_footer: HeaderFooter | None = None,
) -> SheetModel:
    sheet = SheetBuilder(name)
    for col, width in enumerate(WIDTHS, start=1):
        sheet.width(col, width)
    last_col = len(HEADERS)
    sheet.merge(1, 1, 1, last_col, f"{substation}\n{TITLE}", TITLE_STYLE)
    sheet.height(1, TITLE_HEIGHT)
    for col, label in enumerate(HEADERS, start=1):
        sheet.set(2, col, label, HEADER)
    row = 2
    for entry in rows:
        row += 1
        values = (entry.rev, entry.date.isoformat(), *entry[2:])  # the overrides last
        for col, (value, style) in enumerate(zip(values, CELL_STYLES, strict=True), start=1):
            sheet.set(row, col, value, style)
    setup = PrintSetup(
        orientation="portrait",
        fit_to_width=1,
        fit_to_height=0,
        margins=styles.BOM_MARGINS,
        center_horizontally=True,
        print_area=CellRange(first_row=1, first_col=1, last_row=row, last_col=last_col),
        repeat_rows=(1, 2),
    )
    return sheet.build(setup, header_footer)
