"""Group C: SFPs, cable managers and serial cables (spec: Derivation rules -> Network
accessories (group C); Data model and generation order, step 3)."""

from collections.abc import Sequence

from bomgen.engine.errors import EngineError
from bomgen.engine.items import BomItem
from bomgen.engine.kits import device_item
from bomgen.engine.tags import without_prefix
from bomgen.engine.units import DeviceRow, describe, expand_devices
from bomgen.models.bom import BomLine, Group, Qty, QtySum
from bomgen.models.library import Category, DeviceType, Library, Media
from bomgen.models.panel import DeviceInstance, Panel, PortAllocation, PortPlan

# "roughly one per rack-mounted switch/patch panel"
CABLE_MANAGED = frozenset({Category.NETWORK_SWITCH, Category.PATCH_PANEL})


def accessories(panel: Panel, rows: Sequence[DeviceRow], library: Library) -> list[BomItem]:
    """SFPs per host in group B order, then cable managers, then serial cables."""
    items = [item for row in rows for item in _sfp_items(panel, row, library)]
    managed = sum(row.instance.qty for row in rows if row.device.category in CABLE_MANAGED)
    if managed:
        items.append(_commodity(panel, library, Category.CABLE_MANAGER, managed))
    serial_ports = sum(plan.serial_ports for row in rows if (plan := port_plan(panel, row)))
    if serial_ports:
        items.append(_commodity(panel, library, Category.SERIAL_CABLE, serial_ports))
    return items


def port_plan(panel: Panel, row: DeviceRow) -> PortPlan | None:
    """The row's port plan, keyed by its tag or else by its part id."""
    if row.tag is not None and row.tag in panel.port_plans:
        return panel.port_plans[row.tag]
    return panel.port_plans.get(row.device.part_id)


def _sfp_items(panel: Panel, row: DeviceRow, library: Library) -> list[BomItem]:
    plan = port_plan(panel, row)
    if plan is None:
        return []
    # One row per SFP part and media: the tag names the media.
    terms: dict[tuple[str, Media], list[int]] = {}
    parts: dict[str, DeviceType] = {}
    for allocation in (*plan.uplinks_l3, *plan.uplinks, *plan.downlinks):
        if allocation.media is Media.RJ45:
            continue
        part = _sfp_for(row, allocation, library)
        parts[part.part_id] = part
        counts = terms.setdefault((part.part_id, allocation.media), [])
        counts.append(allocation.count)
        if allocation.spare:
            counts.append(allocation.spare)
    host = without_prefix(row.tag, panel.tag_prefix) if row.tag else None
    items = []
    for (part_id, media), counts in terms.items():
        part = parts[part_id]
        qty: Qty = counts[0] if len(counts) == 1 else QtySum(parts=tuple(counts))
        tag = f"{host} SFP ({media.value})" if host else f"SFP ({media.value})"
        line = BomLine(
            group=Group.C,
            tag=tag,
            description=describe(part, row.lan, None),
            qty=qty,
            make=part.make,
            model=part.model,
            ordering_code=part.ordering_code,
            part_id=part.part_id,
        )
        items.append(BomItem(line))
    return items


def _sfp_for(row: DeviceRow, allocation: PortAllocation, library: Library) -> DeviceType:
    """The SFP serving ``allocation``: the host's make first, else library order."""
    matches = [
        device
        for device in library.devices
        if device.category is Category.SFP
        and any(p.speed is allocation.speed and p.media is allocation.media for p in device.ports)
    ]
    if not matches:
        host = row.tag or row.device.part_id
        raise EngineError(
            f"{host}: no SFP in the library for {allocation.speed.value} "
            f"{allocation.media.value} ports"
        )
    same_make = [device for device in matches if device.make == row.device.make]
    return (same_make or matches)[0]


def _commodity(panel: Panel, library: Library, category: Category, qty: int) -> BomItem:
    """One row of the first library part in ``category``."""
    part = next((d for d in library.devices if d.category is category), None)
    if part is None:
        raise EngineError(f"{panel.id}: the library has no {category.value} part")
    (row,) = expand_devices(panel, library, [DeviceInstance(part_id=part.part_id, qty=qty)])
    return device_item(row, library, Group.C)
