# M21 Panel priority and waist-height placement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inside each generated panel, rack units stack by a fixed priority (time server, network,
servers, others), a KVM or console sits with its bottom edge at waist height, and the layout
gives every unit an absolute top U.

**Architecture:** Panel assignment is unchanged (equipment order, ADR 0013 R6; design decision f).
`Unit` gains `priority` and `waist`, set from the part's category in `_units`. `PanelFill.stack()`
sorts by priority before equipment order; a new `PanelFill.place(rules)` turns the stack into
top-U positions, anchoring waist units at `waist_u`. `fits()` uses `place()`, so a panel holding a
KVM loses the space its anchoring wastes. BOM row order (`_rows`) stays equipment order.

**Tech Stack:** Python 3.12, pytest, ruff, mypy (CLAUDE.md).

**Spec:** `docs/superpowers/specs/2026-10-31-part-picking-design.md` §2 (d, e, f), §5, §9;
ADR 0013 (R5–R7) and ADR 0024 (`defaults.layout`, `kvm` and `console` categories, from M20).

## Global Constraints

- Gate before every commit: `ruff check . && ruff format --check .`, `python -m mypy`,
  `python -m pytest -q -p no:cacheprovider`.
- TDD; tests named after the rule. Conventional commits. One PR for the milestone; based on main
  after #239 (M20) and #238 (M19) merge.
- Golden values must not move (`pytest tests/golden`): the example has no KVM and its panels
  already follow the priority (design §9). If one moves, stop and tell A1 (ADR first).
- `waist_u = round((waist_height_mm − rack_start_mm) / 44.45)`, U counted from 1 at the bottom of
  the rack space; with the ASSUMED defaults 1000 and 200 mm that is U18.
- Priority classes (design §5, assumption §10: gateway and firewall are network):
  1 `gps_clock`; 2 `network_switch`, `patch_panel`, `firewall`, `gateway`; 3 `workstation`;
  4 everything else. Waist categories: `kvm`, `console`. Ties keep `_order` (equipment order).
- DIN-rail units (0 U) take no position. A pinned `position` (R7) still wins over priority and
  over the waist anchor.

## Review Focus

1. Two waist units in one panel (KVM and console): both anchored, the first in stack order at
   `waist_u`, the next directly above it with the R5 clearance — tested in Task 2.
2. A panel too short for the anchor (`waist_u + anchored height − 1 > capacity_u`): an error
   naming the panel, not a crash and not a silent move — Task 3.
3. A pinned KVM (`DeviceMove` with `position`): placed by the pin, not at waist height, no
   waist error — Task 2.
4. Units that do not fit above the anchor go below it in stack order; if they overflow U1 the
   panel does not fit (`fits()` false), so the fill opens a new pair — Task 2.
5. Hand-written panels and `bomgen build --no-layout` are untouched (the layout never reads
   them) — covered by the existing golden tests.

---

### Task 1: Priority order in the stack

**Files:**
- Modify: `src/bomgen/engine/layout.py` (`Unit`, `_units`, `PanelFill.stack`)
- Test: `tests/unit/engine/test_layout.py`

**Interfaces:**
- Produces: `Unit.priority: int = 4`, `Unit.waist: bool = False` (new dataclass fields, after
  `cable_manager_u`); `PRIORITY: dict[Category, int]` and `WAIST: frozenset[Category]` module
  constants; `_stack_order(unit) -> tuple[int, int, str, int]` = `(priority, *_order(unit))`.

- [ ] **Step 1: Failing tests**
  - `test_time_server_stacks_above_network_in_a_panel`: `PanelFill(1, [gw(rank 0, priority 2),
    gps(rank 1, priority 1)]).stack()` lists gps first.
  - `test_priority_ties_keep_equipment_order`: two priority-2 units, rank 1 and 0 → rank 0 first.
  - `test_priority_does_not_choose_the_panel`: `fill()` of a pair stream whose second entry is a
    priority-1 unit puts each unit in the same panel as with all priorities equal.
  - `test_units_carry_priority_and_waist_from_the_category` (on the `example` fixture via
    `layout_preview`): the gps units have priority 1, the rtac units 4, none is waist.
- [ ] **Step 2: Run, expect FAIL** — `python -m pytest tests/unit/engine/test_layout.py -q`
- [ ] **Step 3: Implement.** `_units` sets `priority=PRIORITY.get(device.category, 4)` and
  `waist=device.category in WAIST`. `stack()` sorts the unpinned units by `_stack_order`; pins
  insert as today. `fill_streams`, `place_common` and `add` keep `_order`.
- [ ] **Step 4: Run, expect PASS**, then `pytest tests/golden` (no change) and the full gate.
- [ ] **Step 5: Commit** `feat(layout): stack panel units by priority`

### Task 2: Absolute positions and the waist anchor

**Files:**
- Modify: `src/bomgen/engine/layout.py` (`LayoutRules`, `PanelFill`, `layout_preview`)
- Test: `tests/unit/engine/test_layout.py`

**Interfaces:**
- Consumes: Task 1's `Unit.waist`, `stack()`.
- Produces: `LayoutRules.waist_u: int | None = None`; `PanelFill.place(rules) -> dict[Unit, int]
  | None` (top U per rack unit, U1 = bottom; `None` when the stack cannot be placed);
  `PanelFill.top_u(unit, rules) -> int | None`; `waist_u(layout: LayoutDefaults) -> int`.
  `fits()` becomes `trial.place(rules) is not None`; `used_u` and `free_u` unchanged.

- [ ] **Step 1: Failing tests** (RULES with `capacity_u=32, blank_plate_u=1, waist_u=18`)
  - `test_waist_u_from_the_project_heights`: `waist_u(LayoutDefaults()) == 18`;
    `waist_u(LayoutDefaults(waist_height_mm=1100, rack_start_mm=100)) == 22`.
  - `test_units_stack_from_the_top_without_a_kvm`: 1U, 2U → top U 32 and 30 (one plate between).
  - `test_kvm_bottom_sits_at_waist_height`: 2U switch + 1U KVM → KVM top U 18, switch top U 32.
  - `test_units_that_do_not_fit_above_the_kvm_go_below_it`: 13 × 1U units then KVM (1U) with
    `waist_u=18`: above the anchor there are U32..U20 with plates, so 7 fit above; the rest are
    placed from U16 down in stack order.
  - `test_a_console_stacks_above_the_kvm_at_waist_height`: KVM (rank 0) and console (rank 1),
    both 1U → KVM top U 18, console top U 20.
  - `test_a_panel_that_overflows_below_the_kvm_does_not_fit`: `place()` is None and `fits()`
    false when the units below would need U0.
  - `test_a_pinned_kvm_ignores_waist_height`: KVM pinned at `position=1` → top U 32.
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement.** Clearance between two physical neighbours is `blank_plate_u` unless
  the upper block has a cable manager (R5 as amended); free space larger than that needs no plate.
  Without an unpinned waist unit (or with `waist_u is None`), place top-down from `capacity_u`.
  With one: the unpinned waist units, in stack order, form an anchor block whose bottom is
  `waist_u`; walk the other rack units in stack order placing from the top while the unit's
  bottom stays above the anchor top plus clearance; from the first that does not, place the rest
  from `waist_u − 1` (minus clearance under the anchor) downward. Return `None` if the anchor top
  exceeds `capacity_u` or any bottom is below 1. `layout_preview` builds
  `LayoutRules(..., waist_u=waist_u(loaded.project.defaults.layout))`.
- [ ] **Step 4: Run, expect PASS**; `pytest tests/golden`; full gate.
- [ ] **Step 5: Commit** `feat(layout): place units by top U with the KVM at waist height`

### Task 3: Waist-height error, ADR 0013 amendment

**Files:**
- Modify: `src/bomgen/engine/layout.py` (`IssueKind`, `_Builder.check_height`/`finish`)
- Modify: `docs/decisions/0013-network-sizing-and-panel-layout.md` (an *Amended* paragraph
  under Layout, like the two there); `CHANGELOG.md` `[Unreleased]` Added
- Test: `tests/unit/engine/test_layout.py`

- [ ] **Step 1: Failing tests**
  - `test_a_panel_too_short_for_waist_height_is_an_error`: `capacity_u=16`, `waist_u=18`, one
    KVM unit → `fill()` gives one issue, kind `"waist-height"`, subject `"panel 1"`, message
    `"panel 1 has 16 U; a KVM or console at waist height needs U18"` (a taller anchor block says `"needs U18 to U20"`), `is_error` true.
  - `test_waist_height_error_reaches_the_layout_report` on the example with a 1U `kvm` part
    added (via `with_entry`-style helper and a library copy) and `rack_u_reserved` raised so the
    capacity is below 18.
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement.** Add `"waist-height"` to `IssueKind` (an error). In `fill`, a waist
  unit that cannot be anchored in a new empty panel either is still added (as `device-too-tall`
  does today) and reported once per panel in `finish`; `place()` for that panel falls back to
  top-down so positions exist.
- [ ] **Step 4: Run, expect PASS**; full gate; `python data/library/build.py` no diff.
- [ ] **Step 5: Docs**: ADR 0013 *Amended (Ali, 2026-10-31, part-picking design §5)* paragraph:
  priority classes, ties, waist anchor and formula, below-anchor rule, pins win, absolute top U,
  blank space still no BOM row (Q25), panel assignment unchanged. CHANGELOG entry.
- [ ] **Step 6: Commit** `docs: amend ADR 0013 with panel priority and waist height` and open the
  PR.
