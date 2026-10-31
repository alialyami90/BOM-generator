"""Device tags (spec: Tag naming conventions).

Device tags follow ``<PANEL>-<LEVEL>-<TYPE>-<LAN><NN>``; a library ``tag_pattern`` or a
panel ``tag`` overrides that. A row of several units carries one range or list tag.
"""

from dataclasses import dataclass

from bomgen.io.mirror import lan_index
from bomgen.models.library import Category, DeviceType, PurdueLevel
from bomgen.models.panel import Lan

# First NN per Purdue level; EXT devices carry the LAN letter only.
FIRST_NUMBER: dict[PurdueLevel, int] = {PurdueLevel.L2: 1, PurdueLevel.L1: 11, PurdueLevel.L3: 1}
# Housekeeping parts whose units are always numbered: FAN-1,2, TH-1,2,3, WS-TH-1.
NUMBERED_CATEGORIES = frozenset({Category.FAN, Category.THERMOSTAT})


@dataclass(frozen=True)
class Tags:
    """The row's tag and one tag per unit (``None`` for untagged parts)."""

    row: str | None
    units: tuple[str | None, ...]


def first_number(device: DeviceType) -> int:
    """Where this device's unit numbering starts in a panel."""
    if device.purdue_level is None:
        return 1
    return FIRST_NUMBER.get(device.purdue_level, 1)


def device_tags(
    device: DeviceType,
    *,
    prefix: str,
    lan: Lan | None,
    qty: int,
    start: int,
    override: str | None = None,
) -> Tags:
    """Tags for ``qty`` units of ``device``, numbered from ``start``."""
    numbers = range(start, start + qty)
    if override is not None:
        units = (override,) if qty == 1 else tuple(f"{override}-{n}" for n in range(1, qty + 1))
        return Tags(override, units)
    level = device.purdue_level.value if device.purdue_level else ""
    type_code = device.tag_type or ""
    if device.tag_pattern is not None:
        fields = {
            "prefix": prefix,
            "level": level,
            "type": type_code,
            "lan": lan or "",
            "lan_index": lan_index(lan) if lan else "",
        }
        units = tuple(device.tag_pattern.format(**fields, nn=f"{n:02d}") for n in numbers)
        return Tags(_range(units), units)
    if device.tag_type is None:
        return Tags(None, (None,) * qty)
    if device.purdue_level is not None:
        head = f"{prefix}-{level}-{type_code}"
        if device.purdue_level is PurdueLevel.EXT and qty == 1:
            tag = f"{head}-{lan}" if lan else head
            return Tags(tag, (tag,))
        units = tuple(f"{head}-{lan or ''}{n:02d}" for n in numbers)
        return Tags(_range(units), units)
    if device.category in NUMBERED_CATEGORIES or qty > 1:
        units = tuple(f"{prefix}-{type_code}-{n}" for n in numbers)
        return Tags(f"{prefix}-{type_code}-{','.join(map(str, numbers))}", units)
    tag = f"{prefix}-{type_code}"
    return Tags(tag, (tag,))


def _range(units: tuple[str, ...]) -> str:
    """``PSA1-L1-ESW-A11 to A16`` from the first and last unit tags."""
    if len(set(units)) == 1:
        return units[0]
    return f"{units[0]} to {units[-1].rsplit('-', 1)[-1]}"


def without_prefix(tag: str, prefix: str) -> str:
    """The tag as written inside descriptions and SFP rows: no ``<PANEL>-`` prefix."""
    return tag.removeprefix(f"{prefix}-")


def short_tag(unit_tag: str | None, device: DeviceType, prefix: str) -> str:
    """A unit as MCB rows and nameplates name it: no panel prefix, underscores; an
    untagged unit is named by its model."""
    if unit_tag is None:
        return device.model or device.part_id
    return without_prefix(unit_tag, prefix).replace("-", "_")
