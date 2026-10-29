# STATE: the whole team

One file for every role's state. It merges the per-role `STATE.md` files, the roster, role 3's
reference notes and role 8's code map, as they stood at the final handover on 2026-10-29. Read it
first, then [NEXT.md](NEXT.md), [LESSONS.md](LESSONS.md) and [CHECKPOINT.md](CHECKPOINT.md).

Stable knowledge stays where it lives ([`CLAUDE.md`](../../CLAUDE.md), [`docs/agents.md`](../agents.md),
[`docs/plan.md`](../plan.md), [`docs/spec/`](../spec/), the ADRs in [`docs/decisions/`](../decisions/));
these files link to it rather than copy it.

## 1. Project-wide state (2026-10-29)

- **Ali retired every agent on 2026-10-29 (13:50 UTC).** Every role is unstaffed. The next holder of
  a role starts with no history and takes the next letter (role 1's next holder is C1, and so on).
  Rights go by role number: C1 has A1's rights in `docs/agents.md`.
- Repo `alialyami90/BOM-generator`, default branch `main`. origin/main at the handover:
  `032bbea` (#212, README status for v0.2.1), plus the role-handoff PRs #213–#223 (docs only).
- **Open PRs: none. Uncommitted or unmerged work: none, in any role.** Old `claude/*` branches on
  origin hold only squash-merged history; don't delete them without the lead's say-so.
- **Releases.** v0.1.0 (tag on `2064227`), v0.1.1 (`135d7ee`), v0.2.0 (`f65a5fe`, #195, the first
  release from main) and **v0.2.1** (`1678343`, #211, published 2026-10-29 03:17 UTC with
  `bomgen-setup-0.2.1.exe`, 29.7 MB, and `default.bomlib` built from psa-devices 1.1.0):
  https://github.com/alialyami90/BOM-generator/releases/tag/v0.2.1. `pyproject.toml` and
  `bomgen.__version__` are `0.2.1`. Check tags with `git ls-remote origin 'refs/tags/v0.2*'`.
- **Product.** v0.1 is M0–M11 (engine, sheets, checks, desktop app, installer). v0.2 is Ali's ten
  points on v0.1.0 ([`docs/backlog.md`](../backlog.md), all "Done in v0.2.0"; milestones M12–M18 in
  `docs/plan.md`): layout fixes, alternatives as library parts with per-project/substation brand
  sets (ADR 0017), a separate DC MCB brand (ADR 0023), the shipped library psa-devices 1.1.0 in
  `data/library/` (Q38), branch MCB sizing from running and inrush current (ADR 0019), in-app
  library editing with local versions and CSV (ADR 0018), in-app project/substation/panel editing
  with round-trip writers (ADR 0021), and the loose material sheet and page (ADR 0020, ADR 0022).
  v0.2.1 is the UI polish pass from [`docs/ui/polish-v02.md`](../ui/polish-v02.md) (items 1–16,
  #205–#208) plus #194, #198–#201.
- **Numbers.** ADRs 0001–0023 are all Accepted (Ali accepted the last 15 in #184); next free ADR
  **0024**. Open questions Q1–Q41 are resolved; next free question **Q42**. Next milestone after M18
  is **M19**. The number table is in `docs/agents.md` → "Numbers".
- **Changelog** is current through #211; `[Unreleased]` is empty.
- **Next feature work waits on Ali's testing feedback on v0.2.1** (README "Status" says so).

### Verification at the handover (origin/main `032bbea`)

Every role ran the gate on the same tree and got the same result:

| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | All checks passed; 345 files formatted |
| `python -m mypy` | no issues in 224 source files |
| `python -m pytest -q -p no:cacheprovider` | 2672 passed, 0 failed, 0 skipped (5–7 min) |
| `python -m pytest -q tests/golden` | 95 passed |
| `pytest tests/unit/library_store tests/unit/test_bundle_container.py` | 378 passed (role 5) |
| `pytest` on role 8's sizing/layout tests and `tests/golden/layout` | 99 passed (role 8) |
| `pytest tests/unit/sheets tests/unit/writer` | 139 passed (role 10) |
| `python data/library/build.py` | no diff (role 3) |
| `node --check src/bomgen/app/ui/*.js` and Playwright E2E | pass, no console errors (role 11, on `2d74d45`, same app tree) |
| `impeccable detect --json` on `src/bomgen/app/ui` and `docs/ui/prototype` | `[]` (role 4, at #204 `de69ec0`) |

CI on #211 (the v0.2.1 bump): ruff, mypy, pytest and "Build Windows installer" all green. Not run
in the Linux sessions: the Windows installer, the WebView2 window and real Excel. The CI job
"Build Windows installer" is the check for the first two.

### Waiting on Ali

- **"What after v0.2.1?"** B1's card (`cmsg_01CGuLumA5u5e7gSGbisWmMi8kT7H49pypGPBmn8yWT6TM`, "What
  should the team do after v0.2.0?") is unanswered and lives in the retired B1 thread, so an answer
  can't reach a new lead. NEXT.md item 1.1.
- **Q11 header fit** (role 10): does the calc-sheet header overlap the table in Excel's Print
  Preview? No card sent yet.
- **Q23** (issued sheets vs masters, plan §6): the default is the masters. Act only on an answer.
- **ASSUMED seed values** for a new substation (roles 1 and 2), see "Known gaps" below.

### Known gaps and risks (not blocking, worth raising with Ali)

- **The spec is behind the code.** The spec master is a Claude Doc ([`docs/spec/`](../spec/) says how to
  update it). The v0.2 overrides live only in ADRs 0017, 0019, 0020, 0022, 0023 and Q35, Q37–Q41.
  Updating the spec needs Ali's go-ahead (CLAUDE.md).
- **ASSUMED seeds.** `src/bomgen/io/lifecycle.py` `_blank` seeds a new substation with
  `generated_panels`, a cabinet number pattern `f"{substation_id.upper()}-PSA-{{n:04d}}"`, the
  example's Rawabi Fixed Frame enclosure and document numbers/dates, each with an `# ASSUMED` YAML
  comment (#189, #192). No source gives these.
- The Windows installer and GUI can't run in the Linux sessions; "Build Windows installer" (which
  also runs the launcher self-test, #186) is their check.

### Roles at the handover

Roles, ownership and rules are in [`docs/agents.md`](../agents.md) → "Roles". The letter counts context
resets (A, B, C, … Z, AA); a refresh keeps the letter, a reset or retirement moves to the next one.

| Role | Last holder | Next holder | Last thread (retired, read-only via `read_thread`) |
| --- | --- | --- | --- |
| 1 Lead developer | B1 | C1 | `cmsg_01CGuLumA5u5e7gSGbisWmMiJaADCWuiNCb42qQHM1dpuv` |
| 2 Input models and examples | B2 | C2 | `cmsg_01CGuLumA5u5e7gSGbisWmMi6PZvzPso7corbrGkzwhE7j` |
| 3 Device database researcher | B3 | C3 | `cmsg_01CGuLumA5u5e7gSGbisWmMiMn4Ay5kTA4wLV22n9mEuru` (titled A3) |
| 4 UI designer | B4 | C4 | `cmsg_01CGuLumA5u5e7gSGbisWmMi9aAhgzZ2TPaUfJEPHXE2iF` |
| 5 Library update packages | B5 | C5 | `cmsg_01CGuLumA5u5e7gSGbisWmMiTNDc3q6MynAdyRny37PKC3` |
| 6 Windows installer and release | B6 | C6 | `cmsg_01CGuLumA5u5e7gSGbisWmMiHdmiF2zR4D9rPGYUSRQDkT` |
| 7 Lead developer assistant | B7 | C7 | `cmsg_01CGuLumA5u5e7gSGbisWmMi1Z9DLRFEw35bgfG7ruFWKo` |
| 8 Sizing and layout engine | B8 | C8 | `cmsg_01CGuLumA5u5e7gSGbisWmMiWrgyedtbG3UzCXSmJ5mdJm` |
| 9 BOM rule engine | B9 | C9 | `cmsg_01CGuLumA5u5e7gSGbisWmMiEVdwRwy2F5RdK8ptK2QkGn` |
| 10 Excel workbook writer | B10 | C10 | `cmsg_01CGuLumA5u5e7gSGbisWmMi5oJH7cuxNZWDrjADGPLnRU` |
| 11 Desktop app | B11 | C11 | `cmsg_01CGuLumA5u5e7gSGbisWmMiSRmFy8hwGpYU6cXpyyR56y` |

Older retired threads: A1 `cmsg_01CGuLumA5u5e7gSGbisWmMi3nTuZbpZkUB1t4T5nt6GfE`, A6
`cmsg_01CGuLumA5u5e7gSGbisWmMi9TL26SYzpQs1CWS9qSpPPv`, A5 `cmsg_01CGuLumA5u5e7gSGbisWmMi4GsrhHJfEnM1ZoKq6Av5HP`,
A8 `cmsg_01CGuLumA5u5e7gSGbisWmMiHgm9Qm4pLo8R5GdLXizMMu`, A11 `cmsg_01CGuLumA5u5e7gSGbisWmMiWeWKSTZqDbuAfYdwHEZoYc`.
New holders get new threads from the coordinator; find them with `list_threads`. A message to a
retired thread is lost.

### How a release happens (ADR 0009, amended by #153)

1. Role 7 merges a docs PR with a `## [x.y.z] - YYYY-MM-DD` CHANGELOG section and updated compare
   links. No agent names; version bumps, docs, chore and refactor PRs get no entry. Ali's rule:
   never release without a changelog section.
2. Role 6 opens the bump PR, which changes only `version` in `pyproject.toml`, `__version__` in
   `src/bomgen/__init__.py` and the assert in `tests/test_package.py` (examples #195, #211). Not
   before the lead says go, because merging it publishes.
3. Role 1 squash-merges it once CI and "Build Windows installer" are green. The push to main runs
   `release.yml` (path-filtered to those version and changelog files):
   - `plan` reads `__version__`. If tag `vX.Y.Z` exists it builds nothing; otherwise it checks
     pyproject agrees and the CHANGELOG section exists, and fails (nothing created) or prints
     `Releasing vX.Y.Z from <sha>`.
   - `installer` freezes, smoke-tests the frozen app, packs `default.bomlib` from
     `data/library/psa-devices.yaml` plus `data/device-db`, compiles with Inno Setup, then
     installs, smoke-tests and uninstalls.
   - `release` runs `gh release create vX.Y.Z --target <sha>` with both assets, which also creates
     the tag. If a release already exists for the tag (made in the UI), it uploads with `--clobber`
     and fills an empty body.
4. Role 6 checks with `get_release_by_tag`, sends Ali the link and tells the lead. About 6 minutes
   from merge to published release.
5. Hold all other merges from the CHANGELOG merge until the release is published, so the tag matches
   the changelog. Nobody pushes tags by hand.

Also supported: a hand-pushed `v*` tag equal to `__version__` releases that commit (how v0.1.x went),
and `workflow_dispatch` builds without publishing. PRs touching `packaging/**`, `src/bomgen/app/**`,
`data/library/**`, `data/device-db/**`, `pyproject.toml` or `release.yml` run the same build without
publishing. Release runs never cancel each other; PR runs do.

## 2. Role 1: Lead developer

- Owns (agents.md row 1): `docs/agents.md`, `CLAUDE.md`, `.github/workflows/ci.yml`, plan sections 1,
  2, 4 (intro) and 5, and the handoff files in this folder. Reviews, approves and squash-merges every
  PR; hands out ADR and question numbers; sets the merge order.
- B1's branch for its own docs PRs was `claude/project-thread-bf49ch` (restarted from main each time).
- B4's two layout nits from #207 were fixed in #208; no known UI defects remain open.

## 3. Role 2: Input models and examples

- Owns `src/bomgen/models/`, `src/bomgen/io/`, `src/bomgen/cli.py`, `src/bomgen/build.py`,
  `examples/`, plan section 3 and the M1 section. Also keeps `schemas/` current, since it is generated
  from the models (not in the agents.md row).
- B2's only push branch: `claude/project-thread-cyo20r` (restarted on main for each PR).

### Merged (newest first)

| PR | What | Where the decision lives |
| --- | --- | --- |
| #189 | `create_substation` seeds a blank substation with `generated_panels`, so the app's equipment editor can add the first rows (`Substation._consistent` refuses equipment without it, ADR 0013). `cabinet_number` (`<ID UPPER>-PSA-{n:04d}`) and the enclosure (the example's Rawabi Fixed Frame) are marked `# ASSUMED`. `options` are empty. A copy keeps its source's block. | B1 agreed; values unsourced |
| #187 | Writers emit a mapping that gains its first entry in block style (no `{ }`), and write a repeated scalar (the register's issue dates) in full, with no `&id001` anchors. Found by B11 in #185. | `io/round_trip.py` `_Representer`, `set_entry` |
| #182 | `delete_project` refuses `.git`, the home folder and drive roots. It deletes only the files `.bomproj` export saved, plus `out/` and `__pycache__/`, and removes the folder only when empty. | ADR 0021 |
| #163 | `fields.part_users(substation, part_id)` lists every row that uses a part (equipment, panel devices with mirrors skipped, loose items and children, library children and loose_items). For B11. | — |
| #152 | `output.power_footnotes` on the substation (role 10 prints them). gis01 has the printer footnote. | Q40 |
| #151 | `catalogue_choice.mcb_dc`, `Catalogues.mcb_dc`, `Catalogues.dc_mcb` | Q39, ADR 0023 |
| #149 | `io/yaml_source.py` parses each file text once (LRU of 64 texts, returning deep copies). Suite time halved. | LESSONS |
| #145 | `McbBrand.ac_rated` (default true). The loader refuses an `ac_rated: false` brand as `mcb`. | ADR 0023 |
| A2's | #97, #104 (M13); #106, #112, #115, #119 (M17 writers); #122, #124 (M18 loose items) | ADR 0017, 0021, 0022 |

### Code map

- `models/`: pydantic v2 input models, all `extra="forbid"` (`_base.InputModel`). `project.py`
  (project, register, defaults, output settings), `substation.py` (substation, equipment, network,
  layout, `generated_panels`), `panel.py` (panels, enclosures), `library.py` (devices, catalogues,
  brand sets, `resolve_catalogues`). `bom.py`, `calc.py`, `sheet.py`, `report.py`, `output.py` are the
  engine's output models, used by roles 9 and 10.
- `io/loader.py`: `load_project`, `load_substation`, `load_library`, `load_inputs`; YAML to models
  plus located issues (`io/errors.py`). `io/references.py`: cross-file checks (unknown part ids,
  register keys, catalogue choices, mirrors, equipment, layout). `io/yaml_source.py`: YAML with line
  numbers through the parse cache. `io/round_trip.py`: ruamel round-trip load/dump keeping comments
  and byte-identical output (`load_text`, `dump_text`, `set_entry`, `edit_document`, `write_atomic`).
- Writers (ADR 0021), each refusing an edit that adds a problem: `io/edit.py` (`edit_substation`,
  `commit`, enclosure/options/port plan/layout helpers), `io/fields.py` (`set_field`, `insert_item`,
  `move_item`, `validate_field`, `assumed_fields`, `document_users`, `part_users`), `io/panel_edit.py`,
  `io/loose_edit.py`, `io/mirror.py`, `io/lifecycle.py` (create or delete projects and substations).
- `io/schema.py` plus `bomgen schema` write `schemas/*.json`. Regenerate them in the same PR as any
  model change; no test compares the committed files. They were in sync at `032bbea`.
- `cli.py`: `validate`, `build`, `layout`, `schema`. `build.py`: inputs to workbook.

### What works

- Every `examples/` file round-trips byte-identical (`tests/unit/test_round_trip.py`); the golden test
  reproduces the spec's example values; a blank substation from `create_substation` takes equipment
  and loads (`test_lifecycle.py`).
- MCB choice: `mcb` sizes AC and refuses a DC-only brand; `mcb_dc` (unset: follows `mcb`; `default`:
  the library's DC set) must resolve to a set with `dc_rating_v`. The engine sizes DC from
  `catalogues.dc_mcb`. `examples/library.yaml` marks `schneider-c60h-dc` `ac_rated: false` (#130).

### Known gaps

- **The unset `mcb_dc` fallback is stored, not computed.** When `mcb` names a brand with no
  `dc_rating_v`, `resolve_catalogues` copies it into `Catalogues.mcb_dc` with `model_copy`, skipping
  the `_dc_set_is_dc_rated` validator. Re-validating a resolved library would refuse a project that
  loads today. NEXT role 2 task 1.
- `fed_from` accepts any panel id (ADR 0022 point 4) and `bomgen layout` writes generated panels with
  PyYAML (ADR 0021), both by design.
- A copied substation keeps the source's `generated_panels.cabinet_number`, so a copy of gis01 renders
  `861-GIS01-PSA-0001` too and the user must edit it (B1 asked for this).

## 4. Role 3: Device database researcher

- Owns `data/device-db/` and `tests/unit/test_device_db.py`; `data/library/` (`build.py`, the
  generated `psa-devices.yaml`) and `tests/unit/test_shipped_library.py`; `docs/device-db-findings.md`.
- B3's thread branch: `claude/project-thread-0iv7xg` (nothing unmerged).
- **Off-repo:** the M14 generator and research files are in the project files folder
  `/mnt/project-files/handoff/03-device-db/`. `q38-shipped-library.patch` there is obsolete (#161
  merged it).

### How the pieces fit

| Piece | Path | Source of truth | Who reads it |
| --- | --- | --- | --- |
| Device database (reference data) | `data/device-db/*.yaml`, its `README.md` | Web research, every figure sourced | Humans; `build.py`; packed into `.bomlib` with `--add data\device-db` |
| Findings | `docs/device-db-findings.md`, items 1–31 | Research notes | Ali, the lead |
| Database checks | `tests/unit/test_device_db.py` (18 tests) | README "Record format", "Field rules", "Checks" | CI |
| Example library | `examples/library.yaml` | The spec's example workbook plus M14 alternatives | **Role 2's file**; goldens |
| Shipped library | `data/library/psa-devices.yaml` | **Generated** by `data/library/build.py` | `release.yml` packs it as psa-devices 1.1.0 |
| Shipped library checks | `tests/unit/test_shipped_library.py` (role 3, 5 tests), `tests/unit/engine/test_engine_shipped_library.py` (role 9, 6 tests, #171) | — | CI |

The engine never reads `data/device-db/` directly.

### `data/device-db` layout

63 records with 126 alternatives (2 brands × low/mid/high tiers): `electrical.yaml` 11/22,
`housekeeping.yaml` 13/26, `network.yaml` 13/26, `sel-automation.yaml` 15/30,
`workstation-loose.yaml` 11/22. Each record has a `part_id` (a library part id, or a local catalogue
id such as `MCB-*`, `AUX-*`, `TB-*`, `BUSBAR-*` with `library_refs`), `kind`, `datasheet`,
`alternatives` and `sources`. Each tier has `make`/`model`/`ordering_code`, `verified`, the electrical
keys (README "Electrical data for the library (M14)") and `sources`. Read `data/device-db/README.md`
before editing.

### How M14 turned the database into library parts (#130)

Generator files (off-repo, see above): `library_entries.py` (run `python3 <path>/library_entries.py .`
from the repo root; it imports `bomgen.io.round_trip` from `src/`, so not with `-I`), `m14_merge.py`
(imported by it), `assemble.py` and `layout_data.py` (merged the research into `data/device-db`), and
`research-m14/` (briefs, inputs, raw outputs). `library_entries.py` was written against the **pre-M14**
`examples/library.yaml` and is **not idempotent**: on today's file it appends a second copy. To add
parts now, edit `examples/library.yaml` by hand (with role 2's OK) or adapt the script.

Rules it applied:
- **Part id** `f"{original}.{slug(make)}-{TIER}"`, upper case (`SEL-2730M-EXT.MOXA-LOW`).
- Every original gets `alt_group: <its part_id>  # M14 (ADR 0017)` after `category:`; alternatives get
  the same `alt_group` and `tier: low|mid|high`. A tier marked `same_as` is not a separate part.
- **Copied** from the original: `description_template`, `tag_type`, `purdue_level`, `tag_pattern`,
  `load_type`, `alarm_on_branch_mcb`, `hwio_points`, `cores`, `terminals`. **Not copied:**
  `di_inputs` (finding 31) and `min_branch_mcb_a` (deprecated by Q35).
- Children and loose items map to the same-brand, same-tier alternative where one exists, otherwise
  to the original child.
- **Supply:** VDC/VAC gives `voltage_v`, `unit_power_w`, `load_type`; VDC also `power_supplies` (1 or
  2); adds `inrush_a`/`inrush_ms`/`input_v_min`/`input_v_max` when the tier states them.
- A rack part with unknown height leaves `height_u` out (the loader rejects 0). `port_groups` become
  `ports`; SFP slots get `media: null`. A powered tier with no power figure is skipped (11; finding 30).
- **Catalogue brands** (lower-case ids): `mcb` — `schneider-c60h-dc` (`codes` for 1/2/6/10/16 A, no
  8 A, `ac_rated: false`), `abb-s200m-uc` (`code_pattern` `2CDS272061R0{rating:02d}4`),
  `siemens-5sy5` (`5SY52{rating:02d}-7`); all carry `trip_curve: C`, `magnetic_trip_multiple` (AC,
  absent for C60H-DC), `magnetic_trip_multiple_dc`, `dc_rating_v`. `aux_contact`: `schneider-c60h-dc`
  A9N26924, `abb-s2c-h6r` 2CDS200912R0001, `siemens-5st3010`. `terminal_blocks`: `weidmuller`, `wago`
  (each must list every default type UT-16, UT-2.5-MTD, UT-2.5-MT). `busbars`: `phoenix-contact`,
  `nvent-erico`. `housekeeping`: `alternatives-a`, `alternatives-b` (from the mid tiers).
- **Default MCB** iC60N stays (Q37) with `trip_curve: C`, `magnetic_trip_multiple: 6.4` (8 In ±20 %)
  and `magnetic_trip_multiple_dc: 9.05`.
- Output is normalised with `dump_text(load_text(text))` and checked idempotent
  (`tests/unit/test_round_trip.py` requires that fixed point).

### The shipped library (Q38, #161)

- `data/library/build.py`: `datasheets()` reads every record's `datasheet` for `inrush_a`,
  `inrush_ms`, `input_v_min`, `input_v_max`; `build(example_text, figures)` inserts them into each
  **original** (no `tier`) after `alt_group`, with a `# datasheet (data/device-db)` comment on the
  first, raising if the example already has the key; then swaps the header for a GENERATED one.
- It adds input ranges to 11 originals (RST2228-L2, RST2228-L1-24MM, SEL-2730M-EXT, FGR-60F,
  SEL-3555-GW, SEL-3555-RTAC, SEL-2488, SEL-2240, SEL-3355, NAP-F23, NAP-K55) and inrush to the 5 SEL
  ones (20, 20, 8, 17, 20 A).
- Effect (pinned by #171): SEL-3555-GW/RTAC and SEL-3355 branches size to 6 A (20 A inrush exceeds
  2 A × 9.05); the others stay at the 2 A floor; mains unchanged; `dc_float` warns for the iC60N (Q37)
  and the FGR-60F (Q41).
- `release.yml` packs it with `--add data\device-db` as psa-devices 1.1.0. Name and version must match
  `examples/project.yaml` `library:` (`test_packaging.py`).

### What works, gaps, risks

- The example library loads 329 devices (50 originals, 279 alternatives); goldens unchanged;
  `build.py` reproduces the committed file byte for byte; the example builds with the shipped library.
- Data gaps (not bugs): finding 30 (11 alternatives have no power figure, so they are not library
  parts); finding 31 (SEL-2244-2 alternatives have no `di_inputs`); 83 of 378 alternative tiers are
  `verified: false` (codes from a naming pattern; check before ordering).
- Risks: the generator is off-repo and not idempotent. Any edit to `examples/library.yaml` must be
  followed by `python data/library/build.py`, or
  `test_the_shipped_library_is_up_to_date_with_its_sources` fails and role 9's shipped-library test may
  shift. Bumping psa-devices past 1.1.0 means changing `examples/project.yaml` `library:` and
  `release.yml` together; agree it with roles 1, 2 and 6 first.
- Role 3 PR history: #6, #18 (initial database; rack heights, mounting, switch port roles); #30
  (FOPP-96SM 1U, Q33); #40, #42 (README field rules; `pack` checks records); #121 (M14 research,
  findings 22–29); #130 (M14 library entries: 279 alternatives, brand sets, findings 30–31, 10 tests
  outside the role); #161 (Q38 shipped library and build script, C60H-DC `ac_rated: false`,
  release.yml and ADR 0009); #144, #172 (checkpoints).
- Settled questions: Q33 (FOPP-96SM is 1U), Q35 (branch MCB rule: 1.3 × running current, inrush ÷
  magnetic multiple, 2 A floor; DC multiple for DC loads), Q37 (iC60N stays default; DC ranges are
  brand sets; the float warns), Q38 (datasheet inrush and input ranges only in the shipped library),
  Q39/ADR 0023 (separate `mcb_dc`; a DC-only brand only there), Q41 (FGR-60F stays, warning accepted;
  no DC-rated firewall researched).

## 5. Role 4: UI designer

- Owns `docs/ui/` (design docs, `tokens.json`, fonts, prototype, tools) and the M9 section of
  `docs/plan.md`. Writes no Python. B4's branch: `claude/project-thread-7hk4h2`.

| PR | Who | What (all docs-only inside `docs/ui/`) |
| --- | --- | --- |
| #82 | A4 | "Departures in the built app" for v0.1 (`screens.md`) |
| #91 | A4 | v0.2 part 1: `editing.md` (three kinds of write, save bar, validation, create/rename/delete, field inventory) |
| #94 | A4 | v0.2 part 2: Panels board pins, drag contract, keyboard, editable panel editor |
| #99 | A4 | v0.2 part 3: Library editors (pending set, catalogues and brands, device editor, alternatives, CSV, review and apply) |
| #102 | A4 | v0.2 part 4: Loose material page on its own sheet (ADR 0020), substation catalogue brand |
| #142 | B4 | Loose material follows ADR 0022: a free-text item has no Fed from and no children; Qty is a whole number ≥ 1 or `1 Lot` |
| #191 | B4 | The substation name is the BOM title's second line; the "Title line" field is gone |
| #204 | B4 | `polish-v02.md` (16 ranked findings), the **Changed marker** in `components.md`, save-bar invalid sentence as one control, validation wording in `editing.md` |

Reviews for role 11: #131 and #146 (Loose material; B4 wrongly endorsed yellow `td.changed` in #146,
reversed by #204 item 1); polish fixes screen-checked in the real app: #205 passed on `da84991` (found
a race, fixed in #207), #206 passed on `f27bc7c`, #207 failed at `c3ce633` (Role select clipped, table
hit the Result card, part ids broke mid-id, brand names clipped) and passed at `e4b5294`. **#208 was
not screen-checked.** With #205–#208 merged, all 16 `polish-v02.md` items are done.

Drift between design docs and the built app:
1. `screens.md` "Departures in the built app" is v0.1-only; its first bullet ("Projects, substations
   and settings are read-only") is wrong since v0.2, and the v0.2 departures are not recorded.
2. The Panels board is read-only for hand-written panels (Build uses the panel files, so a pin would
   not change the BOM); `editing.md` "Panels board: drag, drop, pin, delete" doesn't say so.
3. The prototype shows v0.2 as designed, not as built (no Changed marker, no #205–#208 polish). By the
   house rule in `screens.md` "Departures" the prototype isn't changed; the departures list records it.
4. Unfiled nits: the device editor save bar reads "1 unsaved change · added to pending changes" before
   saving; Project › Overview showed "psa-devices 1.1.0" in the Home table while the header badge said
   1.0.0 (seen after a local library edit, maybe correct, not investigated); "Same as the project
   (Library default)" has a capital L mid-sentence.

Off-repo: the real-app screen-check harness is in `/mnt/project-files/ui/harness/` (`README.md`,
`serve.py`, `shoot.js`).

## 6. Role 5: Library update packages

- Owns `src/bomgen/library_store/`, `tests/unit/library_store/`, ADR 0008, ADR 0018 and the M8
  section; also the de facto owner of `src/bomgen/project_store/` (M8b, ADR 0012), which agents.md
  doesn't list. B5's branch: `claude/project-thread-31eptw`. ADR 0008 and 0018 are Accepted (#184).
- Delivered: M8/M8b (A5: #9, #31, #41, #50, #53, #59: `.bomlib` pack/verify/manifest with checksums,
  per-user store with rollback, import dry-run, `bomgen library …`, `.bomproj` export/import/backup with
  dry-runs, device-db records inside a `.bomlib`). M16 store side: #92 ADR 0018; #95 device-db checker
  accepts M14 keys; #105 local versions `<base>+local.N`; #113 `save_local_version` and `.bomlib`
  backup (`export_package`, `bomgen library export`); #114 edit operations by path; #116 `export_csv`
  and `bomgen library export-csv`; #118 `preview_csv_import`/`import_csv` and `import-csv` (with the
  "probably an Excel formula" hint); #120 `compare_alternatives`; #127 `write_bundle` creates folders
  and a failed `active` write restores the previous version. B5: #164 device-record edits
  (`records.py`) for the Datasheet tab; #170 ADR 0018 amendment "device-record edits"; #179
  `catalogues.mcb_dc` in the CSV as the `default_dc` row, `plain_message` row messages, "Compared with …
  Saving makes …" wording. Reviewed others' changes in its files: #165, #161, #130.

| Module (`src/bomgen/library_store/`, API re-exported in `__init__.py`) | What it holds |
| --- | --- |
| `manifest.py` | `Manifest` (`manifest.json` of a `.bomlib`), `LIBRARY_FILE`, `LIBRARY_SCHEMA_VERSION = 1`, `FORMAT_VERSION` |
| `package.py` | `pack`, `read_package`, `PackageContents`; uses the shared `bomgen.bundle.container` zip code |
| `store.py` | `LibraryStore` (`<name>/<version>/…` plus `<name>/active`), `install`, `rollback`, `read_version`, `export_package`; `default_library_home()` (`BOMGEN_LIBRARY_HOME`, else `%LOCALAPPDATA%\bomgen\libraries` / XDG) |
| `service.py` | `validate_library`, `import_library` (CLI, launcher and app share them) |
| `preview.py` | `preview_library_import`: the `.bomlib` dry-run (`Check` list, first failure stops) |
| `diff.py` | `LibraryDiff`, `diff_libraries` (parts added/changed/removed, catalogues and brand sets as `kind:id`, files) |
| `versions.py` | `Version` (MAJOR.MINOR.PATCH with optional `+local.N`) |
| `device_db.py` | `DeviceRecord` and models, `parse_device_records`, `load_device_records` |
| `edit.py` | `SetValue`/`Insert`/`Remove`, `parse_edits`, `apply_edits`, `check_field` (paths into `library.yaml`) |
| `records.py` | `apply_record_edits`, `check_record_field`, `write_records`, `changed_records` (keyed by `part_id`) |
| `local.py` | `save_local_version`, `save_edits(edits, record_edits=…)`, `next_local_version`, `dump_library` |
| `csv_export.py` | `TABLES`, `library_tables`, `export_csv`, `export_installed_csv`, `DEFAULT_DC_ID = "default_dc"` |
| `csv_import.py` | `preview_csv_import` → `CsvPreview`, `import_csv`, `plain_message` |
| `alternatives.py` | `compare_alternatives` → `AlternativeRow`s for a device and its `alt_group` |
| `cli.py` | `bomgen library pack | import | list | export | export-csv | import-csv | rollback` |

Callers outside the folder: `src/bomgen/app/` (api, catalogues, editing, launcher, library_csv,
library_edit, …), `src/bomgen/io/` (loader, edit, fields, lifecycle), `checks.py`, `cli.py`. The shared
container (`src/bomgen/bundle/container.py`, `errors.py`, `checks.py`) serves both stores.

Files outside the role that role-5 PRs changed (all approved): `bundle/container.py`, `errors.py`,
`checks.py` (#127, #113 `RefusalKind.NO_CHANGES`) and `tests/unit/test_bundle_container.py`;
`models/project.py` and `schemas/project.schema.json` (#105, `LibraryVersion` accepts `+local.N`);
plan M16 text, the `docs/decisions/README.md` row, ADR 0018.

Known gaps (none requested; don't start them unasked): the CSV doesn't carry device-database records
(an import keeps the base version's `device-db/`); `LibraryPackageError` carries only a message and a
kind; a rewritten `device-db/*.yaml` or `library.yaml` loses its YAML comments (documented in ADR 0018).

## 7. Role 6: Windows installer and release

- B6's branch `claude/project-thread-s79idd` and A6's `claude/project-thread-y4aekh` hold only merged
  history. ADR 0009 is Accepted (#184). Design in [ADR 0009](../decisions/0009-installer-layout-and-releases.md);
  user steps in [docs/install.md](../install.md); build steps in [packaging/README.md](../../packaging/README.md).

| File | What it is |
| --- | --- |
| `packaging/bomgen.spec` | PyInstaller spec: one folder `dist/bomgen/`, two exes (`BOM Generator.exe` windowed, `bomgen.exe` console). Bundles all of `src/bomgen/app/ui/` and writes `bomgen_modules.txt` for `--self-test`. |
| `packaging/bomgen.iss` | Inno Setup. Per-user install (`PrivilegesRequired=lowest`) to `%LOCALAPPDATA%\Programs\BOM Generator`; Start-menu shortcut; `.bomlib`/`.bomproj` associations (HKCU); `default.bomlib` to `{app}\library`; WebView2 bootstrapper check (warn only). **AppId `{9B1E5C2A-4F37-4E8B-9D61-2C7A0F3B8E15}` must never change.** |
| `packaging/entry_app.py`, `entry_cli.py` | Entry scripts calling `launcher.app_main` and `launcher.cli_main` |
| `packaging/requirements.txt` | Build-only deps (`pyinstaller==6.22.3`), kept out of pyproject on purpose |
| `packaging/release-notes.md` | Header of every Release body; GitHub's generated notes are appended |
| `packaging/README.md` | Local Windows build steps |
| `.github/workflows/release.yml` | `plan` (ubuntu) → `installer` (windows) → `release` (ubuntu) |
| `docs/install.md` | End-user install, upgrade, library packages, uninstall |
| `src/bomgen/app/launcher.py` | `parse_args`, `app_main` (window, `.bomlib` import, `.bomproj` open, `--self-test`, first-start default library), `cli_main` (typer app with UTF-8 console), `self_test`, `ui_files`/`ui_files_missing`, `install_bundled_library` |
| ADR 0009, plan M11 section | Design record |
| `tests/unit/test_launcher.py` (43), `tests/unit/test_packaging.py` (22) | `test_packaging` reads release.yml, the spec and the iss as text and pins key lines |

Edits outside this list, each approved at the time: the three version strings (every bump),
`src/bomgen/cli.py` (#70, `utf8_console` made public), the ADR 0009 row of `docs/decisions/README.md`
(#153).

What the Windows job proves each run: **frozen app** `--version`, `--help`, `validate` and `build` on
`examples/project.yaml` (checks `.checks.json` exists and "0 failed"), `--self-test` (every module in
the build-time manifest imports; since #186 every script, stylesheet and font `index.html` loads is
bundled), then the real window with title "BOM Generator". **Installed app** on a fresh
`BOMGEN_LIBRARY_HOME`: first start lists `psa-devices\s+<version> (active)` (version pinned to
`examples/project.yaml` `library:`); reinstall plus second start leaves the store unchanged; `.bomlib`
double-click import; `build` with the installed `bomgen.exe`; shortcut and both associations.
**Uninstall** removes exe, ProgIDs, extension keys and shortcut.

Known issues: an existing install keeps its library store on upgrade by design (double-click the
release's `default.bomlib` to move; Ali was told at v0.2.0); a broken bundled default library shows its
message on every start while the store is empty (role 5 accepted); first-start and import messages show
the raw refusal kind (e.g. `invalid_package`, a nit left as is); unsigned builds, so SmartScreen warns
(plan Q19).

Merged history: #2 installer pipeline · #15 `.bomlib` import and `.bomproj` association · #24 fixture
fix · #38 launcher runs `run_window` with UI and pywebview bundled · #47 frozen `validate` smoke · #55
frozen `build` smoke · #57 PowerShell `$name:` fix · #70 UTF-8 console · #84 v0.1.0 · #86 default
library bundled and installed on first start, v0.1.1, attach to an existing release · #153 release
from main · #186 self-test checks every UI file · #195 v0.2.0 · #211 v0.2.1 · checkpoints #138, #162,
#169, #196. Reviewed #161. Release runs: v0.2.1 push run (published 03:17), v0.2.0 run 40797286698,
v0.1.1 run 40773272092, v0.1.0 run 40736513114 (attempt 2).

## 8. Role 7: Lead developer assistant

- Owns `README.md`, `CHANGELOG.md`, `tests/unit/README.md`, `tests/golden/README.md`; other files only
  when the lead assigns exact lines (last time: ADR Status lines and `docs/decisions/README.md` rows in
  #184). B7's branch: `claude/project-thread-vl9f9y`.
- Last commit covered by the changelog: `1678343` (#211, the 0.2.1 bump, no entry). Every non-docs PR
  up to #212 has an entry or was ruled out (#195 and #211 bumps, #197 refactor).
- Owned files at `032bbea`: `README.md` has overview, Status (v0.2.1 released, next work waits on Ali's
  feedback; "Done in v0.1" M0–M11, "Done in v0.2" M12–M18), Usage (validate, build, layout, library,
  CSV editing, project sharing), Development, CI; every command was run on a scratch copy.
  `CHANGELOG.md` is Keep a Changelog with `[Unreleased]` (empty), `[0.2.1]`, `[0.2.0]`, `[0.1.1]`,
  `[0.1.0]` and compare links. Both test READMEs have one row per module; the row loops and the link
  loop (LESSONS role 7 L4, L5) print nothing.
- B7's merged PRs: #147 (README v0.2 status, library CSV usage, 14 unit rows), #160 (M14/M18 done,
  release from main; changelog #130–#154), #174 (changelog #155–#171), #184 (15 ADRs Accepted), #193
  (`[0.2.0]`), #209 (`[0.2.1]`), #210 (checkpoint), #212 (README Status for v0.2.1, 9 missing rows).

## 9. Role 8: Sizing and layout engine

- Owns `src/bomgen/engine/sizing.py`, `src/bomgen/engine/layout.py`, `tests/golden/layout/`, the M1c
  section, and its tests `tests/unit/engine/test_sizing.py`, `test_layout.py`, `test_layout_cli.py` and
  plan [`docs/superpowers/plans/2026-10-28-m1c-sizing-and-layout.md`](../superpowers/plans/2026-10-28-m1c-sizing-and-layout.md).
  B8's branch: `claude/project-thread-3ttgw8`. Role-8 code last changed in `ef65800` (#100).
- The rules (R1–R10) are in [ADR 0013](../decisions/0013-network-sizing-and-panel-layout.md) and
  [the approved design, section 4](../superpowers/specs/2026-10-28-substations-and-auto-layout-design.md).
- Merged: #19 M1c (`sizing.py` R1–R4, `layout.py` R5–R9, `bomgen layout`, `build --no-layout`,
  `with_layout`, golden `tests/golden/layout/`, confirmed by Ali); #90 M12 (blank plate only under a
  rack block ending in its active device, ADR 0013 R5 amendment); #100 M17 engine
  (`DeviceMove.position`/`PairMove.position`, every override pins its units, `PanelFill.is_pinned` /
  `position`, R7 amendment); #176 plan §3 `position` example; checkpoints #135, #221.
- What works: L1 ranked then picked, L2 from kept units, generated port plans, the 32U fill with A/B
  streams, common devices spread, removals, overrides with positions and pins, blank plates,
  `port-capacity`/`replaced-panel`/`missing-panel`/`stale-*` issues, `panels:` list reconciliation. The
  app drives the engine for the Panels board (#126, #129) and for edits that re-lay out (`io/edit.py`),
  refusing a move when `layout_preview` with the candidate reports a new error. No known bugs.

### Code map

`src/bomgen/engine/sizing.py` (R1–R4, pure, no I/O):

| Name | What it does |
| --- | --- |
| `SwitchPorts`, `switch_ports(device)` | A library switch's ports by what they may connect (`usable_for`) |
| `NetworkInputs` | `ied_count`, topology, ring size, uplinks, spare fraction |
| `l1_reserved_ports`, `usable_ports`, `l1_links` | R1 port arithmetic (uplinks/ring ports reserved, spare taken off) |
| `rank_l1_switches`, `pick_l1_switch`, `L1Candidate` | R1 model choice: fewest per side, then fewest ports, then `part_id`; a pinned `part_id` wins |
| `size_network` → `NetworkPlan` | L1 and L2 counts per side (R1, R2); `ied_count` kept for the check report (R4) |
| `L2Link`, `l2_port_plan`, `l1_port_plan` | Generated port plans (R3) |
| `SizingError` | Inputs no library switch can meet |

`src/bomgen/engine/layout.py` (R5–R10), bottom up:
1. **Fill (pure):** `Unit`, `LayoutRules` (capacity, blank plate U), `blank_plates`, `used_u`,
   `PanelFill` (`stack()`, `is_pinned`, `position`, `fits`), `_Builder`, `fill()` (R5, R6: A stream in
   odd panels, B in even, lock-step; common units into the panel with most free U).
2. **Overrides:** `auto_layout(units, rules, removed=, moves=)` drops removals, fills, then applies
   `DeviceMove`/`PairMove` in order (R7), recording a pin with optional `position`. Issues:
   `stale-override`, `stale-removal`, `move-does-not-fit`, `unknown-panel`, `device-too-tall`,
   `panel-empty`, `missing-height`.
3. **Substation mapping:** `network_inputs`, `l1_candidates`, `_size`, `_units`, `_side_ports`,
   `_capacity_issues` (`port-capacity`), `_rows`, `_port_plans`, `_panel` turn a `LoadedSubstation` into
   `Panel` models with `generated=True`.
4. **Entry points:** `layout_preview(loaded, overrides=None) -> LayoutResult` (`overrides` replaces the
   file's `layout:` block; L2 re-sized from kept units); `layout_substation(loaded)` (CLI);
   `with_layout(loaded)` (used by `bomgen build`; replaces `panels:` only when a listed panel file is
   `generated: true`, adds `replaced-panel` for hand-written files still listed);
   `render_panel_yaml(panel)` (with `GENERATED_HEADER`); `reconcile_panels_list(text, files)` (rewrites
   `panels:` as text so comments survive); `_loose_material_issues` (`missing-panel`).

`WARNING_KINDS` = `stale-override`, `stale-removal`, `replaced-panel`; every other `IssueKind` is an
error (`LayoutIssue.is_error`).

| Caller outside role 8 | Owner | Uses |
| --- | --- | --- |
| `src/bomgen/cli.py` (`bomgen layout`, `build --no-layout`) | role 2 | `with_layout`, `layout_substation`, `render_panel_yaml`, `reconcile_panels_list` |
| `src/bomgen/build.py` | role 2 | lays out first with `with_layout` |
| `src/bomgen/app/network.py` (Panels board) | role 11 | `layout_preview`, `LayoutResult`, `Unit`, `blank_plates`; sends `pinned`, `position`, `plate_below_u` |
| `src/bomgen/app/editing.py` | role 11 | `layout_preview(loaded, candidate)`, `is_error` |
| `src/bomgen/app/substations.py` | role 11 | `with_layout`, `LayoutIssue` |
| `src/bomgen/io/edit.py` | role 2 | `layout_preview` after an edit |

Any change to `LayoutResult`, `PanelFill`, `Unit` or the issue kinds is an API change for these callers.

| Test | Covers |
| --- | --- |
| `tests/unit/engine/test_sizing.py` | R1–R4, named `test_r<N>_...` |
| `tests/unit/engine/test_layout.py` | R5–R10, overrides, pins, positions, blank plates, issues |
| `tests/unit/engine/test_layout_cli.py` | `bomgen layout`, `build --no-layout`, `panels:` reconciliation |
| `tests/golden/layout/` | gis01 laid out: 3 L1 per side, demand 8, psa1 23U, psa2 19U (Ali confirmed) |
| `tests/unit/test_substation_model.py` (role 2's) | the `position` fields |
| `tests/unit/app/test_app_network_api.py` (role 11's) | board values that follow from the engine |

Files outside "Owns" that role 8 changed (all reviewed): `cli.py` (`layout`, `build --no-layout`);
`models/substation.py`, `schemas/substation.schema.json`, `tests/unit/test_substation_model.py`
(`position`, #100); `tests/unit/app/test_app_network_api.py`; ADR 0013 R5/R7 amendments; the design
spec's R1/R2/R10 example numbers; plan §3 `position` example (#176).

Risks: `Equipment.l2_ports` counts once per entry (R2 text), so an entry with `qty` > 1 and L2 ports
would be under-counted (no example has one). The board contract is that a move never re-flows other
devices, which is why overrides apply after the fill (R7). Spec vs code: the spec example shows 6 L1
per side; the rules give 3 and Ali confirmed 3 (`expected_panels.yaml` header).

## 10. Role 9: BOM rule engine

- Owns the rest of `src/bomgen/engine/` (not `sizing.py`, `layout.py`), `src/bomgen/checks.py`,
  `src/bomgen/revision.py`, `src/bomgen/models/bom.py`, `calc.py`, `output.py`, `report.py`,
  `tests/golden/` except `layout/`, `tests/unit/test_revision.py`, the engine tests in
  `tests/unit/engine/` (helper `engine_factories.py`), and the M2–M4, M7 engine note and M15 plan
  sections. `tests/golden/test_cli_build.py` was written by role 2: tell role 2 before changing it. The
  free-text loose line in `engine/kits.py` came with role 2's #122 (ADR 0022): tell role 2 before
  changing its behaviour. B9's branch `claude/project-thread-q31ztb` and A9's
  `claude/project-thread-9l1061` hold only merged history.
- Not role 9's though it calls the engine: `build.py`, `cli.py`, `models/library.py`, `project.py`,
  `panel.py`, `io/`, `examples/` (role 2); `sheets/`, `writer/` (role 10, which consumes `BuildResult`);
  `app/` (role 11); `data/` (role 3).

`engine/pipeline.py` `build(loaded) -> BuildResult` runs steps 1–12 in the spec's "Data model and
generation order". Callers: `build.py`, `app/output.py`, `app/preview.py`.

| Module | What it does |
| --- | --- |
| `engine/units.py` | step 1: expands a panel's device instances into tagged `DeviceRow`s |
| `engine/tags.py` | tag naming (`<PANEL>-<LEVEL>-<TYPE>-<LAN><NN>`, `tag_pattern`, panel overrides) |
| `engine/enclosure.py` | group A: the enclosure row |
| `engine/kits.py` | step 2: device rows with kit children (group B), and `loose_table` (None with no rows) |
| `engine/network.py` | group C: SFPs, cable managers, serial cables |
| `engine/housekeeping.py` | group D: lamp, fans, filters, thermostats, IPR kit, change-over diodes, socket |
| `engine/ac_dist.py` | group E: CINC and the AC branches, from `catalogues.mcb` |
| `engine/dc_dist.py` | group F: Q1/Q2 mains, Q1.n/Q2.n branches, spares, QCODs, `branch_sizing` (ADR 0019), all from `catalogues.dc_mcb` (ADR 0023) |
| `engine/mcb.py` | `rating_at_least`, `rating_above`, `mcb_line` take an `McbCatalogue`; aux contact rows; `alarms_wired` |
| `engine/terminals.py` | group G: terminal strips (X1, X3-AC, X4-DC1/DC2, XDIN, …) |
| `engine/grounding.py` | group H: grounding busbars |
| `engine/assemble.py` | step 11: separators and SR.NO in group order |
| `engine/power.py` | step 4: Power Consumption rows and totals (2,177.5 W DC, 1,090.3 W AC on the example) |
| `engine/thermal.py` | heat checks and the ventilation choice (forced and natural) |
| `engine/items.py`, `errors.py` | `BomItem` with kit children and `flatten`; `EngineError` |
| `checks.py` | `check_report(loaded, result) -> CheckReport`; ids `sfp_slots`, `dc_main`, `branch_mcb`, `dc_float`, `airflow`, `natural_convection`, `line_up`, `di_capacity`, `library_version`; `render_text`, `render_json` |
| `revision.py` | `read_previous_issue(path)`, `compare_with_previous(...)`, `render_revisions` (ADR 0016) |

Merged: M2 #22; M3 #36; M4 #44, #46; M7 engine #58 (ADR 0016), #67 (Q34, ADR 0014); M15 #103 (ADR
0019, Q35); `dc_float` #109 (ADR 0019 item 7, Q37); M18 engine #123 (no loose table without rows);
ADR 0023 engine side #154 (`f319f64`; group F, branch sizing and the `dc_float` item use
`catalogues.dc_mcb`; group E and CINC keep `catalogues.mcb`); shipped-library sizing tests #171
(`8be24d5`: SEL-3555-GW/RTAC and SEL-3355 at 6 A, set by inrush 20 A ÷ 9.05 = 2.2 A; their feeds'
spares 6 A; QCOD spares and others 2 A; mains unchanged); checkpoints #141, #159, #216. Since #154 the
only other-role change in role 9's files is #157 (role 10, power footnote fields in `models/calc.py`).

What works: the example reproduces the spec's values with goldens citing their sections (power and
heat in `test_engine_power_heat.py`; groups A–H in `expected_groups_*.py`/`test_engine_groups_*.py`;
the check report in `test_check_report.py`: 0 failed, 50 branch MCBs at 2 A, the iC60N `dc_float` WARN
at 125 V against 140 V, two `dc_main` WARNs where the workbook's 16 A mains differ from the rule's 10 A,
Q3). `bomgen build` prints "0 failed, 3 warnings, 64 passed" (`test_cli_build.py`). Revision round trip
(`test_revision_round_trip.py`). ADR 0023 choices in `test_engine_dc_dist.py`, `test_engine_ac_dist.py`,
`test_checks.py`. No known bugs. Every question raised is resolved (Q3–Q8 on defaults; Q30, Q31, Q35,
Q37, Q39, Q41); ADRs 0014, 0016, 0019, 0023 Accepted.

Risks: DC aux contacts still come from `aux_contact` even when `mcb_dc` names another brand (ADR 0023
consequences). The app's Catalogues tab lists only `catalogues.mcb` (A1 accepted). Shipped devices with
`inrush_a` and no `inrush_ms` count the inrush (ADR 0019 item 1b); if role 3 adds `inrush_ms` under
`inrush_min_ms` (10 ms), those branches drop to the floor and `test_engine_shipped_library.py` says so:
update its expectations, not the engine. That test copies `examples/` and swaps in the shipped library,
so recheck it after changes there. Spec vs code: Q3–Q6 and Q8 run on defaults with warnings; Q7 was
replaced by Q35 and ADR 0019.

## 11. Role 10: Excel workbook writer

- Owns `src/bomgen/sheets/`, `src/bomgen/writer/`, `src/bomgen/models/sheet.py`, `tests/unit/sheets/`,
  `tests/unit/writer/`, the M5/M6 plan sections, ADR 0020 and the plans
  `docs/superpowers/plans/2026-10-28-m5-sheet-models.md` and `…-m6-excel-writer.md`.
  `tests/golden/test_workbook.py` sits in role 9's folder: change it only with role 9's agreement or the
  lead's request. B10's branch: `claude/project-thread-pcjgix`.

| PR | Commit | What |
| --- | --- | --- |
| #21 | e37d9a6 | M6: `models/sheet.py`, `writer/xlsx.py` (XlsxWriter, ADR 0003) |
| #48 | 02241ed | M5: `sheets/` (BOM, Power Consumption, Heat Dissipation, Heat Calculations, header/footer, `build_workbook`), pycel golden |
| #69 | d01dcbe | Writes `<stem>.tmp-<hex><suffix>` beside the target, then `os.replace`; failures raise `WriterError`, target untouched |
| #96 | 4c97af7 | M18 sheet side (ADR 0020): Loose Material sheet; `output.sheet_names.loose_material`; revision compare falls back to host sheet table 1 for older issues |
| #157 | a21e675 | Power footnotes: one row per `output.power_footnotes` entry, two rows below the NOTES, merged B:L, wrapped, 15 pt per line, inside the print area (Q40) |

- `build_workbook(loaded, result, *, logo=None) -> WorkbookModel` (`sheets/workbook.py`). Sheet order:
  panel BOMs, Loose Material (only when `result.loose` is not None), Power Consumption, Heat
  Dissipation, Heat Calculations. `write_workbook(workbook, path) -> Path` (`writer/xlsx.py` is the only
  module importing XlsxWriter).
- `tests/golden/test_workbook.py` recalculates all 924 formula cells with pycel and checks 2,177.5 W
  DC, 1,090.3 W AC, 3,267.8 W; airflow 391/391/172 vs 716; line-up 954.8 vs 2,148; console A = 4.848
  m², ΔT = 6.96 °C; and the printer footnote (text, `\n`, wrap, B:L merge, 30 pt height, print area).
- Callers: `build.py` (role 2) and `app/output.py` (role 11) call `build_workbook` then
  `write_workbook`; `app/api.py` exposes `build_workbook` for the Preview tab, so a change to the sheet
  models' shape reaches role 11's Preview.
- Decisions by Ali: Q36 → ADR 0020 (loose material is its own sheet under its host panel's header,
  overriding OUT-3 and the spec's sheet-4 loose table); Q40 (footnotes print; print area ends after the
  last footnote, not the reference's A1:L97); Q11 (header size computed by `fitting_size`, at most 20 pt).
- Limits: Excel header fit is unverified — `fitting_size` gives 17 pt at 49–50 % print scale and 11 pt
  at 78 % with `LINE_SPACING = 1.2`; LibreOffice can't settle it. pycel 1.0b30 is a pre-release dev
  dependency (its `ast` warnings are filtered). `FORMULA_COUNT = 924` moves whenever the layout adds or
  removes formulas (update it with a comment). Footnote height is estimated (lines plus overflow at
  about 255 characters × 15 pt).
- Environment seen: Python 3.13.17, XlsxWriter 3.2.9, openpyxl 3.1.5 on 2026-10-29 (3.12 and 3.3.0 the
  day before); both pass. pyproject pins only `XlsxWriter>=3.2`, `openpyxl>=3.1`, `pycel>=1.0b30`.

## 12. Role 11: Desktop app

- Owns `src/bomgen/app/` (**except `launcher.py`**, role 6), `src/bomgen/app/ui/`, `tests/unit/app/`
  and the M10 section. Doesn't own the spec, ADRs and plan structure (role 1), CHANGELOG (role 7), `io/`
  writers (role 2), library store and CSV (role 5), engine (roles 8–10) or `docs/ui/` (role 4). B11's
  branch `claude/project-thread-apbolc` (a successor can't push there).
- Design source: [editing.md](../ui/editing.md), [screens.md](../ui/screens.md),
  [components.md](../ui/components.md), tokens `docs/ui/tokens.json` → `src/bomgen/app/ui/tokens.css`,
  prototype `docs/ui/prototype/`, last audit [polish-v02.md](../ui/polish-v02.md).
- Screenshots of the last PRs are in the project files folder `a11-screens/` (not in git). The E2E
  scratch scripts are gone; LESSONS says how to rebuild them.

Merged (B11, oldest first): Loose material page #146 (replaced A11's #131); library editing (M16 app
side) #155 device editor and pending set, #166 lists/Add device/Delete/In use, #175 Datasheet tab, #178
export and CSV import, #180 Alternatives; #181 create/rename/delete projects and substations (M17d);
every field editable (M17c): #185 Overview and Network inputs with the setup card, #188 equipment rows,
#190 Settings tabs and the shared `App.draftForm`, #192 document register and "Add the core switches";
#194 "Use this instead"; #197 Overview and Network onto `App.draftForm`; follow-ups #198–#201; v0.2
polish (released in v0.2.1): #205 (items 1, 5, 6, 15: changed dot, "N fields need fixing" button,
tabular numbers, route change closes dialogs), #206 (items 2, 3, 8, 14: errors in words, unfinished rows
unchecked until save, choice labels, datasheet height, muted delete), #207 (items 4, 7, 9–13, 16 plus
extras: two-line equipment rows with Change… inline, Role 170 px, busy state and route-race guard,
resolved brand names, register two-line rows, save bar flush with the window bottom), #208 (ids never
break; device editor tab offset). Earlier A11: #117, #126 (board drag), #129 (Move… dialog).

What works: every v0.2 field is editable (Overview, Settings General/Documents/Output/Constants, Network
inputs and equipment, document register, Loose material, library devices and datasheets). Panels are
edited on the board (generated panels) and read-only for hand-written ones. Forms share `App.draftForm`
(draft of changed fields, each checked by a `check_*` endpoint, one save bar, Ctrl+S, reset on route
change; prefixes `po-` Overview, `st-` Settings, `n-` Network, `rg-` register); Loose material and the
device editor keep their own bars. Library pending set → Review and apply writes a new local version.
Alternatives, Use this instead, Change… on Network rows. Checks, Preview, Build, Backup and share, CSV,
project import, backup restore.

Risks: the Change… and Add device pickers list the **active** library, so a project pinned to an older
version may refuse a part (the model's message shows on the row). No undo for a dropped pending library
device (only the confirm dialog). Spec disagreements and open questions: none.
