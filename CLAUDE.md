# Working rules for Claude

## Team

Work is split across agents, one per project thread (`Ax - Role`). Roles, file
ownership, shared-file rules, ADR/question numbering and the review flow are in
[`docs/agents.md`](docs/agents.md). Change only files your role owns; A1 (lead)
reviews and approves every PR, Ali merges.

## Source of truth

- The spec in `docs/spec/` is authoritative. Reference it by section name; do not
  restate it in code comments or docs.
- If code and spec disagree, **ask Ali before changing either**. Record the answer
  in an ADR (`docs/decisions/`) or in the plan's open questions.
- `docs/plan.md` holds the module breakdown, input schemas, milestones and open
  questions. Keep it current when a decision changes it.

## How work is delivered

- Small PRs, one milestone each (see `docs/plan.md`). Do not mix milestones.
- Conventional commit messages: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`,
  `chore:`, `ci:`, `build:`; scope optional, e.g. `feat(dc-dist): size main MCBs`.
- Significant design choices get an ADR in `docs/decisions/` (copy
  `0000-template.md`, next free number).
- Never commit generated `.xlsx` outputs. Build into `out/` or a temp dir
  (both are git-ignored).

## Before every commit

Run all three and commit only when they pass:

```bash
ruff check . && ruff format --check .
mypy
pytest
```

## Testing rules

- TDD: write the failing test first for each rule in the spec, then the code.
  Name tests after the rule, e.g. `test_x3_ac_is_two_per_ac_mcb_including_cinc`.
- Golden test: building from `examples/` must reproduce the example values the
  spec gives (tags, MCB counts and ratings, terminal block quantities, power
  totals 2,177.5 W DC and 1,090.3 W AC, heat totals, airflow results). The
  expected values live in `tests/golden/` and cite the spec section they come from.
- Writer tests reopen the generated file and assert formulas, styles, merges,
  print settings and header/footer strings.

## Layout

```
docs/spec/        generator spec (authoritative) + how to update it
docs/decisions/   ADRs
docs/plan.md      plan, milestones, open questions
docs/agents.md    agent roles and file ownership
src/bomgen/       package source
tests/unit/       one test module per rule area
tests/golden/     example-project golden values and tests
examples/         YAML inputs reproducing the spec's example project
data/device-db/   researched datasheet details and alternative brands (reference only)
schemas/          JSON Schemas exported from the models (bomgen schema)
```

## UI work

The Windows desktop app's UI (milestones M9–M10 in `docs/plan.md`) is designed
with the `impeccable` skill first: tokens, component specs and an HTML/CSS
prototype in `docs/ui/` (M9). The app (M10) implements the approved design and
ends with an impeccable polish pass. Business rules stay in the engine, never
in the UI.
