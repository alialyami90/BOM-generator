"""Device rows with their kit children, and the loose-material table (spec: Data model
and generation order, step 2; How each panel BOM groups its materials -> Loose material)."""

from collections.abc import Iterable, Sequence

from bomgen.engine.items import BomItem, flatten
from bomgen.engine.units import DeviceRow, describe, lookup
from bomgen.io.derived import effective_part_id
from bomgen.models.bom import BomLine, Group, LooseTable, Qty
from bomgen.models.library import Library, LooseItem
from bomgen.models.panel import Panel
from bomgen.models.project import LooseExtra, LooseMaterial
from bomgen.models.substation import Equipment, EquipmentRole


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


def annunciator_items(
    equipment: Iterable[Equipment], library: Library, panels: Sequence[Panel]
) -> list[LooseExtra]:
    """Each annunciator row as a loose item with its part's kit, fed from panel 001: design
    §10 puts the annunciator in loose material (plan M45, Q51; Ali, plan M1c)."""
    if not panels:
        return []
    items = []
    for entry in equipment:
        part_id = effective_part_id(entry)
        if entry.role is EquipmentRole.ANNUNCIATOR and part_id is not None:
            kit = [i.part_id for i in lookup(library, part_id).loose_items]
            items.append(
                LooseExtra(part_id=part_id, qty=entry.qty, children=kit, fed_from=panels[0].id)
            )
    return items


def loose_table(
    material: LooseMaterial | None,
    substation: str,
    panel_rows: Iterable[tuple[Panel, Sequence[DeviceRow]]],
    library: Library,
) -> LooseTable | None:
    """The loose-material table: the project's items in order, then each device's loose
    items as one parent block (plan Q30); None when it has no rows (ADR 0020)."""
    if material is None:
        return None
    items = [_loose_extra(extra, library) for extra in material.items]
    for _panel, rows in panel_rows:
        for row in rows:
            if row.device.loose_items:
                items.append(_device_loose(row, library))
    if not items:
        return None
    return LooseTable(
        title=(substation, material.title), lines=flatten(items), host_panel=material.host_panel
    )


def _loose_line(part_id: str, tag: str | None, qty: Qty, library: Library) -> BomLine:
    part = lookup(library, part_id)
    return BomLine(
        group=Group.B,
        tag=tag,
        description=describe(part, None, None),
        qty=qty,
        make=part.make,
        model=part.model,
        ordering_code=part.ordering_code,
        part_id=part.part_id,
    )


def _loose_extra(extra: LooseExtra, library: Library) -> BomItem:
    if extra.part_id is None:  # free text: no make, model or ordering code (ADR 0022)
        assert extra.description is not None  # the model requires one or the other
        return BomItem(
            BomLine(group=Group.B, tag=extra.tag, description=extra.description, qty=extra.qty)
        )
    per_parent = extra.qty if isinstance(extra.qty, int) else 1
    line = _loose_line(extra.part_id, extra.tag, extra.qty, library)
    children = tuple(_loose_line(c, None, per_parent, library) for c in extra.children)
    return BomItem(line.model_copy(update={"merge_fg": bool(children)}), children)


def _device_loose(row: DeviceRow, library: Library) -> BomItem:
    def qty(item: LooseItem) -> Qty:
        return item.qty * row.instance.qty if isinstance(item.qty, int) else item.qty

    first, *rest = row.device.loose_items
    line = _loose_line(first.part_id, first.tag, qty(first), library)
    children = tuple(_loose_line(i.part_id, None, qty(i), library) for i in rest)
    return BomItem(line.model_copy(update={"merge_fg": bool(children)}), children)
