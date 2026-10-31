# M25 AC branch MCB per VAC device Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every panel unit with `supply_type: VAC` gets its own AC branch MCB in group E, after the
socket and before the spare, sized from the AC catalogue the way DC branches are sized.

**Architecture:** `branch_sizing` takes the catalogue and the AC/DC trip multiple as inputs so the
AC side reuses it. `ac_distribution` receives the panel's device rows and the constants, adds one
`C<n>` per VAC unit, and returns `BranchMcb` records (feed None, unit tag set) beside its BOM items.
Terminal X3-AC (2 per AC MCB) and the AC aux contacts follow from the existing counts.

**Tech Stack:** Python 3.12, pydantic v2, pytest, ruff, mypy.

**Spec:** `docs/spec/generator-spec-v2.md` "Derivation rules → AC distribution (group E)" and
"Generation order" step 6; ADR 0019 (branch sizing), ADR 0023 (AC set is `catalogues.mcb`). Ali's
decision 2026-10-31 (card from A1): "one AC branch MCB per VAC unit, after the socket".

## Global Constraints

- Gate before every commit (CLAUDE.md). TDD, tests named after the rule.
- The example has no VAC device in any panel (checked 2026-10-31 against `examples/`), so no golden
  value may move: group E counts, AC aux contacts, X3-AC quantities and the check report stay as
  they are. If one moves, stop and tell A1.
- Based on main after the M24 engine PR (it adds `BranchMcb.unit_tag` and `feed`).
- New ADR `docs/decisions/0025-ac-branch-per-vac-device.md`, Proposed; plan row M25 and Q52 in
  `docs/plan.md`; spec hand-edited under Ali's decision, said so in the commit (as #234).

## Decisions this plan makes (A1 approved 2026-10-31; Q52 records them)

1. **Order:** lamp, fan/thermostat circuits, thermostat-only circuits, socket, then one branch per VAC
   unit in group B order (A side before B on a pair, unit number order), then the spare(s).
2. **Rating:** `branch_sizing` with `catalogues.mcb`, the AC magnetic multiple
   (`magnetic_multiple`), `constants.ac_v` when the part has no `voltage_v`, the same floor
   (`min_branch_mcb_a`) and `inrush_min_ms`.
3. **Spare rating:** stays the largest housekeeping branch (today's rule), so a big VAC load does not
   enlarge the spare. (DC takes the largest branch; recommendation keeps AC spares as the spec says.)
4. **CINC:** today's rule (6 A, or above the socket), raised to the smallest catalogue rating above
   the largest branch and at least the panel's AC design current (Σ current factor × W / V over the
   VAC units). This is the one rule Ali's answer does not cover; recommended because CINC must carry
   the new loads.
5. **Aux contacts:** a VAC unit with `alarm_on_branch_mcb` adds its `C<n>` to the AC aux contact
   list, as DC branches do.
6. **Load text:** the unit's tag without the panel prefix, as the DC branches name theirs.

## Review Focus

1. A redundant VAC entry: one branch per side, each in its own panel — Task 2.
2. A VAC unit with `power_supplies` > 0 is impossible (library rule) — no test needed; a VAC unit
   excluded from power (`excluded_from_power`) gets no branch — Task 2.
3. The WS console panel (no fans): order lamp, TH-1, VAC units, spare — Task 2.
4. An AC catalogue with no trip curve: sized from running current and the floor, like DC — Task 1.
5. A derived part overridden to VAC (ADR 0024) gets a branch and the preview's ps1 — Task 3.

---

### Task 1: `branch_sizing` for either catalogue

**Files:** Modify `src/bomgen/engine/dc_dist.py` (`branch_sizing`, `_trip_multiple`); move both to
`src/bomgen/engine/branches.py` only if the import from `ac_dist` would cycle. Test
`tests/unit/engine/test_engine_dc_dist.py` (existing sizing tests must pass unchanged).

**Produces:** `branch_sizing(device, library, constants)` unchanged in signature: a part with
`supply_type: VAC` uses `catalogues.mcb` and its AC multiple, and the AC system voltage when
`voltage_v` is None (simpler than an `ac` flag, since the part's supply type already says it).

- [ ] Failing tests: `test_an_ac_branch_is_sized_from_the_ac_catalogue` (250 W at 230 V, factor
  1.3 → 1.41 A running → 2 A); `test_an_ac_branch_uses_the_ac_magnetic_multiple` (inrush 40 A, C
  curve AC multiple 5 → 8 A need → 10 A).
- [ ] Implement; gate; commit `refactor(dc-dist): branch sizing for the AC catalogue too`.

### Task 2: One AC branch per VAC unit

**Files:** Modify `src/bomgen/engine/ac_dist.py` (`ac_distribution` signature and `AcCircuits`),
its caller in the pipeline, `src/bomgen/engine/terminals.py` only if `ac_mcbs` is not already the
MCB count. Test `tests/unit/engine/test_engine_ac_dist.py`, `test_engine_terminals.py`.

**Produces:** `ac_distribution(panel, library, ventilation, rows, constants) -> AcCircuits`;
`AcCircuits.branch_mcbs: list[BranchMcb]` (VAC units only), collected into
`BuildResult.branch_mcbs` after the DC ones.

- [ ] Failing tests: `test_each_vac_unit_gets_a_branch_after_the_socket` (forced panel with socket
  and a VAC unit → C1 lamp, C2, C3 fan circuits, C4 TH-3, C5 socket 10 A, C6 the unit, C7 spare 2 A);
  `test_a_redundant_vac_entry_gets_one_branch_per_side`; `test_a_vac_unit_raises_cinc_above_its_branch`
  (unit sized 10 A → CINC 16 A); `test_a_vac_unit_with_alarm_adds_an_ac_aux_contact`;
  `test_x3_ac_counts_the_vac_branches` (2 per AC MCB); `test_no_vac_unit_leaves_group_e_unchanged`
  (today's example panel rows equal).
- [ ] Implement; `pytest tests/golden` unchanged; gate; commit
  `feat(ac-dist): one AC branch MCB per VAC unit`.

### Task 3: Check report, preview, docs

**Files:** `src/bomgen/checks.py` (branch lines already iterate `branch_mcbs`; check the AC ones say
"AC"), `src/bomgen/engine/preview.py` (ps1 from the AC record), docs.

- [ ] Failing tests: `test_an_ac_branch_mcb_is_reported_with_its_numbers`;
  `test_preview_gives_a_vac_unit_its_ac_mcb` (ps1 `PSA1-C6`, ps2 None).
- [ ] Implement.
- [ ] Docs: ADR 0025 (Proposed) with decisions 1–6; spec "AC distribution (group E)" bullet for the
  VAC branches and CINC, step 6 wording; `docs/plan.md` M25 row and Q52 (Ali's answer plus 1–6);
  CHANGELOG.
- [ ] Gate; commit `docs: ADR 0025 AC branch per VAC device`; open the PR.
