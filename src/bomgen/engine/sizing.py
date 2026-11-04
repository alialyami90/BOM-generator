"""Network sizing: L1 and L2 switch counts and their port plans (ADR 0013, rules R1-R4).

Pure functions on small value types; ``engine.layout`` maps the substation onto them.
Every count here is per side: each IED has an A port and a B port, so ``ied_count``
IEDs need ``ied_count`` ports on each side. An IED schedule (ADR 0034) gives the ports
per side by speed and media instead, and the L1 switches are sized against their port
groups: fixed ports serve their own speed and media, SFP slots any media of their speed.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction

from bomgen.engine.errors import EngineError
from bomgen.models.library import DeviceType, Media, PortKind, PortSpeed, PortUse
from bomgen.models.panel import PortAllocation, PortPlan
from bomgen.models.substation import ExternalLink, IedRow, Topology

__all__ = [
    "L1Candidate",
    "L2Link",
    "NetworkInputs",
    "NetworkPlan",
    "PortBudget",
    "SizingError",
    "SwitchPorts",
    "Topology",
    "external_l2_links",
    "external_sides",
    "ied_l2_links",
    "ied_ports_per_side",
    "l1_links",
    "l1_port_plan",
    "l1_reserved_ports",
    "l1_slot_downlinks",
    "l2_count",
    "l2_port_plan",
    "pick_l1_switch",
    "port_budgets",
    "rank_l1_switches",
    "size_network",
    "switch_ports",
    "usable_ports",
]


class SizingError(EngineError):
    """The network inputs cannot be met by the chosen switches."""


Need = tuple[PortSpeed, Media]
SideKey = str  # "a" or "b"


@dataclass(frozen=True)
class PortPool:
    """A switch's ports of one speed: fixed ports of one media, or SFP slots (media None)."""

    speed: PortSpeed
    media: Media | None
    use: PortUse
    count: int


@dataclass(frozen=True)
class SwitchPorts:
    """A switch's port count by what each port may connect (library ``usable_for``)."""

    part_id: str
    ied: int
    uplink: int
    any: int
    pools: tuple[PortPool, ...] = ()

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
    # IED ports per side by speed and media, from the schedule; None: the quick count
    ied_ports_per_side: Mapping[SideKey, Mapping[Need, int]] | None = None
    # the engineer's switch counts per side (plan M72); None: the sizing's
    l1_per_side: int | None = None
    l2_per_side: int | None = None


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
    l1_by_side: tuple[int, int] = field(default=(0, 0))  # L1 switches sides A and B need
    l1_needed: int = 0  # the sizing's counts per side, before the engineer's (plan M72)
    l2_needed: int = 0


@dataclass(frozen=True)
class PortBudget:
    """One side's ports on one switch level (plan M72): every port of its switches, the
    reserved uplink, interlink or ring ports, the spare kept free, and the ports in use."""

    switches: int = 0
    ports: int = 0
    reserved: int = 0
    spare: int = 0
    used: int = 0

    @property
    def free(self) -> int:
        return self.ports - self.reserved - self.spare - self.used


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
    pools = tuple(
        PortPool(g.speed, None if g.kind is PortKind.SFP_SLOT else g.media, g.usable_for, g.count)
        for g in device.ports
    )
    return SwitchPorts(
        device.part_id, counts[PortUse.IED], counts[PortUse.UPLINK], counts[PortUse.ANY], pools
    )


def ied_ports_per_side(rows: Iterable[IedRow]) -> dict[SideKey, dict[Need, int]]:
    """Ports each side's L1 switches take for the schedule rows landing on L1."""
    sides: dict[SideKey, dict[Need, int]] = {"a": {}, "b": {}}
    for row in rows:
        if row.lands_on != "l1":
            continue
        for side in _sides(row):
            for need in row.ports:
                key = (need.speed, need.media)
                sides[side][key] = sides[side].get(key, 0) + row.qty * need.count
    return sides


def ied_l2_links(rows: Iterable[IedRow], side: SideKey) -> list["L2Link"]:
    """The schedule rows landing on L2 directly, as one side's L2 links."""
    return [
        L2Link(f"{row.bay} {row.name}", row.qty * need.count, need.speed, need.media)
        for row in rows
        if row.lands_on == "l2" and side in _sides(row)
        for need in row.ports
    ]


def external_sides(link: ExternalLink) -> tuple[SideKey, ...]:
    """The sides an external link is on: both when redundant, else side A."""
    return ("a", "b") if link.redundant else ("a",)


def external_l2_links(links: Iterable[ExternalLink], side: SideKey) -> list["L2Link"]:
    """The external links landing on one side's L2 switches (plan M61)."""
    return [
        L2Link(link.name, link.count, link.speed, link.media)
        for link in links
        if link.lands_on == "l2" and side in external_sides(link)
    ]


def _sides(row: IedRow) -> tuple[SideKey, ...]:
    return {"dual": ("a", "b"), "single_a": ("a",), "single_b": ("b",)}[row.attachment]


def _need_text(need: Need) -> str:
    return f"{need[0].value} {need[1].value}"


def _ied_pools(
    ports: SwitchPorts, net: NetworkInputs
) -> dict[tuple[PortSpeed, Media | None], tuple[int, int]]:
    """Per switch, the IED ports by speed and media (None: SFP slots) as (all, usable):
    the reserved ports come off the uplink ports first, then the shared ports in order."""
    left = max(0, l1_reserved_ports(net) - ports.uplink)
    raw: dict[tuple[PortSpeed, Media | None], int] = {}
    for pool in ports.pools:
        if pool.use is PortUse.UPLINK:
            continue
        count = pool.count
        if pool.use is PortUse.ANY:
            taken = min(left, count)
            left -= taken
            count -= taken
        if count:
            key = (pool.speed, pool.media)
            raw[key] = raw.get(key, 0) + count
    keep = 1 - Fraction(str(net.port_fraction))
    return {key: (n, math.floor(n * keep)) for key, n in raw.items()}


def _overflow(
    pools: Mapping[tuple[PortSpeed, Media | None], tuple[int, int]],
    n: int,
    demand: Mapping[Need, int],
    *,
    usable: bool,
) -> dict[Need, int]:
    """The demand ``n`` switches' fixed ports leave for their SFP slots."""
    pick = 1 if usable else 0
    return {
        need: over
        for need, count in demand.items()
        if (over := count - n * pools.get(need, (0, 0))[pick]) > 0
    }


def _fits(
    pools: Mapping[tuple[PortSpeed, Media | None], tuple[int, int]],
    n: int,
    demand: Mapping[Need, int],
) -> bool:
    slots: dict[PortSpeed, int] = {}
    for (speed, _), over in _overflow(pools, n, demand, usable=True).items():
        slots[speed] = slots.get(speed, 0) + over
    return all(over <= n * pools.get((speed, None), (0, 0))[1] for speed, over in slots.items())


def _unserved(
    pools: Mapping[tuple[PortSpeed, Media | None], tuple[int, int]], demand: Mapping[Need, int]
) -> list[Need]:
    return [
        need
        for need, count in demand.items()
        if count and not (pools.get(need, (0, 0))[1] or pools.get((need[0], None), (0, 0))[1])
    ]


def _scheduled_count(ports: SwitchPorts, net: NetworkInputs, demand: Mapping[Need, int]) -> int:
    """The fewest switches whose usable ports take one side's scheduled demand."""
    demand = {need: count for need, count in demand.items() if count}
    if not demand:
        return 0
    pools = _ied_pools(ports, net)
    unserved = _unserved(pools, demand)
    if unserved:
        names = ", ".join(_need_text(need) for need in unserved)
        raise SizingError(f"L1 switch {ports.part_id} has no usable port for {names} IEDs")
    n = math.ceil(sum(demand.values()) / sum(u for _, u in pools.values()))
    while not _fits(pools, n, demand):
        n += 1
    return n


def _l1_by_side(ports: SwitchPorts, net: NetworkInputs) -> tuple[int, int]:
    """L1 switches each side needs (A, B)."""
    if net.ied_ports_per_side is None:
        usable = _l1_usable(ports, net)
        n = math.ceil(net.ied_count / usable) if net.ied_count else 0
        return (n, n)
    sides = net.ied_ports_per_side
    a, b = (_scheduled_count(ports, net, sides.get(side, {})) for side in ("a", "b"))
    return (a, b)


def l1_slot_downlinks(ports: SwitchPorts, n: int, demand: Mapping[Need, int]) -> dict[Need, int]:
    """One side's scheduled IED ports that land on the ``n`` L1 switches' SFP slots: the
    demand their fixed ports of the same speed and media do not take (ADR 0034, item 3)."""
    pools = _ied_pools(ports, NetworkInputs(ied_count=0))
    return _overflow(pools, n, demand, usable=False)


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
    if net.ied_ports_per_side is not None:
        return sum(u for _, u in _ied_pools(ports, net).values())
    return usable_ports(ports, reserved=l1_reserved_ports(net), port_fraction=net.port_fraction)


def rank_l1_switches(candidates: Iterable[SwitchPorts], net: NetworkInputs) -> list[L1Candidate]:
    """Every candidate with a usable port, best first: fewest per side, fewest ports, part id."""
    ranked = []
    for ports in candidates:
        usable = _l1_usable(ports, net)
        if usable <= 0:
            continue
        if net.ied_ports_per_side is None:
            ranked.append(L1Candidate(ports, math.ceil(net.ied_count / usable), usable))
            continue
        try:
            ranked.append(L1Candidate(ports, max(_l1_by_side(ports, net)), usable))
        except SizingError:  # its ports don't serve the schedule's mix
            continue
    return sorted(ranked, key=lambda c: (c.per_side, c.ports.total, c.ports.part_id))


def pick_l1_switch(candidates: Iterable[SwitchPorts], net: NetworkInputs) -> SwitchPorts:
    candidates = list(candidates)
    ranked = rank_l1_switches(candidates, net)
    if not ranked and net.ied_ports_per_side is not None:
        demand = {n: c for side in net.ied_ports_per_side.values() for n, c in side.items() if c}
        served = {
            need
            for ports in candidates
            for need in demand
            if need not in _unserved(_ied_pools(ports, net), {need: 1})
        }
        missing = ", ".join(_need_text(n) for n in demand if n not in served)
        if missing:
            raise SizingError(f"no L1 switch in the library has a usable port for {missing} IEDs")
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
    by_side = _l1_by_side(l1, net)
    n_l1 = _counted("L1", max(by_side), net.l1_per_side, _l1_need_text(l1, net))
    links_l1 = l1_links(n_l1, net)
    rings = math.ceil(n_l1 / net.ring_max_switches) if net.topology is Topology.RING else 0
    l2_usable = usable_ports(l2, reserved=net.l3_uplinks_per_l2, port_fraction=net.port_fraction)
    if l2_usable <= 0:
        raise SizingError(
            f"L2 switch {l2.part_id} has no port left after {net.l3_uplinks_per_l2} L3 "
            f"uplinks and {net.port_fraction:.0%} spare"
        )
    demand = links_l1 + sum(link.ports for link in links)
    l2_per_side, l2_needed = l2_count(net, demand, l2_usable)
    return NetworkPlan(
        ied_count=net.ied_count,
        l1_part_id=l1.part_id,
        l1_per_side=n_l1,
        l1_usable_ports=l1_usable,
        l1_links_per_side=links_l1,
        rings_per_side=rings,
        l2_part_id=l2.part_id,
        l2_per_side=l2_per_side,
        l2_usable_ports=l2_usable,
        l2_demand_per_side=demand,
        l1_by_side=by_side,
        l1_needed=max(by_side),
        l2_needed=l2_needed,
    )


def l2_count(net: NetworkInputs, demand: int, usable: int) -> tuple[int, int]:
    """L2 switches per side for ``demand`` ports, and the count the sizing needs (R2): the
    engineer's count when set, which may add switches but never take one away (plan M72)."""
    needed = max(1, math.ceil(demand / usable))
    text = f"{demand} L2 ports per side, {usable} usable on each switch"
    return _counted("L2", needed, net.l2_per_side, text), needed


def _counted(level: str, needed: int, override: int | None, text: str) -> int:
    if override is None:
        return needed
    if override < needed:
        raise SizingError(
            f"{level} switches per side is set to {override}, fewer than the {needed} "
            f"the sizing needs: {text}"
        )
    return override


def _l1_demand(net: NetworkInputs) -> int:
    """IED ports on the busier side's L1 switches."""
    if net.ied_ports_per_side is None:
        return net.ied_count
    return max((sum(side.values()) for side in net.ied_ports_per_side.values()), default=0)


def _l1_need_text(ports: SwitchPorts, net: NetworkInputs) -> str:
    return f"{_l1_demand(net)} IED ports per side, {_l1_usable(ports, net)} usable on each switch"


def _device_ports(ports: SwitchPorts, reserved: int) -> int:
    """A switch's ports a device may take once the reserved ports are off (R1)."""
    return max(0, ports.ied + ports.any - max(0, reserved - ports.uplink))


def port_budgets(
    plan: NetworkPlan, net: NetworkInputs, l1: SwitchPorts, l2: SwitchPorts
) -> tuple[PortBudget, PortBudget]:
    """The busier side's L1 and L2 port budgets for the plan's switch counts (plan M72)."""
    if net.ied_ports_per_side is None:
        l1_devices = _device_ports(l1, l1_reserved_ports(net))
    else:
        l1_devices = sum(n for n, _ in _ied_pools(l1, net).values())
    n1, n2 = plan.l1_per_side, plan.l2_per_side
    l2_devices = _device_ports(l2, net.l3_uplinks_per_l2)
    return (
        PortBudget(
            switches=n1,
            ports=n1 * l1.total,
            reserved=n1 * l1_reserved_ports(net),
            spare=n1 * (l1_devices - plan.l1_usable_ports),
            used=_l1_demand(net),
        ),
        PortBudget(
            switches=n2,
            ports=n2 * l2.total,
            reserved=n2 * net.l3_uplinks_per_l2,
            spare=n2 * (l2_devices - plan.l2_usable_ports),
            used=plan.l2_demand_per_side,
        ),
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
