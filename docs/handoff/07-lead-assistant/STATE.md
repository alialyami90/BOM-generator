# STATE: role 7, Lead developer assistant (final handover by B7)

- Written by: B7, 2026-10-29, at the retirement of every agent. The next holder (C7) starts with
  no history: read this file, then `NEXT.md`, `LESSONS.md` and `checkpoints/2026-10-29-final.md`.
- `main` at handover: `032bbea` (#212). Released: v0.2.1, tag `v0.2.1` on `1678343` (#211);
  v0.2.0 on `f65a5fe` (#195). `pyproject.toml` version `0.2.1`.
- Last commit covered by the changelog: `1678343` (#211, the 0.2.1 bump, which gets no entry).
  Every non-docs PR up to #212 has an entry in `CHANGELOG.md` or was ruled out by the lead
  (#195 and #211 bumps, #197 refactor; LESSONS L12). `[Unreleased]` is empty.
- Gate at `a151c32` (#212's head, same tree as `032bbea`): `ruff check .` and
  `ruff format --check .` pass, `mypy` passes (224 source files), `pytest` 2672
  passed in about 5 minutes.
- Open PRs on the repo at handover: none. Uncommitted work: none.
- My branch: `claude/project-thread-vl9f9y`, reset to `origin/main` after every merge (L8).
  Other `claude/*` branches on origin belong to other roles; don't touch or delete them.

## The role
- Definition: `docs/agents.md` → "Roles" (A7 row) and "A7 — Lead developer assistant". Roles are
  keyed by number: C7 has A7's rights.
- Files I own: `README.md`, `CHANGELOG.md`, `tests/unit/README.md`, `tests/golden/README.md`, and
  this folder plus row 7 of `../ROSTER.md`. Other files only when the lead assigns exact lines
  (last time: ADR Status lines and `docs/decisions/README.md` rows in #184).
- The lead (role 1) reviews, approves and squash-merges every PR. At handover the lead was B1;
  Ali is retiring all agents, so find the current lead with `list_threads` before messaging
  (L14). Never ask Ali to merge.
- Project rules from Ali: use the Superpowers skills; ask Ali questions only on a decision card
  with the recommendation marked; read the handoff docs well.

## What each owned file holds now (all verified at `032bbea`)
- `README.md`: overview, Status (v0.2.1 released, next work waits on Ali's testing feedback;
  "Done in v0.1" M0–M11 and "Done in v0.2" M12–M18), Usage (validate, build, layout, library,
  CSV editing, project sharing), Development, CI. Every command was run on a scratch copy (L3).
- `CHANGELOG.md`: Keep a Changelog; sections `[Unreleased]` (empty), `[0.2.1]`, `[0.2.0]`,
  `[0.1.1]`, `[0.1.0]`, with compare link refs at the bottom.
- `tests/unit/README.md`: one row per unit test module (`| Module | Milestone | What it checks |`).
  The L4 row loop prints nothing.
- `tests/golden/README.md`: one row per golden module; the L4 loop for `tests/golden` prints nothing.
- Relative links in all four files resolve (L5 loop prints nothing).

## My merged PRs as B7
- #147: README v0.2 status and library CSV usage; 14 rows in `tests/unit/README.md`.
- #160: README marks M14 and M18 done, releases from main; changelog for #130–#154.
- #174: changelog for #155–#171.
- #184: 15 ADRs marked "Accepted (Ali, 2026-10-28)" (lines assigned by B1).
- #193: `## [0.2.0] - 2026-10-29`.
- #209: `## [0.2.1] - 2026-10-29` (B1's review: no agent names, no lead-in, wrap at 78; L13).
- #210: handoff checkpoint (L12, L13 added).
- #212: README Status for v0.2.1; the 9 missing unit-test rows.

## Decisions and why
- No changelog entry for docs-only, handoff, chore, version-bump or internal-refactor PRs
  (B1, L12): the release heading records the version, and the changelog is for users.
- Entries are worded from the PR description (or the final squash message), with no agent
  names, wrapped near 78 columns (B1, L13).
- Docs passes are batched into one PR over a range of merges; the lead says when (L2).
- Release sections are opened before the bump PR; the installer/release role opens the bump
  after the changelog merges (pattern #193 then #195, #209 then #211).
- README Status wording at v0.2.1 was set by B1 in its request for #212.

## Waiting on / blockers
- The next work waits on Ali's testing feedback on v0.2.1 (tracked in `docs/backlog.md` when it
  comes). Nothing for role 7 to do until merges land on `main`.
- No questions to Ali open. No open PRs.
