"""The Summary BOM: lines consolidated by ordering code across panels and loose material
(ADR 0035, plan M63)."""

from bomgen.engine.summary import summarize
from bomgen.models.bom import BomLine, BuildResult, Group, LooseTable, PanelBom, QtySum
from bomgen.models.calc import LineRef


def line(qty: int | str | QtySum = 1, **fields: object) -> BomLine:
    values: dict[str, object] = {"group": Group.E, "description": "2A,2P MCB", "qty": qty}
    return BomLine.model_validate(values | fields)


MCB = {"make": "Schneider", "model": "A9F74202", "ordering_code": "A9F74202"}


def panel(panel_id: str, sheet: str, *lines: BomLine) -> PanelBom:
    return PanelBom(title=("t", "t"), lines=lines, panel_id=panel_id, sheet_name=sheet)


def result(*panels: PanelBom, loose: LooseTable | None = None) -> BuildResult:
    return BuildResult(panels=panels, loose=loose)


def test_same_ordering_code_across_panels_sums_qty() -> None:
    summary = summarize(
        result(
            panel("p1", "1", line(tag="P1-Q1", **MCB), line(2, tag="P1-Q2", **MCB)),
            panel("p2", "2", line(tag="P2-Q1", **MCB)),
        )
    )
    (only,) = summary.lines
    assert only.qty == 4
    assert (only.make, only.model, only.ordering_code) == ("Schneider", "A9F74202", "A9F74202")
    assert [s.ref for s in only.sources] == [
        LineRef(panel_id="p1", line=0),
        LineRef(panel_id="p1", line=1),
        LineRef(panel_id="p2", line=0),
    ]


def test_description_is_the_first_seen() -> None:
    summary = summarize(
        result(
            panel("p1", "1", line(description="first", **MCB), line(description="second", **MCB))
        )
    )
    assert summary.lines[0].description == "first"


def test_free_text_items_group_by_description() -> None:
    loose = LooseTable(
        title=("t", "t"),
        host_panel="p1",
        lines=(line(description="Display cable"), line(3, description="Display cable")),
    )
    summary = summarize(result(panel("p1", "1", line(description="Display cable")), loose=loose))
    (only,) = summary.lines
    assert only.qty == 5
    assert only.sources[-1].ref == LineRef(panel_id=None, line=1)


def test_same_make_without_a_code_groups_by_description() -> None:
    summary = summarize(
        result(
            panel(
                "p1",
                "1",
                line(make="Hubbell", description="Fiber Management Spool"),
                line(make="Hubbell", description="Splice Holder"),
            )
        )
    )
    assert [s.description for s in summary.lines] == ["Fiber Management Spool", "Splice Holder"]


def test_text_quantity_stays_its_own_line() -> None:
    summary = summarize(
        result(
            panel(
                "p1",
                "1",
                line("1 Lot", description="Patch cords"),
                line("1 Lot", description="Patch cords"),
            )
        )
    )
    assert [s.qty for s in summary.lines] == ["1 Lot", "1 Lot"]


def test_formula_quantity_counts_its_value() -> None:
    summary = summarize(result(panel("p1", "1", line(QtySum(parts=(24, 3)), **MCB))))
    assert summary.lines[0].qty == 27


def test_where_used_lists_sheet_tag_qty() -> None:
    summary = summarize(
        result(
            panel("p1", "1", line(tag="P1-Q1", **MCB), line(2, tag="P1-Q2", **MCB), line(**MCB)),
            panel("p2", "2", line(tag="P2-Q1", **MCB)),
        )
    )
    sheets = {"p1": "1", "p2": "2", None: "Loose Material"}
    assert summary.lines[0].where_used(sheets) == "1: P1-Q1, P1-Q2 (4); 2: P2-Q1 (1)"


def test_lines_keep_first_seen_order() -> None:
    summary = summarize(
        result(
            panel("p1", "1", line(description="A"), line(**MCB)),
            panel("p2", "2", line(description="B"), line(description="A")),
        )
    )
    assert [s.description for s in summary.lines] == ["A", "2A,2P MCB", "B"]
