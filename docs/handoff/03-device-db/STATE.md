# Role 3 state: Device database researcher

- **Name:** A3, handing over to B3. **Date:** 2026-10-28.
- **Thread branch:** `claude/project-thread-0iv7xg` (#130's head is `87eee46`).
- **Local:** HEAD `372418c` on the local-only branch `followup-q38`.
- **origin/main:** `aad6094` (#133).
- **Owns:** see `docs/agents.md` → Roles, row 3. That is `data/device-db/` and
  `tests/unit/test_device_db.py`, plus the M14 library data assigned in plan.md §4 M14.

## Merged

- #18: rack heights and port roles.
- #30: FOPP-96SM is 1U (Q33).
- #40: README field rules.
- #42: `pack` in the README.
- #121: M14 research. It adds electrical data for every alternative and the DC MCB ranges,
  findings 22–29, and the test_device_db checks.

## In review

- **#130**, `feat(library): alternatives as library parts and DC-rated brand sets (M14)`.
  - What it does:
    - Adds 279 alternative parts with `alt_group` and `tier`.
    - Adds `catalogue_brands`:
      - MCB: C60H-DC, S200M UC and 5SY5.
      - Aux contacts.
      - Weidmuller and WAGO terminal blocks.
      - Phoenix and nVent busbars.
      - Two housekeeping sets.
    - Adds the default MCB trip data.
    - Bumps to psa-devices 1.1.0 (`examples/project.yaml`, `release.yml`).
    - Adds findings 30–31.
    - Changes 10 tests outside role 3, approved by A1 and listed in the PR body:
      - A5's 5 library_store files: signed off by A5.
      - A8's test_layout: A1 checks it, since A8's thread is closed.
      - A11's 2 app tests: only the 1.1.0 version.
  - CI: green on `87eee46` (ruff, mypy, pytest, Windows installer, ci-status).
  - Reviews:
    - A5 signed off its 5 test files (relay, 20:29 UTC).
    - A2 commented: nothing to change.
    - A1 pre-read it and will merge after A2 and A5.
  - Notes from A2 that are not role 3's work:
    1. A DC-only MCB brand can be chosen for AC branches. A2 owns the follow-up.
    2. The default iC60N's `dc_rating_v: 125` now WARNs against `dc_float_v: 140` in the
       example check report. A1 and Ali are to confirm.
    3. The suite is slower, at about 10 min against about 2 min.

## In progress (not pushed)

- **Q38 follow-up**, the shipped library: commit `372418c`, stacked on #130.
  - Copy: `/mnt/project-files/handoff/03-device-db/q38-shipped-library.patch`. It leaves out
    the generated YAML; rebuild that with `python data/library/build.py`.
  - Not pushed, because the thread branch carries #130. Plan in NEXT.md §1.
  - Files:
    - `data/library/build.py`
    - `data/library/psa-devices.yaml` (generated)
    - `tests/unit/test_shipped_library.py`
    - `data/device-db/README.md`
    - `.github/workflows/release.yml` (A6's)
    - `tests/unit/test_packaging.py` (A6's)
  - Status: finished, and the gate passes (table below).
- **Uncommitted changes:** none in the main checkout.
- **M14 generator scripts:** these are outside the repo, in
  `/mnt/project-files/handoff/03-device-db/`; see LESSONS.md. The research briefs and raw outputs
  are in `research-m14/` there. Everything they found is merged into `data/device-db/`.

## What works and what's broken

- Works:
  - The example library loads 329 devices (50 originals and 279 alternatives).
  - Goldens are unchanged, with 2,177.5 W DC and 1,090.3 W AC; `tests/golden/` passes in the
    pytest run below. The new `dc_float` WARN in the check report is not a golden value.
  - The shipped library builds the example project with no failed checks. SEL branch MCBs
    go from 2 A to 6 A (A9F74202 → A9F74206), as Q35 expects with 20 A inrush.
- Not in the library yet:
  - 11 alternatives with no power figure (finding 30 in `docs/device-db-findings.md`).
  - The SEL-2244-2 alternatives have no `di_inputs` (finding 31).
- Known bugs: none.

## Verification

| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` on 372418c | pass, 272 files | 2026-10-28 |
| `python3 -m mypy` on 372418c | pass, 211 files | 2026-10-28 |
| `python3 -m pytest -q` on 372418c | 2417 passed, 0 failed, 0 skipped, 11m09s | 2026-10-28 |
| #130 CI on 87eee46 | all green | 2026-10-28 |

- Goldens were not run on their own: they are part of the pytest run above.
- Not run: the Windows installer, locally. CI covers it on #130.

## Waiting on

- A1: merge #130 (since 2026-10-28 20:23 UTC).
- A1 and Ali: confirm the iC60N float warning (A2's note 2 on #130).
- No questions from role 3 to Ali are open. Q33, Q37 and Q38 are resolved; see plan.md §6.

## Risks and assumptions

- **Ownership.**
  - `data/library/` is a new path. A1 suggested it, but it is not in agents.md's row 3.
    Ask A1 to add it.
  - #130 edits `examples/library.yaml` and `examples/project.yaml` (A2's). Both were
    approved by A1 for M14.
- **Q38 says A6 repoints `release.yml`.** A1's later relay assigned that to role 3, with
  A6 reviewing.
- **Finding 24.** The FGR-60F's input range tops out at 125 V, below the battery float.
  Fortinet should confirm.

## Spec and code disagreements

None known for role 3.
