"""Panel definition and panel mirror models.

Models the spec section "Inputs the tool needs" (2. Panel definition) and ADR 0010.
Cross-record checks (unknown part ids, mirror resolution and option merging) live in
the loader.
"""

from datetime import date
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    Field,
    NonNegativeInt,
    PositiveInt,
    StringConstraints,
    model_validator,
)

from bomgen.models._base import AutoBool, DocumentKey, ExcelSheetName, InputModel, PartId, Rev
from bomgen.models.library import Media, PortSpeed

Lan = Literal["A", "B"]
PanelId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]*$")]
TagPrefix = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9]*$")]


class PanelKind(StrEnum):
    NETWORK = "network"
    CONTROL = "control"
    CONSOLE = "console"


class CableEntry(StrEnum):
    TOP = "top"
    SIDE = "side"


class Ventilation(StrEnum):
    AUTO = "auto"
    FORCED = "forced"
    NATURAL = "natural"


class BaseFrame(InputModel):
    """The plinth under the enclosure (spec: Inputs, 2. Panel definition)."""

    h_mm: PositiveInt
    d_mm: PositiveInt
    w_mm: PositiveInt


class Enclosure(InputModel):
    """The cabinet enclosure (spec: Inputs, 2. Panel definition)."""

    make: str
    model: str
    ordering_code: str | None = None
    h_mm: PositiveInt
    d_mm: PositiveInt
    w_mm: PositiveInt
    base_frame: BaseFrame | None = None
    cable_entry: CableEntry


class DeviceInstance(InputModel):
    """A device placed in a panel, in group B display order."""

    part_id: PartId
    qty: PositiveInt = 1
    tag: str | None = None
    purpose: str | None = None
    lan: Lan | None = None
    hwio_points: NonNegativeInt | None = None  # the row's HWIO total, overriding the library's
    first_nn: PositiveInt | None = None  # first {nn} of the row, continuing a range (ADR 0013)


class PortAllocation(InputModel):
    """A count of ports of one speed and media used for one purpose, plus spares."""

    count: PositiveInt
    speed: PortSpeed
    media: Media
    spare: NonNegativeInt = 0


class PortPlan(InputModel):
    """How one device's ports are allocated (keyed by part id or tag in the panel)."""

    uplinks_l3: list[PortAllocation] = Field(default_factory=list)
    uplinks: list[PortAllocation] = Field(default_factory=list)
    downlinks: list[PortAllocation] = Field(default_factory=list)
    serial_ports: NonNegativeInt = 0


class PanelOptions(InputModel):
    """Per-panel switches and overrides (spec: Inputs, 2. Panel definition)."""

    aux_socket_a: PositiveInt | None = None
    smoke_detector: bool = True
    change_over_diodes: AutoBool = "auto"
    ventilation: Ventilation = Ventilation.AUTO
    dc_spare_branches_per_feed: NonNegativeInt = 1
    ac_spare_branches: NonNegativeInt = 1
    main_mcb_override_a: PositiveInt | None = None
    inter_panel_terminals: NonNegativeInt | None = None
    terminal_overrides: dict[str, NonNegativeInt] = Field(default_factory=dict)
    grounding_busbars: list[str] = Field(
        default_factory=lambda: ["ac_safety_ground", "instrument_ground"]
    )


class DocumentInfo(InputModel):
    """A BOM sheet's document header and footer values."""

    doc_no: str
    rev: Rev
    issue_date: date


class RevisionMark(InputModel):
    """Cells of one tagged row to highlight as revised."""

    tag: str
    columns: Annotated[list[Literal["A", "B", "C", "D", "E", "F", "G", "H"]], Field(min_length=1)]


class Revision(InputModel):
    highlight: list[RevisionMark] = Field(default_factory=list)


class Panel(InputModel):
    """A full panel definition (``panels/<id>.yaml``)."""

    id: PanelId
    cabinet_number: str
    cabinet_name: str
    tag_prefix: TagPrefix
    lan: Lan | None = None
    sheet_name: ExcelSheetName
    kind: PanelKind
    enclosure: Enclosure
    devices: Annotated[list[DeviceInstance], Field(min_length=1)]
    port_plans: dict[str, PortPlan] = Field(default_factory=dict)
    options: PanelOptions = Field(default_factory=PanelOptions)
    document: DocumentKey
    generated: bool = False  # written by the layout engine (ADR 0013)
    revision: Revision = Field(default_factory=Revision)


class PanelMirror(InputModel):
    """A panel defined as a mirror of another (spec: "What changes by panel type").

    ``options`` holds ``PanelOptions`` keys and is validated after the loader merges
    it over the mirrored panel's options.
    """

    id: PanelId
    mirror_of: PanelId
    cabinet_number: str
    cabinet_name: str
    tag_prefix: TagPrefix
    lan: Lan | None = None
    sheet_name: ExcelSheetName
    options: dict[str, Any] = Field(default_factory=dict)
    document: DocumentKey
    generated: bool = False  # written by the layout engine (ADR 0013)
    revision: Revision = Field(default_factory=Revision)

    @model_validator(mode="after")
    def _not_self_mirror(self) -> "PanelMirror":
        if self.mirror_of == self.id:
            raise ValueError("a panel cannot be a mirror of itself (mirror_of equals id)")
        return self
