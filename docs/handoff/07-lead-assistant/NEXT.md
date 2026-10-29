# NEXT: role 7

**Next action:** run the resume steps in `../README.md`, then `git log --oneline 1678343..origin/main`.
If only docs/handoff PRs are listed (#212 and later handoff checkpoints), there is nothing to
do: wait for the lead. Otherwise start task 1.

## 1. Standing: post-merge pass (every wake)
1. `git fetch origin main && git checkout -B claude/<your-branch> origin/main`.
2. `git log --oneline 1678343..origin/main` (move this sha forward in STATE.md after each pass).
   Don't wait for the lead to report merges (L11).
3. For each non-docs PR: `pull_request_read` with method `get` for its description, and
   `git show -s --format=%B <sha>` for the squash message. Add one entry under `[Unreleased]`
   in Added / Changed / Fixed, newest first, PR number in brackets, no agent names, about 78
   columns (L1, L12, L13). Skip docs, handoff, chore, bump and internal-refactor PRs.
4. New test module? Run the L4 loop and add a row to `tests/unit/README.md` or
   `tests/golden/README.md` with its milestone and what it checks (read its docstring and test
   names).
5. A milestone done or a CLI command changed? Update README Status or Usage, and run the new
   command on a scratch copy of `examples/` with `BOMGEN_LIBRARY_HOME` and `BOMGEN_WORKSPACE`
   pointed at scratch folders (L3).
6. Run the L5 link loop and the gate (`ruff check . && ruff format --check .`, `python -m mypy`,
   `python -m pytest -q -p no:cacheprovider`, about 5 min).
7. Ask the lead whether to open now or batch (L2). Then open one docs PR (L7 mechanics), assign
   `alialyami90`, `subscribe_pr_activity`, and message the lead's thread with the number.
8. Report stale lines in other roles' files to the lead with path, line and evidence (L6).

## 2. Next release (when the lead calls it)
- Rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD` and put a new empty `## [Unreleased]`
  above it.
- Link refs: `[Unreleased]: .../compare/vX.Y.Z...HEAD`, add `[x.y.z]: .../compare/vPREV...vX.Y.Z`.
- Word the last PR's entry from its final squash message. Patterns: #193, #209.
- Open it before the bump; the release role opens the bump after it merges. The bump gets no entry.
- After the release, update README Status ("vX.Y.Z is released"; move finished milestones from
  any "In progress" list to "Done in vX").

## 3. Handoff
- Before a context reset or when asked: update STATE.md, NEXT.md, LESSONS.md (append only), add
  `checkpoints/<date>.md`, update row 7 of `../ROSTER.md`, and open a docs-only PR for the lead.

## Don't do
- Don't edit `docs/plan.md`, `docs/agents.md`, `CLAUDE.md`, `docs/backlog.md`, `docs/spec/`,
  `docs/ui/`, `docs/decisions/` or code unless the lead assigns the exact lines.
- Don't approve or merge PRs; don't request Ali as reviewer (assign `alialyami90`).
- Don't run `bomgen layout --force` or project imports on the real `examples/`.
- Don't commit `.xlsx` outputs; build into `out/` or a scratch folder.
- Don't message a retired lead thread (L14).
