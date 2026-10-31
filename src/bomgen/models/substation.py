"""Substation file model: one system's settings, equipment, network, spares and layout.

Models ADR 0012 (a substation is today's project settings plus the sizing inputs) and
ADR 0013 (equipment, network, spares, layout). Paths stay as written (relative to the
substation file); the loader resolves them and applies the project defaults.
"""

from enum import StrEnum
from pathlib import Path
from string import Formatter
from typing import Any, Literal

from pydantic import (
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from bomgen.models._base import DocumentKey, ExcelSheetName, InputModel, PartId
from bomgen.models.library import (
    CatalogueChoice,
    LoadType,
    Media,
    PortSpeed,
    SfpChoice,
    SupplyType,
)
from bomgen.models.panel import Enclosure, PanelId, PanelKind, PortPlan, TagPrefix
from bomgen.models.project import ConstantOverrides, LooseMaterial, OutputSettings, Spares


class SubstationInfo(InputModel):
    id: PanelId
    name: str


class CalcSheet(InputModel):
    """A calculation sheet's register document and its scope line."""

    document: DocumentKey
    scope: str


class Calculations(InputModel):
    power_consumption: CalcSheet
    heat_dissipation: CalcSheet
    heat_calculations: CalcSheet


class EquipmentRole(StrEnum):
    L1_SWITCH = "l1_switch"
    L2_SWITCH = "l2_switch"
    EXT_SWITCH = "ext_switch"
    FIREWALL = "firewall"
    FOPP = "fopp"
    OTHER = "other"
    # Parts page rows (ADR 0024): sized as other
    TIME_SERVER = "time_server"
    OPERATOR_WS = "operator_ws"
    ENGINEERING_WS = "engineering_ws"
    DA_SERVER = "da_server"
    KVM = "kvm"
    CONSOLE = "console"
    ANNUNCIATOR = "annunciator"
    TIME_ACCESSORY = "time_accessory"


class Side(StrEnum):
    NONE = "none"
    A = "a"
    B = "b"


class PartOverrides(InputModel):
    """Library values replaced for one equipment entry (ADR 0024)."""

    height_u: NonNegativeInt | None = None
    unit_power_w: NonNegativeFloat | None = None
    supply_type: SupplyType | None = None
    voltage_v: PositiveInt | None = None
    power_supplies: Literal[0, 1, 2] | None = None
    inrush_a: PositiveFloat | None = None
    load_type: LoadType | None = None

    def values(self) -> dict[str, object]:
        """The overridden values only."""
        return {name: getattr(self, name) for name in self.model_fields_set}


class Equipment(InputModel):
    """A device the substation needs, before any panel exists (ADR 0013)."""

    id: PanelId  # what layout overrides and the UI name, never a tag
    part_id: PartId | None = None  # an l1_switch without one is picked from the library
    role: EquipmentRole
    redundant: bool = False
    side: Side = Side.NONE
    qty: PositiveInt = 1
    l2_ports: NonNegativeInt = 0
    l2_speed: PortSpeed = PortSpeed.G1
    l2_media: Media = Media.MM
    # copied onto every panel row the layout writes for this entry (as on DeviceInstance)
    purpose: str | None = None
    hwio_points: NonNegativeInt | None = None  # a row's HWIO total, overriding the library's
    port_plan: PortPlan | None = None  # per unit; the layout scales it by the row's qty
    ordering_code: str | None = None  # the BOM's ordering code instead of the library's
    overrides: PartOverrides | None = None
    sfp: list[SfpChoice] = Field(default_factory=list)
    cable_manager: bool | None = None  # None: the category's rule (ADR 0013, amended)

    @model_validator(mode="after")
    def _consistent(self) -> "Equipment":
        if self.part_id is None and self.role is not EquipmentRole.L1_SWITCH:
            raise ValueError(f"part_id is needed for a {self.role.value}")
        changed = self.ordering_code is not None or self.overrides is not None or self.sfp
        if self.part_id is None and changed:
            raise ValueError("pick the switch to override its data (set part_id)")
        sized = (EquipmentRole.L1_SWITCH, EquipmentRole.L2_SWITCH)
        if self.sfp and self.role not in sized:
            raise ValueError("sfp is for L1 and L2 switches; leave it out")
        if self.role in sized and self.port_plan is not None:
            raise ValueError(
                f"the {self.role.value} port plan is computed by the switch sizing; "
                "leave port_plan out"
            )
        if self.redundant and self.side is not Side.NONE:
            raise ValueError("a redundant device has one unit per side; leave side out")
        if self.role is EquipmentRole.L1_SWITCH and "qty" in self.model_fields_set:
            raise ValueError(
                "the L1 switch count is computed from network.ied_count; leave qty out"
            )
        return self


class Topology(StrEnum):
    STAR = "star"
    RING = "ring"


class Network(InputModel):
    ied_count: NonNegativeInt = 0  # field IEDs: sizes the L1 switches, never a BOM row
    topology: Topology = Topology.STAR
    ring_max_switches: PositiveInt = 6
    l1_uplinks_per_switch: PositiveInt = 1
    l1_interlink: bool = True
    l3_uplinks_per_l2: NonNegativeInt = 2


UnitSide = Literal["a", "b"]


class UnitRef(InputModel):
    """Units of one equipment entry: ``unit`` (1-based) and ``side``; None means all."""

    device: PanelId
    unit: PositiveInt | None = None
    side: UnitSide | None = None


class DeviceMove(UnitRef):
    """Move single units into a panel; a redundant entry's move names its side.

    ``position`` (1 = top) is the unit's place among the panel's rack devices; without
    it the unit takes its automatic place in the panel (ADR 0013, R7).
    """

    panel: PositiveInt
    position: PositiveInt | None = None


class PairMove(InputModel):
    """Move both sides of a redundant entry (its ``unit``-th pair, or all) into two panels."""

    pair: PanelId
    unit: PositiveInt | None = None
    panel: tuple[PositiveInt, PositiveInt]
    position: PositiveInt | None = None  # in both panels, as on DeviceMove

    @field_validator("panel")
    @classmethod
    def _two_panels(cls, panel: tuple[int, int]) -> tuple[int, int]:
        if panel[0] == panel[1]:
            raise ValueError("a pair moves into two different panels")
        return panel


class Layout(InputModel):
    """Layout inputs; the usable U per panel is computed, not written (ADR 0013)."""

    blank_plate_u: NonNegativeInt = 1
    overrides: list[DeviceMove | PairMove] = Field(default_factory=list)
    removed: list[UnitRef] = Field(default_factory=list)  # units left out of the layout


def _check_number_template(value: str) -> str:
    fields = [name for _text, name, _spec, _conv in Formatter().parse(value) if name is not None]
    if fields != ["n"]:
        raise ValueError("must hold the panel number placeholder {n} exactly once")
    try:
        value.format(n=1)
    except (ValueError, TypeError) as error:
        raise ValueError(f"cannot format the panel number: {error}") from None
    return value


class GeneratedPanels(InputModel):
    """Identity of the panels the layout writes; ``{n}`` is the panel number (ADR 0013)."""

    id: str
    cabinet_number: str
    cabinet_name: str
    tag_prefix: str
    sheet_name: str
    kind: PanelKind = PanelKind.NETWORK
    enclosure: Enclosure
    document: DocumentKey
    options: dict[str, Any] = Field(default_factory=dict)  # every generated panel
    options_by_panel: dict[PositiveInt, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("id", "cabinet_number", "cabinet_name", "tag_prefix", "sheet_name")
    @classmethod
    def _number_templates(cls, value: str) -> str:
        return _check_number_template(value)

    @model_validator(mode="after")
    def _rendered_values_are_valid(self) -> "GeneratedPanels":
        for name, kind in _RENDERED.items():
            rendered = getattr(self, name).format(n=1)
            try:
                kind.validate_python(rendered)
            except ValidationError as error:
                problem = error.errors()[0]["msg"]
                raise ValueError(f"{name} gives {rendered!r} for panel 1: {problem}") from None
        return self


_RENDERED: dict[str, TypeAdapter[str]] = {
    "id": TypeAdapter(PanelId),
    "tag_prefix": TypeAdapter(TagPrefix),
    "sheet_name": TypeAdapter(ExcelSheetName),
}


class Substation(InputModel):
    """The substation file (``substation.yaml``)."""

    substation: SubstationInfo
    document: DocumentKey  # the workbook's document: its number and rev name the file
    calculations: Calculations
    panels: list[Path] = Field(default_factory=list)  # hand-written or generated, sheet order
    manual_panels: list[Path] = Field(default_factory=list)  # never touched by the layout
    output: OutputSettings = Field(default_factory=OutputSettings)
    constants: ConstantOverrides | None = None
    spares: Spares | None = None
    catalogue_choice: CatalogueChoice | None = None  # brand sets; unset keys inherit
    loose_material: LooseMaterial | None = None
    equipment: list[Equipment] = Field(default_factory=list)
    network: Network = Field(default_factory=Network)
    layout: Layout = Field(default_factory=Layout)
    generated_panels: GeneratedPanels | None = None

    @model_validator(mode="after")
    def _consistent(self) -> "Substation":
        both = sorted(
            {p.as_posix() for p in self.panels} & {p.as_posix() for p in self.manual_panels}
        )
        if both:
            raise ValueError(f"listed in both panels and manual_panels: {', '.join(both)}")
        if self.equipment:
            for role in (EquipmentRole.L1_SWITCH, EquipmentRole.L2_SWITCH):
                entries = [e for e in self.equipment if e.role is role]
                if len(entries) != 1 or not entries[0].redundant:
                    raise ValueError(f"equipment needs exactly one redundant {role.value}")
            if self.generated_panels is None:
                raise ValueError("equipment needs generated_panels to name the panels it fills")
        return self
