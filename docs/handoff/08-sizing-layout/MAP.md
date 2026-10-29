# MAP: role 8's code, callers and tests

A guide to the files, for a successor who has never opened them. The rules themselves
(R1-R10) are in [ADR 0013](../../decisions/0013-network-sizing-and-panel-layout.md) and
[the approved design, section 4](../../superpowers/specs/2026-10-28-substations-and-auto-layout-design.md).
Read those first; this file only says where each rule lives.

## `src/bomgen/engine/sizing.py` (R1-R4, pure, no I/O)

| Name | What it does |
| --- | --- |
| `SwitchPorts`, `switch_ports(device)` | A library switch's ports by what they may connect (`usable_for`) |
| `NetworkInputs` | `ied_count`, topology, ring size, uplinks, spare fraction: what sizing needs |
| `l1_reserved_ports`, `usable_ports`, `l1_links` | R1 port arithmetic (uplinks/ring ports reserved, spare taken off) |
| `rank_l1_switches`, `pick_l1_switch`, `L1Candidate` | R1 model choice: fewest per side, then fewest ports, then `part_id`; a pinned `part_id` wins |
| `size_network` -> `NetworkPlan` | L1 and L2 counts per side (R1, R2); `ied_count` kept only for the check report (R4) |
| `L2Link`, `l2_port_plan`, `l1_port_plan` | Generated port plans (R3) |
| `SizingError` | Inputs no library switch can meet |

## `src/bomgen/engine/layout.py` (R5-R10)

Layers, bottom up:

1. **Fill (pure).** `Unit` (one placeable unit: equipment id, unit number, side, height,
   cable manager U), `LayoutRules` (capacity, blank plate U), `blank_plates`, `used_u`,
   `PanelFill` (`stack()`, `is_pinned`, `position`, `fits`), `_Builder`, `fill()` (R5, R6:
   A stream in odd panels, B in even, lock-step; common units into the panel with most free U).
2. **Overrides.** `auto_layout(units, rules, removed=, moves=)` drops removals first, fills, then
   applies `DeviceMove` / `PairMove` in order (R7). Every move records a pin in `PanelFill.pins`
   with its optional `position`. Issues: `stale-override`, `stale-removal`, `move-does-not-fit`,
   `unknown-panel`, `device-too-tall`, `panel-empty`, `missing-height`.
3. **Substation mapping.** `network_inputs`, `l1_candidates`, `_size`, `_units`, `_side_ports`,
   `_capacity_issues` (`port-capacity`), `_rows`, `_port_plans`, `_panel` turn a
   `LoadedSubstation` into `Panel` models with `generated=True`.
4. **Entry points.**
   - `layout_preview(loaded, overrides=None) -> LayoutResult`: the whole thing. `overrides`
     replaces the file's `layout:` block (the app passes a candidate before saving).
     L2 is re-sized from the **kept** units (after removals).
   - `layout_substation(loaded)`: `layout_preview` with the file's own overrides (CLI).
   - `with_layout(loaded)`: used by `bomgen build`. Replaces `panels:` only when a listed
     panel file is `generated: true`; otherwise returns the input unchanged (keeps the spec
     goldens). Adds `replaced-panel` for hand-written files still listed in `panels:`.
   - `render_panel_yaml(panel)`: the generated `panels/<id>.yaml` text (with `GENERATED_HEADER`).
   - `reconcile_panels_list(text, files)`: rewrites the `panels:` list in `substation.yaml`
     as text so comments survive.
   - `_loose_material_issues`: `missing-panel` when loose material names a panel the layout
     no longer writes.

`WARNING_KINDS` = `stale-override`, `stale-removal`, `replaced-panel`; every other
`IssueKind` is an error (`LayoutIssue.is_error`).

## Callers outside role 8 (change these only with their owner)

| Caller | Owner | Uses |
| --- | --- | --- |
| `src/bomgen/cli.py` (`bomgen layout`, `build --no-layout`) | A2 (role 8 edited with A1's leave) | `with_layout`, `layout_substation`, `render_panel_yaml`, `reconcile_panels_list` |
| `src/bomgen/build.py` | A2 | the caller lays out first with `with_layout` (agents.md shared-file table) |
| `src/bomgen/app/network.py` (Panels board data) | A11 | `layout_preview`, `LayoutResult`, `Unit`, `blank_plates`; sends `pinned`, `position`, `plate_below_u` |
| `src/bomgen/app/editing.py` (refuses a move that adds errors) | A11 | `layout_preview(loaded, candidate)`, `is_error` |
| `src/bomgen/app/substations.py` | A11 | `with_layout`, `LayoutIssue` |
| `src/bomgen/io/edit.py` | A2 | `layout_preview` after an edit |

Any change to `LayoutResult`, `PanelFill`, `Unit` or the issue kinds is an API change for
these callers: grep them, run `tests/unit/app/` and tell their owners.

## Tests

| File | Covers |
| --- | --- |
| `tests/unit/engine/test_sizing.py` | R1-R4, named `test_r<N>_...` |
| `tests/unit/engine/test_layout.py` | R5-R10, overrides, pins, positions, blank plates, issues |
| `tests/unit/engine/test_layout_cli.py` | `bomgen layout`, `build --no-layout`, `panels:` reconciliation |
| `tests/golden/layout/` (`expected_panels.yaml`, `test_layout_golden.py`) | The gis01 example laid out: 3 L1 per side, demand 8, psa1 23U, psa2 19U (Ali confirmed) |
| `tests/unit/test_substation_model.py` (A2's) | the `position` fields |
| `tests/unit/app/test_app_network_api.py` (A11's) | the board's values that follow from the engine |

Plan: [`docs/superpowers/plans/2026-10-28-m1c-sizing-and-layout.md`](../../superpowers/plans/2026-10-28-m1c-sizing-and-layout.md).
