# 0013. Switches sized from the IED count; panels laid out automatically

- Status: Accepted (Ali, 2026-10-28)
- Date: 2026-10-28
- Spec sections: How each panel BOM groups its materials; Tag naming
  conventions; Derivation rules → Network accessories; Inputs the tool needs →
  2. Panel definition; Data model and generation order

## Context

Today every panel is written by hand: which switches it has and which ports
they use. Ali wants the tool to size the switches and fill the panels itself.
Field IEDs connect to L1 switches; everything else in the substation connects
to L2 switches, which also carry the L1 switches in a star (or a ring). IEDs
must never appear in the BOM. Panels are 42U with only 32U usable, one blank
space between neighbours, A unit in panel 1 and B unit in panel 2 for every
redundant pair, and the engineer can move or delete devices afterwards. Rules
R1–R10 are in the design document named in ADR 0012.

## Decision

- **Inputs per substation**: `equipment` (part, role, redundant, side, L2
  ports needed), `network` (`ied_count`, `topology` star | ring,
  `ring_max_switches`, `l1_uplinks_per_switch`, `l1_interlink`,
  `l3_uplinks_per_l2`), `spares` (`port_fraction` 0.20, `sfp_per_l1`, DC and
  AC branch spares, `rack_u_reserved` 10) and `layout` (`panel_capacity_u`,
  `blank_plate_u`, `overrides`, `removed`). Every spare is an input with
  today's values as defaults. The library adds `height_u` per device, a port
  role per port group and `enclosure_u` on the catalogue.
- **Sizing** (R1–R4): every IED has an A port and a B port, so `ied_count`
  ports are needed on each side. Per side, usable L1 ports = floor((ports −
  reserved) × (1 − spare)), where reserved is the uplink plus the A–B interlink
  in a star (Q28) or two ring ports, and spare is `spares.port_fraction`
  (default 20 %, confirmed 2026-10-28); L1 count = ceil(IEDs / usable). The
  L1 switch model comes from the library: the engine ranks every L1-capable
  switch (fewest switches per side, then fewest ports, then part id) and picks
  the first unless the `l1_switch` equipment entry pins a `part_id`; the UI
  shows the ranking so the engineer can pin another (Ali, 2026-10-28). L2 demand = the
  equipment's L2 ports + one link per L1 switch in a star, or two per ring of
  at most `ring_max_switches` (Q27); L2 count from the same usable-port
  formula with the L3 uplinks reserved. Port plans and SFPs are generated from
  the sizing, so the spec's network-accessory rules are unchanged. The IED
  count appears only on the check report.
- **Layout** (R5–R9): devices fill panels in BOM group order; a panel holds
  `Σ height_u + (k − 1) × blank_plate_u ≤ panel_capacity_u` (32U), DIN-rail
  parts cost 0U, overflow opens a new panel. Every rack-mounted switch,
  firewall or patch panel unit carries a 1U cable manager directly under it as
  one block with no blank plate inside, and the block counts against the 32U
  (Q32, Ali 2026-10-28); the cable-manager BOM count therefore comes from the
  layout when a generated panel exists. Redundant pairs fill an A stream
  (odd panels) and a B stream (even panels) in lock-step. Common devices go
  into those same panels, each into the panel with the most free U (Q26).
  Blank space produces no BOM row (Q25). `layout.overrides` move a device or
  a pair after the fill and `layout.removed` drops one before it; a move that
  does not fit is a check-report error. Generated panels are written as
  today's `panels/*.yaml` with a `generated` header; B panels in full, not as
  `mirror_of`.

  *Amended (Ali, 2026-10-28, backlog point 8):* a cable manager is a passive
  plate, so it may touch the device below it. The blank plate goes only between
  two rack neighbours whose upper block ends in an active device; a block that
  ends in its cable manager needs none. A panel holds `Σ block_u + p ×
  blank_plate_u ≤ panel_capacity_u`, where `p` counts the rack blocks, except
  the lowest, that carry no cable manager. The example's generated panels drop
  from 29U and 25U to 23U and 19U; the BOM is unchanged (Q25).

  *Amended (2026-10-28, M17, the Panels board's pins):* every override pins the
  units it names, also when it names the panel the fill chose, so "Pin here"
  holds when later changes would place the unit elsewhere; `layout_preview`
  reports whether each unit is pinned (`PanelFill.is_pinned`) and its place
  (`PanelFill.position`). `DeviceMove` and `PairMove` take an optional
  `position`, the unit's place among the panel's rack devices (1 = top, past the
  bottom = last; DIN-rail parts do not count); without it the unit takes its
  group-order place. The blank-plate rule applies to the pinned order. Overrides
  still apply after the fill, in order, and a later override of a unit replaces
  an earlier one.

  *Amended (Ali, 2026-10-31, part-picking design §5, M21):* panel choice is
  unchanged (equipment order). Inside a panel the rack units stack top to bottom
  by priority: 1 time server (`gps_clock`); 2 network (`network_switch`,
  `patch_panel`, `firewall`, `gateway`); 3 servers and workstations
  (`workstation`); 4 the rest; ties keep equipment order. A KVM or console
  (`kvm`, `console`) is placed with its bottom edge at `waist_u = round((waist_height_mm
  − rack_start_mm) / 44.45)`, U counted from 1 at the bottom of the rack space, from the
  project's `defaults.layout` (ASSUMED 1000 and 200 mm, U18); a second one sits
  directly above it with the normal clearance. The other units fill from the top
  down to it, and those that do not fit above go below it in stack order. A panel
  fits only when every unit gets a place, so the space the anchor leaves counts.
  Each rack unit gets a top U (`PanelFill.place`, `top_u`); blank space still has
  no BOM row (Q25). A pinned `position` wins over the priority and the anchor. A
  panel too short for the anchor is a layout error naming the panel, and its units
  stack from the top. The BOM row order (group B) stays equipment order.

  *Amended (Ali, 2026-10-31, M22 review):* a network device can have or not have its
  cable manager. `cable_manager` on an equipment entry (and on a panel row) is true,
  false or unset; unset keeps the rule above (a rack switch, firewall or patch panel
  has one, a gateway does not), true or false overrides it for a switch, patch panel,
  firewall or gateway and is refused on any other part. The layout gives the unit its
  1U manager only when it has one (without it the R5 plate rule applies as for any
  device) and writes the answer on every generated row of those four categories, and
  the BOM counts the managers from those rows, as Q32 says. This fixes a rack firewall
  in a generated panel, which took the manager's U but got no BOM row. Hand-written
  panels keep the M2 count (switches and patch panels) unless a row sets the flag.

  *Amended (2026-10-31, M24, the Device preview's drag):* `DeviceMove` and `PairMove`
  also take `top_u`, the rack U the top of the unit's block (manager included) sits
  on, counted from 1 at the bottom (the same U in both panels of a pair). It is
  exclusive with `position` ("give position or top_u, not both"). A `top_u` unit is
  placed first and wins over the priority and the waist anchor; the anchor comes next;
  the other units, `position` pins included, fill from the top in stack order and go
  below a fixed block they would overlap or touch without their clearance. A `top_u`
  block that leaves the rack (`pin-outside-rack`) or overlaps another fixed block or
  the anchor (`pin-overlaps`) is a layout error naming the panel; the units still get
  their U.
- **Pipeline**: a step 0 (`engine/sizing.py`, `engine/layout.py`,
  `bomgen layout`) runs before the existing steps 1–15; `bomgen build
  --no-layout` keeps hand-written panels working.

## Consequences

- The spec example keeps its hand-written panels and golden values; the
  layout engine gets its own golden from the example substation (R10), which
  Ali confirms in review.
- Business rules stay in the engine; the UI's Panels board only writes
  overrides and re-runs the layout.
- The ring rule (two ports per ring, six switches per ring by default) was
  accepted by default and can be revisited without changing the inputs.
- Hand-written panels keep the M2 rule "one cable manager per switch or patch
  panel"; generated panels report the count from the layout. Both give nine
  for the spec example.
