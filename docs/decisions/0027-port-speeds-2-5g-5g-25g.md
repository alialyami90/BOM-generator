# 0027. Port speeds 2.5G, 5G and 25G

- Status: Accepted (Ali, 2026-10-31)
- Date: 2026-10-31
- Spec sections: Inputs the tool needs (device library, ports)

## Context

A library part's port groups give each group's speed, for SFP sizing (spec: Inputs the tool
needs, the `ports` row). The model took 10M, 100M, 1G and 10G. The contractor's 2026-10-31
delivery has four FortiGate firewalls with 2.5G, 5G or 25G ports: FG-401G, FG-701G, FG-600F
and FG-601F. They cannot be imported while their ports cannot be written down.

The SFP sizing (spec: Derivation rules: what follows from the devices, the SFP bullet) only
ever allocates 1G and 100M links: 1G SM uplinks to L3, 1G MM downlinks and L1 uplinks, and
100BASE-FX for 100 Mb devices. No rule allocates a 2.5G, 5G or 25G link.

## Decision

1. `PortSpeed` gains `2.5G`, `5G` and `25G` (members `G2_5`, `G5`, `G25`), so a port group
   can describe those ports.
2. The new speeds are descriptive only. An equipment entry's `l2_speed` and an `sfp` choice's
   `speed` (ADR 0024) refuse them with "… ports are not sized for SFPs (ADR 0027)", so they
   never become an SFP pick. The speeds sizing can use stay 10M, 100M, 1G and 10G
   (`SFP_SPEEDS`).
3. The JSON schemas, the library editor's speed list and the device-database format follow
   the enum.

## Consequences

- FG-401G and FG-701G can then come in by a data PR. FG-600F and FG-601F also wait on a
  voltage and load type from the contractor.
- Nothing changes for existing libraries and projects, and the goldens don't move.
- A design that needs 25G uplinks sized for SFPs needs a new sizing rule and a new ADR first.
