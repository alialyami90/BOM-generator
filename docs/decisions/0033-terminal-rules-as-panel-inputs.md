# 0033. Terminal rules as panel inputs

- Status: Accepted (Ali, 2026-11-03)
- Date: 2026-11-03
- Spec sections: Derivation rules → Terminal block quantities (group G); Inputs, 3. Project
  settings (spares)

## Context

"Terminal block quantities (group G)" gives each strip a fixed or derived quantity and one block
type. The engine computes them in `engine/terminals.py`; `PanelOptions.terminal_overrides` already
lets a YAML file set a strip's quantity, but the app shows neither the rule nor the override, there
is no spare allowance, and a strip can't use another block type (fused or test terminals). The
engineering workflow review (2026-11-03, F6) asks for a Terminals tab. Milestone M57 of the agent
plan builds it.

## Decision

1. **The table's quantities are defaults.** Each strip keeps the spec's rule as its automatic
   quantity, returned with a rule text ("2 × 6 AC MCBs = 12"). `terminal_overrides` (exists) sets a
   strip's quantity per panel and replaces the automatic one, spare included.
2. **Spare terminals.** `spares.terminals_fraction` (project default, substation override, like the
   other spares; default 0) adds a spare allowance to each automatic quantity, rounded up, before
   any override: 10% makes X3-AC 12 → 14 and X4-DC1 32 → 36 in Cabinet 001. It applies to the
   distribution, housekeeping and wiring strips (X-AC, X3-AC, X-DC1/2, X4-DC1/2, TBL, THF, XSD,
   XPS, X4-COD, X-ANN, XIP). Strips a library part brings through its `terminals` (XDIP*, XDIN,
   XRTAC-C*) are left as the part gives them, because they match the device's connections.
3. **Block type per strip.** `PanelOptions.terminal_block_overrides` maps a strip code to a block
   type in the chosen terminal-block catalogue (for fused or test terminals); the part number
   follows that type. Unset keeps the spec's type.
4. The spec gets one sentence under "Terminal block quantities (group G)": the quantities are panel
   defaults the engineer may override per strip, and a spare fraction applies before overrides.

## Consequences

- At fraction 0 with no override the golden values are unchanged.
- A spare fraction changes group G on every panel of the substation at once; the Terminals tab
  shows the rule with the spare added so the engineer sees why.
- Terminal-block catalogues need the extra block types listed before they can be picked.
