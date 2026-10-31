# M22 Parts page and device preview design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Design the Parts page (replacing Network) and the device Preview in `docs/ui/` with the
impeccable skill (specs, components and a clickable prototype), so M23 and M24 build an
approved design.

**Architecture:** Docs-only, inside `docs/ui/`. Following the M9 house pattern, the written
specs (`screens.md`, `components.md`, `editing.md`) say what each screen and component does.
The prototype (`docs/ui/prototype/`, vanilla JS on illustrative `data.js`) gets two new screen
files that run in a browser with no server. Existing tokens are reused; a token is added only
when no existing one fits, and then also in `tokens.json` and through `build-tokens.mjs`.

**Tech Stack:** HTML, CSS and vanilla JS (the prototype), Markdown, the `impeccable` skill,
Playwright for screenshots.

**Spec:** `docs/superpowers/specs/2026-10-31-part-picking-design.md`, sections 2, 3, 5 (waist
height, for the elevation), 6, 7 and 10. CLAUDE.md "UI work".

## Global Constraints

- Docs-only PR: everything under `docs/ui/` plus this plan in `docs/superpowers/plans/`.
  Nothing in `src/`, and no CHANGELOG entry (docs PRs get none).
- Load the `impeccable` skill before designing. Follow `docs/ui/design-language.md` and
  ADR 0011. Reuse existing components (save bar, Changed marker, Override marker, Device
  picker, Table, Banner, Panel column, Device block) before inventing new ones.
- The prototype's house rule (`screens.md` "Departures") stands: existing prototype screens
  are not edited to match the built app. Only the new screens, the route map, the rail item
  and their illustrative data are added.
- Copy follows `editing.md` "Validation" and the voice in `design-language.md`: labels, not
  enum values ("Time server clock", not `time_server`); the problem and the fix.
- Controls that cannot act are absent (LESSONS "Controls that cannot act").
- Business rules stay in the engine. The prototype shows illustrative results and never
  computes sizing, MCBs or placement beyond what `engine-stub.js` already fakes.
- Gate: `for f in docs/ui/prototype/*.js; do node --check $f; done`; `impeccable detect --json
  docs/ui/prototype` returns `[]`; `test_tokens_match_the_design` passes if tokens change.
- Screenshots (light and dark, 1280×800 and 1024×768) go to
  `/mnt/project-files/a11-screens/m22-parts/`.
- Ali reviews the design on a decision card before M23 starts (CLAUDE.md M9 rule).

## Decisions (A1, 2026-10-31)

1. **Name.** The new step is **Device preview** (`#/device-preview`, rail item after Parts); the
   Parts button reads "Generate preview" (Ali's words in the design). The workbook **Preview**
   stays as it is. The approval card to Ali says the name avoids two "Preview" items.
2. **Scope.** M22 designs both the Parts page and the device preview. The same PR updates the
   M22 row in `docs/plan.md` and design §8 to say so.

## Review Focus

1. **A part dropped from the library.** A row whose saved part is no longer in the active
   library shows the id in error with "Pick another part". The details strip is empty, not
   zeros.
2. **An override equal to the library value.** It is not marked overridden (no reset shown),
   and saving drops it. Spec this in `editing.md`.
3. **An L1 or L2 row with the part left to the sizing.** It has no details strip to
   override; one line says "Pick the switch to change its data." (the M20 refusal, worded for
   the page).
4. **Many rows (20+ from the plus row).** The page stays one column. Rows collapse their
   details strip into one summary line, and the save bar never covers the last row.
5. **Elevation of a panel that overflows, or a KVM that cannot sit at waist height.** The
   elevation draws what fits, marks the overflow in red with the check report's sentence, and
   never draws units outside the rack.

---

### Task 1: Written spec for both screens

**Files:**
- Modify: `docs/ui/screens.md`: map and route table (`#/parts`, with `#/network` redirecting;
  `#/device-preview`), a new "Parts" section replacing "Network", a new "Device preview" section, flows
  ("set up a substation" becomes Parts → Device preview → Checks → Build).
- Modify: `docs/ui/components.md`: new **Part row** (dropdown, part number box, quantity, A
  and B, details strip, row menu with remove and reorder), **Details strip value** (read,
  editing, overridden with reset, invalid), **SFP sub-row**, **Accessory sub-row**, **Add row
  by category** (the plus row), **Collapsible section** (Network fine tuning), **Rack
  elevation** (scale, U ruler, unit block, blank space, waist-height line, off-waist mark,
  overflow), each with sizes, states and accessibility notes.
- Modify: `docs/ui/editing.md`: field inventory for Parts (each field, its file and key from
  design §4, its validation sentence); overrides (equal-to-library is not an override, "Reset
  all"); the plus row's categories; dragging on the elevation reuses "Drag and drop contract"
  with the KVM off-waist rule from design §6.
- Modify: `docs/ui/README.md` status line (M22 added Parts and Device preview).
- Modify: `docs/plan.md` M22 row and design §8 (`docs/superpowers/specs/2026-10-31-part-picking-design.md`): M22 covers the Parts page and the device preview.

- [ ] **Step 1:** Load `impeccable`; shape both screens against design §3 and §6 (layout,
  hierarchy, states). Record the decisions in the three files above.
- [ ] **Step 2:** Self-check: every row in design §3's table and every bullet in §6 and §7 maps
  to a spec line; every Review Focus item has a state in `components.md` or `editing.md`.
- [ ] **Step 3: Commit** `docs(ui): Parts and Device preview screen and component specs`

### Task 2: Parts page in the prototype

**Files:**
- Create: `docs/ui/prototype/screens-parts.js` (`SCREENS.parts`)
- Modify: `docs/ui/prototype/index.html` (script tag), `app.js` or `ui.js` (rail item "Parts"
  in place of Network, `#/network` → `#/parts`), `data.js` (illustrative library parts per
  category including `kvm` and `console`, one substation's rows, overrides, SFP and accessory
  picks), `styles.css` (new component classes only).

- [ ] **Step 1:** Build the page: Field IEDs and Topology, closed **Network fine tuning**,
  the device rows in design §3's default order, MCB and TB brand rows, the plus row, and the
  save bar (the existing component).
- [ ] **Step 2:** Prototype states reachable from the "Prototype states" button: new
  substation (setup card), set up and clean, values overridden (marked, with reset), invalid
  override (inline error, save bar sentence), row with no part number (warning from §7.1), part
  missing from the library (Review Focus 1), sized L1 row (Review Focus 3), 20+ rows (Review
  Focus 4).
- [ ] **Step 3:** `node --check` on every prototype file; open in Chromium with no console
  errors; screenshot each state, light and dark.
- [ ] **Step 4: Commit** `docs(ui): Parts page prototype`

### Task 3: Device preview in the prototype

**Files:**
- Create: `docs/ui/prototype/screens-device-preview.js` (`SCREENS["device-preview"]`)
- Modify: `index.html`, the rail, `data.js` (per-unit placement: panel, top U, MCB tags and
  ratings, terminal strip), `styles.css`

- [ ] **Step 1:** Build the device table (columns from design §6, overridden values marked,
  filter by panel) and one elevation per panel (U ruler, units with tag and height, blank
  space, waist-height line), with check issues above both, linking to the Parts row.
- [ ] **Step 2:** Pointer-event dragging on the elevation, using the same states as the
  board (M19, `editing.md` contract); a KVM dropped off waist height is allowed and marked.
- [ ] **Step 3:** States: clean, warnings from §7.3 (MCB at minimum, 0 W), overflow and a KVM
  that cannot sit at waist height (Review Focus 5), an engine error with no placement.
- [ ] **Step 4:** `node --check`, Chromium with no console errors, screenshots.
- [ ] **Step 5: Commit** `docs(ui): Device preview prototype with the panel elevation`

### Task 4: Critique, audit, review

- [ ] **Step 1:** Run the impeccable critique and audit on both screens; fix the findings, or
  record them in `screens.md` "Decisions from the critique pass" with a reason.
- [ ] **Step 2:** `impeccable detect --json docs/ui/prototype` returns `[]`; final screenshots
  to `/mnt/project-files/a11-screens/m22-parts/`.
- [ ] **Step 3: Commit** `docs(ui): critique pass for Parts and Device preview`; open the PR (A1
  reviews and merges).
- [ ] **Step 4:** A1 puts the design in front of Ali on a decision card (approve, or approve
  with changes). M23 starts after his answer.
