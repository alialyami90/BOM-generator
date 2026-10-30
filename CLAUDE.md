# Working rules for Claude

## Commandments (Ali, 2026-10-30)

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific
instructions as needed.

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require
constant clarification.

These guidelines are working if: fewer unnecessary changes in diffs, fewer rewrites due to
overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Project state

Current state, next steps, lessons and checkpoints are in [`docs/handoff/`](docs/handoff/)
(`STATE.md`, `NEXT.md`, `LESSONS.md`, `CHECKPOINT.md`). Read them before starting work and
keep them current when work stops.

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
- Numbers: the next free ADR number is the one after the last row of
  `docs/decisions/README.md`; the next free open question is the one after the highest
  `Q` number in `docs/plan.md` "Open questions".
- `src/bomgen/cli.py`: other command groups live in their own module and attach with
  one `app.add_typer(...)` line. `build` calls `bomgen.build.build_substation`.
- A new CI job in `.github/workflows/ci.yml` must join `ci-status`'s `needs` (ADR 0006).
- Never commit generated `.xlsx` outputs. Build into `out/` or a temp dir
  (both are git-ignored).

## Review and merge

1. Run the checks below, then open a PR from a branch.
2. Review it against its milestone's scope in `docs/plan.md`, the spec and this file.
3. Squash-merge it once CI is green and the branch has no conflict with `main`.
4. A dependent PR rebases on `main` after the PR it depends on merges.

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
docs/handoff/     project state, next steps, lessons, checkpoints
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
