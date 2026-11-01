# NEXT

What to do next, by area. Read [STATE.md](STATE.md) first. Nothing is half done: every item below is
either waiting on Ali or ready to start.

## 1. Getting started

1. Read [STATE.md](STATE.md), this file, [LESSONS.md](LESSONS.md), [CHECKPOINT.md](CHECKPOINT.md),
   then [`CLAUDE.md`](../../CLAUDE.md).
2. `git fetch origin main`, `git checkout -B <branch> origin/main`, `git status --short`,
   `git log --oneline -10`. Check what merged since STATE.md was written.
3. Fresh container: `pip install -e ".[dev]"` (not `.[app]`, which fails on Linux). Then the gate in the
   module form, because the `mypy`/`pytest` on PATH are not the project's:
   `ruff check . && ruff format --check .`, `python -m mypy`, `python -m pytest -q -p no:cacheprovider`
   (5–7 min; run it in the background). Compare with STATE.md → "Verification" and note any drift in
   LESSONS.md.
4. For UI work also run `for f in src/bomgen/app/ui/*.js; do node --check $f; done`. For data work also
   run `python data/library/build.py` and check `git status` is clean (if not, the example library or
   device-db was edited without regenerating: regenerate and include it in the next PR), and check
   `/mnt/project-files/handoff/03-device-db/` still has the M14 generator.

**Keeping these files current.** When work stops, update STATE.md and NEXT.md in place, append to
LESSONS.md, and add a dated entry at the top of CHECKPOINT.md, in a docs-only PR.

**Team.** The audit of 2026-10-30 ([Claude Doc](https://claude.ai/artifact/DXyJnufrHguPCCVWgeLGPh), "Agent team") recommends four roles, each
owning the areas below: a lead and reviewer (plan milestones, ADRs, PR review and merge, releases, these
files, cards to Ali; Opus 5.5, high effort), engine, models and writers (sections 6, 12–14; Opus 5.5,
high), desktop app and UI (sections 8, 10, 15; Sonnet 5.5, high; Opus 5.5 only for a new screen designed
from scratch) and data and docs (sections 7, 11; Sonnet 5.5, medium). Haiku 5.5 at low effort only for
mechanical loops run inside a role. The lead hands one milestone to one role as one PR.

## 2. Working rules

- One milestone per PR, a conventional commit, TDD with tests named after the rule, the gate green
  before every commit.
- PR body starts with the attribution lines from the session's instructions and ends with the
  attribution footer. Assign `alialyami90` (requesting Ali as reviewer fails, since he is the PR author)
  and subscribe to the PR. Each PR is checked for conflicts and green CI, then squash-merged. Never ask
  Ali to merge.
- PRs touching `src/bomgen/app/`, `packaging/`, `pyproject.toml` or `release.yml` also need a green
  "Build Windows installer".
- Ask Ali questions only on a decision card with one option marked recommended, and record the answer
  as a plan §6 question.
- Don't edit `docs/spec/` without Ali's go-ahead; if code and spec disagree, ask Ali before changing
  either. Don't move golden values without an ADR. Only Ali marks ADRs Accepted. Don't commit `.xlsx`.
  Don't force-push (LESSONS "Branch restart"). Don't bump the version outside a release PR (on main it
  publishes at once). Don't push tags.
- Next free numbers: ADR 0031, Q62, milestone M35.

## 3. Questions for Ali (one card each, recommendation marked)

1. **What comes after v0.3.1?** Options "Test v0.3.1, send feedback" (recommended: part picking
   shipped and nobody has used it in the field yet) and "I'll describe the next work now".
2. **ASSUMED seeds:** show the cabinet number pattern, the enclosure and the document number/date
   defaults a new substation gets; recommend "Keep them, edit per project in the app". If he changes
   them, change `_blank` in `src/bomgen/io/lifecycle.py` and
   `test_a_blank_substation_seeds_generated_panels_so_equipment_can_be_added`, and drop `# ASSUMED` on
   any value he confirms.
3. **Excel header fit (Q11):** "Does the header on Power Consumption and Heat Dissipation overlap the
   table in Excel's Print Preview?" Options "It fits" (recommended: the size is computed to fit at the
   print scale) and "It overlaps". See section 14 for what each answer means.
4. **Q23** (issued sheets vs masters): keep the default (the masters) until he answers.
5. **Q51** (annunciator mounted in a panel), **Q54** (power of the -2 SEL computers) and **Q55**
   (categories for the contractor's other part types) are open in plan §6.

**Next work:** M19–M26 shipped in v0.3.0, and v0.3.1 fixed the blank-substation crash (STATE.md §1). Engine model changes (step 4) come from A4's plan.

## 4. When Ali's feedback arrives

Write it into `docs/backlog.md` as numbered points (as for v0.2), propose milestones in `docs/plan.md`
(from M27), give decisions an ADR (0028 on) or a plan question (Q56 on), and deliver one PR per
milestone.

## 5. Next release (v0.2.2 or v0.3.0)

Follow STATE.md → "How a release happens".

1. **Changelog PR first.** Rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD` with a new empty
   `## [Unreleased]` above; link refs `[Unreleased]: .../compare/vX.Y.Z...HEAD` and
   `[x.y.z]: .../compare/vPREV...vX.Y.Z`; word the last PR's entry from its final squash message
   (patterns #193, #209).
2. **Bump PR** after the changelog merges: confirm `CHANGELOG.md` has `## [X.Y.Z]` and `list_tags` has
   no `vX.Y.Z`; change only the three version lines; reinstall with `pip install -e ".[dev]"` so the
   version metadata updates; run the gate; title `chore(release): version X.Y.Z` (copy #211's body) and
   say merging publishes. Hold other merges until the release is out.
3. **After the merge**, find the push run of `release.yml` on main (`actions_list`, branch main, event
   push). `plan` must pass and `installer` must run all its steps (`get_workflow_job`; 90 s is normal on a
   cache hit). Then `get_release_by_tag vX.Y.Z`: `bomgen-setup-X.Y.Z.exe` and `default.bomlib` present,
   tag on the merge commit. Send Ali the link.
   - `plan` fails (pyproject mismatch or missing changelog): nothing was created; fix in a follow-up PR.
   - `installer` fails: read `get_job_logs`, fix in a PR with the Windows job green. A merged fix
     re-releases only if it touches `__version__`, `pyproject.toml` or `CHANGELOG.md`; otherwise use
     "Re-run failed jobs" on the release run.
   - Tag creation refused (a ruleset): the fallback is Ali publishing a release in the GitHub UI on that
     commit with tag `vX.Y.Z`; the tag push re-runs the workflow, which attaches the assets.
4. **Then** update README Status ("vX.Y.Z is released"; move finished milestones to "Done in vX").

## 6. Input models and I/O

1. **Compute the unset `mcb_dc` fallback instead of storing it** (not urgent).
   - Store `mcb_dc` in the resolved catalogues only when it is written (a brand id or `default`);
     otherwise leave the library's own `catalogues.mcb_dc`, or `None`. `Catalogues.dc_mcb` already falls
     back to `mcb`.
   - Keep ADR 0023 point 2: `{mcb: brand}` with no `mcb_dc` must still size DC with that brand, even
     when the library carries its own `catalogues.mcb_dc`; so when `mcb` is written and `mcb_dc` is not,
     set `mcb_dc` to `None` instead of copying. When neither is written, the library's own value wins.
   - Tests first (`tests/unit/test_library_alternatives.py`, `test_catalogue_choice_loader.py`):
     `test_a_resolved_library_validates_again` (`Library.model_validate(resolved.model_dump())` doesn't
     raise); keep every ADR 0023 test green; goldens unchanged.
   - Grep first: `engine/dc_dist.py`, `engine/mcb.py`, `checks.py`, `app/projects.py`,
     `io/references.py` (all read `catalogues.dc_mcb`, never `mcb_dc`).
2. Writer API additions the app needs (`io/fields.py`, `io/edit.py`, `io/panel_edit.py`,
   `io/loose_edit.py`, `io/lifecycle.py`): one PR each, tests first, with a line in ADR 0021 or 0022 when
   a writer rule changes.

By design, not tasks: `fed_from` accepting any panel id (ADR 0022 point 4); `bomgen layout` using
PyYAML (ADR 0021). Don't change `examples/` values the goldens check without a spec citation.

## 7. Device database and shipped library

1. **Finding 30: power figures for 11 skipped alternatives.** Give each alternative in
   `docs/device-db-findings.md` item 30 a sourced `unit_power_w` with `power_basis` and `power_note`
   (README "Electrical data for the library (M14)"), plus inrush if a datasheet gives it. Records:
   `data/device-db/network.yaml` `SEL-2730M-EXT` Siemens low tier (SCALANCE XR324-4M EEC; use the
   125 V DC code 6GK5324-4GG10-4JR2, finding 27); `data/device-db/sel-automation.yaml` `SEL-3555-GW`
   and `SEL-3555-RTAC` Hitachi low and high (RTU540 discontinued, 560CMG10 not found, finding 27, so a
   replacement model may be needed), `SEL-2488` Arbiter mid (1202B/C), `SEL-2240` Hitachi low and high,
   `SEL-3355` Siemens IPC427E, IPC647E and IPC847E (IPC647E is 2U). Never invent a figure; set
   `verified` per the README; at most ~35 web fetches per run. Then update finding 30 and run the gate
   (`test_device_db.py` covers the power basis).
   - **Second PR:** add the now-powered tiers to `examples/library.yaml` as library parts using the rules
     in STATE.md "How M14 turned the database into library parts", run `python data/library/build.py`,
     commit both files, and check the goldens and `test_engine_shipped_library.py` are unchanged.
2. **Finding 31: `di_inputs` for the SEL-2244-2 alternatives.** Record each module's digital input count
   in `data/device-db/sel-automation.yaml`, then set `di_inputs` on its library part (same two-PR route).
   Check how the engine uses `di_inputs` first.
3. **Move the M14 generator into the repo** before task 1's second PR: make it idempotent (skip existing
   part ids), put it under `data/device-db/tools/`, and make it pass ruff and mypy.

Don't: put the originals' inrush or input range in `examples/library.yaml` (Q38; it moves the goldens);
change the default MCB from iC60N (Q37); research a DC-rated firewall to replace the FGR-60F (Q41);
hand-edit `data/library/psa-devices.yaml`; bump psa-devices without changing `examples/project.yaml`
and `release.yml` together.

## 8. UI design

1. **Screen-check #208 on main** ("keep row ids whole and the device editor's tab offset", `dce6277`).
   Network › Equipment: a row id in the cell sub line (e.g. `ext-fw` on FGR-60F) stays on one line; the
   part id (e.g. `RST2228-L1-24MM`) never breaks and *Change…* drops under it when there is no room.
   Library › any device › Electrical: the first field row sits as close under the tabs as on other tabs;
   the save bar meets the window bottom on short and long tabs. On failure, fix it with the exact symptom
   and CSS in mind.
2. **Fix the wording nits** in STATE.md section 5, drift item 2, if they are still there.
3. **New screens or flows** start with the `impeccable` skill, a section in
   `editing.md`/`screens.md`/`components.md` and a prototype screen (CLAUDE.md "UI work").

Setup: gate venv `uv venv /tmp/venv && uv pip install -p /tmp/venv -e ".[dev]"`; impeccable via
`sh <skills>/impeccable/scripts/impeccable detect --json <dir>` (find the dir with
`ls /root/.claude/skills/synced/*/impeccable`); real-app harness per LESSONS.md; prototype checks
`docs/ui/tools/build-standalone.mjs`, `docs/ui/tools/build-tokens.mjs --check`, Playwright with
`page.on('pageerror')`.

Don't: put business rules in the UI; let the app's `tokens.css` and fonts drift from `docs/ui/` (they
must stay byte-identical); use `#FFFF00` for anything but the workbook's revised cells; redesign v0.2
parts 1–4.

## 9. Library store and packages

No work is planned; M8, M8b and the M16 store side are done. Reference for questions:
- Edits are JSON ops `{"op": "set" | "insert" | "remove", "path": [...], "value": ..., "index": ...}`. A
  string segment is a mapping key or, in a list, the item's `part_id` (devices) or `id` (brands); an int
  is a position. `apply_edits`/`check_field` (`edit.py`), `save_edits` (`local.py`).
- Device records use the same ops keyed by `part_id` (`["SW-1", "datasheet", "weight_kg"]`):
  `apply_record_edits`/`check_record_field` (`records.py`), `save_edits(..., record_edits=...)`. Changed
  records stay in their `device-db/` file; new ones go to `device-db/local.yaml`.
- `preview_csv_import(source, store, name, base=None, skip_invalid=False)` → `CsvPreview` with `checks`,
  `problems` (`RowProblem`: table, Excel row, column, plain message, key), `rows`, `diff`, `changes`,
  `edits` (for the app's pending set), `library`, `base`. `skip_invalid=True` turns row failures into a
  warning and skips the rows.
- CSV: one file per table (ADR 0018). `catalogue_id` `default` is `catalogues.<kind>`, `default_dc` is
  `catalogues.mcb_dc`, any other id is a brand. A missing table keeps the installed rows; a present table
  replaces them; a missing column keeps installed values.
- Alternatives are only the `alt_group` key on devices; `compare_alternatives` gives the rows.

When a model field is added, the CSV needs its column in the same PR or right after
([ADR 0018](../decisions/0018-library-csv-exchange.md) Consequences);
`test_a_device_with_every_field_set_survives_the_round_trip` catches a missing one. Optional ideas,
only if asked: `LibraryPackageError` carrying manifest and `active` data; CSV tables for device records.
Keep ADR edits in their own `docs(adr): …` PR.

## 10. Windows installer and release

- **App work that adds a dependency or a data file outside `src/bomgen/app/ui/`:** check the frozen
  build carries it. UI files are covered by `--self-test` since #186. Otherwise check the PR's Windows
  job, or freeze on Windows with `pip install ".[app]" -r packaging/requirements.txt`,
  `pyinstaller packaging/bomgen.spec --noconfirm --clean`, then `dist\bomgen\bomgen.exe build
  examples\project.yaml` and `"dist\bomgen\BOM Generator.exe" --self-test`. Precedent: ruamel.yaml
  (#106) needed no spec change.
- **Reviewing a change to these files** (as with #161): check the pack step, the first-start regex, the
  `test_packaging` pins, ADR 0009 and a green Windows job on the PR head.
- Ideas not started: code signing (Q19) only with a certificate from Ali, as a `signtool` step after
  "Compile the installer" with the secret in repo settings; a smoke step upgrading from the previous
  release's installer; bump `actions/checkout@v4`, `setup-python@v5`, `upload-artifact@v4`,
  `download-artifact@v4` when GitHub's Node 20 deprecation becomes an error.

Rules of the release workflow: any change to `release.yml`, `bomgen.iss`, `bomgen.spec` or
`launcher.py` needs "Build Windows installer" green on the PR head before merging (since #55); keep
build, tag and release in one run and release runs uncancelled; keep the main-push path filter to the
three version and changelog files; the Release workflow is not part of `ci-status` (ADR 0006) and never
a required check; never change the Inno Setup `AppId`; the pack step's library name and version must
match `examples/project.yaml` `library:` (`test_packaging`). Never move or delete a published tag or
release, and never make the launcher bundle or import any library but the one default package.

## 11. Documentation and changelog

After every non-docs merge (`git log --oneline 723507a..origin/main`; move this sha forward after each
pass):
1. For each non-docs PR: `pull_request_read get` for its description and `git show -s --format=%B <sha>`
   for the squash message. One entry under `[Unreleased]` in Added/Changed/Fixed, newest first, PR
   number in brackets, about 78 columns. Skip docs, handoff, chore, bump and internal-refactor PRs.
2. New test module? Run the row loop (LESSONS.md) and add a row to `tests/unit/README.md` or
   `tests/golden/README.md` with its milestone and what it checks.
3. Milestone done or CLI changed? Update README Status or Usage and run the new command on a scratch
   copy of `examples/` with `BOMGEN_LIBRARY_HOME` and `BOMGEN_WORKSPACE` pointed at scratch folders.
4. Run the link loop and the gate. Batch these updates into one docs PR over a range of merges.

Never run `bomgen layout --force` or project imports on the real `examples/`.

## 12. Sizing and layout engine

No task is open. For any change (a layout fix from the Panels board or equipment editor, or a new or
changed R-rule from Ali):
1. Read the R-rule in ADR 0013 and the design's section 4. If code and spec disagree, ask Ali on a card.
2. Failing test first, named `test_r<N>_...`.
3. Keep the goldens unless Ali directs; if one must move, ask Ali first.
4. If an R-rule changes, add a dated amendment to ADR 0013 (as R5 and R7 have).
5. Grep the callers (STATE.md section 9); if their values change, run `tests/unit/app/`.

Don't place pins before the automatic fill (pins-first re-flows other devices); don't count
`l2_ports` per unit without asking Ali (R2 says per entry).

## 13. BOM rule engine

No task is open; the next is the model changes (step 4) in A4's plan. Likely work:
- **A DC aux-contact choice.** If Ali wants DC aux contacts to follow `mcb_dc`, add the choice key to the
  models, then switch `aux_contact_line` in `engine/dc_dist.py` to it. Tests first, e.g.
  `test_dc_aux_contacts_use_the_dc_aux_choice`.
- **New shipped-library data.** When `inrush_a`, `inrush_ms` or `input_v_max` change in `data/library/`,
  rerun `tests/unit/engine/test_engine_shipped_library.py` and update only its expectations (goldens
  stay on `examples/`, Q38).
- **A changed engine rule** (anything Ali changes in plan §6): find the module in STATE.md section 10,
  write the failing test named after the rule, change the code, keep the goldens unless an ADR moves
  them. Check `sheets/` when `BuildResult` changes shape.

Don't: revive `DeviceType.min_branch_mcb_a` as a rating input (ADR 0019 item 4); count inrush peaks
under `inrush_min_ms` (item 3); switch the default DC MCB from the iC60N (Q37) or drop the FGR-60F or
iC60N `dc_float` warnings (Q37, Q41); put CINC on the DC set (group E's AC main, ADR 0023 point 1); read
`catalogues.mcb` in DC code (pass `library.catalogues.dc_mcb` to the `engine/mcb.py` helpers).

## 14. Excel workbook writer

1. **Calc-sheet header fit in Excel** (M5, Q11), once Ali answers (section 3 item 4):
   - Overlap: raise `LINE_SPACING` (1.2) in `src/bomgen/sheets/header_footer.py`, e.g. to 1.4, and
     update the expected sizes in `tests/unit/sheets/test_header_footer.py` (failing test first).
     `fitting_size` floors, so at 1.4 the sizes become 15 pt at 49 %, 14 pt at 50 % and 9 pt at 78 %
     (checked 2026-10-29).
   - Fits: no code change; record the answer in Q11.

Don't hard-code project text (such as a footnote) in the sheets; it comes from inputs. Don't judge print
layout from LibreOffice PDFs. `tests/unit/writer/test_no_xlsx_in_repo.py` enforces no committed `.xlsx`.

## 15. Desktop app

No task is open; Ali's v0.2.1 feedback decides the next app work. If he reports an app bug, fix it
test-first in a small PR. Since the audit: the app never shows the prototype's data; without a bridge
every page is "BOM Generator could not reach its engine" with *Try again* (#227), and the device
editor shows `min_branch_mcb_a` read-only as deprecated (#228).

How to work: TDD (for UI-only changes, an asserting test in `test_app_ui_assets.py`); conventional
commits (`fix(app): …`); never commit scratch scripts or screenshots. For UI PRs run a Playwright E2E
(LESSONS.md "E2E without the window"), save screenshots to the project files folder `a11-screens/`, and
screen-check the real app. Measure clipping, gaps and wrapping with `getBoundingClientRect`, not by eye.

Open ideas (none asked for): Add device and Change… could list the project's own library version instead
of the active one; undo for a dropped pending library device; one save-bar component for Loose material
and the device editor (today `screens-loose.js` and `screens-libedit.js` build their own with
`App.fixLine`); a smoke test driving the WebView2 window on the Windows CI runner.

Don't put business rules in the UI, and don't use dynamic bridge calls (`Bridge.call(name)`).
