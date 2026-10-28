# Agent roles

The project is built by several Claude agents working in parallel, one per
project thread, named `Ax - Role`. Ali owns the project: he answers spec and
design questions and accepts ADRs. A1 leads the other agents, approves PRs and
merges them.

This file says who owns what, so two agents never change the same thing in
different ways. The working rules in [`CLAUDE.md`](../CLAUDE.md) apply to every
agent; the milestones are in [`plan.md`](plan.md) → "Milestones".

## Roles

| Agent | Thread | Delivers | Owns (may change freely) |
| --- | --- | --- | --- |
| A1 | Lead developer | Reviews, cross-thread consistency, this file | `docs/agents.md`, `CLAUDE.md`, `.github/workflows/ci.yml`, plan sections 1, 2, 4 (intro), 5 |
| A2 | Input models and examples | M1 | `src/bomgen/models/`, `src/bomgen/io/`, `src/bomgen/cli.py`, `examples/`, plan section 3 and the M1 section |
| A3 | Device database researcher | Reference data, outside the milestones | `data/device-db/`, its validation test |
| A4 | UI designer | M9 | `docs/ui/`, the M9 section |
| A5 | Library update packages | M8 | `src/bomgen/library_store/`, ADR 0008, the M8 section |
| A6 | Windows installer and release | M11 | `packaging/`, `.github/workflows/release.yml`, `docs/install.md`, `src/bomgen/app/launcher.py`, ADR 0009, the M11 section |
| A7 | Lead developer assistant | Documentation and small tasks A1 hands out | `README.md`, `tests/unit/README.md`, `tests/golden/README.md`; other files only when A1 assigns them |

Each agent also owns its tests (`tests/unit/<area>/` or `tests/unit/test_<area>.py`)
and its implementation plan under `docs/superpowers/plans/`.

### A1 — Lead developer

- Reviews every PR against its milestone's scope in `plan.md`, the spec and
  `CLAUDE.md`, posts an "A1: approved" review when it fits, checks CI and
  conflicts, and squash-merges it. Ali merges nothing himself unless he wants to.
- Checks for conflicts between threads: shared files, schema changes, CLI
  wiring, ADR and question numbers, CI jobs. Sends fix requests to the owning
  thread rather than changing another agent's files.
- Hands out ADR and open-question numbers, sets the merge order, and keeps this
  file current.
- Recommends when to start the milestones nobody owns yet (see "Not started").

### A2 — Input models and examples (M1)

pydantic models, the YAML loader with mirroring and readable errors, JSON
Schema export, `bomgen validate`, and `examples/` transcribed from Ali's
workbook. Owns the input schema: any other agent that needs a new field asks
A2. Provides `bomgen.io.loader.load_library()` for A5 and the root typer `app`
in `bomgen.cli` that other command groups attach to.

### A3 — Device database researcher

Datasheet details and two alternative brands (low / mid / high part numbers)
for every device, in `data/device-db/`. This is reference data: the generator
reads `examples/` and project libraries, never `data/device-db/` directly.
Library field names and part ids follow A2's schema; wattages and codes match
the example library so the golden totals don't move. Does not touch `src/` or
`examples/`.

### A4 — UI designer (M9)

Designs the desktop app with the `impeccable` skill: tokens, component specs,
screen flows and the clickable prototype in `docs/ui/`. Asks Ali the design
questions. Reads inputs from A2 (schema), A3 (alternatives) and A5 (import
preview) but writes no Python. A design that needs a new input field or engine
output goes to A2 or A1 first.

### A5 — Library update packages (M8)

`.bomlib` packing, verification, the per-user library store, import preview,
rollback and the `bomgen library …` command group. Validates libraries with
A2's loader, and registers its command group in `bomgen.cli` with one
`add_typer` line after M1 merges.

### A6 — Windows installer and release (M11)

PyInstaller spec, Inno Setup per-user installer, `.bomlib` file association,
and the tag-driven release workflow. Built early with placeholders; it wires
the real CLI, library import and window as M1, M8 and M10 land.

### A7 — Lead developer assistant

Supports A1 with documentation and small tasks: keeps `README.md` and the
test READMEs in step with what has merged, checks that docs links and the ADR
index are correct, and does the small, well-defined fixes A1 assigns. Works on
its own branch and PRs like everyone else and does not approve PRs. Anything
that touches another agent's files goes through that agent, unless A1 says
otherwise.

## Shared files

These files belong to more than one agent. Change only your own part, keep the
change small, and rebase on `main` before asking for review.

| File | Rule |
| --- | --- |
| `docs/plan.md` | Edit only your milestone's section and the open questions you resolve. Structure and other sections: A1. |
| `docs/decisions/README.md` | Add one row for your own ADR. |
| `pyproject.toml` | Add only the dependencies, extras and entry points your milestone needs. The `bomgen` console script is A2's. |
| `src/bomgen/cli.py` | A2's. Other command groups live in their own module and attach with one `app.add_typer(...)` line. |
| `.github/workflows/` | `ci.yml` is A1's; a new job must join `ci-status`'s `needs` (ADR 0006). Other workflows belong to the agent that adds them. |
| `CLAUDE.md` | A1. Ask A1 for changes. |
| `README.md` | A7, under A1's direction. |

## Numbers

ADR and open-question numbers are handed out by A1 so two threads don't take
the same one. Ask A1 before you add one.

| Kind | Taken | Next free |
| --- | --- | --- |
| ADR | 0009 installer layout (A6), 0010 input models (A2), 0011 UI design language and bundled fonts (A4) | 0012 |
| Open question | Q22 workbook corrections, Q23 issued sheets vs masters (A2) | Q24 |

## Review and merge

1. The owning agent runs `ruff check . && ruff format --check .`, `mypy` and
   `pytest`, opens a PR from its own branch and tells A1 the number.
2. A1 reviews scope, spec, tests and cross-thread effects. Problems go back to
   the owning thread as a list; the owner fixes them on the same PR.
3. When it fits, A1 posts the approval and squash-merges once CI is green and
   the branch has no conflict with `main`.
4. A dependent PR rebases on `main` after the PR it depends on merges.

Merge order while the current work is open: M1 (A2) first, since M8, M11 and the
device database all read its schema; then M8 (A5) and the device database (A3);
then M11 (A6), rebased so its launcher calls the real CLI. M9 (A4) is docs only
and can merge whenever Ali approves the design.

## Not started

| Milestone | Recommendation |
| --- | --- |
| M2–M4 rule engine | Start when M1 merges, as one agent working M2, M3, M4 in order: they share `engine/` and build up the same golden test. |
| M6 Excel writer | Can start when M1 merges, in parallel with M2: it only needs `models/sheet.py`, which it defines. |
| M5 sheet models | Starts after M4 and M6, by the M6 agent. |
| M7 check report, revision highlighting | After M5; also wires A5's library-version check into the report. |
| M10 desktop app | After Ali approves the M9 design and M8 merges. |

New agents get the next `A` number and a row in "Roles" when Ali starts them.
