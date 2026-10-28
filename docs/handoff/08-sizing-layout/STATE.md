# STATE: role 8, Sizing and layout engine

| | |
| --- | --- |
| Name | B8 (took over from A8 on 2026-10-28). You are B8; at your own checkpoint, hand over to C8 |
| Branch | `claude/project-thread-21lj2r` (reused for every PR; restart it from `origin/main` after each merge) |
| HEAD at checkpoint | `aad6094` (= `origin/main`; gate run on `9313db1`, which differs only by the handoff skeleton #133); this checkpoint is a docs-only commit on the same branch; its PR is in the checkpoint file |
| origin/main | `aad6094` |

## Merged
- **#19 M1c**: `src/bomgen/engine/sizing.py` (R1-R4), `src/bomgen/engine/layout.py` (R5-R9), `bomgen layout`,
  `bomgen build --no-layout`, `with_layout`, golden `tests/golden/layout/` (Ali confirmed it).
- **#90 M12**: blank plate only under a rack block that ends in an active device (ADR 0013 R5 amendment).
- **#100 M17 engine**: `DeviceMove.position` / `PairMove.position`, every override pins its units,
  `PanelFill.is_pinned` / `PanelFill.position` (ADR 0013 R7 amendment). Merged as `ef65800`.

## In review / in progress / uncommitted
None. No open PR for role 8. Working tree clean apart from this checkpoint.

## What works (evidence: the verification table below)
- Sizing, layout, overrides with positions and pins, removals sized from kept units,
  `port-capacity` / `replaced-panel` / `missing-panel` issues, `panels:` list reconciliation.
- The app already uses the engine output: `src/bomgen/app/network.py` sends `pinned` and
  `position`, and `screens-panels.js` draws plates from `plate_below_u` (A11's files).

## Known bugs
None known.

## Verification (2026-10-28, this session, on `origin/main` 9313db1)
| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | pass (270 files formatted) |
| `python3 -m mypy` | pass (210 source files) |
| `python3 -m pytest -q` | 2414 passed, 0 failed, 0 skipped |
| `python3 -m pytest -q tests/golden` | 94 passed |
| `python3 -m pytest -q tests/unit/engine/test_sizing.py tests/unit/engine/test_layout.py tests/unit/engine/test_layout_cli.py tests/golden/layout` | 99 passed |

Not run: the Windows installer and the GUI (role 8 doesn't touch them).

## Files outside agents.md "Owns" that role 8 changed (all merged, all reviewed by A1)
- `src/bomgen/cli.py`: `layout` command and `build --no-layout` (A1 allowed it).
- `src/bomgen/models/substation.py`, `schemas/substation.schema.json`, `tests/unit/test_substation_model.py`:
  the `position` fields (#100, proposed to A2, A2 reviewed).
- `tests/unit/app/test_app_network_api.py` (A11's): values that follow from M12 and #100.
- `docs/decisions/0013-network-sizing-and-panel-layout.md`: dated R5 and R7 amendments.
- `docs/superpowers/specs/2026-10-28-substations-and-auto-layout-design.md`: R1/R2/R10 example numbers after Ali's golden answer.
- Role 8 also owns (per its brief) `tests/unit/engine/test_sizing.py`, `test_layout.py`, `test_layout_cli.py`
  and `docs/superpowers/plans/2026-10-28-m1c-sizing-and-layout.md`; agents.md "Owns" doesn't list them.

## Blockers and waiting on
- Waiting on A1 (since 2026-10-28 18:50 UTC): the next M17 or M18 engine task. Nothing blocked.
  Reach A1 with `message_thread` to thread `cmsg_01CGuLumA5u5e7gSGbisWmMi3nTuZbpZkUB1t4T5nt6GfE`
  ("A1 - Lead developer"). A8 asked on 2026-10-28 with this checkpoint; read A1's reply there first.

## Risks and unverified assumptions
- `Equipment.l2_ports` counts once per entry (R2 text), not per unit; an entry with `qty` > 1 and
  L2 ports would be under-counted. No example has one. See LESSONS.
- agents.md "Owns" for role 8 omits the test files and the `layout` CLI command; A8 told A1 with this checkpoint.

## Spec vs code
No open disagreement. The spec example shows 6 L1 switches per side; the rules give 3, and
Ali confirmed 3 for the layout golden (`tests/golden/layout/expected_panels.yaml` header).
