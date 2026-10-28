# Role 3 state: Device database researcher

- **Name:** B3. **Date:** 2026-10-28 (second checkpoint).
- This is a refresh with no context reset, so the name stays B3. After the next reset the
  successor is C3.
- **Branch:** `claude/project-thread-0iv7xg`, reset to origin/main after the squash merge.
- **HEAD = origin/main:** `159591f` (#161). It already includes B5's #165.
- **Owns:** see `docs/agents.md` → Roles, row 3: `data/device-db/` and its test. A1 is
  adding `data/library/` to row 3 (A1's relay, 22:21 UTC).

## Merged

- #18 rack heights and port roles.
- #30 FOPP-96SM 1U (Q33).
- #40, #42 README rules.
- #121 M14 research.
- #130 M14 library entries: 279 alternatives, the brand sets, psa-devices 1.1.0.
- #144 checkpoint B3.
- #161 Q38 shipped library:
  - `data/library/build.py` generates `data/library/psa-devices.yaml`.
  - `ac_rated: false` on `schneider-c60h-dc` in both libraries.
  - release.yml packs the shipped file, and ADR 0009 is updated. These are B6's files:
    A1 assigned the release.yml repoint and B6 approved the ADR line.
  - `test_shipped_library.py`.

## In review / in progress

- **In review:** nothing besides this checkpoint PR.
- **Uncommitted:** none.
- **Off-repo:** the M14 generator scripts are in `/mnt/project-files/handoff/03-device-db/`
  (LESSONS.md). `library_entries.py` there now writes `ac_rated: false` for a brand with no
  AC trip band.

## What works and what's broken

- Works:
  - The example library loads 329 devices (50 originals and 279 alternatives).
  - Goldens are unchanged, with 2,177.5 W DC and 1,090.3 W AC; `tests/golden/` is part of
    the pytest run below.
  - The shipped library adds inrush or input range to 11 originals. With it, the example
    builds with no failed checks, and its SEL branch MCBs go from 2 A to 6 A.
  - The C60H-DC brand is valid as `catalogue_choice.mcb_dc` and refused as `mcb` (ADR 0023).
- Not in the library yet:
  - 11 alternatives with no power figure (finding 30, `docs/device-db-findings.md`).
  - The SEL-2244-2 alternatives have no `di_inputs` (finding 31).
- Known bugs: none.

## Verification

| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` on 159591f | pass, 326 files | 2026-10-28 |
| `python3 -m mypy` on 159591f | pass, 217 files | 2026-10-28 |
| `python3 -m pytest -q` on 159591f | 2525 passed, 0 failed, 0 skipped, 4m23s | 2026-10-28 |
| `python data/library/build.py` on 159591f | no diff (shipped file up to date) | 2026-10-28 |
| #161 CI on 64a8e65, including the Windows installer | all green | 2026-10-28 |

## Waiting on

- A1 and Ali: confirm the default iC60N's `dc_float` WARN, raised in A2's review of #130.
- No questions from role 3 to Ali are open. Q33, Q37 and Q38 are resolved; see plan.md §6.

## Risks and assumptions

- **Finding 24.** The FGR-60F's input range tops out at 125 V, below the 140 V float.
  Fortinet should confirm.
- **Edits to the example library.** Any edit to `examples/library.yaml` (A2/B2) must be
  followed by `python data/library/build.py`, or `test_the_shipped_library_is_up_to_date_with_its_sources` fails.

## Spec and code disagreements: none known for role 3
