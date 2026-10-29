Next action: re-run the git commands and the gate (STATE.md → Verification), post a readback in your
thread, then ask the lead (ROSTER row 1, currently B1) for role 9's next task. **Nothing is queued:**
every task B9 had is done and every question is answered.

## How to resume (C9 or later)
1. Read `../README.md`, then this folder in the order STATE, NEXT, LESSONS and the latest checkpoint.
   Then read `CLAUDE.md` and `docs/agents.md`.
2. `git fetch origin main && git checkout -B <your thread branch> origin/main`. Don't reuse B9's
   branch history. If your branch name already exists on the remote with merged history, merge its
   tip with `git merge -s ours origin/<branch>` and push without a force: the auto-mode classifier
   refuses `git push -f` (LESSONS).
3. `pip install -e '.[dev]'`, then `python -m ruff check . && python -m ruff format --check .`,
   `python -m mypy`, `python -m pytest -q` (background it: about 6 min) and `python -m pytest -q tests/golden`.
   Compare the results with STATE.md → Verification, and record any drift in LESSONS.md.
4. Post the readback: your name and role, the files you own, the state, your next action, and any drift.

## Likely next work (none assigned; take it only when the lead assigns it)
- **A DC aux-contact choice.** If Ali wants DC aux contacts to follow `mcb_dc` (STATE → Risks), role 2
  adds the choice key, then role 9 switches `aux_contact_line` in `engine/dc_dist.py` to it. Tests
  first, for example `test_dc_aux_contacts_use_the_dc_aux_choice`.
- **New shipped-library data.** When role 3 changes `inrush_a`, `inrush_ms` or `input_v_max` in
  `data/library/`, rerun `tests/unit/engine/test_engine_shipped_library.py`. Update only its
  expectations, keep the goldens on `examples/` (Q38), and tell the lead what moved.
- **A changed engine rule** (anything Ali changes in plan §6): find the rule's module in STATE.md →
  Code map, write the failing test named after the rule, change the code, and keep the goldens unless an
  ADR moves them.

## Rules for any task
- One milestone per PR, a conventional commit (`feat(engine): …`, `test(engine): …`), and the gate
  passing before every commit.
- Tests first, named after the rule (`test_<rule>`). Writer-facing changes to `BuildResult` go to role 10
  first.
- The PR body starts with the two attribution lines from your session's instructions. Copy them from
  there, not from an older PR, and assign it to `alialyami90`. Requesting Ali as reviewer fails
  because he is the PR author, which is harmless. Subscribe to the PR, and when CI is green, message the
  lead's thread. The lead reviews and squash-merges.
- Report each result in the lead's thread with `message_thread`. Ask Ali only on a decision card with
  your recommendation marked, and never ask him to merge.

## Don't do
- Don't edit other roles' files without telling the owner: role 2 has `models/library.py`,
  `models/project.py`, `models/panel.py`, `models/_base.py`, `io/`, `cli.py`, `build.py` and `examples/`.
  Role 8 has `engine/sizing.py` and `engine/layout.py`. Role 10 has `sheets/`, `writer/` and
  `models/sheet.py`. Role 11 has `app/`.
- Don't move golden values without an ADR. Don't settle a spec-vs-code gap by guessing: ask Ali through
  the lead. The next free numbers are Q42 and ADR 0024 (`docs/agents.md` → "Numbers").
- Don't revive `DeviceType.min_branch_mcb_a` as a rating input (ADR 0019 item 4).
- Don't count inrush peaks under `inrush_min_ms` (ADR 0019 item 3).
- Don't switch the default DC MCB away from the iC60N (Q37), and don't drop the FGR-60F or the iC60N
  `dc_float` warnings (Q37, Q41: Ali accepts both).
- Don't put CINC on the DC set: it is group E's AC main (ADR 0023 point 1).
- Don't read `catalogues.mcb` in DC code. Pass `library.catalogues.dc_mcb` to the `engine/mcb.py`
  helpers.
- Don't mark ADRs Accepted: only Ali does that.
