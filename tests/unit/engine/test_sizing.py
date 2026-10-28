"""Network sizing: rules R1-R4 of the substations and auto-layout design (ADR 0013)."""

import pytest

from bomgen.engine.sizing import (
    L2Link,
    NetworkInputs,
    SizingError,
    SwitchPorts,
    Topology,
    l1_links,
    l1_port_plan,
    l1_reserved_ports,
    l2_port_plan,
    pick_l1_switch,
    rank_l1_switches,
    size_network,
    usable_ports,
)
from bomgen.models.library import Media, PortSpeed
from bomgen.models.panel import PortAllocation

# 24 fixed IED ports and 4 SFP slots that may take anything (the design's reading).
L1_ANY = SwitchPorts("L1-ANY", ied=24, uplink=0, any=4)
# The example library's RST2228-L1-24MM: the SFP slots are uplink-only.
L1_RST = SwitchPorts("RST2228-L1-24MM", ied=24, uplink=4, any=0)
# The example library's RST2228-L2: 20 SFP slots for anything, 4 SFP+ uplinks.
L2_RST = SwitchPorts("RST2228-L2", ied=0, uplink=4, any=20)
L2_28 = SwitchPorts("L2-28", ied=0, uplink=0, any=28)


def link(owner: str, ports: int, speed: str = "1G") -> L2Link:
    return L2Link(owner, ports, PortSpeed(speed), Media.MM)


def test_r1_star_reserves_uplink_and_interlink() -> None:
    assert l1_reserved_ports(NetworkInputs(ied_count=40)) == 2


def test_r1_star_without_interlink_reserves_one() -> None:
    assert l1_reserved_ports(NetworkInputs(ied_count=40, l1_interlink=False)) == 1


def test_r1_ring_reserves_two_ring_ports() -> None:
    net = NetworkInputs(ied_count=40, topology=Topology.RING, l1_interlink=False)
    assert l1_reserved_ports(net) == 2


def test_r1_usable_ports_keep_twenty_percent_spare() -> None:
    assert usable_ports(L1_ANY, reserved=2, port_fraction=0.20) == 20  # 26 x 0.8 = 20.8
    assert usable_ports(L1_ANY, reserved=2, port_fraction=0.10) == 23  # 26 x 0.9 = 23.4
    assert usable_ports(L1_RST, reserved=2, port_fraction=0.20) == 19  # 24 x 0.8 = 19.2


def test_r1_spare_fraction_is_exact() -> None:
    # 30 x 0.9 is 26.999… in floats; the rule must give 27.
    ports = SwitchPorts("S30", ied=30, uplink=0, any=0)
    assert usable_ports(ports, reserved=0, port_fraction=0.10) == 27


def test_r1_reserved_ports_come_from_uplink_ports_first() -> None:
    mixed = SwitchPorts("MIX", ied=10, uplink=1, any=4)
    assert usable_ports(mixed, reserved=2, port_fraction=0) == 13  # 1 uplink + 1 any


def test_r1_forty_ieds_need_two_l1_switches_per_side() -> None:
    plan = size_network(NetworkInputs(ied_count=40), L1_ANY, L2_28, [])
    assert plan.l1_per_side == 2
    assert plan.l1_usable_ports == 20


def test_r1_uplink_only_slots_carry_no_ieds() -> None:
    plan = size_network(NetworkInputs(ied_count=40), L1_RST, L2_RST, [])
    assert plan.l1_usable_ports == 19
    assert plan.l1_per_side == 3


@pytest.mark.parametrize(("ieds", "switches"), [(20, 1), (21, 2), (120, 6)])
def test_r1_boundary_counts(ieds: int, switches: int) -> None:
    assert size_network(NetworkInputs(ied_count=ieds), L1_ANY, L2_28, []).l1_per_side == switches


def test_r1_zero_ieds_needs_no_l1_switch() -> None:
    plan = size_network(NetworkInputs(ied_count=0), L1_ANY, L2_28, [])
    assert (plan.l1_per_side, plan.l1_links_per_side, plan.l2_per_side) == (0, 0, 1)


def test_r1_no_usable_port_is_an_error() -> None:
    with pytest.raises(SizingError, match="L1-ANY"):
        size_network(NetworkInputs(ied_count=4, port_fraction=0.99), L1_ANY, L2_28, [])
    tiny = SwitchPorts("TINY", ied=0, uplink=0, any=2)
    with pytest.raises(SizingError, match="TINY"):
        size_network(NetworkInputs(ied_count=4), tiny, L2_28, [])


def test_r1_tool_picks_l1_switch_with_fewest_switches() -> None:
    s16 = SwitchPorts("S16", ied=14, uplink=0, any=2)  # 14 x 0.8 → 11 → 4 switches
    s28 = SwitchPorts("S28", ied=24, uplink=0, any=4)  # 26 x 0.8 → 20 → 2
    s48 = SwitchPorts("S48", ied=44, uplink=0, any=4)  # 46 x 0.8 → 36 → 2
    net = NetworkInputs(ied_count=40)
    assert pick_l1_switch([s16, s48, s28], net) == s28  # tie on 2: fewer ports


def test_r1_ranking_lists_every_candidate_with_its_count() -> None:
    s16 = SwitchPorts("S16", ied=14, uplink=0, any=2)
    s28 = SwitchPorts("S28", ied=24, uplink=0, any=4)
    s48 = SwitchPorts("S48", ied=44, uplink=0, any=4)
    ranked = rank_l1_switches([s16, s48, s28], NetworkInputs(ied_count=40))
    assert [(c.ports.part_id, c.per_side, c.usable_ports) for c in ranked] == [
        ("S28", 2, 20),
        ("S48", 2, 36),
        ("S16", 4, 11),
    ]


def test_r1_pick_tie_breaks_on_part_id() -> None:
    b = SwitchPorts("B", ied=24, uplink=0, any=4)
    a = SwitchPorts("A", ied=24, uplink=0, any=4)
    assert pick_l1_switch([b, a], NetworkInputs(ied_count=40)).part_id == "A"


def test_r1_pick_without_a_usable_candidate_is_an_error() -> None:
    tiny = SwitchPorts("TINY", ied=0, uplink=0, any=2)
    with pytest.raises(SizingError, match="no L1 switch"):
        pick_l1_switch([tiny], NetworkInputs(ied_count=40))
    with pytest.raises(SizingError, match="no L1 switch"):
        pick_l1_switch([], NetworkInputs(ied_count=40))


def test_r2_star_links_one_port_per_l1_switch() -> None:
    assert l1_links(6, NetworkInputs(ied_count=0)) == 6
    assert l1_links(6, NetworkInputs(ied_count=0, l1_uplinks_per_switch=2)) == 12


@pytest.mark.parametrize(("switches", "ports"), [(0, 0), (6, 2), (7, 4), (13, 6)])
def test_r2_ring_takes_two_ports_per_ring(switches: int, ports: int) -> None:
    assert l1_links(switches, NetworkInputs(ied_count=0, topology=Topology.RING)) == ports


def test_r2_l2_usable_ports_reserve_l3_uplinks() -> None:
    plan = size_network(NetworkInputs(ied_count=0), L1_ANY, L2_28, [])
    assert plan.l2_usable_ports == 20  # (28 - 2) x 0.8
    plan = size_network(NetworkInputs(ied_count=0), L1_ANY, L2_RST, [])
    assert plan.l2_usable_ports == 16  # L3 uplinks on the SFP+ slots; 20 x 0.8


def test_r2_spec_example_needs_one_l2_per_side() -> None:
    plan = size_network(NetworkInputs(ied_count=120), L1_ANY, L2_28, [link("gps", 1, "100M")])
    assert (plan.l1_per_side, plan.l2_demand_per_side, plan.l2_per_side) == (6, 7, 1)


def test_r2_demand_over_capacity_adds_l2_switches() -> None:
    links = [link("a", 10), link("b", 10), link("c", 10)]
    plan = size_network(NetworkInputs(ied_count=0), L1_ANY, L2_28, links)
    assert (plan.l2_demand_per_side, plan.l2_per_side) == (30, 2)


def test_r2_ring_rings_per_side() -> None:
    net = NetworkInputs(ied_count=140, topology=Topology.RING)  # 20 usable → 7 switches
    plan = size_network(net, L1_ANY, L2_28, [])
    assert (plan.l1_per_side, plan.rings_per_side, plan.l1_links_per_side) == (7, 2, 4)


def test_r3_l2_plan_has_l3_uplinks_as_single_mode() -> None:
    net = NetworkInputs(ied_count=0)
    plan = size_network(net, L1_ANY, L2_28, [])
    assert l2_port_plan(plan, net, []).uplinks_l3 == [
        PortAllocation(count=2, speed=PortSpeed.G1, media=Media.SM)
    ]
    links = [link("a", 10), link("b", 10), link("c", 10)]
    two = size_network(net, L1_ANY, L2_28, links)
    assert l2_port_plan(two, net, links).uplinks_l3[0].count == 4


def test_r3_l2_downlinks_group_l1_links_and_equipment_by_speed_and_media() -> None:
    net = NetworkInputs(ied_count=40)
    links = [link("ext-fw", 1), link("gps", 1, "100M"), link("rtac", 2)]
    plan = size_network(net, L1_ANY, L2_28, links)
    assert l2_port_plan(plan, net, links).downlinks == [
        PortAllocation(count=5, speed=PortSpeed.G1, media=Media.MM),
        PortAllocation(count=1, speed=PortSpeed.M100, media=Media.MM),
    ]


def test_r3_l1_plan_is_used_ports_plus_spare_per_row() -> None:
    star = NetworkInputs(ied_count=40)
    plan = l1_port_plan(size_network(star, L1_ANY, L2_28, []), star, sfp_per_l1=3)
    assert plan is not None
    assert plan.uplinks == [PortAllocation(count=4, speed=PortSpeed.G1, media=Media.MM, spare=3)]
    ring = NetworkInputs(ied_count=40, topology=Topology.RING)
    plan = l1_port_plan(size_network(ring, L1_ANY, L2_28, []), ring, sfp_per_l1=0)
    assert plan is not None
    assert plan.uplinks == [PortAllocation(count=4, speed=PortSpeed.G1, media=Media.MM)]


def test_r3_no_l1_switch_has_no_l1_plan() -> None:
    net = NetworkInputs(ied_count=0)
    assert l1_port_plan(size_network(net, L1_ANY, L2_28, []), net, sfp_per_l1=3) is None


def test_r4_ied_count_never_reaches_a_port_plan() -> None:
    net = NetworkInputs(ied_count=37)
    links = [link("gps", 1, "100M")]
    plan = size_network(net, L1_ANY, L2_28, links)
    l1 = l1_port_plan(plan, net, sfp_per_l1=3)
    assert l1 is not None
    for port_plan in (l2_port_plan(plan, net, links), l1):
        text = port_plan.model_dump_json().lower()
        assert "37" not in text
        assert "ied" not in text
