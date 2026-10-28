"""Network sizing: L1 and L2 switch counts and their port plans (ADR 0013, rules R1-R4).

Pure functions on small value types; ``engine.layout`` maps the substation onto them.
Every count here is per side: each IED has an A port and a B port, so ``ied_count``
IEDs need ``ied_count`` ports on each side.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from bomgen.engine.errors import EngineError
from bomgen.models.library import DeviceType, Media, PortSpeed, PortUse
from bomgen.models.panel import PortAllocation, PortPlan
from bomgen.models.substation import Topology

__all__ = [
    "L1Candidate",
    "L2Link",
    "NetworkInputs",
    "NetworkPlan",
    "SizingError",
    "SwitchPorts",
    "Topology",
    "l1_links",
    "l1_port_plan",
    "l1_reserved_ports",
    "l2_port_plan",
    "pick_l1_switch",
    "rank_l1_switches",
    "size_network",
    "switch_ports",
    "usable_ports",
]


class SizingError(EngineError):
    """The network inputs cannot be met by the chosen switches."""


@dataclass(frozen=True)
class SwitchPorts:
    """A switch's port count by what each port may connect (library ``usable_for``)."""

    part_id: str
    ied: int
    uplink: int
    any: int

    @property
    def total(self) -> int:
        return self.ied + self.uplink + self.any


@dataclass(frozen=True)
class NetworkInputs:
    ied_count: int
    topology: Topology = Topology.STAR
    ring_max_switches: int = 6
    l1_uplinks_per_switch: int = 1
    l1_interlink: bool = True
    l3_uplinks_per_l2: int = 2
    port_fraction: float = 0.20


@dataclass(frozen=True)
class L2Link:
    """Ports one equipment entry needs on each side's L2 switches."""

    owner: str
    ports: int
    speed: PortSpeed
    media: Media


@dataclass(frozen=True)
class NetworkPlan:
    """Switch counts per side; ``ied_count`` is kept only for the check report (R4)."""

    ied_count: int
    l1_part_id: str
    l1_per_side: int
    l1_usable_ports: int
    l1_links_per_side: int
    rings_per_side: int
    l2_part_id: str
    l2_per_side: int
    l2_usable_ports: int
    l2_demand_per_side: int


@dataclass(frozen=True)
class L1Candidate:
    """One library L1 switch and how many of it each side needs."""

    ports: SwitchPorts
    per_side: int
    usable_ports: int


def switch_ports(device: DeviceType) -> SwitchPorts:
    counts = dict.fromkeys(PortUse, 0)
    for group in device.ports:
        counts[group.usable_for] += group.count
    return SwitchPorts(
        device.part_id, counts[PortUse.IED], counts[PortUse.UPLINK], counts[PortUse.ANY]
    )


def l1_reserved_ports(net: NetworkInputs) -> int:
    """Ports each L1 switch keeps off the IEDs: uplink and A-B interlink, or two ring ports."""
    if net.topology is Topology.RING:
        return 2
    return net.l1_uplinks_per_switch + (1 if net.l1_interlink else 0)


def usable_ports(ports: SwitchPorts, *, reserved: int, port_fraction: float) -> int:
    """Ports left for devices once ``reserved`` (uplink ports first) and the spare are kept."""
    from_any = max(0, reserved - ports.uplink)
    free = max(0, ports.ied + ports.any - from_any)
    return math.floor(free * (1 - Fraction(str(port_fraction))))


def l1_links(n_l1: int, net: NetworkInputs) -> int:
    """L2 ports per side taken by the L1 switches (R2)."""
    if net.topology is Topology.RING:
        return 2 * math.ceil(n_l1 / net.ring_max_switches)
    return n_l1 * net.l1_uplinks_per_switch


def _l1_usable(ports: SwitchPorts, net: NetworkInputs) -> int:
    return usable_ports(ports, reserved=l1_reserved_ports(net), port_fraction=net.port_fraction)


def rank_l1_switches(candidates: Iterable[SwitchPorts], net: NetworkInputs) -> list[L1Candidate]:
    """Every candidate with a usable port, best first: fewest per side, fewest ports, part id."""
    ranked = []
    for ports in candidates:
        usable = _l1_usable(ports, net)
        if usable > 0:
            ranked.append(L1Candidate(ports, math.ceil(net.ied_count / usable), usable))
    return sorted(ranked, key=lambda c: (c.per_side, c.ports.total, c.ports.part_id))


def pick_l1_switch(candidates: Iterable[SwitchPorts], net: NetworkInputs) -> SwitchPorts:
    ranked = rank_l1_switches(candidates, net)
    if not ranked:
        raise SizingError("no L1 switch in the library has a port left for IEDs")
    return ranked[0].ports


def size_network(
    net: NetworkInputs, l1: SwitchPorts, l2: SwitchPorts, links: Sequence[L2Link]
) -> NetworkPlan:
    """Switch counts per side (R1, R2)."""
    l1_usable = _l1_usable(l1, net)
    if l1_usable <= 0 and net.ied_count > 0:
        raise SizingError(
            f"L1 switch {l1.part_id} has no port left for IEDs after "
            f"{l1_reserved_ports(net)} reserved and {net.port_fraction:.0%} spare"
        )
    n_l1 = math.ceil(net.ied_count / l1_usable) if net.ied_count else 0
    links_l1 = l1_links(n_l1, net)
    rings = math.ceil(n_l1 / net.ring_max_switches) if net.topology is Topology.RING else 0
    l2_usable = usable_ports(l2, reserved=net.l3_uplinks_per_l2, port_fraction=net.port_fraction)
    if l2_usable <= 0:
        raise SizingError(
            f"L2 switch {l2.part_id} has no port left after {net.l3_uplinks_per_l2} L3 "
            f"uplinks and {net.port_fraction:.0%} spare"
        )
    demand = links_l1 + sum(link.ports for link in links)
    return NetworkPlan(
        ied_count=net.ied_count,
        l1_part_id=l1.part_id,
        l1_per_side=n_l1,
        l1_usable_ports=l1_usable,
        l1_links_per_side=links_l1,
        rings_per_side=rings,
        l2_part_id=l2.part_id,
        l2_per_side=max(1, math.ceil(demand / l2_usable)),
        l2_usable_ports=l2_usable,
        l2_demand_per_side=demand,
    )


def l2_port_plan(plan: NetworkPlan, net: NetworkInputs, links: Sequence[L2Link]) -> PortPlan:
    """One side's L2 row: L3 uplinks (SM), then L1 links and equipment by speed and media."""
    downlinks: dict[tuple[PortSpeed, Media], int] = {}
    if plan.l1_links_per_side:
        downlinks[(PortSpeed.G1, Media.MM)] = plan.l1_links_per_side
    for link in links:
        if link.ports:
            key = (link.speed, link.media)
            downlinks[key] = downlinks.get(key, 0) + link.ports
    uplinks_l3 = net.l3_uplinks_per_l2 * plan.l2_per_side
    return PortPlan(
        uplinks_l3=(
            [PortAllocation(count=uplinks_l3, speed=PortSpeed.G1, media=Media.SM)]
            if uplinks_l3
            else []
        ),
        downlinks=[
            PortAllocation(count=count, speed=speed, media=media)
            for (speed, media), count in downlinks.items()
        ],
    )


def l1_port_plan(plan: NetworkPlan, net: NetworkInputs, *, sfp_per_l1: int) -> PortPlan | None:
    """One side's L1 row: its uplink, interlink or ring ports as 1G MM, plus the row's spares."""
    if plan.l1_per_side == 0:
        return None
    count = plan.l1_per_side * l1_reserved_ports(net)
    return PortPlan(
        uplinks=[PortAllocation(count=count, speed=PortSpeed.G1, media=Media.MM, spare=sfp_per_l1)]
    )
