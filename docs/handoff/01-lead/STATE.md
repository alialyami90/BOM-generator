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

- Back end merged: M12 layout, M13 library model, M14 data (#130) and the shipped library
  `data/library/psa-devices.yaml` with datasheet figures (#161, Q38), M15 MCB sizing, M16 store
  side plus device-record edits (#164) and the CSV `ac_rated` fix (#165), M17 writers and
  `part_users` (#163), M18 loose model and sheet (#88–#130).
- Q39 (Ali, 2026-10-28): DC MCB brand chosen apart from AC. Model #151 (ADR 0023, Proposed),
  engine #154 (group F and `dc_float` use `catalogues.dc_mcb`; CINC stays AC). #145 refuses a
  DC-only brand (`ac_rated: false`) as `mcb`.
- Also merged after the v0.1.1 tag: #149 YAML parse cache, #152 `output.power_footnotes` model,
  #153 release from main, docs #158, #160, #168, ADR 0018 amendment #170.
- App merged: catalogue tabs, edit endpoints, board drag/drop and keyboard (point 9), Loose
  material page (#146), Library device editor (#155, M16 PR a).
- Numbering: next free ADR 0024, next free question Q40 ([`docs/agents.md`](../../agents.md)).

## Open PRs (2026-10-28 22:30)

| PR | Owner | State |
| --- | --- | --- |
| #157 Power footnote rows on the sheet | B10 | Code fine, gate green; held for Ali's print-area card |
| #166 Library list editing, Add, Delete, In use (M16 a2) | B11 | B4's fixes in 29a05ba; needs CI and Windows build |
| #171 MCB sizing tests on the shipped library | B9 | Tests only; local gate green; CI running |

## Waiting on

- Ali: card "Should the printer footnote print on the Power Consumption sheet?" (21:53,
  recommended "Print it"; the spec says print area A1:L97). Decides #157.
- Ali, standing: Proposed ADRs 0004, 0005, 0007–0011, 0015–0019, 0021–0023. Offer one batch-accept
  card when he has time. Also B10's header-fit Print Preview check needs a card.
- Every role's checkpoint is current (latest: #150, #156, #159, #167, #169, #172).
- Data finding from B9 (#171): FGR-60F's input goes only to 125 V DC, below the 140 V float, so
  `dc_float` warns for it as for the iC60N. Not routed yet (NEXT item 2).

## Threads (route work here)

B2 `cmsg_01CGuLumA5u5e7gSGbisWmMi6PZvzPso7corbrGkzwhE7j`,
A3 (signs as B3) `cmsg_01CGuLumA5u5e7gSGbisWmMiMn4Ay5kTA4wLV22n9mEuru`,
B4 `cmsg_01CGuLumA5u5e7gSGbisWmMi9aAhgzZ2TPaUfJEPHXE2iF`,
B5 `cmsg_01CGuLumA5u5e7gSGbisWmMiTNDc3q6MynAdyRny37PKC3`,
B6 `cmsg_01CGuLumA5u5e7gSGbisWmMiHdmiF2zR4D9rPGYUSRQDkT`,
B7 `cmsg_01CGuLumA5u5e7gSGbisWmMi1Z9DLRFEw35bgfG7ruFWKo`,
B8 `cmsg_01CGuLumA5u5e7gSGbisWmMiWrgyedtbG3UzCXSmJ5mdJm`,
B9 `cmsg_01CGuLumA5u5e7gSGbisWmMiEVdwRwy2F5RdK8ptK2QkGn`,
B10 `cmsg_01CGuLumA5u5e7gSGbisWmMi5oJH7cuxNZWDrjADGPLnRU`,
B11 `cmsg_01CGuLumA5u5e7gSGbisWmMiSRmFy8hwGpYU6cXpyyR56y`.
Retired A threads (A2, A4–A11) must not act; if one does, tell the coordinator.
`list_threads` shows the latest; the coordinator starts new threads as checkpoints merge.

## Verification

| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` | All checks passed; 328 files formatted (on ad7d137) | 2026-10-28 |
| `PYTHONPATH=src python3 -m mypy` | no issues in 217 source files | 2026-10-28 |
| `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider` | 2525 passed, 0 failed, 0 skipped (268 s) | 2026-10-28 |
| `pytest tests/golden` | 94 passed | 2026-10-28 |

Not run here: the Windows installer and GUI (Windows only). The CI "Build Windows installer"
job is the check for those.

## Risks and spec disagreements

- The spec master is a Claude Doc. ADR 0020 (loose material on its own sheet) and the other v0.2
  overrides (Q35, Q37, Q38, Q39, ADR 0022, ADR 0023) are not yet in the spec. That needs Ali,
  through the spec update process in [`docs/spec/`](../../spec/).
- `resolve_catalogues` stores the unset `mcb_dc` fallback via `model_copy`, skipping its
  validator (B2's NEXT task 1, not urgent).
- The app's settings forms and the library CSV don't show `mcb_dc` yet (ADR 0023 consequences).
