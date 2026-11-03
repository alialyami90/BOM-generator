"""Group D: cabinet housekeeping (spec: Derivation rules -> Housekeeping kit (group D);
Data model and generation order, step 5)."""

from collections.abc import Sequence
from dataclasses import dataclass

from bomgen.engine.errors import EngineError
from bomgen.engine.items import BomItem
from bomgen.engine.kits import device_item
from bomgen.engine.units import expand_devices, lookup
from bomgen.models.bom import Group
from bomgen.models.library import FanRef, HousekeepingRef, Library
from bomgen.models.panel import DeviceInstance, Panel, Ventilation
from bomgen.models.project import LooseExtra

FORCED_FANS = 2
FORCED_THERMOSTATS = 3
NATURAL_FILTERS = 2
NATURAL_THERMOSTATS = 1
LAMPS = 1


@dataclass(frozen=True)
class KitCounts:
    """How many of each housekeeping part the panel gets (ADR 0032)."""

    lamps: int
    fans: int
    thermostats: int
    filters: int
    heater: bool
    hygrostat: bool


def kit_counts(panel: Panel, ventilation: Ventilation) -> KitCounts:
    """The panel's housekeeping options, each unset count the spec's for the ventilation."""
    o = panel.options.housekeeping
    forced = ventilation is Ventilation.FORCED

    def given(value: int | None, default: int) -> int:
        return default if value is None else value

    return KitCounts(
        lamps=given(o.lamps, LAMPS),
        fans=given(o.fans, FORCED_FANS) if forced else 0,
        thermostats=given(o.thermostats_forced, FORCED_THERMOSTATS)
        if forced
        else given(o.thermostats_natural, NATURAL_THERMOSTATS),
        filters=0 if forced else given(o.filters, NATURAL_FILTERS),
        heater=o.heater,
        hygrostat=o.hygrostat,
    )


def kit_role(panel: Panel, library: Library, role: str) -> HousekeepingRef:
    """A housekeeping role the panel's options ask for; an error when the library lacks it."""
    ref: HousekeepingRef | None = getattr(library.catalogues.housekeeping, role)
    if ref is None:
        raise EngineError(
            f"{panel.id}: the panel asks for a {role.replace('_', ' ')} but the library's "
            f"housekeeping catalogue has no {role} part"
        )
    return ref


def needs_change_over(panel: Panel, library: Library, loose: Sequence[LooseExtra]) -> bool:
    """Whether the panel gets change-over diodes: the option, or on ``auto`` any
    single-fed DC load in the panel or fed from it."""
    option = panel.options.change_over_diodes
    if option != "auto":
        return option
    part_ids = [d.part_id for d in panel.devices]
    part_ids += [i.part_id for i in loose if i.part_id is not None and i.fed_from == panel.id]
    return any(lookup(library, part_id).power_supplies == 1 for part_id in part_ids)


def housekeeping(
    panel: Panel,
    library: Library,
    ventilation: Ventilation,
    change_over: bool,
    fan: FanRef | None = None,
) -> list[BomItem]:
    """Lamp (+ door switch), filters or fans (``fan``, else the catalogue fan),
    thermostats, heater, hygrostat, smoke detector, IPR kit, diodes, socket."""
    kit = library.catalogues.housekeeping
    fan = fan or kit.fan
    counts = kit_counts(panel, ventilation)
    parts: list[tuple[str, int]] = [(kit.lamp.part_id, counts.lamps)]
    if kit.door_switch is not None:
        parts.append((kit.door_switch.part_id, 1))
    parts += [
        (kit.vent_filter.part_id, counts.filters),
        (fan.part_id, counts.fans),
        (kit.thermostat.part_id, counts.thermostats),
    ]
    for role, wanted in (
        ("heater", counts.heater),
        ("hygrostat", counts.hygrostat),
        ("smoke_detector", panel.options.smoke_detector == "supplied"),
    ):
        if wanted:
            parts.append((kit_role(panel, library, role).part_id, 1))
    parts.append((kit.ipr_kit.part_id, 1))
    if change_over:
        diodes = kit.change_over_diodes
        parts += [(diodes.negative, 1), (diodes.positive, 1)]
    socket_a = panel.options.aux_socket_a
    if socket_a is not None:
        if socket_a != kit.socket.rating_a:
            raise EngineError(
                f"{panel.id}: aux_socket_a is {socket_a} A but the library socket "
                f"{kit.socket.part_id} is {kit.socket.rating_a} A"
            )
        parts.append((kit.socket.part_id, 1))
    instances = [DeviceInstance(part_id=part_id, qty=qty) for part_id, qty in parts if qty]
    return [device_item(row, library, Group.D) for row in expand_devices(panel, library, instances)]
