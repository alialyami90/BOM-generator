# 0025. One AC branch MCB per AC-powered device

- Status: Proposed
- Date: 2026-10-31
- Spec sections: Derivation rules → AC distribution (group E); Data model and generation order (step 6)

## Context

The spec's group E feeds only the lamp, the fan and thermostat circuits and the socket. A device
with `supply_type: VAC` has `power_supplies: 0`, so it got no branch MCB at all, while the Parts page
lets a device be, or be overridden to, 230 VAC (ADR 0024). Ali decided on 2026-10-31 (card from A1):
one AC branch MCB per VAC unit, after the socket (plan Q52).

## Decision

1. **Order:** lamp, fan and thermostat circuits, thermostat-only circuits, socket, then one branch
   per VAC unit in group B order (one per unit of a multi-quantity row), then the spare(s). A
   redundant entry's two sides sit in two panels, so each panel gets its side's branch.
2. **Rating:** `branch_sizing` (ADR 0019) on the AC set `catalogues.mcb` (ADR 0023): running
   current at the part's voltage or the AC system voltage, the inrush against the set's AC magnetic
   multiple, the `min_branch_mcb_a` floor and `inrush_min_ms`. `branch_sizing` picks the set from
   the part's supply type.
3. **Spare rating:** stays the largest housekeeping branch, so a large VAC load does not enlarge
   the spare.
4. **CINC:** today's rule (6 A, or above the socket), raised to the smallest catalogue rating above
   the largest VAC branch and to at least the panel's AC design current (the sum of current factor
   × W ÷ V over its VAC units). Only panels with a VAC unit can change.
5. **Aux contacts:** a VAC unit whose part has `alarm_on_branch_mcb` adds its `C<n>` to the AC aux
   contact row, as DC branches do.
6. **Load text:** the unit's tag without the panel prefix, with underscores, as the DC branches name
   theirs. Each branch is a `BranchMcb` (feed none) in the check report and the Device preview's
   `ps1`.

Excluded parts (`excluded_from_power`) get no branch. X3-AC follows from the MCB count.

## Consequences

- No golden value moves: the example has no VAC device in any panel.
- Decision 4 is not covered by Ali's answer; it is recommended because CINC must carry the new
  loads, and stays Proposed until he confirms it.
- A VAC load above the largest AC catalogue rating is an engine error, as for DC.
