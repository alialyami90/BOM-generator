"""The comparison list of a device and its alternatives (ADR 0017; design: Library editing).

Alternatives are library parts linked by one group key (`alt_group`), so the list is the device
itself first, then the other members in library order, each with the figures the Library screen
compares and the difference from the device.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from bomgen.library_store.device_db import DeviceRecord
from bomgen.models.library import DeviceType, Library, PortGroup


@dataclass(frozen=True)
class AlternativeRow:
    """One comparison row. A delta is this row minus the device, none if either is missing."""

    part_id: str
    is_self: bool
    tier: str | None
    make: str | None
    model: str | None
    unit_power_w: float | None
    inrush_a: float | None
    first_port_group: PortGroup | None
    height_u: int | None
    data_quality: str | None  # confirmed | partial | unverified, from the device database
    power_delta_w: float | None
    inrush_delta_a: float | None
    height_delta_u: int | None


def _delta(value: float | None, reference: float | None) -> float | None:
    return None if value is None or reference is None else value - reference


def compare_alternatives(
    library: Library, part_id: str, records: Mapping[str, DeviceRecord] | None = None
) -> list[AlternativeRow]:
    """`part_id` and its alternatives as comparison rows; `records` adds the data quality.

    Raises `KeyError` for a part the library does not have.
    """
    device = library.get(part_id)
    if device is None:
        raise KeyError(part_id)
    members = [device, *library.alternatives(part_id)]
    return [_row(member, device, records) for member in members]


def _row(
    member: DeviceType, reference: DeviceType, records: Mapping[str, DeviceRecord] | None
) -> AlternativeRow:
    record = records.get(member.part_id) if records else None
    height_delta = _delta(member.height_u, reference.height_u)
    return AlternativeRow(
        part_id=member.part_id,
        is_self=member is reference,
        tier=member.tier,
        make=member.make,
        model=member.model,
        unit_power_w=member.unit_power_w,
        inrush_a=member.inrush_a,
        first_port_group=member.ports[0] if member.ports else None,
        height_u=member.height_u,
        data_quality=record.verified if record else None,
        power_delta_w=_delta(member.unit_power_w, reference.unit_power_w),
        inrush_delta_a=_delta(member.inrush_a, reference.inrush_a),
        height_delta_u=None if height_delta is None else int(height_delta),
    )
