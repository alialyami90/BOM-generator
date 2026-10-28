"""Device library and commodity catalogues.

Models the spec section "Inputs the tool needs" (1. Device library) and ADR 0010.
Cross-record checks (duplicate part ids, dangling references) live in the loader.
"""

from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Literal

from pydantic import (
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

from bomgen.models._base import (
    ChildQuantity,
    InputModel,
    PartId,
    Quantity,
    check_template,
    template_fields,
)


class Category(StrEnum):
    NETWORK_SWITCH = "network_switch"
    FIREWALL = "firewall"
    GATEWAY = "gateway"
    PATCH_PANEL = "patch_panel"
    GPS_CLOCK = "gps_clock"
    RTAC = "rtac"
    IO_CHASSIS = "io_chassis"
    WORKSTATION = "workstation"
    MONITOR = "monitor"
    PERIPHERAL = "peripheral"
    SFP = "sfp"
    CABLE_MANAGER = "cable_manager"
    SERIAL_CABLE = "serial_cable"
    COMPONENT = "component"
    LAMP = "lamp"
    DOOR_SWITCH = "door_switch"
    FAN = "fan"
    VENT_FILTER = "vent_filter"
    THERMOSTAT = "thermostat"
    RELAY = "relay"
    SOCKET = "socket"
    CHANGE_OVER_DIODE = "change_over_diode"
    ANNUNCIATOR = "annunciator"
    SOFTWARE = "software"
    CABLE = "cable"
    ACCESSORY = "accessory"


class PurdueLevel(StrEnum):
    L1 = "L1"
    L2 = "L2"
    EXT = "EXT"
    L3 = "L3"


class SupplyType(StrEnum):
    VDC = "VDC"
    VAC = "VAC"


class LoadType(StrEnum):
    CONTINUOUS = "CONTINUOUS"
    INTERMITTENT = "INTERMITTENT"


class PortSpeed(StrEnum):
    M10 = "10M"
    M100 = "100M"
    G1 = "1G"
    G10 = "10G"


class Media(StrEnum):
    MM = "MM"
    SM = "SM"
    RJ45 = "RJ45"


class PortKind(StrEnum):
    FIXED = "fixed"
    SFP_SLOT = "sfp_slot"


DESCRIPTION_PLACEHOLDERS = {"lan", "level", "purpose"}
TAG_PLACEHOLDERS = {"prefix", "level", "type", "lan", "lan_index", "nn"}
STRIP_PLACEHOLDERS = {"n", "slot"}


class PortGroup(InputModel):
    """A count of identical ports on a device (spec: Inputs, ``ports``)."""

    count: PositiveInt
    speed: PortSpeed
    media: Media | None = None
    kind: PortKind

    @model_validator(mode="after")
    def _fixed_ports_have_media(self) -> "PortGroup":
        if self.kind is PortKind.FIXED and self.media is None:
            raise ValueError("a fixed port group needs media")
        return self


class ChildRule(InputModel):
    """A kit part added as a child row (spec: Inputs, ``children``)."""

    part_id: PartId
    qty: ChildQuantity = 1


class TerminalRule(InputModel):
    """A terminal strip a unit adds (spec: Inputs, ``terminals``; ADR 0010 item 3)."""

    strip: str
    block: str
    count: PositiveInt
    per: Literal["unit", "serial_port"] = "unit"
    first_slot: Annotated[str, Field(pattern=r"^[A-Z]$")] | None = None

    @field_validator("strip")
    @classmethod
    def _strip_placeholders(cls, value: str) -> str:
        return check_template(value, STRIP_PLACEHOLDERS)

    @model_validator(mode="after")
    def _slot_matches_first_slot(self) -> "TerminalRule":
        has_slot = "slot" in template_fields(self.strip)
        if has_slot and self.first_slot is None:
            raise ValueError("a strip using {slot} needs first_slot")
        if not has_slot and self.first_slot is not None:
            raise ValueError("first_slot is only valid when the strip uses {slot}")
        return self


class LooseItem(InputModel):
    """A part shipped loose, not in the panel (spec: Inputs, ``loose_items``)."""

    part_id: PartId
    qty: Quantity = 1
    tag: str | None = None


class DeviceType(InputModel):
    """One orderable part (spec: Inputs, 1. Device library)."""

    part_id: PartId
    category: Category
    make: str | None = None
    model: str | None = None
    ordering_code: str | None = None
    description_template: str
    tag_type: str | None = None
    purdue_level: PurdueLevel | None = None
    tag_pattern: str | None = None
    supply_type: SupplyType | None = None
    voltage_v: PositiveInt | None = None
    unit_power_w: NonNegativeFloat | None = None
    load_type: LoadType | None = None
    power_supplies: Literal[0, 1, 2] = 0
    min_branch_mcb_a: PositiveInt | None = None
    alarm_on_branch_mcb: bool = False
    hwio_points: NonNegativeInt = 0
    ports: list[PortGroup] = Field(default_factory=list)
    cores: PositiveInt | None = None
    children: list[ChildRule] = Field(default_factory=list)
    terminals: list[TerminalRule] = Field(default_factory=list)
    loose_items: list[LooseItem] = Field(default_factory=list)
    excluded_from_power: Annotated[
        bool,
        Field(description="Defaults to true when the part has no supply_type, else false."),
    ] = False

    @model_validator(mode="before")
    @classmethod
    def _default_excluded_from_power(cls, data: object) -> object:
        # ADR 0010 item 5: a part with no supply_type is a passive part.
        if isinstance(data, dict) and "excluded_from_power" not in data:
            return {**data, "excluded_from_power": data.get("supply_type") is None}
        return data

    @field_validator("description_template")
    @classmethod
    def _description_placeholders(cls, value: str) -> str:
        return check_template(value, DESCRIPTION_PLACEHOLDERS)

    @field_validator("tag_pattern")
    @classmethod
    def _tag_placeholders(cls, value: str | None) -> str | None:
        return None if value is None else check_template(value, TAG_PLACEHOLDERS)

    @model_validator(mode="after")
    def _power_rules(self) -> "DeviceType":
        if not self.excluded_from_power:
            missing = [
                name
                for name in ("supply_type", "unit_power_w", "load_type")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"a device not excluded from power needs {', '.join(missing)}")
        if self.power_supplies > 0 and self.supply_type is not SupplyType.VDC:
            raise ValueError("power_supplies above 0 needs supply_type VDC")
        if self.excluded_from_power and self.power_supplies != 0:
            raise ValueError("a device excluded from power must have power_supplies 0")
        if self.cores is None and any(child.qty == "cores" for child in self.children):
            raise ValueError("a child with qty 'cores' needs cores on the parent")
        return self

    @property
    def code(self) -> str | None:
        """BOM column G: the ordering code, else the model, else ``None`` (spec: Columns of a
        panel BOM)."""
        return self.ordering_code if self.ordering_code is not None else self.model


class McbCatalogue(InputModel):
    """MCB family by rating (spec: Inputs, commodity catalogues)."""

    family: str
    make: str
    poles: PositiveInt = 2
    ratings_a: Annotated[list[PositiveInt], Field(min_length=1)]
    code_pattern: str

    @field_validator("ratings_a")
    @classmethod
    def _ratings_increase(cls, value: list[int]) -> list[int]:
        if any(a >= b for a, b in pairwise(value)):
            raise ValueError("ratings_a must be strictly increasing")
        return value

    @field_validator("code_pattern")
    @classmethod
    def _pattern_uses_rating(cls, value: str) -> str:
        check_template(value, {"rating"})
        if "rating" not in template_fields(value):
            raise ValueError("code_pattern must contain {rating}")
        try:
            value.format(rating=1)
        except Exception as exc:  # any failure to format means the pattern is unusable
            raise ValueError(f"code_pattern cannot be formatted with a rating: {exc}") from exc
        return value

    def code_for(self, rating_a: int) -> str:
        """Return the order code for ``rating_a``; raise ``ValueError`` if not catalogued."""
        if rating_a not in self.ratings_a:
            raise ValueError(f"no {self.family} MCB of {rating_a} A in the catalogue")
        return self.code_pattern.format(rating=rating_a)


class AuxContact(InputModel):
    """DC auxiliary alarm contact (spec: Inputs, commodity catalogues)."""

    make: str
    model: str
    ordering_code: str


class TerminalBlockType(InputModel):
    """Terminal block by type (spec: Inputs, commodity catalogues)."""

    make: str
    ordering_code: str


class Busbar(InputModel):
    """Busbar entry (spec: Inputs, commodity catalogues)."""

    description: str


class HousekeepingRef(InputModel):
    """Housekeeping role filled by a device record (ADR 0010 item 1)."""

    part_id: PartId


class FanRef(HousekeepingRef):
    airflow_m3h: PositiveFloat


class SocketRef(HousekeepingRef):
    rating_a: PositiveInt


class Housekeeping(InputModel):
    """Housekeeping kit roles (spec: Inputs, commodity catalogues)."""

    lamp: HousekeepingRef
    door_switch: HousekeepingRef
    fan: FanRef
    vent_filter: HousekeepingRef
    thermostat: HousekeepingRef
    ipr_kit: HousekeepingRef
    change_over_diodes: HousekeepingRef
    socket: SocketRef


class Catalogues(InputModel):
    """Commodity catalogues held by the library (spec: Inputs, 1. Device library)."""

    mcb: McbCatalogue
    aux_contact: AuxContact
    terminal_blocks: Annotated[dict[str, TerminalBlockType], Field(min_length=1)]
    busbars: Annotated[dict[str, Busbar], Field(min_length=1)]
    housekeeping: Housekeeping


class Library(InputModel):
    """The device library file (spec: Inputs, 1. Device library)."""

    devices: Annotated[list[DeviceType], Field(min_length=1)]
    catalogues: Catalogues

    def get(self, part_id: str) -> DeviceType | None:
        """Return the device with ``part_id``, or ``None``."""
        for device in self.devices:
            if device.part_id == part_id:
                return device
        return None

    def part_ids(self) -> list[str]:
        """Return all part ids in file order."""
        return [device.part_id for device in self.devices]
