"""Cable suggestions: the patch cords the port plans call for, as loose rows waiting to be
accepted (plan M65, ADR 0035). Nothing is written here.

Each link is one cord, counted once at its upper end (Q71): an L2 switch's downlinks,
its L3 uplinks and the external links. A downlink is in the cabinet when the panel holds
the device it serves (its own L1 switches, or a device whose port plan sends downlinks
to it), else between cabinets. The L1 A-B interlinks, which have no upper end, count once
from side A; ring links once per neighbour pair. Lengths per class come from the design
basis (Q66); an external link uses its own ``cable_length_m``.
"""

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from bomgen.engine.layout import network_inputs
from bomgen.engine.sizing import NetworkInputs, l1_links
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BuildResult
from bomgen.models.library import Category, Media, PortSpeed, PurdueLevel
from bomgen.models.panel import DeviceInstance, Panel, PortAllocation
from bomgen.models.substation import CableDefaults, Topology

LengthClass = Literal["in_cabinet", "inter_cabinet", "external"]
OTHER_CABINETS = "Other cabinets"
L3_NETWORK = "L3 network"


@dataclass(frozen=True)
class CableSuggestion:
    """One suggested loose row: ``qty`` cords from the upper end ``from_tag``."""

    from_tag: str
    to_tag: str
    qty: int
    speed: PortSpeed | None
    media: Media | None
    length_class: LengthClass
    length_m: float | None
    part_id: str | None
    description: str
    rule: str


@dataclass(frozen=True)
class CableSuggestions:
    rows: tuple[CableSuggestion, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class _Cord:
    from_tag: str
    to_tag: str
    qty: int
    speed: PortSpeed | None
    media: Media | None
    length_class: LengthClass
    rule: str
    length_m: float | None = None  # set: an external link's own length


def suggest_cables(loaded: LoadedSubstation, result: BuildResult) -> CableSuggestions:
    basis = loaded.substation.design_basis
    defaults = (basis.cables if basis else None) or CableDefaults()
    lengths: dict[LengthClass, float | None] = {
        "in_cabinet": defaults.in_cabinet_m,
        "inter_cabinet": defaults.inter_cabinet_m,
        "external": defaults.external_m,
    }
    taken = _existing(loaded)
    cables = [d for d in loaded.library.devices if d.category is Category.CABLE]
    rows: list[CableSuggestion] = []
    missing: dict[tuple[Media | None, float | None], int] = {}
    for cord in _cords(loaded, result):
        if (cord.from_tag, cord.to_tag, cord.media, cord.speed) in taken:
            continue
        length = cord.length_m if cord.length_m is not None else lengths[cord.length_class]
        part = next((d for d in cables if d.media == cord.media and d.length_m == length), None)
        if part is None:
            missing[(cord.media, length)] = missing.get((cord.media, length), 0) + cord.qty
        rows.append(
            CableSuggestion(
                from_tag=cord.from_tag,
                to_tag=cord.to_tag,
                qty=cord.qty,
                speed=cord.speed,
                media=cord.media,
                length_class=cord.length_class,
                length_m=length,
                part_id=part.part_id if part else None,
                description=_description(cord.media),
                rule=cord.rule,
            )
        )
    warnings = tuple(
        f"No library cable for {_kind(media, length)}: {n} cords are free text"
        for (media, length), n in missing.items()
    )
    return CableSuggestions(rows=tuple(rows), warnings=warnings)


def loose_item(row: CableSuggestion) -> dict[str, Any]:
    """The loose-material item an accepted suggestion becomes."""
    cable: dict[str, Any] = {"from_tag": row.from_tag, "to_tag": row.to_tag}
    if row.length_m is not None:
        cable["length_m"] = row.length_m
    if row.media is not None:
        cable["media"] = row.media.value
    if row.speed is not None:
        cable["speed"] = row.speed.value
    named = {"part_id": row.part_id} if row.part_id else {"description": row.description}
    return {**named, "qty": row.qty, "cable": cable}


def _existing(loaded: LoadedSubstation) -> set[tuple[str, str, Media | None, PortSpeed | None]]:
    material = loaded.substation.loose_material
    items = material.items if material else []
    return {
        (i.cable.from_tag, i.cable.to_tag, i.cable.media, i.cable.speed)
        for i in items
        if i.cable is not None
    }


def _description(media: Media | None) -> str:
    if media is Media.RJ45:
        return "RJ45 patch cord"
    return f"LC-LC duplex patch cord, {media.value}" if media else "Patch cord"


def _kind(media: Media | None, length: float | None) -> str:
    parts = [media.value if media else "any media"]
    if length is not None:
        parts.append(f"{length:g} m")
    return " ".join(parts)


def _cords(loaded: LoadedSubstation, result: BuildResult) -> Iterator[_Cord]:
    net = network_inputs(loaded)
    levels = {d.part_id: d.purdue_level for d in loaded.library.devices}
    tags = {
        (p.panel_id, line.part_id): line.tag
        for p in result.panels
        for line in reversed(p.lines)
        if line.part_id and line.tag
    }
    panels = loaded.panels
    for panel in panels:
        l1 = [d for d in panel.devices if levels.get(d.part_id) is PurdueLevel.L1]
        l1_media = _l1_link(panel, l1[0].part_id) if l1 else None
        for part_id, plan in panel.port_plans.items():
            if levels.get(part_id) is not PurdueLevel.L2:
                continue
            upper = tags.get((panel.id, part_id), part_id)
            for alloc in plan.downlinks:
                left = alloc.count
                served: list[tuple[str, int, str]] = []
                for device in l1:
                    if l1_media == (alloc.speed, alloc.media):
                        served.append(
                            (
                                tags.get((panel.id, device.part_id), device.part_id),
                                l1_links(device.qty, net),
                                "L2 downlinks to the L1 switches in the cabinet",
                            )
                        )
                for other, other_plan in panel.port_plans.items():
                    if other == part_id or levels.get(other) in (PurdueLevel.L1, PurdueLevel.L2):
                        continue
                    n = sum(_same(a, alloc) for a in other_plan.downlinks)
                    if n:
                        rule = "L2 downlinks to a device in the cabinet"
                        served.append((tags.get((panel.id, other), other), n, rule))
                for to_tag, n, rule in served:
                    n = min(n, left)
                    if n:
                        left -= n
                        yield _Cord(upper, to_tag, n, alloc.speed, alloc.media, "in_cabinet", rule)
                if left:
                    rule = "L2 downlinks to other cabinets"
                    yield _Cord(
                        upper, OTHER_CABINETS, left, alloc.speed, alloc.media, "inter_cabinet", rule
                    )
            for alloc in plan.uplinks_l3:
                rule = "L2 uplinks to L3"
                yield _Cord(
                    upper, L3_NETWORK, alloc.count, alloc.speed, alloc.media, "external", rule
                )
            yield from _external(loaded, panel, upper)
        if l1:
            yield from _l1_links(panels, panel, l1, net, tags, l1_media)


def _same(a: PortAllocation, b: PortAllocation) -> int:
    return a.count if (a.speed, a.media) == (b.speed, b.media) else 0


def _l1_link(panel: Panel, part_id: str) -> tuple[PortSpeed, Media | None]:
    """The speed and media of an L1 switch's uplinks: its port plan's, else 1G MM."""
    plan = panel.port_plans.get(part_id)
    if plan and plan.uplinks:
        return plan.uplinks[0].speed, plan.uplinks[0].media
    return PortSpeed.G1, Media.MM


def _external(loaded: LoadedSubstation, panel: Panel, upper: str) -> Iterator[_Cord]:
    """The links leaving the substation from this side's L2 switch (plan M61)."""
    for link in loaded.substation.network.external_links:
        if panel.lan == "A" or (link.redundant and panel.lan == "B"):
            yield _Cord(
                upper,
                link.name,
                link.count,
                link.speed,
                link.media,
                "external",
                f"External link {link.name}",
                link.cable_length_m,
            )


def _l1_links(
    panels: Sequence[Panel],
    panel: Panel,
    l1: list[DeviceInstance],
    net: NetworkInputs,
    tags: dict[tuple[str, str], str],
    media: tuple[PortSpeed, Media | None] | None,
) -> Iterator[_Cord]:
    speed, kind = media or (PortSpeed.G1, Media.MM)
    if net.topology is Topology.RING:
        for device in l1:
            tag = tags.get((panel.id, device.part_id), device.part_id)
            n = device.qty - math.ceil(device.qty / net.ring_max_switches)
            if n:
                yield _Cord(tag, tag, n, speed, kind, "in_cabinet", "L1 ring links")
        return
    if not net.l1_interlink or panel.lan != "A":
        return
    others = [
        (p, d)
        for p in panels
        if p.lan == "B"
        for d in p.devices
        if any(d.part_id == x.part_id for x in l1)
    ]
    for index, device in enumerate(l1):
        tag = tags.get((panel.id, device.part_id), device.part_id)
        if index < len(others):
            other_panel, other = others[index]
            to_tag = tags.get((other_panel.id, other.part_id), other.part_id)
        else:
            to_tag = "Side B L1 switches"
        rule = "L1 A-B interlinks, counted from side A"
        yield _Cord(tag, to_tag, device.qty, speed, kind, "inter_cabinet", rule)
