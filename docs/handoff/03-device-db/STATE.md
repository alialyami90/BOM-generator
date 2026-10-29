# Role 3 state: Device database researcher

- **Outgoing name:** B3. Ali retired all agents on 2026-10-29, so the **successor is C3**.
- **Date:** 2026-10-29.
- **Thread branch:** `claude/project-thread-0iv7xg`. It was reset to origin/main and has
  nothing unmerged. The checkpoint branch is `claude/handoff-03-device-db`.
- **origin/main:** `032bbea` (#212, v0.2.1 README).
- **Owns:** `docs/agents.md` → Roles, row 3:
  - `data/device-db/` and `tests/unit/test_device_db.py`
  - `data/library/` (`build.py`, the generated `psa-devices.yaml`) and
    `tests/unit/test_shipped_library.py`
  - `docs/device-db-findings.md`
- **Detail:** [archive/reference.md](archive/reference.md) has the data layout, the
  generator rules, the brand sets, the PR history and the decisions.

## Merged (nothing of role 3 is open)

- #18 rack heights and port roles.
- #30 FOPP-96SM 1U (Q33).
- #40, #42 README rules.
- #121 M14 research.
- #130 M14 library entries: 279 alternatives with `alt_group` and `tier`, plus MCB, aux,
  terminal-block, busbar and housekeeping brand sets.
- #161 Q38 shipped library, C60H-DC `ac_rated: false`, release.yml repoint and ADR 0009.
- #144, #172 checkpoints.
- Shipped since then by other roles: v0.2.0 and v0.2.1, which ship psa-devices 1.1.0 from
  `data/library/psa-devices.yaml`. B9's #171 pins the sizing against that file.

## In review / in progress / uncommitted

- In review: none. In progress: none. Uncommitted: none.
- Off-repo: the M14 generator and the research files are in
  `/mnt/project-files/handoff/03-device-db/` (reference.md §3).
  `q38-shipped-library.patch` there is obsolete, because #161 merged it.

## What works and what's broken

- Works:
  - The example library loads 329 devices: 50 originals and 279 alternatives.
  - Goldens are unchanged (2,177.5 W DC, 1,090.3 W AC).
  - `python data/library/build.py` reproduces the committed shipped file byte for byte.
  - With the shipped library, the example builds. SEL-3555-GW/RTAC and SEL-3355 size to
    6 A, and `dc_float` warns for the iC60N and the FGR-60F, as Q37 and Q41 intend.
- Gaps in the data, not bugs:
  - Finding 30: 11 alternatives have no power figure, so they are not library parts.
  - Finding 31: the SEL-2244-2 alternatives have no `di_inputs`.
  - 83 of the 378 alternative tiers have `verified: false`. Their codes come from a naming
    pattern, so check them before ordering (README).
- Known bugs: none.

## Verification (this session)

| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` on 032bbea | pass, 345 files | 2026-10-29 |
| `python3 -m mypy` on 032bbea | pass, 224 files | 2026-10-29 |
| `python3 -m pytest -q` on 032bbea | 2672 passed, 0 failed, 0 skipped, 5m54s | 2026-10-29 |
| `python data/library/build.py` on 032bbea | no diff | 2026-10-29 |

## Waiting on

Nobody. Every role 3 question is resolved: Q33, Q37, Q38, Q39 and Q41 in plan.md §6.
Q41 settled finding 24: the FGR-60F stays, and its warning is accepted.

## Risks

- **The generator is off-repo and not idempotent** (reference.md §3). New alternatives
  mean editing `examples/library.yaml` by hand (B2's OK) or adapting the script.
- **Editing the example library.** Any edit to `examples/library.yaml` must be followed
  by `python data/library/build.py`. Otherwise `test_the_shipped_library_is_up_to_date_with_its_sources`
  fails, and B9's `test_engine_shipped_library.py` may shift.
- **Bumping psa-devices past 1.1.0** means changing `examples/project.yaml` `library:` and
  release.yml together (`test_packaging.py`). Agree it with B1, B2 and B6 first.

## Spec and code disagreements: none known for role 3
