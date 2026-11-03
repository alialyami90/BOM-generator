"""The Revision History sheet (ADR 0035, ADR 0036, plan M66)."""

from dataclasses import replace
from datetime import date
from pathlib import Path

from bomgen.engine.pipeline import build
from bomgen.io.loader import LoadedSubstation, load_substation
from bomgen.models.sheet import SheetModel
from bomgen.models.substation import IssueRecord
from bomgen.sheets.history_sheet import HistoryRow, history_rows, history_sheet
from bomgen.sheets.workbook import build_workbook

EXAMPLE = Path(__file__).parents[3] / "examples" / "substations" / "gis01" / "substation.yaml"


def record(rev: str, day: int, **names: str) -> IssueRecord:
    return IssueRecord(
        rev=rev,
        date=date(2026, 11, day),
        file=Path(f"out/rev{rev}.xlsx"),
        sha256="a" * 64,
        description=f"Issue {rev}",
        **names,
    )


def with_issues(loaded: LoadedSubstation, *records: IssueRecord) -> LoadedSubstation:
    substation = loaded.substation.model_copy(update={"issues": list(records)})
    return replace(loaded, substation=substation)


def with_names(loaded: LoadedSubstation, **names: str) -> LoadedSubstation:
    key = loaded.substation.document
    documents = dict(loaded.documents)
    documents[key] = documents[key].model_copy(update=names)
    return replace(loaded, documents=documents)


def test_no_history_sheet_without_records_or_names() -> None:
    loaded = load_substation(EXAMPLE)
    names = [s.name for s in build_workbook(loaded, build(loaded)).sheets]
    assert "Revision History" not in names


def test_rows_are_the_records_then_the_current_revision() -> None:
    loaded = with_issues(load_substation(EXAMPLE), record("00", 1, prepared="A. Eng"))
    document = loaded.documents[loaded.substation.document]
    assert history_rows(loaded) == [
        HistoryRow("00", date(2026, 11, 1), "Issue 00", "A. Eng", None, None),
        HistoryRow(document.rev, document.issue_date, "", None, None, None),
    ]


def test_the_current_revision_is_not_repeated_once_recorded() -> None:
    loaded = load_substation(EXAMPLE)
    rev = loaded.documents[loaded.substation.document].rev
    assert [r.rev for r in history_rows(with_issues(loaded, record(rev, 2)))] == [rev]


def test_names_on_the_register_alone_write_the_sheet() -> None:
    loaded = with_names(load_substation(EXAMPLE), prepared="A. Eng", approved="C. Boss")
    sheets = build_workbook(loaded, build(loaded)).sheets
    assert sheets[-1].name == "Revision History"
    row = history_rows(loaded)[0]
    assert (row.prepared, row.checked, row.approved) == ("A. Eng", None, "C. Boss")


def cell(model: SheetModel, ref: str) -> object:
    found = model.cells.get((int(ref[1:]), ord(ref[0]) - ord("A") + 1))
    return None if found is None else found.value


def test_layout() -> None:
    rows = [HistoryRow("00", date(2026, 11, 1), "For review", "A", "B", "C")]
    m = history_sheet("Revision History", "GIS Substation", rows)
    assert cell(m, "A1") == "GIS Substation\nRevision History"
    assert [cell(m, f"{c}2") for c in "ABCDEF"] == [
        "REV",
        "DATE",
        "DESCRIPTION",
        "PREPARED",
        "CHECKED",
        "APPROVED",
    ]
    assert [cell(m, f"{c}3") for c in "ABCDEF"] == ["00", "2026-11-01", "For review", "A", "B", "C"]
    setup = m.print_setup
    assert setup.orientation == "portrait"
    assert setup.repeat_rows == (1, 2)
    assert setup.print_area is not None
    assert setup.print_area.name == "A1:F3"
