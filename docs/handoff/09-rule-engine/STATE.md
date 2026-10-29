# STATE: role 9, BOM rule engine

| | |
| --- | --- |
| Name | B9 - BOM rule engine, handing over to **C9 - BOM rule engine** (Ali retired every agent, 2026-10-29) |
| Date | 2026-10-29 |
| Branch | `claude/project-thread-q31ztb` (B9's thread branch), restarted from origin/main for this checkpoint |
| HEAD / origin/main at checkpoint | 032bbea / 032bbea (the checkpoint commit goes on top) |
| Lead | B1 - Lead developer, thread `cmsg_01CGuLumA5u5e7gSGbisWmMiJaADCWuiNCb42qQHM1dpuv` (A1's thread is retired). Find the current lead in [`../ROSTER.md`](../ROSTER.md), row 1. |

## What role 9 owns

From `docs/agents.md` → "Roles", row A9 (numbers, not letters, carry the rights: C9 = A9):

- `src/bomgen/engine/`, except A8's `sizing.py` and `layout.py`.
- `src/bomgen/checks.py` (step 15 check report) and `src/bomgen/revision.py` (OUT-8 revision comparison).
- `src/bomgen/models/bom.py`, `calc.py`, `output.py`, `report.py` (the engine's output models).
- `tests/golden/` except `tests/golden/layout/` (A8's). `tests/golden/test_cli_build.py` was written by
  A2 with notice; tell role 2 before changing it.
- `tests/unit/test_revision.py` and the engine tests in `tests/unit/engine/` (A8 has `test_sizing.py`,
  `test_layout.py`, `test_layout_cli.py`). `tests/unit/engine/engine_factories.py` is role 9's test helper.
- In `docs/plan.md`: the M2, M3 and M4 sections, the M7 engine note and the M15 section.
- This folder and row 9 of `docs/handoff/ROSTER.md`.
- The free-text loose line in `engine/kits.py` came with A2's #122 (ADR 0022). It lives in role 9's
  file, but tell role 2 before changing its behaviour.

Not role 9's, though it calls into the engine: `src/bomgen/build.py`, `cli.py`, `models/library.py`,
`models/project.py`, `models/panel.py`, `io/` and `examples/` (role 2); `sheets/` and `writer/` (role 10,
which consumes `BuildResult`: tell role 10 before changing its shape); `app/` (role 11);
`data/library/` and `data/device-db/` (role 3).

## Code map (role 9's modules)

The order follows the spec's "Data model and generation order". `engine/pipeline.py` `build(loaded) -> BuildResult` runs steps 1–12. Callers are
`build.py` (`bomgen build`), `app/output.py` and `app/preview.py`.

| Module | What it does |
| --- | --- |
| `engine/units.py` | step 1: expands a panel's device instances into tagged `DeviceRow`s |
| `engine/tags.py` | tag naming (`<PANEL>-<LEVEL>-<TYPE>-<LAN><NN>`, `tag_pattern`, panel overrides) |
| `engine/enclosure.py` | group A: the enclosure row |
| `engine/kits.py` | step 2: device rows with kit children (group B), and the loose-material table (`loose_table`, None when it has no rows) |
| `engine/network.py` | group C: SFPs, cable managers, serial cables |
| `engine/housekeeping.py` | group D: lamp, fans, filters, thermostats, IPR kit, change-over diodes, socket |
| `engine/ac_dist.py` | group E: CINC and the AC branches, sized from `catalogues.mcb` |
| `engine/dc_dist.py` | group F: Q1/Q2 mains, Q1.n/Q2.n branches, spares, QCODs, plus `branch_sizing` (ADR 0019), all from `catalogues.dc_mcb` (ADR 0023) |
| `engine/mcb.py` | `rating_at_least`, `rating_above` and `mcb_line` take an `McbCatalogue`; also the aux contact rows and `alarms_wired` |
| `engine/terminals.py` | group G: terminal strips (X1, X3-AC, X4-DC1/DC2, XDIN and others) |
| `engine/grounding.py` | group H: grounding busbars |
| `engine/assemble.py` | step 11: separators and SR.NO in group order |
| `engine/power.py` | step 4: Power Consumption rows and totals (2,177.5 W DC, 1,090.3 W AC on the example) |
| `engine/thermal.py` | heat checks and the ventilation choice (forced and natural) |
| `engine/items.py`, `errors.py` | `BomItem` with kit children and `flatten`; `EngineError` for inputs that can't produce a BOM |
| `checks.py` | `check_report(loaded, result) -> CheckReport`. The check ids are `sfp_slots`, `dc_main`, `branch_mcb`, `dc_float`, `airflow`, `natural_convection`, `line_up`, `di_capacity`, `library_version`. It also has `render_text` and `render_json` |
| `revision.py` | `read_previous_issue(path)`, `compare_with_previous(...)` and `render_revisions` (ADR 0016) |

## Merged (this role, oldest first)
- M2 groups A–D #22; M3 groups E–H, HWIO, assembly #36; M4 power and heat #44; follow-ups #46.
- M7 engine half: check report and revision comparison #58 (ADR 0016). Q34 resolved and ADR 0014 accepted #67.
- M15 branch MCB sizing from device data #103 (ADR 0019, Q35).
- DC float-voltage checks (`dc_float`, ADR 0019 item 7, Q37) #109.
- M18 engine part: no loose-material table when it has no rows #123.
- ADR 0023 engine side (Q39, separate AC and DC MCB brands) #154 (f319f64, B9). Group F, branch sizing
  and the `dc_float` MCB item use `catalogues.dc_mcb`. Group E (AC branches and CINC) keeps
  `catalogues.mcb`, because CINC is the "Main Auxiliary AC Supply" breaker.
- Shipped-library sizing tests #171 (8be24d5, B9): `tests/unit/engine/test_engine_shipped_library.py`.
  With `data/library/psa-devices.yaml`, the SEL-3555-GW, SEL-3555-RTAC and SEL-3355 branches come out at
  6 A, set by inrush (20 A ÷ the iC60N DC trip multiple 9.05 = 2.2 A). Their feeds' spares are 6 A, the
  QCOD spares and every other branch stay at 2 A, and the mains are unchanged. `dc_float` warns for
  the iC60N (125 V) and the FGR-60F (125 V input), both accepted by Ali (Q37, Q41). No engine change
  was needed.
- Handoff checkpoints #141 and #159, and this one.

## In review / in progress / uncommitted
- **No open PR of role 9** apart from this checkpoint PR, "docs(handoff): final B9 handoff 2026-10-29".
  If it is still open, find it with `list_pull_requests` state=open.
- Working tree clean apart from this checkpoint. No stash.
- Remote branches: `claude/project-thread-q31ztb` is B9's. All of its work is merged, and after
  this PR it holds only merged history. `claude/project-thread-9l1061` is A9's old branch, also
  fully merged (#123 era). Neither needs anything. Don't delete either without the lead's say-so.
- Since #154, the only commit by another role that touched role 9's files is #157 (role 10, power
  footnotes). It added footnote fields that the sheets read; ask role 10 if you touch `models/calc.py`
  power models.

## What works (evidence: the verification table)
- The example build reproduces the spec's values, and the goldens cite their sections:
  - 2,177.5 W DC and 1,090.3 W AC, with the heat totals (`tests/golden/test_engine_power_heat.py`);
  - groups A–H (`expected_groups_a_d.py`, `expected_groups_e_h.py`, `test_engine_groups_*.py`);
  - the check report (`test_check_report.py`: 0 failed, 50 branch MCBs at 2 A, the iC60N `dc_float`
    WARN at 125 V against 140 V, and two `dc_main` WARNs where the workbook's 16 A mains differ from
    the rule's 10 A, Q3).
- `bomgen build` prints "0 failed, 3 warnings, 64 passed" on the example (`tests/golden/test_cli_build.py`).
- Revision round trip against a written issue (`tests/golden/test_revision_round_trip.py`).
- ADR 0023 brand choices: `test_engine_dc_dist.py` covers `mcb_dc` unset, `mcb_dc: default` and a named
  brand; `test_engine_ac_dist.py` checks that AC keeps `mcb`; `test_checks.py` checks the float check
  on the DC set.
- Shipped-library sizing: `test_engine_shipped_library.py` (see Merged).

## Broken / known bugs
- None known in role 9's code.

## Verification
| Command | Result | Date |
| --- | --- | --- |
| `python -m ruff check . && python -m ruff format --check .` | All checks passed; 345 files formatted | 2026-10-29 |
| `python -m mypy` | no issues in 224 source files | 2026-10-29 |
| `python -m pytest -q` | 2672 passed, 0 failed, 0 skipped (342 s) | 2026-10-29 |
| `python -m pytest -q tests/golden` | 95 passed (94 at #171; role 10's #157 added one in `tests/golden/test_workbook.py`) | 2026-10-29 |

The gate ran at 032bbea (main, v0.2.1). Nothing was left unrun: role 9 has no GUI or Windows-only
parts. The golden tests need `pycel`, so run `pip install -e '.[dev]'` first. The full suite takes
about 6 minutes in a cloud container, so run it in the background; the golden tests take about 5 s.

## Waiting on
- Nothing. Every question role 9 raised is resolved: Q3–Q8 run on their defaults, and Q30, Q31, Q35,
  Q37, Q39 and Q41 are in plan §6. ADRs 0014, 0016, 0019 and 0023 are Accepted (Ali, 2026-10-28).

## Risks and unverified assumptions
- The DC aux contacts still come from `aux_contact`, even when `mcb_dc` names another brand (ADR 0023,
  consequences). A DC brand whose contacts differ would need its own `aux_contact` choice. Nobody has
  asked for that.
- The app's Catalogues tab (`app/catalogues.py`, role 11) lists only `catalogues.mcb`. A1 accepted that
  for now.
- Shipped-library devices with a datasheet `inrush_a` and no `inrush_ms` count the inrush (ADR 0019 item
  1b), which gives 6 A where the example has 2 A. This is intended. If role 3 adds `inrush_ms` values
  under `inrush_min_ms` (10 ms), those branches drop back to the floor, and
  `test_engine_shipped_library.py` will say so. Update its expectations then, not the engine.
- `test_engine_shipped_library.py` copies `examples/` to a temp dir and swaps in the shipped library.
  If role 2 changes `examples/` or role 3 regenerates `data/library/psa-devices.yaml`
  (`python data/library/build.py`), recheck it first.

## Spec vs code
- No open disagreement. The spec gaps are in plan §6 with their answers or defaults. Q3, Q4, Q5, Q6 and
  Q8 run on their defaults, and the check report warns where the example departs. Q7 was replaced by
  Q35 and ADR 0019. If code and spec disagree, ask Ali through the lead before changing either
  (CLAUDE.md).
