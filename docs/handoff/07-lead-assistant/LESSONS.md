# LESSONS: role 7 (append-only)

- **L1 Changelog format.** Keep a Changelog; every merged PR number appears once (PRs of
  one milestone step may share an entry, e.g. "(#44, #46)"), newest first in Added and Changed; my own docs PRs get a
  Changed entry too. Released sections since #85: `## [x.y.z] - YYYY-MM-DD` with link refs
  at the bottom (`compare/vA...vB`, `releases/tag/v0.1.0`). Rejected: per-milestone
  entries only (lost the fix PRs).
- **L2 Batching.** A1 prefers one docs PR over a range of merges ("saves a review round")
  and sometimes asks to wait for named PRs (#71–#74 in #75). Ask before opening a pass.
- **L3 Verify commands on a copy.** Run every README command on
  `cp -r examples <scratch>/ex`. `bomgen layout` on the shipped example exits 1 by design
  (`fed_from: psa3`, plan M1c); `--force` rewrites `panels/`. Never on `examples/` itself.
- **L4 README-row coverage loop.**
  `for f in $(cd tests/unit && find . -name 'test_*.py'); do grep -q "$(basename $f)" tests/unit/README.md || echo "missing $f"; done`
  (same for tests/golden).
- **L5 Link check loop.** For each doc: `grep -o '](\([^)#]*\))'`, drop http links, test
  `[ -e "$(dirname $f)/$l" ]`.
- **L6 Other agents' files.** Report stale lines to A1 with path, line and evidence; A1
  fixes them or assigns exact lines (e.g. plan M10 status and agents.md rows in #83).
- **L7 PR mechanics.** Ali is the PR author, so requesting Ali as reviewer fails; assign
  `alialyami90` instead. Body starts with the attribution block and ends with the
  generated-by footer; use the attribution lines the session supplies and add no other
  model name. Docs-only PRs skip the test jobs;
  `ci-status` is the check to report.
- **L8 After a squash merge.** `git fetch origin main && git checkout -B <branch> origin/main`
  then `git push --force-with-lease -u origin <branch>`; the stop hook flags the branch as
  unpushed otherwise.
- **L9 Environment.** `bomgen` may not be on PATH: use a venv and `pip install -e '.[dev]'`
  again after pulling (new modules, pycel). pycel's install can exceed 120 s; run it in
  the background.
- **L10 Markdown tables.** A blank line inside a table ends it; check rendering after
  inserting rows.
- **L11 Drift at this checkpoint.** No earlier STATE.md existed (first checkpoint). Docs
  fell 42 PRs behind because passes were triggered only by A1's merge notes; successor
  should check `git log` for unlisted merges at every wake instead of waiting.
- **L12 What gets no changelog entry (B1, 2026-10-28/29).** Docs-only, handoff and chore PRs,
  version bumps (the section heading records the version) and internal refactors with no
  user-facing change (#197). This replaces L1's "my own docs PRs get a Changed entry".
- **L13 Changelog wording.** User-facing: no agent names ("B4's wording" → say what changed);
  word each entry from the PR's description and, for the last PR of a release, from its final
  squash message (`git show -s --format=%B <sha>`), which can add items the description lacks.
  Wrap at about 78 columns. One entry may group a milestone's PRs.
- **L14 The lead moved.** A1's thread is retired; B1 has its own thread. Check `list_threads`
  for the current lead before messaging, and resend if a note went to a retired thread.
- **L15 Drift at the B7 checkpoint.** STATE.md was written at `aad6094`; 11 docs-only merges had
  landed and #143 was merged, not open. The clone was shallow: `git fetch --unshallow` before
  using old shas such as `39fddc4`.
