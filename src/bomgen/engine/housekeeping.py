"""Group D: cabinet housekeeping (spec: Derivation rules -> Housekeeping kit (group D);
Data model and generation order, step 5)."""

from collections.abc import Sequence

from bomgen.engine.errors import EngineError
from bomgen.engine.items import BomItem
from bomgen.engine.kits import device_item
from bomgen.engine.units import expand_devices, lookup
from bomgen.models.bom import Group
from bomgen.models.library import Library
from bomgen.models.panel import DeviceInstance, Panel, Ventilation
from bomgen.models.project import LooseExtra

FORCED_FANS = 2
FORCED_THERMOSTATS = 3
NATURAL_FILTERS = 2
NATURAL_THERMOSTATS = 1


def needs_change_over(panel: Panel, library: Library, loose: Sequence[LooseExtra]) -> bool:
    """Whether the panel gets change-over diodes: the option, or on ``auto`` any
    single-fed DC load in the panel or fed from it."""
    option = panel.options.change_over_diodes
    if option != "auto":
        return option
    part_ids = [d.part_id for d in panel.devices]
    part_ids += [item.part_id for item in loose if item.fed_from == panel.id]
    return any(lookup(library, part_id).power_supplies == 1 for part_id in part_ids)


def housekeeping(
    panel: Panel, library: Library, ventilation: Ventilation, change_over: bool
) -> list[BomItem]:
    """Lamp (+ door switch), fans or filters, thermostats, IPR kit, diodes, socket."""
    kit = library.catalogues.housekeeping
    parts: list[tuple[str, int]] = [(kit.lamp.part_id, 1)]
    if kit.door_switch is not None:
        parts.append((kit.door_switch.part_id, 1))
    if ventilation is Ventilation.NATURAL:
        parts += [(kit.vent_filter.part_id, NATURAL_FILTERS)]
        parts += [(kit.thermostat.part_id, NATURAL_THERMOSTATS)]
    else:
        parts += [(kit.fan.part_id, FORCED_FANS), (kit.thermostat.part_id, FORCED_THERMOSTATS)]
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
    instances = [DeviceInstance(part_id=part_id, qty=qty) for part_id, qty in parts]
    return [device_item(row, library, Group.D) for row in expand_devices(panel, library, instances)]
