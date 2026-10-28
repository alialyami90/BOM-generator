# STATE: role 9, BOM rule engine

| | |
| --- | --- |
| Name | B9 - BOM rule engine (A9 before the 2026-10-28 reset) |
| Date | 2026-10-28 |
| Branch | `claude/project-thread-q31ztb`, restarted from origin/main after #154 merged |
| HEAD / origin/main at checkpoint | f319f64 / f319f64 (the checkpoint commit goes on top) |

Owns: `docs/agents.md` → "Roles", row A9: `src/bomgen/engine/` except A8's `sizing.py` and
`layout.py`; `src/bomgen/checks.py`, `src/bomgen/revision.py`; `src/bomgen/models/{bom,calc,output,report}.py`;
`tests/golden/` except `layout/`; `tests/unit/test_revision.py`; the engine tests in
`tests/unit/engine/` (A8 has `test_sizing.py`, `test_layout*.py`); in `docs/plan.md` the M2–M4
sections and the M7 engine note. `tests/golden/test_cli_build.py` and the free-text line in
`engine/kits.py` were written by A2 with notice; tell A2 before changing them. Other roles'
current names: [`../ROSTER.md`](../ROSTER.md).

## Merged (this role)
- M2 groups A–D #22; M3 groups E–H, HWIO, assembly #36; M4 power and heat #44; follow-ups #46.
- M7 engine half: check report (`bomgen.checks`) and revision comparison (`bomgen.revision`)
  #58 (ADR 0016). Q34 resolved and ADR 0014 accepted #67.
- M15 branch MCB sizing from device data #103 (ADR 0019, Q35).
- DC float-voltage checks (`dc_float` items, ADR 0019 item 7, Q37) #109.
- M18 engine part: no loose-material table when it has no rows #123 (8327876). The
  free-text loose line in `engine/kits.py` came with A2's #122 (ADR 0022), reviewed by A9.
- ADR 0023 engine side (Q39, separate AC and DC MCB brands) #154 (f319f64, B9): group F
  (mains, branches, spares, QCODs), branch sizing and the `dc_float` MCB item use
  `catalogues.dc_mcb`; group E (AC branches and CINC) keeps `catalogues.mcb`. The helpers in
  `engine/mcb.py` take an `McbCatalogue`, not the library.

## In review / in progress / uncommitted
- No open code PR of this role; #154 merged.
- This checkpoint is the docs-only PR "docs(handoff): refresh B9 checkpoint after #154" for
  A1 to merge; if it is still open, find it with `list_pull_requests` state=open.
- Working tree clean apart from this checkpoint. No stash: A9's stale `stash@{0}` stayed in
  A9's container and is gone.

## What works (evidence: verification table)
- The example build reproduces the spec's values. The golden tests cite the sections:
  2,177.5 W DC and 1,090.3 W AC (`tests/golden/test_engine_power_heat.py`), groups A–H
  (`expected_groups_a_d.py`, `expected_groups_e_h.py`), and the check report
  (`test_check_report.py`: 0 failed; 50 branch MCBs at 2 A; the iC60N `dc_float` WARN 125/140).
- ADR 0023: `tests/unit/engine/test_engine_dc_dist.py` (`mcb_dc` unset, `default`, a brand),
  `test_engine_ac_dist.py` (AC keeps `mcb`), `test_checks.py` (float check on the DC set).
- `bomgen build` prints "0 failed, 3 warnings, 64 passed" on the example
  (`tests/golden/test_cli_build.py`, A2's file).
- A revision round trip against a written issue (`tests/golden/test_revision_round_trip.py`).

## Broken / known bugs
- None known in this role's code.

## Verification
| Command | Result | Date |
| --- | --- | --- |
| `python -m ruff check . && python -m ruff format --check .` | All checks passed; 317 files formatted | 2026-10-28 |
| `python -m mypy` | no issues in 212 source files | 2026-10-28 |
| `python -m pytest -q` | 2459 passed, 0 failed, 0 skipped (193 s) | 2026-10-28 |
| `python -m pytest -q tests/golden` | 94 passed | 2026-10-28 |

The gate ran at f319f64 (main after #130 and #154). Nothing was left unrun: this role has
no GUI or Windows-only parts. Golden tests need `pycel` (`pip install -e '.[dev]'`).

## Waiting on
- A3: the Q38 follow-up PR (`data/library/psa-devices.yaml`). NEXT.md task 1 starts when it
  merges (since 2026-10-28).
- Ali: ADR 0016, ADR 0019 and ADR 0023 still say "Status: Proposed". Only Ali accepts ADRs, and A1
  offers him a batch card (since 2026-10-28).
- Ali: plan §6 Q30 (where a device's loose items go) and Q31 (group A–D rules stated only by
  example). Both run on the ADR 0014 defaults until Ali answers (since M2).

## Risks and unverified assumptions
- #130 (M14, psa-devices 1.1.0 entries and DC-rated brand sets) merged at 70d16c4; the goldens
  did not move (the gate above).
- `mcb_dc` sizes the DC breakers, but the DC aux contacts still come from `aux_contact`
  (ADR 0023 consequences). A DC brand whose contacts differ needs its own choice (not asked).
- The app's Catalogues tab (`app/catalogues.py`, A11's) lists only `catalogues.mcb`; A1 is
  fine with that for now.
- Shipped-library devices with a datasheet `inrush_a` and no `inrush_ms` count the
  inrush (ADR 0019 item 1b), which can give 6 A or 10 A branches. This is intended;
  M14's data should carry `inrush_ms`.

## Spec vs code
- No open disagreement of this role. The spec gaps live in plan §6 with their defaults:
  Q3, Q4, Q5, Q6 and Q8 run on their defaults and the check report warns where the
  example departs; Q7 was replaced by Q35/ADR 0019. Ask Ali, through A1, before changing
  either the spec or the code.
