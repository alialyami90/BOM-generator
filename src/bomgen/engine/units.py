"""Expand a panel's device instances into tagged rows (spec: Data model and generation
order, step 1)."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from bomgen.engine.errors import EngineError
from bomgen.engine.tags import device_tags, first_number
from bomgen.models.library import DeviceType, Library
from bomgen.models.panel import DeviceInstance, Lan, Panel


@dataclass(frozen=True)
class DeviceRow:
    """One device instance of a panel with its tags resolved."""

    device: DeviceType
    instance: DeviceInstance
    lan: Lan | None
    tag: str | None
    unit_tags: tuple[str | None, ...]


def expand_devices(
    panel: Panel, library: Library, instances: Sequence[DeviceInstance] | None = None
) -> tuple[DeviceRow, ...]:
    """Tag ``instances`` (default: the panel's devices) in order, numbering per type and
    level across rows; a row's ``first_nn`` restarts the count (ADR 0013)."""
    used: Counter[tuple[str | None, str | None]] = Counter()
    rows: list[DeviceRow] = []
    for instance in panel.devices if instances is None else instances:
        device = lookup(library, instance.part_id)
        lan = instance.lan or panel.lan
        key = (device.tag_type, device.purdue_level)
        start = next_free = first_number(device) + used[key]
        if instance.first_nn is not None:
            if instance.first_nn < next_free:
                raise EngineError(
                    f"{panel.id}: {instance.part_id} first_nn {instance.first_nn} repeats "
                    f"numbers already used in the panel (next free {next_free})"
                )
            start = instance.first_nn
        tags = device_tags(
            device,
            prefix=panel.tag_prefix,
            lan=lan,
            qty=instance.qty,
            start=start,
            override=instance.tag,
        )
        used[key] = start - first_number(device) + instance.qty
        rows.append(DeviceRow(device, instance, lan, tags.row, tags.units))
    return tuple(rows)


def lookup(library: Library, part_id: str) -> DeviceType:
    """The library record for ``part_id``; the loader has already checked it exists."""
    device = library.get(part_id)
    if device is None:
        raise EngineError(f"part '{part_id}' is not in the library")
    return device


def describe(device: DeviceType, lan: Lan | None, purpose: str | None) -> str:
    """BOM column C from the device's description template."""
    level = device.purdue_level.value if device.purdue_level else ""
    return device.description_template.format(
        lan=lan or "", level=level, purpose=purpose or ""
    ).strip()
