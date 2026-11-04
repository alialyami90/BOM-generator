"""Substation file model: one system's settings, equipment, network, spares and layout.

Models ADR 0012 (a substation is today's project settings plus the sizing inputs) and
ADR 0013 (equipment, network, spares, layout). Paths stay as written (relative to the
substation file); the loader resolves them and applies the project defaults.
"""

from datetime import date
from enum import StrEnum
from pathlib import Path
from string import Formatter
from typing import Annotated, Any, Literal, Self

from pydantic import (
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from bomgen.models._base import DocumentKey, ExcelSheetName, InputModel, PartId, Rev
from bomgen.models.library import (
    CatalogueChoice,
    Category,
    LoadType,
    Media,
    PortSpeed,
    PurdueLevel,
    SfpChoice,
    SizedSpeed,
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
    l2_speed: SizedSpeed = PortSpeed.G1
    l2_media: Media = Media.MM
    # copied onto every panel row the layout writes for this entry (as on DeviceInstance)
    purpose: str | None = None
    hwio_points: NonNegativeInt | None = None  # a row's HWIO total, overriding the library's
    tag: str | None = None  # the row's tag instead of the generated one (plan M59)
    tag_type: str | None = None  # the type code instead of the library's (ADR 0030)
    first_nn: PositiveInt | None = None  # the first unit's {nn}; later units count on
    port_plan: PortPlan | None = None  # per unit; the layout scales it by the row's qty
    ordering_code: str | None = None  # the BOM's ordering code instead of the library's
    overrides: PartOverrides | None = None
    sfp: list[SfpChoice] = Field(default_factory=list)
    cable_manager: bool | None = None  # None: the category's rule (ADR 0013, amended)
    alarm_on_branch_mcb: bool | None = None  # None: the library's value (plan M58)

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


class PortNeed(InputModel):
    """Ports one IED needs on each side it attaches to (ADR 0034)."""

    count: PositiveInt = 1
    speed: PortSpeed = PortSpeed.M100
    media: Media = Media.MM


class IedRow(InputModel):
    """One row of the IED schedule: ``qty`` IEDs of one type in one bay (ADR 0034)."""

    bay: str
    name: str  # the IED type or tag
    qty: PositiveInt = 1
    ports: Annotated[list[PortNeed], Field(min_length=1)] = Field(
        default_factory=lambda: [PortNeed()]
    )
    attachment: Literal["dual", "single_a", "single_b"] = "dual"
    lands_on: Literal["l1", "l2"] = "l1"
    notes: str | None = None


class ExternalLink(InputModel):
    """A link leaving the substation, e.g. to the control centre or PCC (plan M61, Q64)."""

    name: str
    count: PositiveInt = 1  # links on each side it is on
    speed: SizedSpeed = PortSpeed.G1
    media: Media = Media.SM
    lands_on: Literal["l2", "ext"] = "l2"  # the L2 switches or the external switch
    through_firewall: bool = False
    redundant: bool = True  # one per side; else side A only
    cable_length_m: PositiveFloat | None = None  # for the cable schedule (M65)


class Network(InputModel):
    ied_count: NonNegativeInt = 0  # field IEDs: sizes the L1 switches, never a BOM row
    ied_schedule: list[IedRow] = Field(default_factory=list)  # replaces ied_count (ADR 0034)
    external_links: list[ExternalLink] = Field(default_factory=list)  # plan M61
    topology: Topology = Topology.STAR
    ring_max_switches: PositiveInt = 6
    l1_uplinks_per_switch: PositiveInt = 1
    l1_interlink: bool = True
    l3_uplinks_per_l2: NonNegativeInt = 2

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.ied_count and self.ied_schedule:
            raise ValueError("give ied_count or ied_schedule, not both")
        return self


UnitSide = Literal["a", "b"]


class UnitRef(InputModel):
    """Units of one equipment entry: ``unit`` (1-based) and ``side``; None means all."""

    device: PanelId
    unit: PositiveInt | None = None
    side: UnitSide | None = None


def _one_place(position: int | None, top_u: int | None) -> None:
    if position is not None and top_u is not None:
        raise ValueError("give position or top_u, not both")


class DeviceMove(UnitRef):
    """Move single units into a panel; a redundant entry's move names its side.

    ``position`` (1 = top) is the unit's place among the panel's rack devices; ``top_u``
    fixes the top of its block at that rack U (1 = bottom). Without either the unit takes
    its automatic place in the panel (ADR 0013, R7).
    """

    panel: PositiveInt
    position: PositiveInt | None = None
    top_u: PositiveInt | None = None

    @model_validator(mode="after")
    def _one_place(self) -> Self:
        _one_place(self.position, self.top_u)
        return self


class PairMove(InputModel):
    """Move both sides of a redundant entry (its ``unit``-th pair, or all) into two panels."""

    pair: PanelId
    unit: PositiveInt | None = None
    panel: tuple[PositiveInt, PositiveInt]
    position: PositiveInt | None = None  # in both panels, as on DeviceMove
    top_u: PositiveInt | None = None  # in both panels, as on DeviceMove

    @model_validator(mode="after")
    def _one_place(self) -> Self:
        _one_place(self.position, self.top_u)
        return self

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
    max_panels: PositiveInt | None = None  # the most panels the fill may open (plan M62)


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
    enclosure_by_panel: dict[PositiveInt, Enclosure] = Field(default_factory=dict)  # plan M50
    kind_by_panel: dict[PositiveInt, PanelKind] = Field(default_factory=dict)

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


SideLetter = Annotated[str, StringConstraints(pattern=r"^[A-Z]$")]
FIRST_NUMBERS: dict[PurdueLevel, int] = {PurdueLevel.L2: 1, PurdueLevel.L1: 11, PurdueLevel.L3: 1}


def _first_numbers() -> dict[PurdueLevel, PositiveInt]:
    return dict(FIRST_NUMBERS)


class Tagging(InputModel):
    """How device tags print their side and number (ADR 0030, 0031); defaults are today's."""

    side_letters: tuple[SideLetter, SideLetter] = ("A", "B")  # LAN A, LAN B
    first_numbers: dict[PurdueLevel, PositiveInt] = Field(default_factory=_first_numbers)

    @field_validator("side_letters")
    @classmethod
    def _different(cls, value: tuple[str, str]) -> tuple[str, str]:
        if value[0] == value[1]:
            raise ValueError("the two side letters must differ")
        return value

    @field_validator("first_numbers")
    @classmethod
    def _filled(cls, value: dict[PurdueLevel, int]) -> dict[PurdueLevel, int]:
        return FIRST_NUMBERS | value  # a level left out keeps today's number


class SparesPolicy(InputModel):
    """The spares list's policy (ADR 0031); read by the spares list (plan M64) only."""

    percent: dict[Category, NonNegativeFloat] = Field(default_factory=dict)
    minimum_per_part: NonNegativeInt = 1  # Q65: at least one spare per policy line
    categories: list[Category] = Field(default_factory=list)


class SpareExtra(InputModel):
    """A spare the policy does not give: a library part or a free-text item (plan M64)."""

    part_id: PartId | None = None
    description: str | None = None
    qty: PositiveInt

    @model_validator(mode="after")
    def _part_or_description(self) -> "SpareExtra":
        if (self.part_id is None) == (not (self.description or "").strip()):
            raise ValueError("a spare extra names a library part_id or a description (exactly one)")
        return self


class SparesList(InputModel):
    """The substation's edits to the spares list (plan M64): a spare quantity per ordering
    code (the model when a part has none), codes left out, and extra items."""

    items: dict[str, NonNegativeInt] = Field(default_factory=dict)
    excluded: list[str] = Field(default_factory=list)
    extra: list[SpareExtra] = Field(default_factory=list)


class CableDefaults(InputModel):
    """Cord lengths per link class for the cable suggestions (plan M65, Q66): within one
    cabinet, between cabinets, and leaving the substation when the link row gives none."""

    in_cabinet_m: PositiveFloat = 2
    inter_cabinet_m: PositiveFloat = 5
    external_m: PositiveFloat | None = None


class DesignBasis(InputModel):
    """What the engineer states first (ADR 0031). It only sets defaults: a value the
    substation writes itself wins. Unset keys mean today's behaviour."""

    dc_voltage_v: PositiveFloat | None = None
    ac_voltage_v: PositiveFloat | None = None
    redundancy: str = "duplicated_lan"
    purdue_scope: set[Literal["L1", "L2", "EXT"]] | None = None
    time_sync: Literal["gps_clock", "ptp_from_clock", "none"] | None = None
    tagging: Tagging = Field(default_factory=Tagging)
    spares_policy: SparesPolicy | None = None
    vendor_list: str | None = None  # a key of the project's vendor lists (plan M53)
    cables: CableDefaults | None = None  # plan M65, Q66
    notes: str | None = None

    @field_validator("redundancy")
    @classmethod
    def _duplicated_lan_only(cls, value: str) -> str:
        if value.lower() in ("prp", "hsr"):
            raise ValueError(f"{value.upper()} is not supported yet; use duplicated_lan")
        if value != "duplicated_lan":
            raise ValueError("redundancy must be duplicated_lan")
        return value


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class AcceptedWarning(InputModel):
    """A check warning the engineer accepted, with the reason (ADR 0036). It matches a
    warning by check id, panel and subject."""

    check: str
    panel_id: str | None = None
    subject: str | None = None
    reason: NonBlank
    by: str | None = None
    date: date


class Checks(InputModel):
    accepted: list[AcceptedWarning] = Field(default_factory=list)


class IssueRecord(InputModel):
    """One issued workbook (ADR 0036): ``file`` is relative to ``substation.yaml`` when
    inside the project folder, ``sha256`` the file as written."""

    rev: Rev
    date: date
    file: Path
    sha256: Sha256
    description: str
    prepared: str | None = None
    checked: str | None = None
    approved: str | None = None
    accepted_warnings: list[AcceptedWarning] = Field(default_factory=list)


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
    design_basis: DesignBasis | None = None  # ADR 0031
    issues: list[IssueRecord] = Field(default_factory=list)  # ADR 0036, in issue order
    checks: Checks | None = None  # ADR 0036
    spares_list: SparesList | None = None  # plan M64

    @model_validator(mode="after")
    def _consistent(self) -> "Substation":
        both = sorted(
            {p.as_posix() for p in self.panels} & {p.as_posix() for p in self.manual_panels}
        )
        if both:
            raise ValueError(f"listed in both panels and manual_panels: {', '.join(both)}")
        revs = [record.rev for record in self.issues]
        twice = next((rev for rev in revs if revs.count(rev) > 1), None)
        if twice is not None:
            raise ValueError(f"rev '{twice}' is recorded twice in issues")
        if self.equipment:
            for role in (EquipmentRole.L1_SWITCH, EquipmentRole.L2_SWITCH):
                entries = [e for e in self.equipment if e.role is role]
                if len(entries) != 1 or not entries[0].redundant:
                    raise ValueError(f"equipment needs exactly one redundant {role.value}")
            if self.generated_panels is None:
                raise ValueError("equipment needs generated_panels to name the panels it fills")
        return self
