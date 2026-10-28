# STATE: role 9, BOM rule engine

| | |
| --- | --- |
| Name | A9 - BOM rule engine (successor: **B9 - BOM rule engine**) |
| Date | 2026-10-28 |
| Branch | `claude/project-thread-9l1061`, restarted from origin/main after #123 merged |
| HEAD / origin/main at checkpoint | aad6094 / aad6094 (the checkpoint commit goes on top) |

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

## In review / in progress / uncommitted
- No open PR of this role (`list_pull_requests` state=open, 2026-10-28: #130, #131, #132,
  #134 are other roles'). Unsubscribed from #123 after it merged.
- This checkpoint is the docs-only PR "docs(handoff): checkpoint B9 2026-10-28" for A1 to
  merge; if it is still open, find it with `list_pull_requests` state=open.
- Working tree clean apart from this checkpoint.
- `stash@{0}` "WIP on m3: d86fcce" (2026-10-28 12:00) is stale M3 pipeline work that #36
  superseded. Kept, because Ali's checkpoint rules ("never stash, reset or discard") forbid
  dropping it. Do not apply it. It lives only in A9's container; a fresh one won't have it.

## What works (evidence: verification table)
- The example build reproduces the spec's values. The golden tests cite the sections:
  2,177.5 W DC and 1,090.3 W AC (`tests/golden/test_engine_power_heat.py`), groups A–H
  (`expected_groups_a_d.py`, `expected_groups_e_h.py`), and the check report
  (`test_check_report.py`: 0 failed; 50 branch MCBs at 2 A; the iC60N `dc_float` WARN 125/140).
- `bomgen build` prints "0 failed, 3 warnings, 64 passed" on the example
  (`tests/golden/test_cli_build.py`, A2's file).
- A revision round trip against a written issue (`tests/golden/test_revision_round_trip.py`).

## Broken / known bugs
- None known in this role's code.

## Verification
| Command | Result | Date |
| --- | --- | --- |
| `python -m ruff check . && python -m ruff format --check .` | All checks passed; 270 files formatted | 2026-10-28 |
| `python -m mypy` | no issues in 210 source files | 2026-10-28 |
| `python -m pytest -q` | 2414 passed, 0 failed, 0 skipped (129 s) | 2026-10-28 |
| `python -m pytest -q tests/golden` | 94 passed | 2026-10-28 |

The gate ran at 9313db1 and again at aad6094 with this checkpoint staged (ruff, mypy, and
pytest: 2414 passed). `git diff --stat 9313db1 aad6094` shows that #133 changed only
`docs/agents.md` and `docs/handoff/{README,ROSTER}.md`. Nothing was left
unrun: this role has no GUI or Windows-only parts. Golden tests need `pycel`
(`pip install -e '.[dev]'`).

## Waiting on
- A3: the Q38 follow-up PR (`data/library/psa-devices.yaml`). NEXT.md task 1 starts when it
  merges (since 2026-10-28).
- Ali, through A1's card: separate AC and DC MCB choices. If Ali picks that, NEXT.md task 2
  follows B2's model PR (since 2026-10-28).
- Ali: ADR 0016 and ADR 0019 still say "Status: Proposed". Only Ali accepts ADRs, and A1
  offers him a batch card (since 2026-10-28).
- Ali: plan §6 Q30 (where a device's loose items go) and Q31 (group A–D rules stated only by
  example). Both run on the ADR 0014 defaults until Ali answers (since M2).

## Risks and unverified assumptions
- A3's #130 (M14, psa-devices 1.1.0, alternatives and DC-rated brand sets) is open. Per
  Q38 the spec example keeps its values, so the goldens should not move. This is
  unverified until #130 merges. A2's review of #130 notes that a DC-only brand
  (C60H-DC) can be picked for AC branches. A2 plans a model check; whether the engine
  (`ac_dist.py`, `mcb.py`) is involved depends on Ali's AC/DC choice card (NEXT.md 2).
- Shipped-library devices with a datasheet `inrush_a` and no `inrush_ms` count the
  inrush (ADR 0019 item 1b), which can give 6 A or 10 A branches. This is intended;
  M14's data should carry `inrush_ms`.

## Spec vs code
- No open disagreement of this role. The spec gaps live in plan §6 with their defaults:
  Q3, Q4, Q5, Q6 and Q8 run on their defaults and the check report warns where the
  example departs; Q7 was replaced by Q35/ADR 0019. Ask Ali, through A1, before changing
  either the spec or the code.
