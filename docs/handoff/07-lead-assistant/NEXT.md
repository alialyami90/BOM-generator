# NEXT: role 7

**Next action:** one docs PR adding the 9 missing `tests/unit/README.md` rows (STATE.md), then
the standing post-merge pass (task 1) from `fd4d7fd`; ask B1 whether to reword README "Status"
now that v0.2 has shipped.

## 1. Standing: post-merge pass
- At every wake, `git fetch origin main` and `git log --oneline fd4d7fd..origin/main` (move the
  sha forward after each pass) for merges the lead did not report (LESSONS L11).
- For each non-docs PR, read its description (`pull_request_read get`) and add one
  `[Unreleased]` entry in Keep a Changelog style (L1, L12, L13). Batch them; B1 says when to open
  the PR (L2).
- Run the L4 row loop and the L5 link loop; add a row for each new test module.
- Report stale lines in other agents' files to B1 (L6); don't edit them.

## 2. Next release (when B1 calls it)
- Move `[Unreleased]` under `## [x.y.z] - date`, leave an empty `[Unreleased]` on top, update the
  link refs (`[Unreleased]` → `vX...HEAD`, new `[x.y.z]` → `vPrev...vX`). Pattern: #193, #209.
- Open it before the bump; B6 opens the bump PR after it merges. The bump gets no entry (L12).

## Don't do
- Don't edit `docs/plan.md`, `docs/agents.md`, `CLAUDE.md`, `docs/backlog.md`, `docs/ui/`,
  `docs/decisions/` or code unless the lead assigns the exact lines.
- Don't approve or merge PRs; don't request Ali as reviewer (assign `alialyami90`).
- Don't run `bomgen layout --force` or project imports on the real `examples/`.
