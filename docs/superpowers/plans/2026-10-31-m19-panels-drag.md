# M19 Panels board drag and drop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dragging a device on the Panels board works in the installed Windows app, and a
substation with hand-written panels can switch to generated panels in one click so the board
becomes draggable.

**Architecture:** (1) Replace the board's HTML5 drag-and-drop (`dragstart`/`dragover`/`drop`,
which WebView2 under pywebview is the likely blocker of) with pointer events and pointer capture;
same states, bridge check and writes. (2) Move the `bomgen layout` file-writing out of
`cli.py` into `engine/layout.py` so the CLI and a new bridge method `generate_panels` share it;
the read-only banner gets a "Lay out panels" button with a confirm dialog.

**Tech Stack:** vanilla JS UI (`src/bomgen/app/ui/`), pywebview bridge (`app/api.py`), Python 3.12.

**Spec:** `docs/superpowers/specs/2026-10-31-part-picking-design.md` §6a; Ali's card answer
2026-10-31 "Not sure, check both".

## Global Constraints

- The drag contract in `docs/ui/editing.md` "Drag and drop contract" is unchanged: every state in
  its table still holds (dim 45 %, live green/red column, insertion line, refused drop banner,
  drop in place does nothing, Esc cancels, Alt moves one unit of a pair).
- Controls that cannot act are absent (LESSONS "Controls that cannot act").
- Gate: ruff, mypy, pytest; `node --check src/bomgen/app/ui/*.js`; Playwright E2E per LESSONS
  "E2E without the window"; screenshots to `/mnt/project-files/a11-screens/m19-drag/`.
- The PR touches `src/bomgen/app/`, so "Build Windows installer" must be green.

## Review Focus

1. A click without movement must still select the device (`pv-select-dev`), not start a drag:
   drag starts only after 4 px of movement.
2. A drag that ends outside every column does nothing and clears the marks.
3. The page re-rendering mid-drag (a bridge reply calling `App.render`) must not leave a stuck
   drag: `pointercancel` and `lostpointercapture` end it.
4. Generating panels must never delete a hand-written file without a copy: replaced files are
   copied to `panels/hand-written-<YYYYMMDD-HHMMSS>/` first.
5. A substation with no equipment: the "Lay out panels" button is absent (nothing to lay out).

---

### Task 1: Pointer-event drag on the board

**Files:**
- Modify: `src/bomgen/app/ui/screens-panels.js:126` (drop `draggable="true"`), `:233-286`
  (the drag section)
- Modify: `src/bomgen/app/ui/styles.css` (`.dev` gets `touch-action: none` when movable;
  `body.is-dragging-dev` sets `cursor: grabbing` and `user-select: none`)

**Interfaces:**
- Keeps: `probe(n)`, `paint()`, `clearMarks()`, `moveOf`, `others`, `write`, `refusal`.
- Produces: `startDrag(el, e)`, `moveDrag(e)`, `endDrag(e, cancelled)` inside the module IIFE.

- [ ] **Step 1: Write the E2E check first (scratch script, not committed)** that on the example
  with `fed_from: psa1` drives `page.mouse.down/move/up` from an L2 unit in panel 1 to the gap
  after the first device of panel 3 and asserts the toast "Pinned" and the unit's pin icon; a
  second case presses Escape mid-drag and asserts no `.drop-ok`/`.drop-bad` remains and nothing
  was written; a third clicks without moving and asserts `aria-pressed="true"`.
- [ ] **Step 2: Run it against today's code, record the result** (HTML5 DnD does not respond to
  `mouse.down/move/up` in Chromium, so it fails: the test reproduces "nothing moves").
- [ ] **Step 3: Implement.** `pointerdown` (primary button, `onBoard()`, not `busy`) records the
  start point and Alt; `pointermove` past 4 px starts the drag (`setPointerCapture`, add
  `is-dragging`, probe every panel); while dragging, the column comes from
  `document.elementFromPoint(e.clientX, e.clientY)`; `pointerup` runs today's drop body;
  `pointercancel`, `lostpointercapture` and `keydown Escape` end without writing. Suppress the
  click that follows a real drag (one `click` capture listener with a flag).
- [ ] **Step 4: Run the E2E, expect PASS**; `node --check`; screenshots.
- [ ] **Step 5: Commit** `fix(app): drag on the Panels board with pointer events`

### Task 2: Lay out panels from the read-only board

**Files:**
- Modify: `src/bomgen/engine/layout.py` (new `write_generated_panels`)
- Modify: `src/bomgen/cli.py` (`layout` calls it; behaviour and messages unchanged)
- Modify: `src/bomgen/app/api.py` (new `generate_panels`)
- Modify: `src/bomgen/app/ui/screens-panels.js` (banner button + dialog), `docs/ui/editing.md`
- Test: `tests/unit/test_cli.py` (unchanged tests must pass), `tests/unit/engine/test_layout_write.py`,
  `tests/unit/app/test_api_layout.py`

**Interfaces:**
- Produces:
  - `write_generated_panels(substation_file: Path, *, replace_hand_written: bool, backup: bool) -> WrittenPanels`
    where `WrittenPanels` is a frozen dataclass: `written: list[Path]`, `refused: list[Path]`
    (hand-written targets left alone), `backup_dir: Path | None`, `report: LayoutReport`.
  - `Api.generate_panels(project_file: str, substation_id: str) -> dict` →
    `{"written": [...], "backup": str | None, "issues": [...]}`, always with
    `replace_hand_written=True, backup=True`, then the same reload the other layout writes do.

- [ ] **Step 1: Failing tests**
  - `test_generate_panels_copies_hand_written_files_before_replacing_them`: copy `examples/` to
    `tmp_path`, set `fed_from: psa1`, call with `replace_hand_written=True, backup=True`; the
    backup dir holds the old files byte-identical and every written file starts with the
    generated header.
  - `test_generate_panels_refuses_hand_written_files_without_replace` (`refused` lists them,
    nothing written) — the CLI's current behaviour.
  - `test_api_generate_panels_makes_the_board_editable`: after the call,
    `substation_layout(...)["generated"] is True`.
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement** `write_generated_panels` from the body of `cli.layout` (including
  `_relist_panels`, moved with it); `cli.layout` becomes a thin caller printing the same lines.
- [ ] **Step 4: UI.** Under `READ_ONLY`, when the substation has equipment, a secondary button
  "Lay out panels from the equipment" opens a dialog: "This replaces N hand-written panel files
  with panels laid out from the equipment. Copies are kept in panels/hand-written-…/." with
  "Lay out panels" (primary) and "Cancel". After it, the board reloads and is draggable; a toast
  names the backup folder. Update `docs/ui/editing.md` "Panels board" with the button.
- [ ] **Step 5: Run tests and E2E (hand-written example → button → board draggable)**; full gate.
- [ ] **Step 6: Commit** `feat(app): lay out hand-written panels from the board`; CHANGELOG
  `[Unreleased]` Fixed (drag) and Added (button); open the PR.
