# STATE — role 2, Input models and examples

| | |
| --- | --- |
| Outgoing | B2 (retired 2026-10-29, when Ali retired every agent) |
| Successor | C2: read this file, then NEXT.md, LESSONS.md and `checkpoints/2026-10-29-b2.md` |
| Date | 2026-10-29 |
| Branch | `claude/project-thread-cyo20r` (B2's only push branch; restarted on main for each PR) |
| origin/main at handover | 032bbea (v0.2.1 released) |

Other roles' current names are in ROSTER.md. Role 2 owns the files in `docs/agents.md`
"Roles", row 2: `src/bomgen/models/`, `src/bomgen/io/`, `src/bomgen/cli.py`,
`src/bomgen/build.py`, `examples/`, `docs/plan.md`
section 3 and the M1 section, and this folder. Role 2 has also kept `schemas/` current, since
it is generated from the models. All PRs go to the lead (role 1) for review
and merge. Never ask Ali to merge.

## Open PRs, branches, uncommitted work
- **No open PRs** from this role. #187 and #189 (the last two) are squash-merged.
- **No uncommitted work.** Local topic branches `b2-*` from B2's container are merged,
  and the container is gone. `claude/project-thread-cyo20r` on origin holds only
  merged history plus this handoff PR.

## Merged by this role (newest first)
| PR | What | Where the decision lives |
| --- | --- | --- |
| #189 | `create_substation` seeds a blank substation with `generated_panels`, so the app's equipment editor can add the first rows (`Substation._consistent` refuses equipment without it, ADR 0013). `cabinet_number` (`<ID UPPER>-PSA-{n:04d}`) and the enclosure (the example's Rawabi Fixed Frame) are marked `# ASSUMED`. `options` are empty. A copy keeps its source's block. | B1 agreed to the values; they are unsourced (see "Waiting on") |
| #187 | Writers emit a mapping that gains its first entry in block style (no `{ }`), and write a repeated scalar (the register's issue dates) in full, with no `&id001` anchors. Found by B11 in #185. | `io/round_trip.py` `_Representer`, `set_entry` |
| #182 | `delete_project` refuses `.git`, the home folder and drive roots. It deletes only the files `.bomproj` export saved, plus `out/` and `__pycache__/`. It removes the folder only when it is empty. | ADR 0021 |
| #163 | `fields.part_users(substation, part_id)` lists every row that uses a part: equipment, panel devices (mirrors skipped), loose items and their children, and library children and loose_items. Asked for by B11. | — |
| #152 | `output.power_footnotes` on the substation (role 10 prints them). The gis01 example has the printer footnote. | Q40 |
| #151 | `catalogue_choice.mcb_dc`, `Catalogues.mcb_dc`, `Catalogues.dc_mcb` | Q39, ADR 0023 (Accepted) |
| #149 | `io/yaml_source.py` parses each file text once (an LRU of 64 texts, returning deep copies). Suite time halved. | LESSONS |
| #145 | `McbBrand.ac_rated` (default true). The loader refuses an `ac_rated: false` brand as `mcb`. | ADR 0023 |
| A2's | #97, #104 (M13); #106, #112, #115, #119 (M17 writers); #122, #124 (M18 loose items) | ADR 0017, 0021, 0022 |

## Code map (what lives where)
- `models/`: the pydantic v2 input models, all `extra="forbid"` (`_base.InputModel`).
  - `project.py`: project, register, defaults, output settings.
  - `substation.py`: substation, equipment, network, layout, `generated_panels`.
  - `panel.py`: panels and enclosures.
  - `library.py`: devices, catalogues, brand sets, `resolve_catalogues`.
  - `bom.py`, `calc.py`, `sheet.py`, `report.py`, `output.py`: the engine's output models. Roles 9 and 10 use these; role 2 owns the files.
- `io/loader.py`: `load_project`, `load_substation`, `load_library`, `load_inputs`. Each turns YAML into models plus located issues (`io/errors.py`).
- `io/references.py`: cross-file checks, such as unknown part ids, register keys, catalogue choices, mirrors, equipment and layout.
- `io/yaml_source.py`: reads YAML with line numbers, through the parse cache.
- `io/round_trip.py`: ruamel round-trip load and dump, keeping comments and byte-identical output (`load_text`, `dump_text`, `set_entry`, `edit_document`, `write_atomic`).
- Writers (ADR 0021), all refusing an edit that adds a problem:
  - `io/edit.py`: `edit_substation`, `commit`, enclosure/options/port plan/layout helpers.
  - `io/fields.py`: generic `set_field`, `insert_item`, `move_item`, `validate_field`, `assumed_fields`, `document_users`, `part_users`.
  - `io/panel_edit.py`, `io/loose_edit.py`, `io/mirror.py`, `io/lifecycle.py` (create or delete projects and substations).
- `io/schema.py` plus `bomgen schema`: write `schemas/*.json` from the models. Regenerate them in the same PR as any model change. No test compares the committed files, so a stale schema goes unnoticed. They were in sync at 032bbea.
- `cli.py`: the `validate`, `build`, `layout` and `schema` commands. `build.py`: inputs to workbook.

## What works (evidence: the gate below)
- Every `examples/` file round-trips byte-identical (`tests/unit/test_round_trip.py`).
- The golden test reproduces the spec's example values (`tests/golden`).
- A blank substation created by `create_substation` takes equipment and loads (`test_lifecycle.py`).
- The MCB choice:
  - `mcb` sizes AC and refuses a DC-only brand.
  - `mcb_dc` (unset: follows `mcb`; `default`: the library's DC set) must resolve to a set with `dc_rating_v`.
  - The engine now sizes DC from `catalogues.dc_mcb`: `engine/dc_dist.py`, `checks.py` and `app/projects.py` read it.
- `examples/library.yaml` marks `schneider-c60h-dc` `ac_rated: false` (role 3 did this in #130).

## Known gaps and risks
- **The unset `mcb_dc` fallback is stored, not computed.** When `mcb` names a brand with no `dc_rating_v`, `resolve_catalogues` (`models/library.py`) copies it into `Catalogues.mcb_dc` with `model_copy`. That skips the `_dc_set_is_dc_rated` validator. Re-validating a resolved library would refuse a project that loads today. NEXT task 1.
- `fed_from` accepts any panel id (ADR 0022 point 4), by design.
- `bomgen layout` writes generated panels with PyYAML, not the round-trip writer (ADR 0021), by design.
- A copied substation keeps the source's `generated_panels.cabinet_number`. A copy of gis01 therefore renders `861-GIS01-PSA-0001` too, and the user must edit it. B1 asked for this ("a copy keeps its source's block").

## Verification
| Command (origin/main 032bbea) | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` | All checks passed; 345 files formatted | 2026-10-29 |
| `python -m mypy` | no issues in 224 source files | 2026-10-29 |
| `python -m pytest -q -p no:cacheprovider` | 2672 passed, 0 failed (6 min 10 s) | 2026-10-29 |
| `python -m pytest tests/golden` | 95 passed | 2026-10-29 |

Not run: nothing of this role's needs Windows or a GUI.

## Waiting on
- **Ali, Q23** (issued sheets vs masters, plan section 6). The default is the masters. Act only on his answer.
- **Ali, possibly:** the unsourced `generated_panels` defaults from #189 (cabinet-number prefix, enclosure). B1 holds these to raise as one question if needed. Change `_blank` in `io/lifecycle.py` if Ali picks other values.

## Spec vs code
- Loose material is on its own sheet (ADR 0020, Q36). Updating the spec for it is not role 2's job.
