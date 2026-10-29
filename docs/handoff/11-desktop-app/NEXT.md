# NEXT: role 11, Desktop app

**Next action:** apply B4's impeccable polish-audit fixes to the new screens as B1 routes them. If none have arrived, ask B1 for the next task. Nothing past v0.2 is planned yet; B1 is asking Ali.

## How to work
- One PR at a time on `claude/project-thread-apbolc`. Prepare the next PR as a local commit while one is open.
- Restart the branch after each squash merge (force push is denied; never `git rebase origin/main`, which replays the whole history and conflicts):
  ```bash
  C=<commit of the next PR>; git fetch -q origin main claude/project-thread-apbolc
  OLD=$(git rev-parse origin/claude/project-thread-apbolc)
  git checkout -q -B claude/project-thread-apbolc origin/main
  git merge -q -s ours $OLD -m "chore: merge the already-squashed #N branch history (no changes)"
  git cherry-pick $C && git push -u origin claude/project-thread-apbolc
  ```
- After opening a PR:
  1. Subscribe to its activity.
  2. Assign alialyami90.
  3. Message B1 in B1's thread. B1 reviews and merges; never ask Ali to merge.
- CHANGELOG `Unreleased` lines belong to role 7. Pass them through B1.
- Gate before every commit: `ruff check . && ruff format --check .`, `python -m mypy`, then `python -m pytest -q`. The full run takes about 6 minutes, so give it a 600000 ms timeout.
- E2E: a Playwright script in the scratchpad starts a line-based Python bridge over `Api(env=…)` (see LESSONS).

## Open ideas (not ordered; none is asked for yet)
- B4's #146 wording nits on Loose material are still open: the table foot "Quantity is a whole number, or 1 Lot.", and the free-text banner ending "An item that needs power must be added to the library first." (design #142). The polish audit may cover them.
- Add device and Change… list the active library. Showing the project's own library version would avoid parts that the project then refuses.
- Undo for a dropped pending device. Today the confirm dialog is the only guard.

## Don't do
- Business rules in the UI. A missing engine function goes to its owner (agents.md).
- Edit `launcher.py` (role 6), the spec, the plan structure or ADRs (role 1), CHANGELOG (role 7), or other roles' modules.
- Commit `.xlsx` files, or the scratchpad E2E scripts and screenshots.
