# 0013. Switches sized from the IED count; panels laid out automatically

- Status: Accepted (Ali, project thread, 2026-10-28)
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
- **Sizing** (R1–R4): per side, usable L1 ports = floor((ports − reserved) ×
  (1 − spare)), where reserved is the uplink plus the A–B interlink in a star
  (Q28) or two ring ports; L1 count = ceil(IEDs / usable). L2 demand = the
  equipment's L2 ports + one link per L1 switch in a star, or two per ring of
  at most `ring_max_switches` (Q27); L2 count from the same usable-port
  formula with the L3 uplinks reserved. Port plans and SFPs are generated from
  the sizing, so the spec's network-accessory rules are unchanged. The IED
  count appears only on the check report.
- **Layout** (R5–R9): devices fill panels in BOM group order; a panel holds
  `Σ height_u + (k − 1) × blank_plate_u ≤ panel_capacity_u` (32U), DIN-rail
  parts cost 0U, overflow opens a new panel. Redundant pairs fill an A stream
  (odd panels) and a B stream (even panels) in lock-step. Common devices go
  into those same panels, each into the panel with the most free U (Q26).
  Blank space produces no BOM row (Q25). `layout.overrides` move a device or
  a pair after the fill and `layout.removed` drops one before it; a move that
  does not fit is a check-report error. Generated panels are written as
  today's `panels/*.yaml` with a `generated` header; B panels in full, not as
  `mirror_of`.
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
