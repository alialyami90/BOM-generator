# M24 Device preview — engine tasks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One engine call gives the Device preview screen everything it draws: each unit with its
panel, top U, MCBs and strips, each panel's fill, and the issues, plus U-based pins the screen can
write when a unit is dragged or moved by 1 U.

**Architecture:** `engine/preview.py` runs `layout_preview` (with optional candidate overrides),
builds the substation in memory with the existing engine (no workbook), runs `check_report`, and
maps the result to a pydantic `DevicePreview`. `BranchMcb` gains the unit tag and feed so the unit's
MCBs are matched exactly. `DeviceMove`/`PairMove` gain `top_u`, which `PanelFill.place` treats as a
fixed block. The screen (A2's tasks) calls it through a bridge method; `check_layout` already reads
layout issues, so `top_u` pins are checked live with no bridge change.

**Tech Stack:** Python 3.12, pydantic v2, pytest, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-10-31-part-picking-design.md` §6, §7.3;
`docs/ui/screens.md` "Device preview (M22)"; ADR 0013 (amended M21), ADR 0024. Interface agreed with
A2 on 2026-10-31 (items a–g below).

## Global Constraints

- Gate before every commit: `ruff check . && ruff format --check .`, `python -m mypy`,
  `python -m pytest -q -p no:cacheprovider`. TDD, tests named after the rule.
- Golden values must not move; `BranchMcb` only gains fields, the BOM and check report text are
  unchanged.
- U convention (A2 e, f): `top_u` is the top of the whole block (`height_u + cable_manager_u`,
  manager at the bottom), counted 1..`capacity_u` from the bottom of the rack space; `waist_u` is the
  U the anchor's bottom edge sits on.
- One PR for the engine half; A2's screen PR builds on it.

## Review Focus

1. A `top_u` pin that overlaps another pinned block or leaves the rack: a layout error with a
   sentence the screen shows as is, never a crash — Task 2.
2. A `top_u` pin and a `position` pin in one panel: the `top_u` block is fixed, the rank-pinned
   and unpinned units fill around it — Task 2.
3. A panel that overflows: the units that fit keep their U, the rest are `placed: false`, and
   `overflow_u` counts them — Task 3.
4. An engine error (e.g. no SFP for a speed): one error issue, no panels, no exception — Task 4.
5. A redundant entry: both sides listed, each with its own panel, tag and MCBs — Task 4.

---

### Task 1: Branch MCBs name their unit and feed

**Files:** Modify `src/bomgen/models/calc.py` (`BranchMcb`), `src/bomgen/engine/dc_dist.py`
(`_Branch`, `branch_line`). Test `tests/unit/engine/test_engine_dc_dist.py`.

**Produces:** `BranchMcb.unit_tag: str | None = None` (the unit's full tag, e.g. `PSA1-L2-ESW-A01`;
for a QCOD the single-fed unit's tag, None for a loose load), `BranchMcb.feed: Literal[1, 2] | None`
(None on a QCOD).

- [ ] Failing tests: `test_each_branch_mcb_names_its_unit_and_feed` (dual-fed switch row of qty 2 →
  four records, `(tag, unit_tag, feed)` = Q1.1/A01/1, Q1.2/A02/1, Q2.1/A01/2, Q2.2/A02/2);
  `test_a_qcod_names_its_single_fed_unit` (feed None, unit_tag the unit's tag).
- [ ] Implement: `_Branch` carries `unit_tag`; `FedLoad` carries the unit tag when it is a panel row.
- [ ] Gate (goldens unchanged); commit `feat(dc-dist): branch MCBs name their unit and feed`.

### Task 2: Pins by top U

**Files:** Modify `src/bomgen/models/substation.py` (`DeviceMove`, `PairMove`),
`src/bomgen/engine/layout.py` (`_Builder.move`, `PanelFill.pins`, `place`, `IssueKind`); `bomgen
schema`. Test `tests/unit/test_substation_model.py`, `tests/unit/engine/test_layout.py`.

**Produces:** `DeviceMove.top_u: PositiveInt | None`, `PairMove.top_u` (same U in both panels);
both refuse `top_u` with `position` ("give position or top_u, not both"). `PanelFill.pins` values
become `Pin = tuple[Literal["position", "top_u"], int] | None`. New error kinds `"pin-overlaps"`,
`"pin-outside-rack"`.

- [ ] Failing tests: `test_top_u_and_position_are_exclusive`;
  `test_a_unit_pinned_by_top_u_sits_there` (pin 1U at 10 → top U 10, others fill from the top);
  `test_units_fill_around_a_top_u_pin` (pin at 30 in a 1U stack → the first unit at 32, the next
  below the pin with the R5 clearance);
  `test_a_top_u_pin_overlapping_another_is_an_error` → issue `pin-overlaps`, subject
  `"panel 1"`, message `"gps#1/a at U30 overlaps rtac#1 at U30 to U28 in panel 1"`;
  `test_a_top_u_pin_outside_the_rack_is_an_error` → `pin-outside-rack`,
  `"l2#1/a at U33 leaves the rack of panel 1 (U1 to U32)"`;
  `test_a_kvm_pinned_by_top_u_ignores_waist_height`.
- [ ] Implement: fixed blocks are placed first; the waist anchor next; the rest fill the free runs
  top-down in stack order (a unit takes the first run, from the top, that holds it with clearance
  to its neighbours). `position` pins keep their R7 meaning inside that order.
- [ ] Docs: an ADR 0013 *Amended* paragraph (top_u vs position, exclusive, the two new errors); `bomgen schema`.
- [ ] Gate; commit `feat(layout): pin a unit by its top U`.

### Task 3: Placement that reports what did not fit

**Files:** Modify `src/bomgen/engine/layout.py` (`PanelFill`). Test `test_layout.py`.

**Produces:** `PanelFill.placement(rules) -> Placement` with `tops: dict[Unit, int]` (placed rack
units), `unplaced: list[Unit]` (in stack order), `used_u: int` (placed blocks and their plates),
`overflow_u: int` (Σ block_u of the unplaced). `place()` returns `None` exactly when `unplaced` is
non-empty (unchanged for every caller).

- [ ] Failing tests: `test_an_overflowing_panel_places_what_fits` (capacity 5, three 2U units →
  two placed at 5 and 2, one unplaced, `overflow_u == 2`, `used_u == 5`).
- [ ] Implement; `place()` delegates to it. Gate; commit
  `feat(layout): report the units that do not fit`.

### Task 4: `device_preview`

**Files:** Create `src/bomgen/engine/preview.py`, `src/bomgen/models/preview.py`. Test
`tests/unit/engine/test_preview.py` (on the example and on the example with a derived part).

**Consumes:** Tasks 1–3; `layout_preview`, the build's in-memory engine entry used by
`build_substation` (`run_engine` or its current name), `check_report`.

**Produces:** `device_preview(loaded: LoadedSubstation, overrides: Layout | None = None) ->
DevicePreview`, all `OutputModel`:
- `DevicePreview`: `waist_u, waist_height_mm, rack_start_mm, capacity_u, enclosure_u: int`;
  `panels: tuple[PreviewPanel, ...]`; `issues: tuple[PreviewIssue, ...]`.
- `PreviewPanel`: `panel_id, name: str; number: int; side: Literal["a","b"] | None;
  used_u, overflow_u: int; base_frame_mm: int | None; units: tuple[PreviewUnit, ...]` (stack
  order, then unplaced, then DIN rail).
- `PreviewUnit`: `device, role, tag, part_id, library_part_id: str; n: int; side; bom_code:
  str | None; has_part_number: bool; overridden: tuple[str, ...]` (the `PartOverrides` fields set);
  `placed, din_rail, pinned, waist, away_from_waist: bool; top_u: int | None; height_u,
  cable_manager_u: int; watts: float | None; supply: str | None` (`"125 VDC"`); `ps1, ps2:
  PreviewMcb | None; strips: tuple[str, ...]` (the unit's own terminal strip codes).
- `PreviewMcb`: `tag: str; rating_a: int; at_minimum: bool` (rating equals the catalogue's
  floor for `min_branch_mcb_a`).
- `PreviewIssue`: `severity: Literal["error","warning"]; kind, message: str; subject: str |
  None; device: str | None; panel: int | None`. Layout issues, check-report fails and warns,
  `"pinned-away-from-waist"` warnings, and an `EngineError` as one error (`kind "engine"`, no
  panels).

- [ ] Failing tests: `test_preview_lists_every_unit_with_its_top_u` (example: psa1 first unit
  `gps`, top_u 32); `test_preview_gives_each_unit_its_two_dc_mcbs` (l2 side A → ps1
  `PSA1-Q1.n`, ps2 `PSA1-Q2.n`, ratings from `branch_mcbs`); `test_a_single_fed_unit_has_one_mcb`;
  `test_preview_marks_overridden_values_and_the_part_number` (gw with `overrides.unit_power_w`
  and no ordering_code → `overridden == ("unit_power_w",)`, `has_part_number` False);
  `test_a_kvm_pinned_away_from_waist_height_is_a_warning`; `test_an_engine_error_is_one_issue`;
  `test_preview_takes_candidate_overrides_without_writing`.
- [ ] Implement. Gate; commit `feat(engine): device preview`; open the PR, CHANGELOG entry.

## Open question for Ali (via A1)

The engine gives no device an AC branch MCB: the spec's AC distribution (group E) feeds only the
lamp, fans, thermostats and socket, and a `VAC` device has `power_supplies` 0. The Parts page lets a
device be (or be overridden to) 230 VAC, and the prototype shows such units on `Q31`. Until Ali
decides, an AC device's `ps1` and `ps2` are None and the screen shows "—".

---

## App tasks (A2): the screen half

Agreed with A3 on 2026-10-31; Task 4's fields are the interface. Spec: `docs/ui/screens.md` "Device preview (M22)", `docs/ui/components.md` "Rack elevation", `docs/ui/editing.md` "Drag and drop contract", design §6 and §7.3, plus Ali's M22 changes once relayed.

### App constraints

- Tasks 5–8 start after Tasks 1–4 merge, and after Ali approves the M22 design.
- The screen draws only what `DevicePreview` gives. It never computes a U, an MCB, a fit or a waist
  position. Every live drop check goes through the bridge.
- Gate:
  - ruff, mypy and pytest
  - `node --check src/bomgen/app/ui/*.js`
  - Playwright E2E per LESSONS "E2E without the window"
  - screenshots in `/mnt/project-files/a11-screens/m24-preview/`
  - "Build Windows installer" green
  - a CHANGELOG entry
- The Panels board's drag behaviour does not change. Its E2E from M19 still passes after Task 6.

### App review focus

1. **A bridge reply after a newer move.** The live check for an older drop target must not paint
   the current one. Replies carry a sequence number, and stale ones are dropped.
2. **The page re-renders mid-drag.** For example, a substation switch or a save from another
   screen. `pointercancel` and `lostpointercapture` end the drag, with no stuck ghost.
3. **Units that did not fit** (`placed: false`) are listed in the table with "Not placed" and are
   never drawn. The meter shows `used_u + overflow_u` of `capacity_u` in red.
4. **Parts has unsaved changes.** The preview shows the saved parts under an info banner, and
   "Generate preview" on Parts stays disabled with its reason.
5. **An engine error** (`kind "engine"`) shows one banner and no front views or table. "Go to the
   row" appears only when the issue names a `device`.

---

### Task 5: Bridge

**Files:**
- Create `src/bomgen/app/device_preview.py`
- Modify `src/bomgen/app/api.py`
- Test `tests/unit/app/test_app_device_preview_api.py`

**Produces:**
- `device_preview_page(project_file: Path, substation_id: str, store: LibraryStore,
  overrides: list[dict] | None = None) -> dict[str, Any]`. It returns
  `DevicePreview.model_dump(mode="json")` plus `{"saved_at"}`.
- Each unit gains a `label` from `ROLE_LABEL` (M23 `app/parts.py`).
- `Api.device_preview(project_file, substation_id)`.
- Pins are written through the existing `set_layout_overrides`, and live drop checks go through
  the existing `check_layout`. Both now carry `top_u` entries (Task 2).
- Unpin writes the override list without that entry.

**Tests:**
- `test_device_preview_page_labels_each_unit_by_its_row`
- `test_a_pin_by_top_u_is_written_and_the_page_shows_it_pinned`
- `test_unpin_removes_only_that_override`
- `test_check_layout_refuses_a_top_u_that_overlaps_with_the_layout_sentence`

**Commit:** `feat(app): device preview bridge`

### Task 6: One pointer-drag helper for both views

**Files:**
- Create `src/bomgen/app/ui/drag.js`
- Modify `screens-panels.js` and `index.html`

**Produces:** `App.pointerDrag({ handle, start(el), target(e), paint(at), drop(at), cancel() })`.
It covers:
- the 4 px threshold
- `setPointerCapture`
- `elementFromPoint`
- Esc to cancel
- `pointercancel` and `lostpointercapture`
- swallowing the click after a drag

The board moves onto it with no behaviour change, as design §6 asks ("the same pointer-based drag
code").

**Tests:**
- `test_board_and_preview_load_the_shared_drag_helper` (assets)
- the M19 board E2E, unchanged

**Commit:** `refactor(app): shared pointer drag for the board and the device preview`

### Task 7: The Device preview screen

**Files:**
- Create `src/bomgen/app/ui/screens-device-preview.js`, built from the M22 prototype with its data
  swapped for the bridge
- Modify `ui.js`: the "Device preview" rail item after Parts, with the `elevation` icon; route
  `#/device-preview`; disabled until Parts is set up
- Modify `icons.js` and `styles.css`: the M22 `.elev*`, `.eu*`, `.dp-*` and `.pin-tag` classes
- Modify `screens-parts.js`: "Generate preview" in the page head, disabled with "Save your changes
  first." while dirty
- Modify `screens-parts.js`: "Go to the row" lands on Parts with that row focused and scrolled into
  view (`#/parts?row=<device>`)

**Behaviour:** as the M22 spec.
- Errors appear in a banner above the front views, and every panel has a second meta line while
  any panel has an error.
- Warnings come with "Go to the row".
- Front views are 268 px wide at 18 px per U, with a cable-manager band, a waist line at the
  bottom edge of `waist_u`, and DIN-rail parts listed in the footer.
- The table has the legend and filter chips, and selection is linked between the table and the
  front views.
- The selected-unit bar has Up 1 U, Down 1 U and Unpin. Each is shown only when the bridge says
  the move fits, and Arrow Up and Down do the same.
- Drag goes through `App.pointerDrag`: Alt moves one unit of a pair, and every drop is checked live
  through `check_layout`. A drop writes a pin with a toast and Undo.

**Tests:**
- `test_device_preview_draws_only_what_the_engine_gives` (asserts no U or MCB arithmetic beyond
  `top_u` to pixels)
- `test_generate_preview_is_disabled_while_parts_has_changes`
- `test_device_preview_rail_item_follows_parts`

**E2E:** on the example:
- open from Parts
- select a unit, then press Down (a pin is written)
- Unpin
- drag a KVM away from waist height (a warning is listed)
- an A unit dropped on a B panel is refused
- Esc cancels a drag
- the overflow state, made by raising `rack_u_reserved`, shows "Not placed"
- no console errors

Take screenshots, light and dark, at 1280 and 1024.

**Commit:** `feat(app): Device preview page`

### Task 8: Departures from the approved design (A1 agreed, 2026-10-31)

Write these in `docs/ui/screens.md` "Departures in the built app":
- **Strip column:** the engine gives a unit's own terminal strips (`strips`, empty for most units),
  not the X1/X2 feed strips the prototype shows. Recommended: show the column only when some unit
  has strips.
- **AC units:** `ps1` and `ps2` are None until Ali answers A3's AC-MCB question. The cells show
  "—", with the title "AC devices have no branch MCB in this design".

Commit with the CHANGELOG, the `plan.md` M24 row and the handoff files:
`docs: M24 Device preview in the changelog, plan and handoff`.
