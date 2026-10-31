# M26 Device nameplates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every panel BOM gets one "Device nameplate" row whose quantity is the panel's tagged
device units, and the workbook gets a "Nameplates" sheet listing each plate's text per panel.

**Architecture:** The plate text is the short tag the MCB rows already print (`L2_ESW_A01`):
`dc_dist._unit_name` moves to `engine/tags.py` as `short_tag` and both callers use it. A new
`engine/nameplates.py` lists a panel's plates from its expanded group B rows and makes the BOM row
from a new optional housekeeping role `catalogues.housekeeping.nameplate`, so the part follows the
housekeeping brand choice (ADR 0017) like the lamp and fans. `BuildResult` carries the plates per
panel; `sheets/nameplate_sheet.py` lays them out.

**Tech Stack:** Python 3.12, pydantic v2, openpyxl, pytest, ruff, mypy.

**Spec:** Ali's decision (relayed by A1, 2026-10-31): "one Device nameplate commodity row per panel,
qty = the panel's tagged devices (every unit with a tag, including DIN rail; L1/L2 per unit); a new
Nameplates sheet with every plate's text per panel; the text is the MCB rows' short tag".

## Global Constraints

- Gate before every commit (CLAUDE.md). TDD, tests named after the rule. Writer tests reopen the
  file.
- Based on main after M25. ADR `0026-device-nameplates.md` (Proposed) and Q53 in `docs/plan.md`,
  assuming M25 takes ADR 0025 and Q52 and nothing else lands first; take the next free numbers at
  the time.
- Spec values cited by the goldens must not move: power totals 2,177.5 W DC and 1,090.3 W AC,
  heat totals, airflow results, MCB counts and ratings, terminal quantities, HWIO totals.
- Spec hand-edited under Ali's decision, said so in the commit.

## Decisions this plan makes (A1 approved 2026-10-31; Q53 records them)

1. **Which units get a plate:** every group B unit whose tag is set (`DeviceRow.unit_tags`), DIN
   rail included, one per unit of a multi-quantity row. Kit children (blank designation),
   housekeeping parts (IL, FAN-n, TH-n), MCBs, strips and loose items get none. The example's
   WS console therefore gets `SRV/OAS/EAS`, `MONITOR` and `Keyboard & Mouse` (its tag overrides,
   printed as written).
2. **Where the row goes:** the last row of group H, after the busbars. Recommended because it adds
   one SR.NO at the end of each panel and moves no other row, so no Power Consumption reference,
   merge or SR.NO changes. The alternative, the end of group C, renumbers every later row of every
   panel and moves every `='1'!C8`-style reference in the goldens.
3. **The part:** a new optional role `catalogues.housekeeping.nameplate` (a `HousekeepingRef`) and
   the same field on `HousekeepingBrand`. When it is unset there is no row and no sheet, so other
   libraries keep building unchanged. The example library (`examples/library.yaml`) sets the role
   to NAMEPLATE-0828805 (Phoenix Contact US-EMLP), researched by A4 with its device-db record, so
   the goldens show the feature (A1, 2026-10-31). The library part is a plain `accessory` (no new category,
   because the role, not the category, picks it). A4 adds the part and the role to
   `data/library` and `examples/library.yaml`.
4. **Row text:** tag empty, description "Device nameplate" (or the part's description template),
   qty the plate count, make, model and ordering code from the part, no HWIO, no power line. A
   panel with no tagged unit gets no row.
5. **Sheet:** "Nameplates" (`output.sheet_names.nameplates`), after Loose Material and before Power
   Consumption, A4 portrait, the panel BOM's title block and header and footer (as Loose Material),
   columns SR.NO, PANEL (the cabinet number), PLATE TEXT and DEVICE (the group B description),
   one block per panel in panel order, SR.NO continuing. It is issued under the first panel's
   document. It is written only when some panel has a plate.

## Golden values that move (list them in ADR 0026)

- `tests/golden/expected_groups_e_h.py`: group H of each panel gains the nameplate row, at the
  next SR.NO: psa1 qty 11, psa2 qty 11, psa3 qty 3, ws qty 3.
- `tests/golden/test_workbook.py`: the sheet list gains "Nameplates" after "Loose Material", and
  each BOM sheet's last row and print area grow by one row. The new sheet's expected cells go in a
  new golden module citing this ADR.
- Nothing else: Power Consumption, Heat Dissipation and Heat Calculations cells, the check report
  and the HWIO totals stay as they are. If one moves, stop and tell A1.

## Review Focus

1. The short tag comes from one function only: `dc_dist` and `nameplates` both call
   `tags.short_tag` (Task 1).
2. A tag override with spaces or `/` is printed as written; the same text appears on the MCB row
   and the plate (Task 2).
3. No `nameplate` role: no row, no sheet, every golden unchanged (Task 2, Task 4).
4. Revision marks: a new nameplate row on a rebuilt revision is marked like any new row
   (`compare_with_previous`) — Task 3.
5. Hand-written and generated panels count the same way (both go through `expand_devices`) —
   Task 2.

---

### Task 1: One short-tag function

**Files:** Modify `src/bomgen/engine/tags.py` (add `short_tag`), `src/bomgen/engine/dc_dist.py`
(use it, drop `_unit_name`). Test `tests/unit/engine/test_engine_tags.py`.

- [ ] Failing test `test_short_tag_drops_the_panel_prefix_and_uses_underscores`
  (`PSA1-L2-ESW-A01` with prefix `PSA1` → `L2_ESW_A01`; untagged → the part's model).
- [ ] Move the function; gate (goldens unchanged); commit
  `refactor(tags): one short-tag function for MCB rows and nameplates`.

### Task 2: The nameplate row

**Files:** Modify `src/bomgen/models/library.py` (`Housekeeping.nameplate`,
`HousekeepingBrand.nameplate`), `src/bomgen/models/bom.py` (`PanelNameplates`,
`BuildResult.nameplates`); create `src/bomgen/engine/nameplates.py`; wire it in
`engine/pipeline.py` after grounding. `bomgen schema`. Test `tests/unit/engine/test_engine_nameplates.py`.

- [ ] Failing tests: `test_nameplate_qty_is_the_panels_tagged_units` (psa1 → 11);
  `test_nameplate_text_is_the_mcb_short_tag` (psa1 plates equal the Q1.n load names, in order);
  `test_din_rail_units_get_a_plate` (EXT_FW_A);
  `test_kit_children_and_housekeeping_get_no_plate`;
  `test_nameplate_is_the_last_row_of_group_h`;
  `test_no_nameplate_role_means_no_row` (example library without the role → BOM equal to today).
- [ ] Implement; update `expected_groups_e_h.py` with the four rows (cite ADR 0026); gate;
  commit `feat(engine): one device nameplate row per panel`.

### Task 3: The Nameplates sheet

**Files:** Modify `src/bomgen/models/project.py` (`SheetNames.nameplates`),
`src/bomgen/sheets/workbook.py`; create `src/bomgen/sheets/nameplate_sheet.py`. Test
`tests/unit/sheets/test_nameplate_sheet.py`, `tests/golden/test_workbook.py`.

- [ ] Failing writer tests (reopen the file): the sheet sits after Loose Material; title block and
  header row as the BOM sheets; one row per plate with SR.NO, PANEL, PLATE TEXT, DEVICE; A4
  portrait, rows 1–2 repeated, header and footer strings; no sheet without plates.
- [ ] `test_a_new_nameplate_row_is_marked_revised` (revision round trip).
- [ ] Implement; update the workbook golden; gate; commit `feat(sheets): Nameplates sheet`.

### Task 4: Docs

- [ ] ADR 0026 (Proposed): decisions 1–5 and the golden values that move.
- [ ] Spec: Workbook map row; "How each panel BOM groups its materials" group H text and example;
  a "Nameplates sheet" section; Inputs (the housekeeping role, `sheet_names.nameplates`);
  Generation order step 9 ("…then the device nameplate row") and step 12 (the sheet after Loose
  Material).
- [ ] `docs/plan.md` M26 row and Q53; CHANGELOG.
- [ ] Gate; commit `docs: ADR 0026 device nameplates`; open the PR.
