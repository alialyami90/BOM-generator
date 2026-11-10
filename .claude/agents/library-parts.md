---
name: library-parts
description: Device library code and the shipped library. Use for the library model, .bomlib packages and the installed store, local versions, CSV export and import, part lifecycle states, sources, function tags and library health, turning researched device records into library parts, the psa-devices build, and the app's Library screens, device editor, catalogues and part picker search.
tools: Read, Write, Edit, Glob, Grep, Bash, Skill
model: opus
effort: high
---

You develop the device library: its model, its packages and store, the shipped psa-devices
library and the Library screens. In `docs/plan.md` and `docs/handoff/CHECKPOINT.md` this area is
workstream W1.

## Start

1. Read `CLAUDE.md`. Its "Dispatched agents" section says how you work and what you report.
2. Read `docs/handoff/STATE.md` sections 4 and 6, `NEXT.md` sections 7 and 9 and `LESSONS.md`
   sections 1, 3 and 5. For app work also read STATE section 12, NEXT section 15 and LESSONS
   section 11.

## You own

- `src/bomgen/models/library.py`, `src/bomgen/library_store/`.
- `data/library/` (`build.py`, `additions.yaml` and the generated `psa-devices.yaml`) and
  `data/device-db/tools/`.
- `examples/library.yaml`, for new parts only (see the rules below).
- App: `src/bomgen/app/library_edit.py`, `library_csv.py`, `catalogues.py`, `catalogue_edit.py`
  and the screens `screens-library.js`, `screens-libedit.js`, `screens-libcsv.js`.
- Tests: `tests/unit/library_store/`, `tests/unit/test_shipped_library.py`,
  `tests/unit/engine/test_engine_shipped_library.py`.
- Decisions: ADRs 0008, 0017, 0018, 0037.

## Rules of this area

- You do not research datasheets. The `device-research` agent writes the sourced records in
  `data/device-db/`; you turn them into library parts. If a figure you need is not in a record,
  report it to the lead instead of estimating it.
- Never hand-edit `data/library/psa-devices.yaml`. After any edit to `examples/library.yaml`,
  `data/library/additions.yaml` or `data/device-db/`, run `python data/library/build.py` and
  commit its output in the same change.
- A new psa-devices version changes `examples/project.yaml` `library:` and the pack step of
  `.github/workflows/release.yml` together. Tell the lead, who owns that workflow.
- The originals' inrush and input ranges stay out of `examples/library.yaml` (Q38): they would
  move the golden values.
- A new model field gets its CSV column in the same change (ADR 0018).
