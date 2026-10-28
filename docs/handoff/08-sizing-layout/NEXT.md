# NEXT: role 8

Next action: read A1's reply in A1's thread (see STATE "Blockers and waiting on") to the request
for role 8's next engine task, and start that task from a fresh branch off `origin/main`.

## Tasks, in priority order

1. **Show `position` in the plan's override example** (A2's review follow-up on #100; A1 said
   to ride the next role-8 PR, not a PR of its own).
   - File: `docs/plan.md` section 3, the `layout.overrides` example (A2 owns section 3; A2
     suggested the line in review and A1 asked role 8 to add it).
   - Done when an example line such as `- { device: gps, panel: 1, position: 1 }  # 1 = top
     rack device` (`panel` is the integer panel number) is in the next role-8 PR.
   - If A1 has no role-8 PR coming by the next checkpoint, ask A1 whether to send it alone.
2. **Next engine work from A1** (M17 or M18). A1's likely candidate is the loose-material
   "comes with" children (M18). The plan gives the M18 engine to A9, so confirm the
   owner with A1 before starting.
   - For each task: tests first, named after the rule (`test_r<N>_...`); goldens unchanged unless
     Ali directs; a dated ADR 0013 note if an R-rule changes; one milestone per PR; the gate
     passes; open the PR for A1.

## Don't do
- Placing pins before the automatic fill. It was ruled out: A1 agreed on 2026-10-28 to keep R7's
  fill-then-overrides, because pins-first re-flows other devices (see LESSONS).
- Editing `docs/spec/` (Ali's), UI files (`src/bomgen/app/ui/`, A11 and A4) or `models/` without A2's review.
- Committing `.xlsx` output.
