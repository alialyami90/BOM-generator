# 0014. Engine output model and the group A–D derivation choices

- Status: Proposed
- Date: 2026-10-28
- Spec sections: Columns of a panel BOM; Tag naming conventions; Derivation rules →
  Network accessories (group C), Housekeeping kit (group D); Data model and
  generation order

## Context

ADR 0005 splits the pipeline into engine, sheet models and writer. The sheet layer
(A10, M5) needs every BOM line in final order, with enough structure to emit SR.NO
formulas, separator rows, merges and the Power Consumption references. Several
group A–D rules in the spec say what the example shows but not how to decide it in
general (which SFP part serves a port, how many cable managers, where loose items of
a device go).

## Decision

**Output model** (`models/bom.py`). `BuildResult` holds one `PanelBom` per panel in
panel order and an optional `LooseTable`. Each table has two title lines and a flat
tuple of `BomLine`s (group, tag, description, qty, make, model, ordering code, HWIO,
part id, `parent`, `merge_fg`, `revised`). A child line's `parent` is the index of its
parent line in the same table; later references (Power Consumption rows, M4) are
indices too. Quantities are `int`, `"1 Lot"` or `QtySum(parts=(24, 3))`, which the
sheet layer renders as `=24+3`. SR.NO numbers and separator rows are not stored: the
separator positions follow from the groups (`BomTable.separators_before()`), SR.NO
from the line order.

**Derivation choices** (the spec states the example values; these are the rules
that reproduce them):

1. An SFP serves a port-plan allocation when one of its port groups has the same
   speed and media. Among matches, the host's make wins, then library order. RJ45
   allocations need no SFP. One host's allocations served by the same part form one
   row (`QtySum` of the counts and spares).
2. Cable managers = units of `network_switch` and `patch_panel` in the panel
   (001: FOPP + L2 + 6 L1 + EXT = 9); none when that is 0.
3. Serial cables = the RTAC port plans' `serial_ports` (6).
4. Housekeeping: lamp, door switch when catalogued, 2 fans + 3 thermostats (forced)
   or 2 vent filters + 1 thermostat (natural), IPR kit, COD-1/COD-2, socket, in that
   order. Ventilation `auto` is treated as forced until M4 resolves it from the heat
   check. Change-over diodes `auto` = any single-fed (`power_supplies: 1`) load in
   the panel or a loose item `fed_from` it.
5. The loose-material table lists the project's items in order, then each device's
   `loose_items` as one block whose first item is the parent (plan Q30).
6. Tags are trimmed (the workbook's `PSA1-IPR ` has a trailing space) and the
   enclosure row is always `PANEL` (`Aux` writes `Panel`).

## Consequences

The sheet layer reads one flat list per sheet and needs no knowledge of the rules.
Inserting lines in M3 (groups E–H) only appends to the same list. If Ali wants the
loose table in the workbook's order (GPS accessories between software and cables),
the project file needs a position marker for device loose items (A2's schema).
