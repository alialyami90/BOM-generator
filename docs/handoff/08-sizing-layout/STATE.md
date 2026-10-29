# STATE: role 8, Sizing and layout engine

| | |
| --- | --- |
| Name | B8, retired 2026-10-29 (Ali retired every agent). The next agent is **C8**; at your own checkpoint, hand over to D8 |
| Branch | B8 used `claude/project-thread-3ttgw8`. Use whatever branch your session names; start it from `origin/main` and restart it from `origin/main` after each merge |
| origin/main at this checkpoint | `032bbea` (v0.2.1 released: `1678343 chore(release): version 0.2.1`) |
| Role-8 code last changed | `ef65800` (#100, M17 engine). Nothing in `engine/sizing.py`, `engine/layout.py` or `tests/golden/layout/` has changed since |
| Lead | B1 - Lead developer, thread `cmsg_01CGuLumA5u5e7gSGbisWmMiJaADCWuiNCb42qQHM1dpuv` (A1's thread is retired). If B1 is retired too, ask the coordinator who leads |

Code map, callers and tests: [MAP.md](MAP.md). Read it before changing anything.

## Merged (all reviewed and squash-merged by role 1)
- **#19 M1c**: `engine/sizing.py` (R1-R4), `engine/layout.py` (R5-R9), `bomgen layout`,
  `bomgen build --no-layout`, `with_layout`, golden `tests/golden/layout/` (Ali confirmed it).
- **#90 M12**: blank plate only under a rack block that ends in its active device (ADR 0013 R5 amendment).
- **#100 M17 engine**: `DeviceMove.position` / `PairMove.position`, every override pins its units,
  `PanelFill.is_pinned` / `PanelFill.position` (ADR 0013 R7 amendment). Merged as `ef65800`.
- **#135** checkpoint A8 to B8 (docs).
- **#176** plan section 3: `- { device: gps, panel: 1, position: 1 }` in the `layout.overrides`
  example (A2's review follow-up on #100). Merged by B1 as `125258b`. This closes the old NEXT task 1.
- This checkpoint (docs only): its PR number is in [the checkpoint](checkpoints/2026-10-29.md).

## Open PRs, branches, uncommitted work
None besides this checkpoint's PR. No role-8 work is in progress anywhere.

## What works (evidence: the verification table below)
- Sizing (L1 ranked then picked, L2 from kept units), generated port plans, the 32U fill with
  A/B streams, common devices spread, removals, overrides with positions and pins, blank plates,
  `port-capacity` / `replaced-panel` / `missing-panel` / `stale-*` issues, `panels:` list reconciliation.
- The desktop app drives the engine for the Panels board (drag and drop, keyboard moves, the
  Move dialog, pins, deletes, undo: A11's #126, #129) and for edits that re-lay out (A2's `io/edit.py`).
  It refuses a move when `layout_preview` with the candidate overrides reports a new error.

## Known bugs
None known. B1 asked role 8 to stand by for layout fixes from B11's editor work; none came
before the retirement (B11 shipped #198-#208 without touching the engine).

## Verification (2026-10-29, this session, on `origin/main` 032bbea)
| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | pass (345 files formatted) |
| `python3 -m mypy` | pass (224 source files) |
| `python3 -m pytest -q` | 2672 passed, 0 failed, 0 skipped (7 min) |
| `python3 -m pytest -q tests/golden` | 95 passed |
| `python3 -m pytest -q tests/unit/engine/test_sizing.py tests/unit/engine/test_layout.py tests/unit/engine/test_layout_cli.py tests/golden/layout` | 99 passed |

Not run: the Windows installer and the GUI (role 8 doesn't touch them).

## Files outside agents.md "Owns" that role 8 changed (all merged, all reviewed by role 1)
- `src/bomgen/cli.py` (A2's): `layout` command and `build --no-layout` (A1 allowed it).
- `src/bomgen/models/substation.py`, `schemas/substation.schema.json`, `tests/unit/test_substation_model.py`:
  the `position` fields (#100, proposed to A2, A2 reviewed).
- `tests/unit/app/test_app_network_api.py` (A11's): values that follow from M12 and #100.
- `docs/decisions/0013-network-sizing-and-panel-layout.md`: dated R5 and R7 amendments.
- `docs/superpowers/specs/2026-10-28-substations-and-auto-layout-design.md`: R1/R2/R10 example numbers after Ali's golden answer.
- `docs/plan.md` section 3 (A2's): the `position` example line (#176, B1 asked for it).
- Role 8's own: `tests/unit/engine/test_sizing.py`, `test_layout.py`, `test_layout_cli.py`,
  `docs/superpowers/plans/2026-10-28-m1c-sizing-and-layout.md` (agents.md: each agent owns its tests and plan).

## Blockers and waiting on
Nothing. Role 8 has no assigned task. B1's last instruction (2026-10-28 22:53 UTC): "Stand by for
layout fixes from B11's editor work." The loose-material "comes with" children (M18) are role 9's
and already exist (`LooseExtra.children`, `engine/kits.py`); B1 confirmed role 8 has no M18 task.

## Pending questions
None open for role 8. Q24-Q28 (substations/layout) and Q32 (cable managers vs 32U) are resolved
in `docs/plan.md`.

## Risks and unverified assumptions
- `Equipment.l2_ports` counts once per entry (R2 text), not per unit; an entry with `qty` > 1 and
  L2 ports would be under-counted. No example has one. If Ali ever adds one, ask him (card) whether
  R2 means per unit; see LESSONS.
- `src/bomgen/cli.py` and `build.py` are A2's. Ask role 2 or role 1 before touching them again.
- The app's board contract: a move must never re-flow devices other than the one moved. That is why
  overrides apply after the fill (R7). Any change to fill order breaks the board.

## Spec vs code
No open disagreement. The spec example shows 6 L1 switches per side; the rules give 3, and
Ali confirmed 3 for the layout golden (`tests/golden/layout/expected_panels.yaml` header).
