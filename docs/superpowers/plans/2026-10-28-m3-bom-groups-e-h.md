# M3 BOM Groups E–H, HWIO and Assembly Implementation Plan

**Goal:** Extend every cabinet's BOM from groups A–D to A–H: AC and DC distribution, terminal strips, grounding busbars, HWIO per row and panel, and revision marks, in final line order.

**Architecture:** Pure functions in `bomgen.engine` (ADR 0005), each returning `BomItem`s that `pipeline.build()` flattens into `PanelBom.lines` (ADR 0014). The pipeline runs in two passes: groups A–F of every panel, then groups G–H, because XDIN defaults to the substation's HWIO total. SR.NO and separators follow from line order (`BomTable.separators_before`), so assembly only marks revisions.

**Tech Stack:** Python 3.12, pydantic v2 (frozen models), pytest.

**Spec:** `docs/spec/generator-spec-v2.md` → "Derivation rules" (DC distribution, AC distribution, Breaker part numbers, Terminal block quantities, HWIO points), "Tag naming conventions → Circuit and strip codes", "Data model and generation order" steps 6–11. Plan M3, Q6, Q22, Q34.

## Global Constraints

- Engine never imports XlsxWriter, openpyxl or `models/sheet.py`; it never writes files.
- MCB rows: tag `<PREFIX>-<code>`, description `<r>A, 2P MCB For <load>`, model and code `A9F742<rr>` from the catalogue; the load is the tag without the prefix, `-` → `_`.
- Ratings are the smallest catalogue size at or above the need; a missing size is an `EngineError`.
- Spare counts are panel options (`dc_spare_branches_per_feed`, `ac_spare_branches`).
- Terminal quantities without a stated rule come from the panel kind (Q6); `terminal_overrides` wins and naming an absent strip is an `EngineError`.
- Console panels' aux contacts carry HWIO 0 (Q34).

## Review Focus

1. A single-fed DC load in a panel without change-over diodes → `EngineError`.
2. DC main with `main_mcb_override_a` → the override, else ΣQ rounded up with a 6 A minimum.
3. X4-DC rounding to a multiple of 8 only in network cabinets.
4. XDIN = Σ HWIO of every panel, and only in a panel with DI slot strips.
5. Revision marks naming a tag that no line has → `EngineError`.

---

### Task 1: Group E AC distribution (step 6)

**Files:** Create `src/bomgen/engine/{mcb.py,ac_dist.py}`; Test `tests/unit/engine/test_engine_ac_dist.py`.

**Produces:** `mcb.rating_at_least`, `mcb.rating_above`, `mcb.mcb_line`, `mcb.aux_contact_line`, `mcb.alarms_wired`; `ac_dist.AcCircuits(items, mcbs)`, `ac_dist.ac_distribution(panel, library, ventilation)`.

- [x] Tests: `test_branches_in_load_order_with_one_spare`, `test_cinc_is_16a_with_a_10a_socket`, `test_console_without_fans_has_lamp_thermostat_spare_all_1a`, `test_spare_count_is_a_panel_input`, `test_mcb_count_includes_cinc`, `test_breaker_rows_carry_catalogue_make_and_code`.
- [x] Fail → implement → pass → commit `feat(engine): group E AC distribution`.

### Task 2: Group F DC distribution (step 7)

**Files:** Create `src/bomgen/engine/dc_dist.py`; Test `tests/unit/engine/test_engine_dc_dist.py`.

**Produces:** `FedLoad`, `DcCircuits(items, branches_per_feed, qcods, design_current_a, main_a)`, `single_fed_loads`, `unit_current`, `branch_rating`, `dc_distribution(panel, library, constants, rows, fed, change_over)`.

- [x] Tests: `test_one_branch_per_supply_on_each_feed_same_n`, `test_spare_branches_per_feed_is_a_panel_input`, `test_branch_rating_is_min_rating_or_current_with_margin`, `test_main_mcb_is_next_size_above_design_current_minimum_6a`, `test_main_mcb_override_wins`, `test_alarmed_branches_add_aux_contacts`, `test_single_fed_load_goes_through_qcod_with_a_spare`, `test_single_fed_load_without_change_over_is_an_error`, `test_console_aux_contacts_carry_no_hwio`.
- [x] Fail → implement → pass → commit `feat(engine): group F DC distribution`.

### Task 3: Group G terminal strips (step 8)

**Files:** Create `src/bomgen/engine/terminals.py`; Test `tests/unit/engine/test_engine_terminals.py`.

**Produces:** `StripInputs(ventilation, ac_mcbs, dc_branches_per_feed, change_over, annunciator_feeds, xdin_default)`, `terminal_strips(panel, library, rows, inputs)`.

- [x] Tests: the spec table per cabinet kind, X3-AC = 2 × AC MCBs, X4-DC rounding, XPS / XSD / X4-COD / X-ANN presence, overrides; device strips XDIP per DI slot from `first_slot`, XDIN from the HWIO total, XRTAC per serial port, order before XIP.
- [x] Fail → implement → pass → commits `feat(engine): group G fixed terminal strips`, `feat(engine): device terminal strips (XDIP, XDIN, XRTAC)`.

### Task 4: Group H, revision marks, `first_nn`

**Files:** Create `src/bomgen/engine/{grounding.py,assemble.py}`; Modify `src/bomgen/engine/units.py`; Tests `test_engine_grounding.py`, `test_engine_assemble.py`, `test_engine_tags.py`.

- [x] Grounding rows from `options.grounding_busbars` (tag and description, qty 1); unknown busbar → `EngineError`.
- [x] `mark_revisions(panel, lines)` sets `revised` from `revision.highlight`.
- [x] A row's `first_nn` restarts its type and level count (ADR 0013).

### Task 5: Pipeline and golden

**Files:** Modify `src/bomgen/engine/{pipeline.py,kits.py}`; Create `tests/golden/{expected_groups_e_h.py,test_engine_groups_e_h.py}`; Modify `tests/unit/engine/test_engine_pipeline.py`.

- [x] Two-pass `build()`; the loose table title from `loose_material.title`.
- [x] Golden: every E–H row of 001, 002, 003 and WS citing the workbook rows; Q1.1–Q1.13, CINC/Q1/Q2 ratings, aux contact counts, the terminal table, HWIO 17/17/6 and XDIN 40, 71 lines on 001, separators before E–H.
- [x] ruff, mypy, pytest; commit `test(golden): groups E–H of the example cabinets`.
