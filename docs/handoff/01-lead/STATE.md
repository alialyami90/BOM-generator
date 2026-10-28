# Role 1 (lead): state

- Name: A1 - Lead developer, handing over to B1. Date: 2026-10-28.
- Branch: per-topic branches `claude/project-thread-2fnqi0-<topic>`; this checkpoint is on
  `claude/project-thread-2fnqi0-checkpoint-b1`.
- origin/main at checkpoint: ded5fe4. Release tags: v0.1.0 (2064227), v0.1.1 (9313db1, run
  cancelled before publish; see "Waiting on").

## Where v0.2 stands

Ali's ten v0.2 points are tracked in [`docs/backlog.md`](../../backlog.md), and the milestones
M12–M18 are in [`docs/plan.md`](../../plan.md) → "M12–M18 (v0.2)".

- Back end merged: M12 layout (#90, #100, #101), M13 library model (#97), M15 MCB sizing
  (#103, #109), M16 store side (#105, #113, #114, #116, #118, #120, #127), M17 writers and
  lifecycle (#106, #112, #115, #119), M18 loose model and sheet (#96, #108, #122, #123, #124),
  M14 research data (#121).
- App merged: catalogue tabs (#93), edit endpoints (#117), board drag/drop, keyboard and Move…
  (#126, #129; point 9 done).
- Decisions this session (plan §6): Q35 (computed sizing, 2 A floor, spikes under 10 ms
  ignored), Q36 (own sheet), Q37 (keep iC60N; DC ranges as brand sets; float-voltage warning),
  Q38 (datasheet data in the shipped library only). ADRs 0017–0022 numbered; next free ADR
  0023, next free question Q39 ([`docs/agents.md`](../../agents.md) numbering table).

## Open PRs (2026-10-28 20:50)

| PR | Owner | State |
| --- | --- | --- |
| #130 M14 library entries | A3 | Gate and CI green; A2 reviewed (notes in NEXT §3); waiting on B5; held for v0.1.1 |
| #131 Loose material page | A11/B11 | Not reviewed; needs Windows build; held for v0.1.1 |
| #140 B7 checkpoint | A7 | ROSTER conflict; A7 asked to merge main |
| (coming) v0.1.1 CHANGELOG | A7 | Requested 20:47 |
| (coming) roles 3 and 9 checkpoints | A3, A9 | Not yet opened |

## Waiting on

- Ali: card "Should projects choose the DC MCB brand separately from the AC one?" (20:43,
  recommended "Separate AC and DC choices").
- Ali: re-tag v0.1.1 at the commit that has A7's changelog. Ali said "Dont release with a
  missing changlog" (to A6). A6 cancelled run 40765665083 before publish.
- A7: CHANGELOG 0.1.1 covering #88–#129. A3: the Q38 follow-up after #130.
  B2: the `McbBrand.ac_rated` guard.
- Ali, standing: 13 ADRs still "Proposed" (0004, 0005, 0007–0011, 0015–0019, 0021, 0022).
  Not urgent; offer him a batch-accept card when he has time.

## Threads (route work here; old A2, A4, A8, A10, A11 threads are retired)

B2 `cmsg_01CGuLumA5u5e7gSGbisWmMi6PZvzPso7corbrGkzwhE7j`,
B4 `cmsg_01CGuLumA5u5e7gSGbisWmMi9aAhgzZ2TPaUfJEPHXE2iF`,
B8 `cmsg_01CGuLumA5u5e7gSGbisWmMiWrgyedtbG3UzCXSmJ5mdJm`,
B10 `cmsg_01CGuLumA5u5e7gSGbisWmMi5oJH7cuxNZWDrjADGPLnRU`,
B11 `cmsg_01CGuLumA5u5e7gSGbisWmMiSRmFy8hwGpYU6cXpyyR56y`.
A3, A5→B5, A6, A7 and A9 are in their current threads; `list_threads` shows the latest.
The coordinator starts B threads as checkpoints merge; tell it each merge.

## Verification

| Command (on origin/main ded5fe4) | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` | All checks passed; 296 files formatted | 2026-10-28 |
| `PYTHONPATH=src python3 -m mypy` | no issues in 210 source files | 2026-10-28 |
| `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider` | 2414 passed, 0 failed, 0 skipped (147 s) | 2026-10-28 |
| `pytest tests/golden` | 94 passed | 2026-10-28 |

Not run here: the Windows installer and GUI (Windows only). The CI "Build Windows installer"
job is the check for those.

## Risks and spec disagreements

- The spec master is a Claude Doc. ADR 0020 (loose material on its own sheet) and the other v0.2
  overrides (Q35, Q37, Q38, ADR 0022) are not yet written into the spec. That needs Ali, through
  the spec update process in [`docs/spec/`](../../spec/).
- The test suite gets slower with #130 (NEXT §3).
