# 0006. CI gated by paths-filter with an always-on ci-status job

- Status: Accepted (set by the project brief)
- Date: 2026-10-28
- Spec sections: —

## Context

CI must run lint, type-check and tests on PRs and pushes to `main`, but not when
a change touches only docs (`docs/**`, `**/*.md`, `LICENSE`). A workflow skipped
via `paths-ignore` reports no status, so a required check would hang.

## Decision

`.github/workflows/ci.yml`: a `changes` job runs `dorny/paths-filter` and
outputs `code`; `lint`, `typecheck` and `test` run only when `code == 'true'`;
a final `ci-status` job runs with `if: always()` and passes when every job
succeeded or was skipped. Branch protection should require only `ci-status`.

## Consequences

Docs-only PRs get a green required check in seconds. New jobs must be added to
`ci-status`'s `needs` list or they won't gate merges.
