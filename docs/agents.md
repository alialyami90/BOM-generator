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
| A1 | Lead developer | Reviews, cross-thread consistency, this file | `docs/agents.md`, `CLAUDE.md`, `.github/workflows/ci.yml`, `docs/handoff/README.md`, `docs/handoff/01-lead/`, plan sections 1, 2, 4 (intro), 5 |
| A2 | Input models and examples | M1, M1b | `src/bomgen/models/`, `src/bomgen/io/`, `src/bomgen/cli.py`, `src/bomgen/build.py`, `examples/`, plan section 3 and the M1 section |
| A3 | Device database researcher | Reference data, outside the milestones | `data/device-db/`, its validation test; the shipped library `data/library/` (build script, generated file, `test_shipped_library.py`; plan Q38) |
| A4 | UI designer | M9, the M10e polish findings (done) | `docs/ui/`, the M9 section |
| A5 | Library update packages | M8, M8b | `src/bomgen/library_store/`, ADR 0008, the M8 section |
| A6 | Windows installer and release | M11 | `packaging/`, `.github/workflows/release.yml`, `docs/install.md`, `src/bomgen/app/launcher.py`, ADR 0009, the M11 section |
| A7 | Lead developer assistant | Documentation and small tasks A1 hands out | `README.md`, `CHANGELOG.md`, `tests/unit/README.md`, `tests/golden/README.md`; other files only when A1 assigns them |
| A8 | Sizing and layout engine | M1c | `src/bomgen/engine/sizing.py`, `src/bomgen/engine/layout.py`, `tests/golden/layout/`, the M1c section |
| A9 | BOM rule engine | M2, M3, M4, M7 (engine) | the rest of `src/bomgen/engine/`, `src/bomgen/checks.py`, `src/bomgen/revision.py`, `src/bomgen/models/bom.py`, `src/bomgen/models/calc.py`, `src/bomgen/models/output.py`, `src/bomgen/models/report.py`, `tests/golden/` (except `layout/`), `tests/unit/test_revision.py`, the M2–M4 sections and the M7 engine note |
| A10 | Excel workbook writer | M6, then M5 | `src/bomgen/sheets/`, `src/bomgen/writer/`, `src/bomgen/models/sheet.py`, the M5–M6 sections |
| A11 | Desktop app | M10 (done) | `src/bomgen/app/` except `launcher.py` (A6), `src/bomgen/app/ui/`, `tests/unit/app/`, the M10 section |

Each agent also owns its `docs/handoff/<NN-role>/` folder and its row in
`docs/handoff/ROSTER.md` (restart-safe checkpoints; names keep the role number, the letter
counts resets, so B1 has A1's rights). Each agent also owns its tests (`tests/unit/<area>/` or `tests/unit/test_<area>.py`)
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
- Recommends when to start the milestones nobody owns yet (see "Status").

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
output goes to A2 or A1 first. Done: the M9 design, the M10e polish findings, and
the departures the built app made from the design, recorded in `docs/ui/` (#82).

### A5 — Library update packages (M8)

`.bomlib` packing, verification, the per-user library store, import preview,
rollback and the `bomgen library …` command group. Validates libraries with
A2's loader, and registers its command group in `bomgen.cli` with one
`add_typer` line after M1 merges.

### A6 — Windows installer and release (M11)

PyInstaller spec, Inno Setup per-user installer, `.bomlib` file association,
and the release workflow (a merged version bump with its CHANGELOG section
builds, tags and publishes; ADR 0009). Built early with placeholders; it wires
the real CLI, library import and window as M1, M8 and M10 land.

### A8 — Sizing and layout engine (M1c)

Rules R1–R10 of the approved design (ADR 0013): L1/L2 switch counts from the
IED count and spares, generated port plans, 32U panel fill with A/B streams,
common devices spread, overrides and removals, `bomgen layout`, and the layout
golden. Pure functions in `engine/`; asks A2 for any input field it is missing
and never edits `models/` or `io/` itself. Starts when M1b is on main.

### A9 — BOM rule engine (M2–M4)

Steps 1–11 of "Data model and generation order" as pure functions over the
loaded models: groups A–H, tags, kits, network accessories, power and heat,
HWIO, assembly, and `engine/pipeline.py` returning a `BuildResult`. One PR per
milestone, each extending the golden test on `examples/`. Builds on the
hand-written example panels; A8's generated panels feed in later through the
same `Panel` models. A new input field goes through A2; the sheets consume
`BuildResult`, so changes to it are announced to A10 first.

### A10 — Excel workbook writer (M6, then M5)

`models/sheet.py` (`SheetModel`, cells, styles, print setup, header/footer),
`writer/xlsx.py` (the only module importing XlsxWriter, ADR 0003) and, in M5,
`sheets/*.py` turning A9's `BuildResult` into sheet models with live formulas.
Writer tests reopen the file with openpyxl. Starts M6 now against a hand-built
`SheetModel`; M5 waits for A9's M4.

### A11 — Desktop app (M10)

Builds the approved design (docs/ui, #8 and #23, ADR 0007 and 0011) as the
pywebview app: the UI files move from the prototype into `src/bomgen/app/ui/`,
the Python API behind `docs/ui/screens.md` "What the app needs from the
engine" calls the engine, library store, project store and writer, and plugs
into `launcher.app_main` with one call agreed with A6. Order: shell and Home,
Project, Library, Backup/share screens against what is on main; Substation,
Network and Panels once M1b and M1c land; Checks, Preview and Build once M5
and M7 land. No business rule in the UI: anything missing from the engine goes
to its owner. A4 owns the design and reviews the screens; the milestone ends
with A4's impeccable polish pass. Done: M10a–M10e (#28 to #81). Substation and
project editing waits for the project and substation writers (plan M10 status).

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
| `src/bomgen/cli.py` | A2's. Other command groups live in their own module and attach with one `app.add_typer(...)` line. `build` calls `bomgen.build.build_substation`. |
| `src/bomgen/build.py` | A2's. The one build sequence `bomgen build` and the app share: A9's pipeline, compare and check report, A10's sheets and writer; each owner adds its own step after telling A2. The caller lays out first with A8's `with_layout` (`cli.build`, the app's `resolve()`). |
| `.github/workflows/` | `ci.yml` is A1's; a new job must join `ci-status`'s `needs` (ADR 0006). Other workflows belong to the agent that adds them. |
| `CLAUDE.md` | A1. Ask A1 for changes. |
| `README.md` | A7, under A1's direction. |

## Numbers

ADR and open-question numbers are handed out by A1 so two threads don't take
the same one. Ask A1 before you add one.

| Kind | Taken | Next free |
| --- | --- | --- |
| ADR | 0009 installer layout (A6), 0010 input models (A2), 0011 UI design language and bundled fonts (A4), 0012 projects/substations/.bomproj (A1, accepted), 0013 network sizing and panel layout (A1, accepted), 0014 engine data model (A9, accepted), 0015 desktop app bridge (A11, accepted), 0016 check report and revision comparison (A9, proposed); reserved: 0017 library alternatives and catalogue brands (A2), 0018 library CSV exchange (A5), 0019 branch MCB sizing (A9), 0020 loose-material sheet (A10), 0021 project and substation file writers (A2), 0022 free-text loose items (A2), 0023 separate AC and DC MCB brands (B2) | 0024 |
| Open question | Q22 workbook corrections, Q23 issued sheets vs masters (A2), Q24–Q28 substations/layout (resolved), Q29 thermostat and fan library defaults (A3), Q30 loose-table order (A9), Q31 M2 engine rules bundle (A9), Q32 cable managers vs 32U (resolved), Q33 FOPP-96SM height (resolved), Q34 M3 group E–H rules (resolved), Q35 branch MCB sizing rule (resolved), Q36 loose-material placement (resolved), Q37 default DC MCB set (resolved), Q38 datasheet data in the shipped library (resolved), Q39 separate AC and DC MCB brands (resolved), Q40 power footnote in the print area (resolved) | Q41 |

## Review and merge

1. The owning agent runs `ruff check . && ruff format --check .`, `mypy` and
   `pytest`, opens a PR from its own branch and tells A1 the number.
2. A1 reviews scope, spec, tests and cross-thread effects. Problems go back to
   the owning thread as a list; the owner fixes them on the same PR.
3. When it fits, A1 posts the approval and squash-merges once CI is green and
   the branch has no conflict with `main`.
4. A dependent PR rebases on `main` after the PR it depends on merges.

A1 sets the merge order when open PRs touch the same files.

## Status

Every milestone up to M11 is on main (v0.1.1): M0–M11, with M1b, M1c and M8b. The
next version is M12–M18, built from Ali's feedback. Its points, owners and status are in
[`backlog.md`](backlog.md); A1 keeps that file current.

New agents get the next `A` number and a row in "Roles" when Ali starts them.
