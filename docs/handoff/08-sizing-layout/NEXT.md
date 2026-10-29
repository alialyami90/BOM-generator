# NEXT: role 8

Next action: after the README resume steps, post a readback in your thread, then tell the lead
(see STATE "Lead") that C8 is live and ask for role 8's next engine task. Until one comes, idle.
Don't invent work in role 8's files.

## Tasks, in priority order

1. **Wait for and take the lead's next engine task.** Likely kinds:
   - a layout fix from the desktop app's Panels board or equipment editor (A11's callers in MAP.md);
   - a new R-rule or a rule change Ali asks for (sizing, fill, plates, overrides).
   For each task:
   1. Read the relevant R-rule in ADR 0013 and the design's section 4. If code and spec disagree,
      ask Ali on a decision card with a recommendation before changing either (CLAUDE.md).
   2. Write the failing test first, named after the rule (`test_r<N>_...`), in role 8's test files.
   3. Keep the goldens unchanged unless Ali directs. If a golden must move, ask Ali first.
   4. If an R-rule changes, add a dated amendment to ADR 0013 (as R5 and R7 have).
   5. If a model field is needed, propose it to role 2 (models/ and io/ are theirs) and wait for
      their review; role 8 never edits models/ alone.
   6. Grep the callers in MAP.md; if the change alters their values, run `tests/unit/app/` and tell
      role 11 (and role 2 for `io/edit.py`).
   7. Run the gate (ruff, format, mypy, full pytest), one milestone per PR, conventional commit,
      open the PR for the lead, subscribe to it, fix CI and review comments until it merges.
2. **At your own handoff**, update STATE, NEXT, append to LESSONS, add a dated checkpoint, set your
   ROSTER row, and send it as a docs-only PR to the lead.

## Don't do
- Placing pins before the automatic fill. It was ruled out: A1 agreed on 2026-10-28 to keep R7's
  fill-then-overrides, because pins-first re-flows other devices (see LESSONS).
- Counting `l2_ports` per unit without asking Ali (R2 says per entry).
- Editing `docs/spec/` (Ali's), UI files (`src/bomgen/app/ui/`, roles 11 and 4), `models/`/`io/`
  without role 2's review, or `cli.py`/`build.py` without role 2's or the lead's leave.
- Asking Ali to merge; the lead squash-merges. Asking Ali in plain text; use a card with a recommendation.
- Committing `.xlsx` output.
