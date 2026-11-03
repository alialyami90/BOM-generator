"""The Summary BOM: every panel's and the loose material's lines consolidated for
procurement (ADR 0035, plan M63).

A line with a model or ordering code groups by (make, model, ordering code); any other
line groups by (make, description). A text quantity ("1 Lot") is never summed: it stays
its own line.
"""

from bomgen.models.bom import (
    BomLine,
    BomTable,
    BuildResult,
    QtySum,
    SummaryLine,
    SummarySource,
    SummaryTable,
)
from bomgen.models.calc import LineRef


def summarize(result: BuildResult) -> SummaryTable:
    tables: list[tuple[str | None, BomTable]] = [(p.panel_id, p) for p in result.panels]
    if result.loose is not None:
        tables.append((None, result.loose))
    groups: dict[tuple[object, ...], list[tuple[BomLine, SummarySource]]] = {}
    for table_id, table in tables:
        for index, bom_line in enumerate(table.lines):
            qty = bom_line.qty.value if isinstance(bom_line.qty, QtySum) else bom_line.qty
            source = SummarySource(
                ref=LineRef(panel_id=table_id, line=index), tag=bom_line.tag, qty=qty
            )
            groups.setdefault(_key(bom_line, source), []).append((bom_line, source))
    return SummaryTable(lines=tuple(_line(members) for members in groups.values()))


def _key(bom_line: BomLine, source: SummarySource) -> tuple[object, ...]:
    if isinstance(source.qty, str):
        return ("text-qty", source.ref)
    if bom_line.model or bom_line.ordering_code:
        return ("part", bom_line.make, bom_line.model, bom_line.ordering_code)
    return ("item", bom_line.make, bom_line.description)


def _line(members: list[tuple[BomLine, SummarySource]]) -> SummaryLine:
    first, _ = members[0]
    sources = tuple(source for _, source in members)
    qty: int | str = sources[0].qty
    if isinstance(qty, int):
        qty = sum(source.qty for source in sources if isinstance(source.qty, int))
    return SummaryLine(
        description=first.description,
        qty=qty,
        make=first.make,
        model=first.model,
        ordering_code=first.ordering_code,
        sources=sources,
    )
