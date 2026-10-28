"""Generated BOM lines, the engine's output for the sheet layer (ADR 0005).

Models the spec sections "Columns of a panel BOM" and "Data model and generation
order" (entity BomLine). Lines hold values only; SR.NO formulas, separator rows and
cell addresses are laid out by the sheet layer.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt

Column = Literal["A", "B", "C", "D", "E", "F", "G", "H"]


class OutputModel(BaseModel):
    """Base for engine output: immutable, no unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Group(StrEnum):
    """BOM groups in sheet order (spec: How each panel BOM groups its materials)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"


SEPARATED_GROUPS = frozenset({Group.E, Group.F, Group.G, Group.H})


class QtySum(OutputModel):
    """A quantity written as a sum, e.g. SFPs ``=24+3`` (spec: Columns, QUANTITY)."""

    parts: Annotated[tuple[PositiveInt, ...], Field(min_length=2)]

    @property
    def value(self) -> int:
        return sum(self.parts)


Qty = int | Literal["1 Lot"] | QtySum


class BomLine(OutputModel):
    """One material row, columns B-H (spec: Columns of a panel BOM).

    ``parent`` is the index of the parent line in the same table; the parent's tag is
    merged down over its children. ``merge_fg`` on a parent merges its F and G cells
    down over the following children whose own cell is empty.
    """

    group: Group
    tag: str | None = None
    description: str
    qty: Qty
    make: str | None = None
    model: str | None = None
    ordering_code: str | None = None
    hwio: NonNegativeInt = 0
    part_id: str | None = None
    parent: NonNegativeInt | None = None
    merge_fg: bool = False
    revised: frozenset[Column] = frozenset()


class BomTable(OutputModel):
    """A titled BOM table: two title lines and its material lines in order."""

    title: tuple[str, str]
    lines: tuple[BomLine, ...]

    def separators_before(self) -> tuple[int, ...]:
        """Indices of the lines that get an empty bordered row above them."""
        result: list[int] = []
        previous: Group | None = None
        for index, bom_line in enumerate(self.lines):
            if bom_line.group in SEPARATED_GROUPS and bom_line.group != previous:
                result.append(index)
            previous = bom_line.group
        return tuple(result)


class PanelBom(BomTable):
    """One cabinet's BOM sheet."""

    panel_id: str
    sheet_name: str


class LooseTable(BomTable):
    """The loose-material table printed under the host panel's BOM."""

    host_panel: str


class BuildResult(OutputModel):
    """Everything the engine derives from a loaded project."""

    panels: tuple[PanelBom, ...]
    loose: LooseTable | None = None
