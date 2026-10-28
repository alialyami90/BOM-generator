"""Revision comparison with the previous issue (spec: Output requirements, OUT-8; plan
M7, Q10; ADR 0016)."""

from pathlib import Path
from typing import Any, cast

import openpyxl
import pytest

from bomgen.io.errors import InputError
from bomgen.models.bom import BomLine, BuildResult, Column, Group, LooseTable, PanelBom, Qty, QtySum
from bomgen.models.report import PreviousIssue, PreviousTable, RevisionChange, RevisionKind
from bomgen.revision import compare_with_previous, read_previous_issue, render_revisions

HEADERS = ("SR.NO", "ITEM DESIGNATION", "DESCRIPTION", "QUANTITY", "MAKE", "MODEL", "ORDERING CODE")
ALL: frozenset[Column] = frozenset("BCDEFGH")  # type: ignore[arg-type]


def line(tag: str | None, description: str, qty: Qty = 1, **fields: Any) -> BomLine:
    return BomLine(group=Group.B, tag=tag, description=description, qty=qty, **fields)


def result(*lines: BomLine, loose: tuple[BomLine, ...] = ()) -> BuildResult:
    panel = PanelBom(panel_id="p1", sheet_name="1", title=("001", "S - P"), lines=lines)
    table = LooseTable(title=("S", "Loose"), lines=loose, host_panel="p1") if loose else None
    return BuildResult(panels=(panel,), loose=table)


def row(tag: str = "", description: str = "", qty: str = "1", **cells: str) -> dict[Column, str]:
    out: dict[Column, str] = {
        "B": tag,
        "C": description,
        "D": qty,
        "E": "",
        "F": "",
        "G": "",
        "H": "",
    }
    out.update(cast(dict[Column, str], cells))
    return out


def previous(*rows: dict[Column, str], loose: tuple[dict[Column, str], ...] = ()) -> PreviousIssue:
    tables = [PreviousTable(rows=rows)]
    if loose:
        tables.append(PreviousTable(rows=loose))
    return PreviousIssue(source="rev0.xlsx", sheets={"1": tuple(tables)})


def compare(
    current: BuildResult, before: PreviousIssue
) -> tuple[list[frozenset[Column]], list[RevisionChange]]:
    marked, report = compare_with_previous(current, before)
    return [x.revised for x in marked.panels[0].lines], list(report.changes)


def test_unchanged_rows_are_not_marked() -> None:
    revised, changes = compare(
        result(line("Q1", "6A MCB", 2, make="Schneider")),
        previous(row("Q1", "6A MCB", "2", E="Schneider")),
    )
    assert revised == [frozenset()]
    assert changes == []


def test_changed_cells_of_a_tagged_row_are_marked() -> None:
    revised, changes = compare(result(line("Q1", "10A MCB", 3)), previous(row("Q1", "6A MCB", "2")))
    assert revised == [frozenset({"C", "D"})]
    assert [(c.kind, c.tag, c.columns) for c in changes] == [
        (RevisionKind.CHANGED, "Q1", frozenset({"C", "D"}))
    ]


def test_marks_join_the_manual_highlight() -> None:
    revised, _ = compare(
        result(line("Q1", "6A MCB", 3, revised=frozenset({"F"}))), previous(row("Q1", "6A MCB"))
    )
    assert revised == [frozenset({"D", "F"})]


def test_added_rows_are_marked_in_full_and_removed_rows_reported() -> None:
    revised, changes = compare(
        result(line("Q1", "6A MCB"), line("Q3", "2A MCB")),
        previous(row("Q1", "6A MCB"), row("Q2", "4A MCB")),
    )
    assert revised == [frozenset(), ALL]
    assert [(c.kind, c.tag) for c in changes] == [
        (RevisionKind.ADDED, "Q3"),
        (RevisionKind.REMOVED, "Q2"),
    ]


def test_untagged_rows_match_by_description_under_their_tag() -> None:
    # Kit children leave B empty; one inserted above another must not mark the rest.
    revised, changes = compare(
        result(
            line("K1", "Kit"),
            line(None, "Card A", parent=0),
            line(None, "Card B", parent=0),
            line(None, "Card C", 2, parent=0),
        ),
        previous(row("K1", "Kit"), row("", "Card A"), row("", "Card C")),
    )
    assert revised == [frozenset(), frozenset(), ALL, frozenset({"D"})]
    assert [(c.kind, c.tag, c.description) for c in changes] == [
        (RevisionKind.ADDED, "K1", "Card B"),
        (RevisionKind.CHANGED, "K1", "Card C"),
    ]


def test_untagged_rows_with_a_new_description_pair_in_order() -> None:
    revised, _ = compare(
        result(line("K1", "Kit"), line(None, "Card A2", parent=0)),
        previous(row("K1", "Kit"), row("", "Card A")),
    )
    assert revised == [frozenset(), frozenset({"C"})]


def test_repeated_tags_match_in_order() -> None:
    revised, _ = compare(
        result(line("SFP", "SFP MM", 4), line("SFP", "SFP SM", 2)),
        previous(row("SFP", "SFP MM", "4"), row("SFP", "SFP SM", "1")),
    )
    assert revised == [frozenset(), frozenset({"D"})]


def test_cells_compare_as_written() -> None:
    # The sum formula's value, the lot text and HWIO 0 left blank.
    revised, _ = compare(
        result(line("SFP", "SFP", QtySum(parts=(24, 3))), line("LOT", "Cable", "1 Lot", hwio=0)),
        previous(row("SFP", "SFP", "27"), row("LOT", "Cable", "1 Lot")),
    )
    assert revised == [frozenset(), frozenset()]


def test_kit_children_compare_with_column_b_empty() -> None:
    # The tag column is merged over a kit's children, so a child's tag never shows.
    revised, _ = compare(
        result(line("K1", "Kit"), line("K1-C", "Card", parent=0)),
        previous(row("K1", "Kit"), row("", "Card")),
    )
    assert revised == [frozenset(), frozenset()]


def test_loose_table_is_the_second_table_on_its_host_sheet() -> None:
    marked, report = compare_with_previous(
        result(line("Q1", "6A MCB"), loose=(line("ANN", "Annunciator", 2),)),
        previous(row("Q1", "6A MCB"), loose=(row("ANN", "Annunciator", "1"),)),
    )
    assert marked.loose is not None
    assert [x.revised for x in marked.loose.lines] == [frozenset({"D"})]
    assert [c.sheet for c in report.changes] == ["1"]


def test_a_new_sheet_is_marked_and_a_dropped_sheet_reported() -> None:
    before = PreviousIssue(
        source="rev0.xlsx", sheets={"9": (PreviousTable(rows=(row("X1", "Old"),)),)}
    )
    revised, changes = compare(result(line("Q1", "6A MCB")), before)
    assert revised == [ALL]
    assert [(c.sheet, c.kind) for c in changes] == [
        ("1", RevisionKind.ADDED),
        ("9", RevisionKind.REMOVED),
    ]


def write_issue(path: Path, rows: list[tuple[Any, ...]]) -> Path:
    book = openpyxl.Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "1"
    for values in rows:
        sheet.append(values)
    book.create_sheet("Power Consumption").append(("SR.NO", "x", "y"))
    book.save(path)
    return path


def test_previous_issue_tables_start_at_the_bom_header(tmp_path: Path) -> None:
    path = write_issue(
        tmp_path / "rev0.xlsx",
        [
            ("001\nS - P",),
            HEADERS,
            (1, "Q1", " 6A MCB ", 2.0, "Schneider", None, "A9F74206", 4),
            (None,) * 7,  # a separator
            (2, None, "Card\r\nA", 1),
            ("S\nLoose",),
            HEADERS,
            (1, "ANN", "Annunciator", "1 Lot"),
        ],
    )
    issue = read_previous_issue(path)
    assert issue.source == "rev0.xlsx"
    assert list(issue.sheets) == ["1"]  # no BOM header on the calculation sheet
    panel, loose = issue.sheets["1"]
    assert panel.rows == (
        row("Q1", "6A MCB", "2", E="Schneider", G="A9F74206", H="4"),
        row("", "Card\nA", "1"),
    )
    assert loose.rows == (row("ANN", "Annunciator", "1 Lot"),)


def test_unreadable_previous_issue_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "rev0.xlsx"
    path.write_text("not a workbook")
    with pytest.raises(InputError, match=r"rev0\.xlsx: not a readable \.xlsx workbook"):
        read_previous_issue(path)


def test_revisions_render_one_line_per_change() -> None:
    _, report = compare_with_previous(
        result(line("Q1", "10A MCB"), line("Q3", "2A MCB")),
        previous(row("Q1", "6A MCB"), row("Q2", "4A MCB")),
    )
    assert render_revisions(report).splitlines() == [
        "changed  1  Q1  10A MCB  C",
        "added    1  Q3  2A MCB",
        "removed  1  Q2  4A MCB",
        "against rev0.xlsx: 1 changed, 1 added, 1 removed",
    ]
