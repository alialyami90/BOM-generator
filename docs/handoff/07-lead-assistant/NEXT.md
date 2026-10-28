# NEXT: role 7

**Next action:** rerun the handoff README's step-4 checks, then message A1 that the docs lag
#88–#129 and #133 and, on its go-ahead, open one docs-only PR from `origin/main` for them.

## 1. Docs pass for #88–#129 (v0.2 work, M12–M18)
- Files (all mine): `CHANGELOG.md`, `README.md`, `tests/unit/README.md`.
- Depends on: A1's go-ahead; ask whether #130 and #131 should be waited for (A1 has
  preferred one PR over a range, LESSONS L2).
- Do:
  - CHANGELOG `[Unreleased]`: every merged PR number from #88 on appears, newest first, Added
    vs Changed; PRs of one milestone step may share an entry citing all numbers (LESSONS L1). Read each with `git show --stat --format=%B <sha>`.
  - README Status: add the v0.2 milestones that are done or in progress per
    `docs/backlog.md` (A1's file) and `docs/plan.md` → "M12–M18 (v0.2)"; fix "Next:".
  - README Usage: `bomgen library export`, `export-csv`, `import-csv` (from `--help`),
    each run once on a scratch copy of `examples/` (LESSONS L3).
  - tests/unit/README.md: one row per missing module listed in STATE.md, milestone and
    "what it checks" from the module docstring and test names.
- Acceptance: the coverage loop prints nothing; link check prints nothing; every merged PR
  number since `39fddc4` appears in CHANGELOG; README commands ran on a copy.
- Tests to write first: none (docs only); the CLAUDE.md gate must still pass with
  2414 or more tests.
- Done when: gate passes, docs-only PR is open, assigned to alialyami90, A1 told the number.

## 2. Standing: post-merge pass
- At every wake, run `git log --oneline <last covered sha>..origin/main` for merges A1 did not
  report (LESSONS L11), then ask A1 before opening a pass (L2).
- Links, ADR index against `docs/decisions/`, stale lines in other agents' docs → report
  to the owner via A1, don't edit (LESSONS L6). One changelog entry per merged PR.

## 3. Next release (when A6 bumps the version)
- Move `[Unreleased]` under `## [x.y.z] - date`, add the bump PR's entry, update link refs
  at the bottom (pattern from #85 and #87).

## Don't do
- Don't edit `docs/plan.md`, `docs/agents.md`, `CLAUDE.md`, `docs/backlog.md`, `docs/ui/`,
  `docs/handoff/README.md` or code unless A1 assigns the exact lines.
- Don't approve or merge PRs; don't request Ali as reviewer.
- Don't run `bomgen layout --force` or project imports on the real `examples/`.
