Next action: re-run the git commands and the gate (STATE.md → Verification), then ask A1 in the "A1 - Lead developer" thread for the next role-9 task.

All assigned work is merged (STATE.md → Merged). A1 assigns new work. The candidates
below wait for A1's go-ahead or for another PR, so none of them starts unasked. Find A1's
thread with `list_threads`. If A1 assigns nothing, start task 1 once #130 has merged,
and say so in A1's thread.

## 1. Check the engine against the shipped library after M14 (#130)
- Goal: confirm that branch sizing and the `dc_float` checks give sensible results with
  psa-devices 1.1.0's datasheet data. Milestone M15 follow-up. Code change only if a
  defect shows.
- Files: none to change at first. If a defect shows: `src/bomgen/engine/dc_dist.py`,
  `src/bomgen/checks.py`, `tests/unit/engine/test_engine_dc_dist.py`, `tests/unit/engine/test_checks.py`
  (all role 9). The library data is A3's (`data/device-db/`, the shipped library), and
  `examples/` is A2's.
- Depends on: A3's #130 merged (A1 merges).
- Also ask A1 and A2 whether the engine should refuse a DC-only MCB set (C60H-DC) on AC
  branches (`ac_dist.py`, `mcb.py`), or whether A2's model check is enough.
- Acceptance: the spec, "Derivation rules → DC distribution (group F)" and "Breaker part
  numbers"; ADR 0019 items 1–7. The goldens stay as they are (Q38: the example keeps its
  values).
- Tests first, only if a defect shows, named after the rule, e.g.
  `test_branch_is_smallest_rating_meeting_running_inrush_and_floor`.
- Done: the gate passes, `python -m pytest tests/golden` passes with unchanged values, and
  a PR is open for A1, or A1 is told that nothing needed changing.

## 2. Accept ADR 0016 and ADR 0019
- Goal: set "Status: Accepted" once A1 agrees. Milestones M7 and M15 are done.
- Files: `docs/decisions/0016-*.md`, `0019-*.md` and their rows in `docs/decisions/README.md`.
  Ask A1 first, because the README index is shared.
- Done: a docs-only PR is open for A1.

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
  ask Ali through A1 (next free Q39, ADR 0023: `docs/agents.md` → "Numbers").
- Don't revive `DeviceType.min_branch_mcb_a` as a rating input (ADR 0019 item 4).
- Don't count inrush peaks under `inrush_min_ms` (Ali, 2026-10-28; ADR 0019 item 3).
- Don't switch the default DC MCB away from the iC60N (Q37: "Keep iC60N as default").
- Don't apply `stash@{0}` (see STATE.md). Don't ask Ali to merge: A1 merges.
