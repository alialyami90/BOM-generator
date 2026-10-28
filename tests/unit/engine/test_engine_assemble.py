"""Assembly: revision marks per cell (spec: Output requirements OUT-8; Data model and
generation order, step 11)."""

import pytest
from engine_factories import panel

from bomgen.engine.assemble import mark_revisions
from bomgen.engine.errors import EngineError
from bomgen.models.bom import BomLine, Group


def lines() -> tuple[BomLine, ...]:
    return (
        BomLine(group=Group.A, tag="PANEL", description="x", qty=1),
        BomLine(group=Group.F, tag="PSA1-Q1.3", description="y", qty=1),
    )


def test_revision_marks_flag_the_listed_columns_of_the_tagged_row() -> None:
    p = panel(
        [{"part_id": "LAMP"}],
        revision={"highlight": [{"tag": "PSA1-Q1.3", "columns": ["C", "D"]}]},
    )
    marked = mark_revisions(p, lines())
    assert marked[0].revised == frozenset()
    assert marked[1].revised == frozenset({"C", "D"})


def test_revision_mark_for_an_unknown_tag_is_an_error() -> None:
    p = panel([{"part_id": "LAMP"}], revision={"highlight": [{"tag": "PSA1-Q9", "columns": ["C"]}]})
    with pytest.raises(EngineError, match="PSA1-Q9"):
        mark_revisions(p, lines())
