"""Substation file model: one system's settings, equipment, network, spares and layout.

Models ADR 0012 (a substation is today's project settings plus the sizing inputs) and
ADR 0013 (equipment, network, spares, layout). Paths stay as written (relative to the
substation file); the loader resolves them and applies the project defaults.
"""

from enum import StrEnum
from pathlib import Path
from string import Formatter
from typing import Any

from pydantic import (
    Field,
    NonNegativeInt,
    PositiveInt,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from bomgen.models._base import DocumentKey, ExcelSheetName, InputModel, PartId
from bomgen.models.library import Media, PortSpeed
from bomgen.models.panel import Enclosure, PanelId, PanelKind, TagPrefix
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


class Side(StrEnum):
    NONE = "none"
    A = "a"
    B = "b"


class Equipment(InputModel):
    """A device the substation needs, before any panel exists (ADR 0013)."""

    part_id: PartId
    role: EquipmentRole
    redundant: bool = False
    side: Side = Side.NONE
    qty: PositiveInt = 1
    l2_ports: NonNegativeInt = 0
    l2_speed: PortSpeed = PortSpeed.G1
    l2_media: Media = Media.MM

    @model_validator(mode="after")
    def _consistent(self) -> "Equipment":
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


class DeviceMove(InputModel):
    device: str
    panel: PositiveInt


class PairMove(InputModel):
    pair: str
    panel: tuple[PositiveInt, PositiveInt]

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
    removed: list[str] = Field(default_factory=list)


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
    loose_material: LooseMaterial | None = None
    equipment: list[Equipment] = Field(default_factory=list)
    network: Network = Field(default_factory=Network)
    layout: Layout = Field(default_factory=Layout)
    generated_panels: GeneratedPanels | None = None

    @model_validator(mode="after")
    def _consistent(self) -> "Substation":
        if not self.panels and not self.manual_panels:
            raise ValueError("list at least one file in panels or manual_panels")
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
