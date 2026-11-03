"""Library health: what the library owner should review and what is weak (M68).

Each measure works on a validated library; `parts_in_use` reads the substation files of the
projects on this PC so an obsolete part can say where it is still picked.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

import yaml

from bomgen.models.library import SOURCED_FIELDS, DeviceType, Library, PartState, SourcedField

# roles a housekeeping set may leave empty; a gap only when the default set fills it
_OPTIONAL_ROLES = ("door_switch", "nameplate", "heater", "hygrostat", "smoke_detector")


@dataclass(frozen=True)
class Health:
    states: dict[str, int]  # every state, zero included
    assumed: list[tuple[str, list[SourcedField]]]  # part id, the fields whose source is assumed
    alone: list[str]  # parts with no alternative
    obsolete_in_use: list[tuple[str, list[str]]]  # part id, where it is picked
    mcb_gaps: list[tuple[str, list[int]]]  # brand id, the default set's ratings it lacks
    housekeeping_gaps: list[tuple[str, list[str]]]  # brand id, roles the default fills


def missing_sources(device: DeviceType) -> list[str]:
    """The sized figures the part sets without saying where they come from."""
    return [f for f in SOURCED_FIELDS if _is_set(device, f) and f not in device.sources]


def _is_set(device: DeviceType, field: str) -> bool:
    value = getattr(device, field)
    return value is not None and value != []


def library_health(library: Library, used: Mapping[str, Sequence[str]] | None = None) -> Health:
    """Every measure of ``library``; ``used`` maps a part id to where projects pick it."""
    used = used or {}
    counts = Counter(d.state for d in library.devices)
    groups = Counter(d.alt_group for d in library.devices if d.alt_group is not None)
    reference = set(library.catalogues.mcb.ratings_a)
    if library.catalogues.mcb_dc is not None:
        reference |= set(library.catalogues.mcb_dc.ratings_a)
    default = library.catalogues.housekeeping
    filled = [r for r in _OPTIONAL_ROLES if getattr(default, r) is not None]
    return Health(
        states={s: counts[s] for s in get_args(PartState)},
        assumed=[
            (d.part_id, fields)
            for d in library.devices
            if (fields := [f for f, s in d.sources.items() if s.kind == "assumed"])
        ],
        alone=[
            d.part_id for d in library.devices if d.alt_group is None or groups[d.alt_group] < 2
        ],
        obsolete_in_use=[
            (d.part_id, list(used[d.part_id]))
            for d in library.devices
            if d.state == "obsolete" and used.get(d.part_id)
        ],
        mcb_gaps=[
            (b.id, missing)
            for b in library.catalogue_brands.mcb
            if (missing := sorted(reference - set(b.ratings_a)))
        ],
        housekeeping_gaps=[
            (b.id, gaps)
            for b in library.catalogue_brands.housekeeping
            if (gaps := [r for r in filled if getattr(b, r) is None])
        ],
    )


def parts_in_use(substations: Mapping[str, Path]) -> dict[str, list[str]]:
    """Where each part is picked: ``substations`` maps a label to a substation file. A file
    that is missing or does not read is skipped; health is a hint, not a check."""
    used: dict[str, list[str]] = {}
    for label, file in substations.items():
        try:
            data = yaml.safe_load(file.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        equipment = data.get("equipment") if isinstance(data, dict) else None
        for entry in equipment if isinstance(equipment, list) else []:
            part = entry.get("part_id") if isinstance(entry, dict) else None
            if isinstance(part, str) and label not in used.setdefault(part, []):
                used[part].append(label)
    return used
