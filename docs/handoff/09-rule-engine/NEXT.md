Next action: re-run the git commands and the gate (STATE.md → Verification), then check whether A3's Q38 follow-up PR (it adds `data/library/psa-devices.yaml`) has merged, and start task 1 if it has.

A1 assigned tasks 1 and 2 on 2026-10-28; task 2 is done (#154). Task 3 waits on Ali. Find A1's thread with
`list_threads` and report each result there.

## 1. Check the engine against the shipped library (WAITING on A3's Q38 follow-up PR)
- Goal: confirm that branch sizing and the `dc_float` warnings give the expected results
  with the shipped `data/library/psa-devices.yaml`. This is an M15 follow-up. Change code
  only if a defect shows.
- Expected (A1, 2026-10-28):
  - the SEL-3555, SEL-3355 and spare branches come out at 6 A;
  - the goldens stay as they are (Q38: the spec example keeps its values).
- Files: none to change at first. If a defect shows: `src/bomgen/engine/dc_dist.py`,
  `src/bomgen/checks.py`, `tests/unit/engine/test_engine_dc_dist.py`,
  `tests/unit/engine/test_checks.py` (all role 9). The library data is A3's
  (`data/library/`, `data/device-db/`), and `examples/` is A2's.
- Depends on: A3's Q38 follow-up PR, merged by A1. Find it with `list_pull_requests`.
- Acceptance: the spec, "Derivation rules → DC distribution (group F)" and "Breaker part
  numbers"; ADR 0019 items 1–7.
- Tests first, only if a defect shows, named after the rule, e.g.
  `test_branch_is_smallest_rating_meeting_running_inrush_and_floor`.
- Done: the gate passes, `python -m pytest tests/golden` passes with the values unchanged,
  and either a PR is open for A1 or A1 is told that nothing needed changing.

## 2. Separate AC and DC MCB choices: engine side (DONE, #154)
- Merged at f319f64. Nothing left; see STATE.md → Merged.

## 3. Q30 and Q31 answers (when Ali answers, through A1)
- Goal: implement any rule Ali changes. Milestone: whichever A1 names, one PR.
- Files: `src/bomgen/engine/kits.py` (loose order, Q30); `network.py`, `housekeeping.py`,
  `thermal.py` (Q31 items 2–4); goldens only with an ADR.
- Tests first, e.g. `test_loose_table_lists_project_items_then_device_loose_items` (exists;
  change it to the new order), `test_cable_managers_one_per_switch_and_patch_panel_unit`.

## Don't do
- Don't edit other roles' files without telling the owner: A2 has `models/library.py`,
  `models/project.py`, `models/_base.py`, `io/`, `cli.py`, `build.py` and `examples/`. A8 has
  `engine/sizing.py` and `layout.py`. A10 has `sheets/` and `writer/`. Tell A10 before
  changing the shape of `BuildResult`.
- Don't move golden values without an ADR. Don't settle a spec-vs-code gap by guessing:
  ask Ali through A1 (next free Q40, ADR 0024: `docs/agents.md` → "Numbers").
- Don't revive `DeviceType.min_branch_mcb_a` as a rating input (ADR 0019 item 4).
- Don't count inrush peaks under `inrush_min_ms` (Ali, 2026-10-28; ADR 0019 item 3).
- Don't switch the default DC MCB away from the iC60N (Q37: "Keep iC60N as default").
- Don't open a PR that marks ADRs Accepted. Only Ali accepts ADRs, and A1 offers him a
  batch card for all the Proposed ones (A1, 2026-10-28).
- Don't apply `stash@{0}` (see STATE.md). Don't ask Ali to merge: A1 merges.
