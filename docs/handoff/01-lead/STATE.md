# Role 1 (lead): state

- Name: A1 - Lead developer, handing over to B1. Date: 2026-10-28.
- Branch: per-topic branches `claude/project-thread-2fnqi0-<topic>`; this checkpoint is on
  `claude/project-thread-2fnqi0-checkpoint-b1`.
- origin/main at checkpoint: see the "Verification" table. Releases: v0.1.0 (2064227) and v0.1.1
  (135d7ee, published with the installer and default.bomlib). Since #153 a merged version bump with
  its CHANGELOG section builds, tags and publishes itself (ADR 0009, amended); no one pushes tags.

## Where v0.2 stands

Ali's ten v0.2 points are tracked in [`docs/backlog.md`](../../backlog.md), and the milestones
M12–M18 are in [`docs/plan.md`](../../plan.md) → "M12–M18 (v0.2)".

- Back end merged: M12 layout, M13 library model, M14 data in the example (#130), M15 MCB sizing,
  M16 store side, M17 writers, M18 loose model and sheet (#88–#129, #130).
- Q39 (Ali, 2026-10-28): DC MCB brand chosen apart from AC. Model #151 (ADR 0023, Proposed),
  engine #154 (group F and `dc_float` use `catalogues.dc_mcb`; CINC stays AC). #145 refuses a
  DC-only brand (`ac_rated: false`) as `mcb`.
- Other merges after the v0.1.1 tag: #149 YAML parse cache (suite 2 min → about 1 min), #152
  `output.power_footnotes` model.
- App merged: catalogue tabs, edit endpoints, board drag/drop and keyboard (point 9), Loose
  material page (#146, replaced #131).
- Numbering: next free ADR 0024, next free question Q40 ([`docs/agents.md`](../../agents.md)).

## Open PRs (2026-10-28 22:00)

| PR | Owner | State |
| --- | --- | --- |
| #155 Library device editor (M16 app, PR a) | B11 | CI, Windows build and B4's screen review pending |
| #157 Power footnote rows on the sheet | B10 | Code fine; held for Ali's print-area card |
| (coming) Q38 shipped library `data/library/` | A3 | Asked 21:50; also sets `ac_rated: false` on C60H-DC |
| (coming) README/CHANGELOG pass for #130–#154 | B7 | Asked 21:55 |

## Waiting on

- Ali: card "Should the printer footnote print on the Power Consumption sheet?" (21:53,
  recommended "Print it"; the spec says print area A1:L97). Decides #157.
- Ali, standing: Proposed ADRs 0004, 0005, 0007–0011, 0015–0019, 0021–0023. Offer one batch-accept
  card when he has time. Also B10's header-fit Print Preview check needs a card.
- Checkpoint refreshes asked of A3 (after Q38), B6 (after #153), B9 (after #154).

## Threads (route work here)

B2 `cmsg_01CGuLumA5u5e7gSGbisWmMi6PZvzPso7corbrGkzwhE7j`,
A3 `cmsg_01CGuLumA5u5e7gSGbisWmMiMn4Ay5kTA4wLV22n9mEuru`,
B4 `cmsg_01CGuLumA5u5e7gSGbisWmMi9aAhgzZ2TPaUfJEPHXE2iF`,
B5 `cmsg_01CGuLumA5u5e7gSGbisWmMiTNDc3q6MynAdyRny37PKC3`,
B6 `cmsg_01CGuLumA5u5e7gSGbisWmMi9TL26SYzpQs1CWS9qSpPPv`,
B7 `cmsg_01CGuLumA5u5e7gSGbisWmMi1Z9DLRFEw35bgfG7ruFWKo`,
B8 `cmsg_01CGuLumA5u5e7gSGbisWmMiWrgyedtbG3UzCXSmJ5mdJm`,
B9 `cmsg_01CGuLumA5u5e7gSGbisWmMiEVdwRwy2F5RdK8ptK2QkGn`,
B10 `cmsg_01CGuLumA5u5e7gSGbisWmMi5oJH7cuxNZWDrjADGPLnRU`,
B11 `cmsg_01CGuLumA5u5e7gSGbisWmMiSRmFy8hwGpYU6cXpyyR56y`.
`list_threads` shows the latest; the coordinator starts new threads as checkpoints merge.

## Verification

| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` | GATE_RUFF | 2026-10-28 |
| `PYTHONPATH=src python3 -m mypy` | GATE_MYPY | 2026-10-28 |
| `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider` | GATE_PYTEST | 2026-10-28 |
| `pytest tests/golden` | GATE_GOLDEN | 2026-10-28 |

Not run here: the Windows installer and GUI (Windows only). The CI "Build Windows installer"
job is the check for those.

## Risks and spec disagreements

- The spec master is a Claude Doc. ADR 0020 (loose material on its own sheet) and the other v0.2
  overrides (Q35, Q37, Q38, Q39, ADR 0022, ADR 0023) are not yet in the spec. That needs Ali,
  through the spec update process in [`docs/spec/`](../../spec/).
- `resolve_catalogues` stores the unset `mcb_dc` fallback via `model_copy`, skipping its
  validator (B2's NEXT task 1, not urgent).
- The app's settings forms and the library CSV don't show `mcb_dc` yet (ADR 0023 consequences).
