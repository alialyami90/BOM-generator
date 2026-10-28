"""Device rows with their kit children (spec: Data model and generation order, step 2)."""

from collections.abc import Iterable

from bomgen.engine.items import BomItem
from bomgen.engine.units import DeviceRow, describe, lookup
from bomgen.models.bom import BomLine, Group
from bomgen.models.library import Library


def device_item(row: DeviceRow, library: Library, group: Group) -> BomItem:
    """The row's line plus one child line per kit part, quantities per parent unit."""
    device, instance = row.device, row.instance
    hwio = instance.hwio_points
    line = BomLine(
        group=group,
        tag=row.tag,
        description=describe(device, row.lan, instance.purpose),
        qty=instance.qty,
        make=device.make,
        model=device.model,
        ordering_code=device.ordering_code,
        hwio=device.hwio_points * instance.qty if hwio is None else hwio,
        part_id=device.part_id,
        merge_fg=bool(device.children),
    )
    children = []
    for rule in device.children:
        child = lookup(library, rule.part_id)
        per_unit = device.cores if rule.qty == "cores" else rule.qty
        assert per_unit is not None  # the library model requires cores for a "cores" child
        children.append(
            BomLine(
                group=group,
                description=describe(child, row.lan, instance.purpose),
                qty=per_unit * instance.qty,
                make=child.make,
                model=child.model,
                ordering_code=child.ordering_code,
                hwio=child.hwio_points * per_unit * instance.qty,
                part_id=child.part_id,
            )
        )
    return BomItem(line, tuple(children))


def main_equipment(rows: Iterable[DeviceRow], library: Library) -> list[BomItem]:
    """Group B: the panel's devices in display order."""
    return [device_item(row, library, Group.B) for row in rows]
