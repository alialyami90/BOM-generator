# STATE — role 2, Input models and examples

| | |
| --- | --- |
| Name | A2 (successor: B2) |
| Date | 2026-10-28 |
| Branch | `claude/project-thread-8jbxpl-handoff` (docs only, from origin/main) |
| HEAD / origin/main | 9313db1 / 9313db1 (checkpoint commit on top) |

Other roles' current names: see ROSTER.md. Where docs say A1, A3, and so on, they mean
the role number. Owns: see `docs/agents.md` "Roles", row A2 (`src/bomgen/models/`, `src/bomgen/io/`,
`cli.py`, `build.py`, `examples/`, `docs/plan.md` section 3 and the M1 section).

## Merged (this role, v0.2)
- M13 library model: #97 (ADR 0017). Input voltage range, DC float: #104.
- M17 writers (ADR 0021): M17a #106 (`io/edit.py`), M17b #112 (`io/panel_edit.py`),
  M17c #115 (`io/fields.py`), M17d #119 (`io/lifecycle.py`).
- M18 model: #122 free-text loose items + `io/loose_edit.py` (ADR 0022); #124 wording.
- Reviewed and approved others: models part of #100 (A8).

## In review
- None of this role's own PRs are open (checked with `list_pull_requests`, 2026-10-28).
- A3's #130 (M14 library entries, psa-devices 1.1.0): A2 review posted 2026-10-28 as a
  COMMENT, no blockers. It waits on A1 to merge. The review raised three points:
  1. The DC-only C60H-DC brand can be chosen for AC branches. This is a model gap,
     and the follow-up is A2's (NEXT task 1).
  2. With the default iC60N `dc_rating_v: 125`, the example's `dc_float` check WARNs
     against the 140 V float. A1 or Ali to confirm.
  3. The full suite runs about 9 min on #130 against about 2 min on main.

## Uncommitted / in progress
- None. The branch `claude/project-thread-8jbxpl-loose-msg` (local and remote) is merged
  #124 and safe to delete. Earlier `-*` topic branches are all merged.

## What works (evidence: gate below)
- Every `examples/` file round-trips byte-identical (`tests/unit/test_round_trip.py`).
- Writers refuse an edit that adds a new located problem and keep file mode and comments.
- Loose items: library part or `description` (exactly one). A free-text item takes no
  `children` and no `fed_from` (`tests/unit/test_loose_edit.py`,
  `tests/unit/test_project_model.py`).

## Known gaps / risks
- **One MCB choice for AC and DC** (`CatalogueChoice.mcb`): a DC-only brand (no AC
  multiple) would also size the AC branches through `engine/ac_dist.py`. Not reported
  today. See NEXT task 1.
- `fed_from` accepts any panel id in the substation. `docs/ui/editing.md` says "a
  generated cabinet"; the UI restricts the choice (ADR 0022 point 4).
- `bomgen layout` still writes generated panel files with PyYAML (ADR 0021,
  Consequences).

## Verification
| Command (origin/main 9313db1, `docs/handoff` worktree) | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` | All checks passed; 270 files formatted | 2026-10-28 |
| `mypy` | no issues in 210 files | 2026-10-28 |
| `pytest` | 2414 passed, 0 failed, 0 skipped (2 min) | 2026-10-28 |
| `pytest tests/golden` | 94 passed | 2026-10-28 |
| `pytest` on #130 head 87eee46 | 2413 passed, 0 failed (9 min) | 2026-10-28 |
Not run: none of this role's code needs Windows or a GUI.

## Waiting on
- Ali: **Q23** (issued sheets vs masters, plan section 6). The default is the masters.
  Open since M1.
- A1: merge #130, then decide on point 2 above.
- A11: questions while it wires `loose_edit`, `panel_edit`, `fields` and `lifecycle`
  into the app. A1 made A2 its reviewer for those APIs (A1's message in this
  thread, 2026-10-28).

## Spec vs code
- Loose material is on its own sheet. This differs from the spec's sheet 4 and OUT-3,
  as ADR 0020 records (Ali, Q36). The spec update is not A2's to change. It is
  tracked in ADR 0020's Consequences.
