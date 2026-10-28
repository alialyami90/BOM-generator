"""BOM line models (spec: Columns of a panel BOM; Data model and generation order)."""

import pytest
from pydantic import ValidationError

from bomgen.models.bom import BomLine, BomTable, Group, QtySum


def line(group: Group, description: str = "x") -> BomLine:
    return BomLine(group=group, description=description, qty=1)


def test_qty_sum_value_is_sum_of_parts() -> None:
    # Derivation rules -> Network accessories: L1 SFPs entered as =24+3.
    assert QtySum(parts=(24, 3)).value == 27


def test_qty_sum_needs_two_parts() -> None:
    with pytest.raises(ValidationError):
        QtySum(parts=(24,))


def test_separator_before_groups_e_to_h_only() -> None:
    # How each panel BOM groups its materials: one empty row before E, F, G, H;
    # A-D run together.
    groups = [Group.A, Group.B, Group.C, Group.D, Group.E, Group.E, Group.F, Group.G, Group.H]
    table = BomTable(title=("t1", "t2"), lines=tuple(line(g) for g in groups))
    assert table.separators_before() == (4, 6, 7, 8)


def test_separator_skips_missing_groups() -> None:
    table = BomTable(title=("t1", "t2"), lines=(line(Group.A), line(Group.G)))
    assert table.separators_before() == (1,)


def test_bom_line_is_frozen() -> None:
    bom_line = line(Group.A)
    with pytest.raises(ValidationError):
        bom_line.tag = "PANEL"  # type: ignore[misc]


def test_bom_line_accepts_lot_and_sum_quantities() -> None:
    assert BomLine(group=Group.B, description="FO", qty="1 Lot").qty == "1 Lot"
    assert BomLine(group=Group.C, description="SFP", qty=QtySum(parts=(24, 3))).qty == QtySum(
        parts=(24, 3)
    )
