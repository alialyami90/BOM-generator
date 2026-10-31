"""Device library and commodity catalogues.

Models the spec section "Inputs the tool needs" (1. Device library), ADR 0010 and, for
alternatives and catalogue brands, ADR 0017. Cross-record checks (duplicate part ids,
dangling references) live in the loader.
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
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

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
    KVM = "kvm"
    CONSOLE = "console"


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


class PortUse(StrEnum):
    """What a port group may connect, for the switch sizing (ADR 0013)."""

    IED = "ied"
    UPLINK = "uplink"
    ANY = "any"


DESCRIPTION_PLACEHOLDERS = {"lan", "level", "purpose"}
TAG_PLACEHOLDERS = {"prefix", "level", "type", "lan", "lan_index", "nn"}
STRIP_PLACEHOLDERS = {"n", "slot"}


class PortGroup(InputModel):
    """A count of identical ports on a device (spec: Inputs, ``ports``)."""

    count: PositiveInt
    speed: PortSpeed
    media: Media | None = None
    kind: PortKind
    usable_for: PortUse = PortUse.ANY

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
    description: str | None = None  # column C of the strip's rows; same placeholders

    @field_validator("strip", "description")
    @classmethod
    def _strip_placeholders(cls, value: str | None) -> str | None:
        return None if value is None else check_template(value, STRIP_PLACEHOLDERS)

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


class SfpChoice(InputModel):
    """The SFP model picked for one port speed and media of a switch (ADR 0024)."""

    speed: PortSpeed
    media: Media
    part_id: PartId


AltGroup = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9][A-Z0-9-]*$")]
Tier = Literal["low", "mid", "high"]


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
    di_inputs: NonNegativeInt = 0  # hardwired digital inputs one unit provides
    ports: list[PortGroup] = Field(default_factory=list)
    cores: PositiveInt | None = None
    height_u: NonNegativeInt | None = None  # rack units; 0 = DIN rail, None = not given yet
    children: list[ChildRule] = Field(default_factory=list)
    terminals: list[TerminalRule] = Field(default_factory=list)
    loose_items: list[LooseItem] = Field(default_factory=list)
    excluded_from_power: Annotated[
        bool,
        Field(description="Defaults to true when the part has no supply_type, else false."),
    ] = False
    alt_group: AltGroup | None = None  # interchangeable parts share a key (ADR 0017)
    tier: Tier | None = None
    inrush_a: PositiveFloat | None = None  # peak inrush current
    inrush_ms: PositiveFloat | None = None  # inrush duration
    input_v_min: PositiveFloat | None = None  # rated input voltage range, V
    input_v_max: PositiveFloat | None = None
    # set by the loader on a part derived from an equipment entry, never in a file (ADR 0024)
    derived_from: SkipJsonSchema[PartId | None] = None
    sfp_choice: SkipJsonSchema[list[SfpChoice]] = Field(default_factory=list)

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
        low, high = self.input_v_min, self.input_v_max
        if low is not None and high is not None and low > high:
            raise ValueError("input_v_min must not be above input_v_max")
        return self

    @property
    def code(self) -> str | None:
        """BOM column G: the ordering code, else the model, else ``None`` (spec: Columns of a
        panel BOM)."""
        return self.ordering_code if self.ordering_code is not None else self.model


TripCurve = Literal["B", "C", "D", "K", "Z"]

# Instantaneous (magnetic) trip band per curve, in multiples of In, on AC (IEC 60898-1;
# IEC 60947-2 for K and Z).
TRIP_BANDS: dict[str, tuple[float, float]] = {
    "B": (3, 5),
    "C": (5, 10),
    "D": (10, 20),
    "K": (8, 14),
    "Z": (2, 3),
}


class McbCatalogue(InputModel):
    """MCB family by rating (spec: Inputs, commodity catalogues; sizing fields ADR 0017)."""

    family: str
    make: str
    poles: PositiveInt = 2
    ratings_a: Annotated[list[PositiveInt], Field(min_length=1)]
    code_pattern: str | None = None
    codes: dict[PositiveInt, str] | None = None  # per rating, when no pattern fits
    trip_curve: TripCurve | None = None
    magnetic_trip_multiple: PositiveFloat | None = None  # on AC
    magnetic_trip_multiple_dc: PositiveFloat | None = None
    dc_rating_v: PositiveFloat | None = None  # the whole MCB, poles in series

    @field_validator("ratings_a")
    @classmethod
    def _ratings_increase(cls, value: list[int]) -> list[int]:
        if any(a >= b for a, b in pairwise(value)):
            raise ValueError("ratings_a must be strictly increasing")
        return value

    @field_validator("code_pattern")
    @classmethod
    def _pattern_uses_rating(cls, value: str | None) -> str | None:
        if value is None:
            return None
        check_template(value, {"rating"})
        if "rating" not in template_fields(value):
            raise ValueError("code_pattern must contain {rating}")
        try:
            value.format(rating=1)
        except Exception as exc:  # any failure to format means the pattern is unusable
            raise ValueError(f"code_pattern cannot be formatted with a rating: {exc}") from exc
        return value

    @model_validator(mode="after")
    def _codes_and_trip(self) -> "McbCatalogue":
        if (self.code_pattern is None) == (self.codes is None):
            raise ValueError("give exactly one of code_pattern and codes")
        if self.codes is not None and set(self.codes) != set(self.ratings_a):
            raise ValueError("codes must list exactly the ratings in ratings_a")
        ac = self.magnetic_trip_multiple
        if self.trip_curve is not None and ac is not None:
            low, high = TRIP_BANDS[self.trip_curve]
            if not low <= ac <= high:
                raise ValueError(
                    f"a {self.trip_curve} curve trips magnetically at {low:g} to {high:g} "
                    f"x In on AC, not {ac:g}"
                )
        dc = self.magnetic_trip_multiple_dc
        if ac is not None and dc is not None and dc < ac:
            raise ValueError("magnetic_trip_multiple_dc must not be below magnetic_trip_multiple")
        return self

    @property
    def magnetic_multiple(self) -> float | None:
        """The AC magnetic trip multiple: as written, else the curve's lower bound."""
        if self.magnetic_trip_multiple is not None:
            return self.magnetic_trip_multiple
        return None if self.trip_curve is None else TRIP_BANDS[self.trip_curve][0]

    def code_for(self, rating_a: int) -> str:
        """Return the order code for ``rating_a``; raise ``ValueError`` if not catalogued."""
        if rating_a not in self.ratings_a:
            raise ValueError(f"no {self.family} MCB of {rating_a} A in the catalogue")
        if self.codes is not None:
            return self.codes[rating_a]
        assert self.code_pattern is not None
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
    tag: str | None = None  # column B of the grounding row


class HousekeepingRef(InputModel):
    """Housekeeping role filled by a device record (ADR 0010 item 1)."""

    part_id: PartId


class FanRef(HousekeepingRef):
    airflow_m3h: PositiveFloat


class SocketRef(HousekeepingRef):
    rating_a: PositiveInt


class ChangeOverDiodes(InputModel):
    """COD-1 and COD-2 device records (spec: Tags, other device type codes)."""

    negative: PartId
    positive: PartId


class Housekeeping(InputModel):
    """Housekeeping kit roles (spec: Inputs, commodity catalogues)."""

    lamp: HousekeepingRef
    door_switch: HousekeepingRef | None = None
    fan: FanRef
    vent_filter: HousekeepingRef
    thermostat: HousekeepingRef
    ipr_kit: HousekeepingRef
    change_over_diodes: ChangeOverDiodes
    socket: SocketRef


class Catalogues(InputModel):
    """Commodity catalogues held by the library (spec: Inputs, 1. Device library)."""

    mcb: McbCatalogue
    mcb_dc: McbCatalogue | None = None  # the DC set when it differs from ``mcb`` (ADR 0023)
    aux_contact: AuxContact
    terminal_blocks: Annotated[dict[str, TerminalBlockType], Field(min_length=1)]
    busbars: Annotated[dict[str, Busbar], Field(min_length=1)]
    enclosure_u: PositiveInt = 42
    housekeeping: Housekeeping

    @field_validator("mcb_dc")
    @classmethod
    def _dc_set_is_dc_rated(cls, value: McbCatalogue | None) -> McbCatalogue | None:
        if value is not None and value.dc_rating_v is None:
            raise ValueError("catalogues.mcb_dc needs dc_rating_v")
        return value

    @property
    def dc_mcb(self) -> McbCatalogue:
        """The MCB set that sizes the DC branches: ``mcb_dc``, else ``mcb`` (ADR 0023)."""
        return self.mcb_dc if self.mcb_dc is not None else self.mcb


DEFAULT_BRAND = "default"  # the brand id of the ``catalogues`` entries
BrandId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*$")]


class McbBrand(McbCatalogue):
    id: BrandId
    name: str | None = None
    ac_rated: bool = True  # false for a DC-only family; refused as ``mcb``, valid as ``mcb_dc``


class AuxContactBrand(AuxContact):
    id: BrandId
    name: str | None = None


class TerminalBlockBrand(InputModel):
    id: BrandId
    name: str | None = None
    types: Annotated[dict[str, TerminalBlockType], Field(min_length=1)]


class BusbarBrand(InputModel):
    id: BrandId
    name: str | None = None
    entries: Annotated[dict[str, Busbar], Field(min_length=1)]


class HousekeepingBrand(Housekeeping):
    id: BrandId
    name: str | None = None


BrandSet = McbBrand | AuxContactBrand | TerminalBlockBrand | BusbarBrand | HousekeepingBrand


class CatalogueBrands(InputModel):
    """Further brand sets per catalogue; ``catalogues`` is the brand ``default`` (ADR 0017)."""

    mcb: list[McbBrand] = Field(default_factory=list)
    aux_contact: list[AuxContactBrand] = Field(default_factory=list)
    terminal_blocks: list[TerminalBlockBrand] = Field(default_factory=list)
    busbars: list[BusbarBrand] = Field(default_factory=list)
    housekeeping: list[HousekeepingBrand] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> "CatalogueBrands":
        for kind in CatalogueBrands.model_fields:
            seen: set[str] = set()
            for brand in getattr(self, kind):
                if brand.id == DEFAULT_BRAND:
                    raise ValueError(
                        f"{kind} brand id '{DEFAULT_BRAND}' names the catalogues entry; "
                        "choose another id"
                    )
                if brand.id in seen:
                    raise ValueError(f"duplicate {kind} brand id '{brand.id}'")
                seen.add(brand.id)
        return self


class CatalogueChoice(InputModel):
    """The brand set picked per catalogue; unset means ``default``."""

    mcb: BrandId | None = None
    mcb_dc: BrandId | None = None  # an ``mcb`` brand for the DC branches; unset: as ``mcb``
    aux_contact: BrandId | None = None
    terminal_blocks: BrandId | None = None
    busbars: BrandId | None = None
    housekeeping: BrandId | None = None


class Library(InputModel):
    """The device library file (spec: Inputs, 1. Device library)."""

    devices: Annotated[list[DeviceType], Field(min_length=1)]
    catalogues: Catalogues
    catalogue_brands: CatalogueBrands = Field(default_factory=CatalogueBrands)

    @model_validator(mode="after")
    def _groups_and_brands(self) -> "Library":
        for device in self.devices:
            for name in ("derived_from", "sfp_choice"):
                if getattr(device, name):
                    raise ValueError(f"{device.part_id}: {name} is set by the loader")
        categories: dict[str, Category] = {}
        for device in self.devices:
            if device.alt_group is None:
                continue
            first = categories.setdefault(device.alt_group, device.category)
            if first is not device.category:
                raise ValueError(
                    f"alt group '{device.alt_group}' mixes categories "
                    f"{first.value} and {device.category.value}"
                )
        keyed = (
            ("terminal_blocks", "types", self.catalogue_brands.terminal_blocks),
            ("busbars", "entries", self.catalogue_brands.busbars),
        )
        for kind, _field, brands in keyed:
            needed = getattr(self.catalogues, kind).keys()
            for brand in brands:
                missing = sorted(needed - getattr(brand, _field).keys())
                if missing:
                    raise ValueError(
                        f"{kind} brand '{brand.id}' lacks {', '.join(missing)} "
                        f"(every key of catalogues.{kind} is needed)"
                    )
        return self

    def get(self, part_id: str) -> DeviceType | None:
        """Return the device with ``part_id``, or ``None``."""
        for device in self.devices:
            if device.part_id == part_id:
                return device
        return None

    def part_ids(self) -> list[str]:
        """Return all part ids in file order."""
        return [device.part_id for device in self.devices]

    def alt_group(self, key: str) -> list[DeviceType]:
        """Return the devices in alternative group ``key``, in file order."""
        return [device for device in self.devices if device.alt_group == key]

    def alternatives(self, part_id: str) -> list[DeviceType]:
        """Return the other members of ``part_id``'s alternative group, in file order."""
        device = self.get(part_id)
        if device is None or device.alt_group is None:
            return []
        return [d for d in self.alt_group(device.alt_group) if d.part_id != part_id]

    def brand_ids(self, kind: str) -> list[str]:
        """Return the brand ids of catalogue ``kind``: ``default`` first, then file order."""
        brands: list[BrandSet] = getattr(self.catalogue_brands, _brand_list(kind))
        return [DEFAULT_BRAND, *(brand.id for brand in brands)]


def resolve_catalogues(library: Library, choice: CatalogueChoice) -> Library:
    """``library`` with the chosen brand sets in ``catalogues``; ``library`` itself when every
    choice is ``default``. Raise ``ValueError`` for an id the library does not have."""
    update: dict[str, object] = {}
    for kind in CatalogueChoice.model_fields:
        brand_id = getattr(choice, kind)
        if kind == "mcb_dc" and brand_id is None:
            brand_id = choice.mcb  # the DC set follows the AC choice unless one is given
        if brand_id is None or brand_id == DEFAULT_BRAND:
            continue
        brands = getattr(library.catalogue_brands, _brand_list(kind))
        brand = next((b for b in brands if b.id == brand_id), None)
        if brand is None:
            known = ", ".join(library.brand_ids(kind))
            raise ValueError(f"no {kind} brand '{brand_id}' (the library has: {known})")
        update[kind] = _plain(kind, brand)
    if choice.mcb_dc == DEFAULT_BRAND and "mcb" in update:
        update["mcb_dc"] = library.catalogues.dc_mcb  # the default DC set, not the AC brand
    if not update:
        return library
    catalogues = library.catalogues.model_copy(update=update)
    return library.model_copy(update={"catalogues": catalogues})


def _brand_list(kind: str) -> str:
    """The ``catalogue_brands`` list a choice key picks from: ``mcb_dc`` picks an ``mcb``."""
    return "mcb" if kind == "mcb_dc" else kind


def _plain(kind: str, brand: BrandSet) -> object:
    """The catalogue value a brand set stands for, without its id and name."""
    if isinstance(brand, TerminalBlockBrand):
        return brand.types
    if isinstance(brand, BusbarBrand):
        return brand.entries
    plain_type: dict[str, type[InputModel]] = {
        "mcb": McbCatalogue,
        "mcb_dc": McbCatalogue,
        "aux_contact": AuxContact,
        "housekeeping": Housekeeping,
    }
    return plain_type[kind].model_validate(brand.model_dump(exclude={"id", "name", "ac_rated"}))
