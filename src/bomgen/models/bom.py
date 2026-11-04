"""Generated BOM lines, the engine's output for the sheet layer (ADR 0005).

Models the spec sections "Columns of a panel BOM" and "Data model and generation
order" (entity BomLine). Lines hold values only; SR.NO formulas, separator rows and
cell addresses are laid out by the sheet layer.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, NonNegativeInt, PositiveInt

from bomgen.models.calc import (
    BranchMcb,
    DcMains,
    HeatResult,
    HousekeepingBranch,
    LineRef,
    PowerConsumption,
    SpareRatings,
)
from bomgen.models.output import OutputModel
from bomgen.models.panel import PanelKind
from bomgen.models.project import CableRef

Column = Literal["A", "B", "C", "D", "E", "F", "G", "H"]


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
    cable: CableRef | None = None  # a loose row's cable data (plan M65)
    note: str | None = None  # the input row's note, for Preview and the Notes sheet (M71)


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
    kind: PanelKind = PanelKind.NETWORK  # the console's header row is taller (plan Q61)


class LooseTable(BomTable):
    """The loose-material table printed under the host panel's BOM."""

    host_panel: str


class Nameplate(OutputModel):
    text: str  # the unit's short tag, as its MCB rows name it
    device: str  # the unit's group B description


class PanelNameplates(OutputModel):
    """The plates of one panel's tagged group B units, in row order (ADR 0026)."""

    panel_id: str
    plates: tuple[Nameplate, ...]


class StripRow(OutputModel):
    """One terminal strip as the Terminals tab shows it (ADR 0033): its automatic quantity
    with the rule that gave it, the panel's override, and the block type the BOM prints."""

    code: str
    description: str
    block: str  # the rule's block type
    block_override: str | None = None
    rule: str
    auto_qty: int  # the rule's quantity with the spare fraction
    override: int | None = None
    spared: bool  # the spare fraction applies (not to the devices' own strips)

    @property
    def qty(self) -> int:
        return self.auto_qty if self.override is None else self.override

    @property
    def model(self) -> str:
        """The block type the BOM prints."""
        return self.block if self.block_override is None else self.block_override


class PanelStrips(OutputModel):
    panel_id: str
    strips: tuple[StripRow, ...]


class BuildResult(OutputModel):
    """Everything the engine derives from a loaded substation: the BOM tables and the
    calculation sheets' power and heat results (``None`` only in hand-built results)."""

    panels: tuple[PanelBom, ...]
    loose: LooseTable | None = None
    power: PowerConsumption | None = None
    heat: HeatResult | None = None
    mains: tuple[DcMains, ...] = ()
    branch_mcbs: tuple[BranchMcb, ...] = ()
    spares: tuple[SpareRatings, ...] = ()  # the spare breakers' rule ratings (plan M58)
    strips: tuple[PanelStrips, ...] = ()  # group G before the BOM rows (ADR 0033)
    housekeeping: tuple[HousekeepingBranch, ...] = ()  # the kit's C branches (ADR 0032)
    nameplates: tuple[PanelNameplates, ...] = ()  # empty when the library has no nameplate


class SummarySource(OutputModel):
    """One BOM row counted in a summary line."""

    ref: LineRef
    tag: str | None = None
    qty: int | str


class SummaryLine(OutputModel):
    """One Summary BOM line: a part, or a free-text item, across every sheet (ADR 0035)."""

    description: str  # the first seen
    qty: int | str  # the sum; a text quantity ("1 Lot") is never summed
    make: str | None = None
    model: str | None = None
    ordering_code: str | None = None
    sources: tuple[SummarySource, ...]

    def where_used(self, sheets: Mapping[str | None, str]) -> str:
        """``sheet: tag, tag (qty)`` per sheet, in order; ``sheets`` names each table."""
        parts: list[str] = []
        by_table: dict[str | None, list[SummarySource]] = {}
        for source in self.sources:
            by_table.setdefault(source.ref.panel_id, []).append(source)
        for table, sources in by_table.items():
            tags = ", ".join(s.tag for s in sources if s.tag)
            numbers = [s.qty for s in sources if isinstance(s.qty, int)]
            qty = sum(numbers) if len(numbers) == len(sources) else sources[0].qty
            label = f"{sheets[table]}: {tags}" if tags else sheets[table]
            parts.append(f"{label} ({qty})")
        return "; ".join(parts)


class SummaryTable(OutputModel):
    lines: tuple[SummaryLine, ...]


class SpareLine(OutputModel):
    """One Spare Parts line (ADR 0035, plan M64). ``summary_line`` indexes the Summary BOM
    line it counts; ``percent`` and ``minimum`` are the rule a policy line follows, unset
    for an overridden line or an extra."""

    description: str
    installed: int | None  # None for an extra
    spare: int
    make: str | None = None
    model: str | None = None
    ordering_code: str | None = None
    basis: str
    summary_line: int | None = None
    percent: float | None = None
    minimum: int = 0
    overridden: bool = False


class SparesTable(OutputModel):
    lines: tuple[SpareLine, ...]
