# STATE — role 2, Input models and examples

| | |
| --- | --- |
| Name | B2 |
| Date | 2026-10-28 |
| Branch | `claude/project-thread-cyo20r` (this session's only push branch; restarted on main per PR) |
| HEAD / origin/main | checkpoint commit on 55a0fd0 / 55a0fd0 |

Other roles' current names: see ROSTER.md. Owns: see `docs/agents.md` "Roles", row A2
(`src/bomgen/models/`, `src/bomgen/io/`, `cli.py`, `build.py`, `examples/`, `docs/plan.md`
section 3 and the M1 section).

## Merged (this role)
- v0.2, by A2: #97, #104 (M13); #106, #112, #115, #119 (M17 writers, ADR 0021); #122, #124
  (M18 model, ADR 0022).
- By B2, 2026-10-28:
  - #145 `McbBrand.ac_rated` (default true). The loader refuses an `ac_rated: false` brand
    as `catalogue_choice.mcb`.
  - #149 `io/yaml_source.py` parses each file text once (LRU of 64 texts, deep copy out).
    Full suite: main 2:10 → 1:04; #130's head 10:01 → 3:05.
  - #151 `catalogue_choice.mcb_dc` (Q39, ADR 0023 Proposed). `Catalogues.mcb_dc` and the
    `Catalogues.dc_mcb` property.
  - #152 `output.power_footnotes` on the substation (for role 10's Power Consumption
    sheet). The gis01 example carries the printer footnote.

## In review
- None of this role's PRs are open.

## Uncommitted / in progress
- None. Local topic branches `b2-*` are all merged and can be deleted.

## What works (evidence: gate below)
- Every `examples/` file round-trips byte-identical (`tests/unit/test_round_trip.py`).
- Writers refuse an edit that adds a located problem (ADR 0021).
- The MCB choice: `mcb` sizes AC and refuses a DC-only brand. `mcb_dc` (unset: follows
  `mcb`; `default`: the library's DC default) must resolve to a set with `dc_rating_v`
  (`tests/unit/test_catalogue_choice_loader.py`, `test_library_alternatives.py`).

## Known gaps / risks
- **The engine still sizes DC from `catalogues.mcb`.** Role 9 switches `engine/dc_dist.py`,
  `engine/mcb.py` and the `dc_float` check to `catalogues.dc_mcb` (A1 passes this on).
  Until then, `mcb_dc` loads and is checked but does not change the BOM.
- **The unset `mcb_dc` fallback is stored, not computed** (A1's note on #151). When `mcb`
  names a brand without `dc_rating_v`, `resolve_catalogues` puts it in `Catalogues.mcb_dc`
  via `model_copy`, which skips the `_dc_set_is_dc_rated` validator. Nothing re-validates
  a resolved library today. See NEXT task 1.
- #130 (role 3, M14 library) is still open. It must add `ac_rated: false` to
  `schneider-c60h-dc` (asked 2026-10-28).
- `fed_from` accepts any panel id (ADR 0022 point 4). `bomgen layout` writes generated
  panels with PyYAML (ADR 0021).

## Verification
| Command (origin/main 55a0fd0) | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` | All checks passed; 317 files formatted | 2026-10-28 |
| `python -m mypy` | no issues in 212 files | 2026-10-28 |
| `python -m pytest` | 2452 passed, 0 failed (1 min 12 s) | 2026-10-28 |
| `python -m pytest tests/golden` | 94 passed | 2026-10-28 |
Not run: nothing of this role's needs Windows or a GUI.

## Waiting on
- Ali: **Q23** (issued sheets vs masters, plan section 6). The default is the masters.
- Role 3: `ac_rated: false` on C60H-DC in #130.
- Role 11: questions on the writer APIs (A2 is its reviewer for them).

## Spec vs code
- Loose material is on its own sheet (ADR 0020, Q36). The spec update isn't role 2's.
