# NEXT: the whole team

One file for every role's next steps, merged from the per-role `NEXT.md` files and the old handoff
README. Read [STATE.md](STATE.md) first. Nothing is half done anywhere: every role's tasks below are
either waiting on Ali or on the lead.

## 1. How to resume any role after a context reset

1. Read, in order: [STATE.md](STATE.md) (the project section and your role's section), this file,
   [LESSONS.md](LESSONS.md), [CHECKPOINT.md](CHECKPOINT.md), then [`CLAUDE.md`](../../CLAUDE.md) and
   [`docs/agents.md`](../agents.md) (roles keyed by number: C1 has A1's rights).
2. Before trusting STATE.md: `git fetch origin main`, `git checkout -B <your session's branch>
   origin/main`, `git status --short`, `git log --oneline -10`. Use the branch your session names, not
   one STATE.md lists.
3. Fresh container: `pip install -e ".[dev]"` (not `.[app]`, which fails on Linux). Then the gate with
   the module form, because the `mypy`/`pytest` on PATH are not the project's:
   `ruff check . && ruff format --check .`, `python -m mypy`, `python -m pytest -q -p no:cacheprovider`
   (5–7 min; run it in the background). Compare with STATE.md → "Verification" and record drift in
   LESSONS.md.
4. Post a readback in your thread (name and role, files you own, state, next action, drift). Find the
   current lead with `list_threads` or ask the coordinator; give your thread id in your first message.
5. Do the first item of your role's section below. Ask Ali only on a decision card
   (`request_decision`) with one option marked recommended. Never ask Ali to merge.

**Updating these files.** At a handoff, edit your role's section of STATE.md and NEXT.md in place,
append to your role's part of LESSONS.md, and add a dated entry at the top of CHECKPOINT.md's log. Send
it as a docs-only PR to the lead. Two roles editing next to each other in the same file will conflict;
merge origin/main and keep the other role's lines.

## 2. Rules for every role

- One milestone per PR, a conventional commit, TDD with tests named after the rule, the gate green
  before every commit.
- PR body starts with the two attribution lines from your session's instructions (copy them from
  there, not from an older PR) and ends with the attribution footer. Assign `alialyami90` (requesting
  Ali as reviewer fails because he is the PR author). `subscribe_pr_activity`, then message the lead's
  thread with the PR number and gate result. The lead reviews and squash-merges.
- Change only files your role owns (agents.md "Owns"). Send fix requests to the owner. A cross-role
  edit needs the owner's or lead's agreement and a line in the PR body.
- Don't edit `docs/spec/` (Ali's, through the lead), don't move golden values without an ADR, don't
  mark ADRs Accepted (only Ali does), don't commit `.xlsx`, don't force-push (see LESSONS "Branch
  restart"), don't bump the version outside a release PR (on main it publishes at once), don't push tags.
- If code and spec disagree, ask Ali (through the lead, on a card) before changing either. Next free
  numbers: ADR 0024, Q42, milestone M19.

## 3. Role 1: Lead developer

**Next action:** run section 1, then `list_pull_requests state=open` and review and merge whatever is
ready (LESSONS role 1 "Review procedure"). Then post item 1.

1. **Ask Ali what comes after v0.2.1.** Post a fresh `request_decision` in your own thread: "What should
   the team do after v0.2.1?" with options "Test v0.2.1, send feedback" (recommended: everything he
   asked for in v0.2 shipped and no one has used it in the field yet) and "I'll describe v0.3 now".
   Close the old card (STATE → "Waiting on Ali") with `close_decision` if you can; otherwise ignore it.
2. **When Ali's feedback arrives:** write it into `docs/backlog.md` as numbered points (as for v0.2),
   propose milestones in `docs/plan.md` (from M19), give decisions an ADR (0024 on) or a plan question
   (Q42 on), and brief each owning role. One PR per milestone.
3. **One card for the ASSUMED seeds:** show Ali the cabinet number pattern, the enclosure and the
   document number/date defaults a new substation gets; recommend "Keep them, edit per project in the
   app". If he changes them, role 2 changes `_blank` in `src/bomgen/io/lifecycle.py`.
4. **Spec catch-up:** when Ali has time, offer one card to bring the spec in line with ADRs 0017, 0019,
   0020, 0022, 0023 and Q35–Q41, through the process in `docs/spec/`.
5. **Excel header fit (Q11).** Card: "Does the header on Power Consumption and Heat Dissipation overlap
   the table in Excel's Print Preview?" Options "It fits" (recommended: the size is computed to fit at
   the print scale) and "It overlaps". Pass the answer to role 10 (section 12) and record it in Q11.
6. **Next release** (v0.2.2 or v0.3.0): STATE → "How a release happens". Hold other merges between the
   CHANGELOG merge and the published release.
7. **Checkpoints:** merge docs-only handoff PRs as they arrive. Adjacent edits in the same handoff file
   conflict; merge non-adjacent ones first and ask the others to merge origin/main just before you merge.

Don't: edit other roles' files; merge app, packaging, pyproject or release-workflow PRs without a green
"Build Windows installer"; ask Ali anything in plain text; ask Ali to merge (he said: "Can you stop
asking me for merges? Check the merge for conflicts and merge it").

## 4. Role 2: Input models and examples

**Next action:** none assigned. After section 1, ask the lead whether anything is queued, then task 1.

1. **Compute the unset `mcb_dc` fallback instead of storing it** (A1's note on #151; not urgent).
   - Store `mcb_dc` in the resolved catalogues only when it is written (a brand id or `default`);
     otherwise leave the library's own `catalogues.mcb_dc`, or `None`. `Catalogues.dc_mcb` already falls
     back to `mcb`.
   - Keep ADR 0023 point 2: `{mcb: brand}` with no `mcb_dc` must still size DC with that brand, even
     when the library carries its own `catalogues.mcb_dc`; so when `mcb` is written and `mcb_dc` is not,
     set `mcb_dc` to `None` instead of copying. When neither is written, the library's own value wins.
   - Tests first (`tests/unit/test_library_alternatives.py`, `test_catalogue_choice_loader.py`):
     `test_a_resolved_library_validates_again` (`Library.model_validate(resolved.model_dump())` doesn't
     raise); keep every ADR 0023 test green; goldens unchanged.
   - Callers to grep first: `engine/dc_dist.py`, `engine/mcb.py`, `checks.py`, `app/projects.py`,
     `io/references.py` (all read `catalogues.dc_mcb`, never `mcb_dc`).
2. **Answer the app's questions on the writers** (`io/fields.py`, `io/edit.py`, `io/panel_edit.py`,
   `io/loose_edit.py`, `io/lifecycle.py`, `fields.part_users`, `fields.assumed_fields`). A small API
   addition is one PR, tests first, with a line in ADR 0021 or 0022 when it changes a writer rule.
3. **Q23** (Ali): keep the default (the masters); act only on his answer and record it in plan §6.
4. **If Ali answers the `generated_panels` defaults:** change `_blank` in `io/lifecycle.py` and
   `test_a_blank_substation_seeds_generated_panels_so_equipment_can_be_added`; drop `# ASSUMED` on any
   value he confirms.

Not tasks: DC sizing from `dc_mcb` (role 9, done); the writer side of `power_footnotes` (role 10);
`fed_from` accepting any panel id (ADR 0022 point 4); `bomgen layout` using PyYAML (ADR 0021);
`examples/library.yaml` device data and `data/device-db/` (role 3); `library_store/` (role 5).
Don't edit `engine/`, `sheets/`, `app/` or `library_store/`, or change `examples/` values the goldens
check without the lead and a spec citation.

## 5. Role 3: Device database researcher

**Next action:** after section 1, do finding 30 as a data PR for the lead.

0. **On any resume** also run `python data/library/build.py` and check `git status` is clean (if not,
   someone edited the example library or device-db without regenerating; regenerate and add it to your
   next PR), and check `/mnt/project-files/handoff/03-device-db/` still has the generator.
1. **Finding 30: power figures for 11 skipped alternatives.** Give each alternative in
   `docs/device-db-findings.md` item 30 a sourced `unit_power_w` with `power_basis` and `power_note`
   (README "Electrical data for the library (M14)"), plus inrush if a datasheet gives it. Records:
   `data/device-db/network.yaml` `SEL-2730M-EXT` Siemens low tier (SCALANCE XR324-4M EEC; use the
   125 V DC code 6GK5324-4GG10-4JR2, finding 27); `data/device-db/sel-automation.yaml` `SEL-3555-GW`
   and `SEL-3555-RTAC` Hitachi low and high (RTU540 discontinued, 560CMG10 not found, finding 27, so a
   replacement model may be needed), `SEL-2488` Arbiter mid (1202B/C), `SEL-2240` Hitachi low and high,
   `SEL-3355` Siemens IPC427E, IPC647E and IPC847E (IPC647E is 2U). Never invent a figure; set
   `verified` per the README; at most ~35 web fetches per run. Then update finding 30, run the gate
   (`test_device_db.py` covers the power basis) and open the PR.
   - **Second PR (needs role 2's OK for `examples/`):** add the now-powered tiers as library parts using
     the rules in STATE role 3 "How M14 turned the database into library parts", run
     `python data/library/build.py`, commit both files, and check the goldens and role 9's
     `test_engine_shipped_library.py` are unchanged.
2. **Finding 31: `di_inputs` for the SEL-2244-2 alternatives.** Record each module's digital input
   count in `data/device-db/sel-automation.yaml`, then set `di_inputs` on its library part (same two-PR
   route). Check how the engine uses `di_inputs` (role 9) first.
3. **Ask the lead whether the M14 generator should move into the repo**, idempotent (skip existing part
   ids), under `data/device-db/tools/`, passing ruff and mypy. Ask before task 1's second PR.

Don't: put the originals' inrush or input range in `examples/library.yaml` (Q38; it moves the goldens);
change the default MCB from iC60N (Q37); research a DC-rated firewall to replace the FGR-60F (Q41);
hand-edit `data/library/psa-devices.yaml`; edit `src/`, `examples/`, `release.yml`, ADR 0009 or other
roles' tests without the lead; bump psa-devices without roles 1, 2 and 6 agreeing.

## 6. Role 4: UI designer

**Next action:** screen-check #208 on `origin/main` in the real app (task 1), then the departures PR
(task 2). Both are small.

1. **Screen-check #208 on main** (role 11, "keep row ids whole and the device editor's tab offset",
   `dce6277`). Network › Equipment: a row id in the cell sub line (e.g. `ext-fw` on FGR-60F) stays on one
   line; the part id (e.g. `RST2228-L1-24MM`) never breaks and *Change…* drops under it when there is no
   room. Library › any device › Electrical: the first field row sits as close under the tabs as on other
   tabs; the save bar meets the window bottom on short and long tabs. Done when the result goes to the
   lead and role 11 in one note each (on failure: exact symptom and suggested CSS fix).
2. **Record the v0.2 departures in `docs/ui/screens.md` "Departures in the built app"** (one docs PR,
   #82 pattern). Remove or rewrite the first bullet ("Projects, substations and settings are
   read-only"). Add, after checking each on main: Panels board read-only for hand-written panels (with
   the reason line the app shows); Move… dialog Position is top, bottom or where the layout puts it, not
   a numbered select; unsaved edits use the Changed marker, never revision yellow (yellow only in Preview
   for revised cells); Network *Change…* at the end of the part-id line, wrapping under it when narrow;
   Settings › General catalogue brands in a 2-column form, each "Same as the project (…)" naming the
   resolved brand; Settings › Documents register select shows the key only; Project › Documents register
   rows are two lines (Confirm on the *Assumed date* line) and Used by drops the substation prefix inside
   its group; Design constants Default column empty on unchanged rows; anything else found walking every
   v0.2 screen against `editing.md`, `screens.md` and the prototype. Done when the PR is open, the gate is
   green and `impeccable detect --json docs/ui/prototype` returns `[]`.
3. **Add the hand-written-panels rule to `docs/ui/editing.md` "Panels board: drag, drop, pin,
   delete"**: the board is read-only, why (Build uses the panel files, so a pin wouldn't change the BOM)
   and how it says so (one-line banner, no grips, no pin or delete actions). Can share task 2's PR.
4. **The wording nits in STATE role 4 drift item 4:** check each on main and send role 11 the ones still
   there in one note. Don't file `polish-v02.md` again; it is complete.
5. **Then design work only on request.** A new screen or flow starts with the `impeccable` skill, a
   section in `editing.md`/`screens.md`/`components.md` and a prototype screen (CLAUDE.md "UI work").

Setup: gate venv `uv venv /tmp/venv && uv pip install -p /tmp/venv -e ".[dev]"`; impeccable via
`sh <skills>/impeccable/scripts/impeccable detect --json <dir>` (find the dir with
`ls /root/.claude/skills/synced/*/impeccable`); real-app harness per LESSONS role 4; prototype checks
`docs/ui/tools/build-standalone.mjs`, `docs/ui/tools/build-tokens.mjs --check`, Playwright with
`page.on('pageerror')`.

Don't: add business rules to the UI; change tokens or fonts without telling role 11 (the app's
`tokens.css` and fonts must stay byte-identical to `docs/ui/`); use `#FFFF00` for anything but the
workbook's revised cells; edit `src/`, `tests/`, the spec, `plan.md` (except M9) or ADRs (engine needs
go to the lead or role 2 via `editing.md` "Back-end needs"); redesign v0.2 parts 1–4.

## 7. Role 5: Library update packages

**Next action:** after section 1, wait for requests from the lead or role 11. M8, M8b and the M16
store side are done. Don't invent code work.

1. **Questions about the store, edit ops or CSV:** answer from the code and ADR 0018 (its amendments at
   the end win). Facts asked often:
   - Edits are JSON ops `{"op": "set" | "insert" | "remove", "path": [...], "value": ..., "index": ...}`.
     A string segment is a mapping key or, in a list, the item's `part_id` (devices) or `id` (brands); an
     int is a position. `apply_edits`/`check_field` (`edit.py`), `save_edits` (`local.py`).
   - Device records use the same ops keyed by `part_id` (`["SW-1", "datasheet", "weight_kg"]`):
     `apply_record_edits`/`check_record_field` (`records.py`), `save_edits(..., record_edits=...)`.
     Changed records stay in their `device-db/` file; new ones go to `device-db/local.yaml`.
   - `preview_csv_import(source, store, name, base=None, skip_invalid=False)` → `CsvPreview` with
     `checks`, `problems` (`RowProblem`: table, Excel row, column, plain message, key), `rows`, `diff`,
     `changes`, `edits` (for the app's pending set), `library`, `base`. `skip_invalid=True` turns row
     failures into a warning and skips the rows.
   - CSV: one file per table (ADR 0018). `catalogue_id` `default` is `catalogues.<kind>`, `default_dc`
     is `catalogues.mcb_dc`, any other id is a brand. A missing table keeps the installed rows; a present
     table replaces them; a missing column keeps installed values.
   - Alternatives are only the `alt_group` key on devices; `compare_alternatives` gives the rows.
2. **A bug or gap in role 5's files:** one small PR per gap, failing test first, full gate.
3. **A new model field (role 2 adds it):** the CSV needs its column in the same PR or a follow-up right
   after ([ADR 0018](../decisions/0018-library-csv-exchange.md) Consequences);
   `test_a_device_with_every_field_set_survives_the_round_trip` catches a missing one.

Optional, only if asked: `LibraryPackageError` carrying manifest and `active` data; CSV tables for
device-database records. Don't: edit `app/`, `models/`, `io/`, `engine/` or `data/`; add model fields
yourself (ask role 2); change an ADR inside a checkpoint PR (ADR edits go in their own `docs(adr): …`
PR); create an ADR without a number from the lead.

## 8. Role 6: Windows installer and release

**Next action:** none open. Wait for the lead or Ali to call the next release, then task 1.

1. **Cut the next release when called** (v0.2.2, v0.3.0, …). Done when Ali has the release link.
   1. Confirm `CHANGELOG.md` on main has `## [X.Y.Z]` (role 7's, merged first) and `list_tags` has no
      `vX.Y.Z`.
   2. Branch from main; change only the three version lines (STATE → "How a release happens"). Reinstall
      with `pip install -e ".[dev]"` so version metadata updates, then run the gate.
   3. Open `chore(release): version X.Y.Z` (copy #211's body); say merging publishes; tell the lead. Not
      before the lead says go.
   4. After the merge, find the push run of `release.yml` on main (`actions_list`, branch main, event
      push). `plan` must pass and `installer` must run all its steps (`get_workflow_job`; 90 s is normal
      on a cache hit). Then `release` publishes.
   5. `get_release_by_tag vX.Y.Z`: `bomgen-setup-X.Y.Z.exe` and `default.bomlib` present, tag on the
      merge commit. Send Ali the link and tell the lead.
   - `plan` fails (pyproject mismatch or missing changelog): nothing was created; fix in a follow-up PR.
   - `installer` fails: read `get_job_logs`, fix in a PR with the Windows job green. A merged fix
     re-releases only if it touches `__version__`, `pyproject.toml` or `CHANGELOG.md`; otherwise "Re-run
     failed jobs" on the release run, or ask the lead.
   - Tag creation refused (a ruleset): tell the lead and Ali. Fallback: Ali publishes a release in the
     GitHub UI on that commit with tag `vX.Y.Z`; the tag push re-runs the workflow, which attaches the
     assets and fills an empty body.
2. **App work that adds a dependency or a data file outside `src/bomgen/app/ui/`:** check the frozen
   build carries it. UI files are covered by `--self-test` since #186. Otherwise check the PR's Windows
   job, or freeze on Windows with `pip install ".[app]" -r packaging/requirements.txt`,
   `pyinstaller packaging/bomgen.spec --noconfirm --clean`, then `dist\bomgen\bomgen.exe build
   examples\project.yaml` and `"dist\bomgen\BOM Generator.exe" --self-test`. Precedent: ruamel.yaml
   (#106) needed no spec change.
3. **Review PRs touching role 6's files** when the lead asks (as with #161): the pack step, the
   first-start regex, the `test_packaging` pins, ADR 0009 and a green Windows job on the PR head.

Ideas not started (ask the lead first): code signing (Q19) only with a certificate from Ali, as a
`signtool` step after "Compile the installer" with the secret in repo settings; a smoke step upgrading
from the previous release's installer; bump `actions/checkout@v4`, `setup-python@v5`,
`upload-artifact@v4`, `download-artifact@v4` when GitHub's Node 20 deprecation becomes an error.

Rules of the release workflow: any change to `release.yml`, `bomgen.iss`, `bomgen.spec` or
`launcher.py` needs "Build Windows installer" green on the PR head before merging (since #55); keep
build, tag and release in one run and release runs uncancelled; keep the main-push path filter to the
three version and changelog files; the Release workflow is not part of `ci-status` (ADR 0006) and never
a required check; never change the Inno Setup `AppId`; the pack step's library name and version must
match `examples/project.yaml` `library:` (`test_packaging`). Don't: move or delete a published tag or
release; edit `src/bomgen/app/` except `launcher.py`, `CHANGELOG.md`, models, examples or `data/`; make
the launcher bundle or import any library but the one default package.

## 9. Role 7: Lead developer assistant

**Next action:** after section 1, `git log --oneline 1678343..origin/main`. If only docs/handoff PRs
are listed, wait for the lead. Otherwise task 1.

1. **Post-merge pass (every wake).**
   1. `git fetch origin main && git checkout -B <your branch> origin/main`.
   2. `git log --oneline 1678343..origin/main` (move this sha forward after each pass). Don't wait for
      the lead to report merges.
   3. For each non-docs PR: `pull_request_read get` for its description and `git show -s --format=%B
      <sha>` for the squash message. One entry under `[Unreleased]` in Added/Changed/Fixed, newest first,
      PR number in brackets, no agent names, about 78 columns. Skip docs, handoff, chore, bump and
      internal-refactor PRs.
   4. New test module? Run the row loop (LESSONS role 7 L4) and add a row to `tests/unit/README.md` or
      `tests/golden/README.md` with its milestone and what it checks (read its docstring and test names).
   5. Milestone done or CLI changed? Update README Status or Usage and run the new command on a scratch
      copy of `examples/` with `BOMGEN_LIBRARY_HOME` and `BOMGEN_WORKSPACE` pointed at scratch folders.
   6. Run the link loop (L5) and the gate.
   7. Ask the lead whether to open now or batch; open one docs PR, assign `alialyami90`, subscribe, and
      message the lead.
   8. Report stale lines in other roles' files to the lead with path, line and evidence.
2. **Next release (when the lead calls it):** rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD` with a
   new empty `## [Unreleased]` above; link refs `[Unreleased]: .../compare/vX.Y.Z...HEAD` and
   `[x.y.z]: .../compare/vPREV...vX.Y.Z`; word the last PR's entry from its final squash message
   (patterns #193, #209). Open it before the bump; role 6 opens the bump after it merges. After the
   release, update README Status ("vX.Y.Z is released"; move finished milestones to "Done in vX").

Don't edit `docs/plan.md`, `docs/agents.md`, `CLAUDE.md`, `docs/backlog.md`, `docs/spec/`, `docs/ui/`,
`docs/decisions/` or code unless the lead assigns exact lines; don't approve or merge; don't run
`bomgen layout --force` or project imports on the real `examples/`.

## 10. Role 8: Sizing and layout engine

**Next action:** after section 1, tell the lead C8 is live and ask for an engine task. Until one comes,
idle; don't invent work in role 8's files.

For each engine task (likely a layout fix from the app's Panels board or equipment editor, or a new or
changed R-rule from Ali):
1. Read the R-rule in ADR 0013 and the design's section 4. If code and spec disagree, ask Ali on a card.
2. Failing test first, named `test_r<N>_...`, in role 8's test files.
3. Keep the goldens unless Ali directs; if one must move, ask Ali first.
4. If an R-rule changes, add a dated amendment to ADR 0013 (as R5 and R7 have).
5. A model field goes to role 2 as a proposal; role 8 never edits `models/` alone.
6. Grep the callers (STATE role 8 code map); if their values change, run `tests/unit/app/` and tell
   role 11 (and role 2 for `io/edit.py`).
7. Gate, one milestone per PR, open for the lead, subscribe, fix CI and reviews until merged.

Don't: place pins before the automatic fill (ruled out on 2026-10-28: pins-first re-flows other
devices); count `l2_ports` per unit without asking Ali (R2 says per entry); edit UI files, `models/`/`io/`
without role 2's review, or `cli.py`/`build.py` without role 2's or the lead's leave.

## 11. Role 9: BOM rule engine

**Next action:** after section 1 (plus `python -m pytest -q tests/golden`), ask the lead for a task.
Nothing is queued.

Likely work (only when assigned):
- **A DC aux-contact choice.** If Ali wants DC aux contacts to follow `mcb_dc`, role 2 adds the choice
  key, then role 9 switches `aux_contact_line` in `engine/dc_dist.py` to it. Tests first, e.g.
  `test_dc_aux_contacts_use_the_dc_aux_choice`.
- **New shipped-library data.** When role 3 changes `inrush_a`, `inrush_ms` or `input_v_max` in
  `data/library/`, rerun `tests/unit/engine/test_engine_shipped_library.py`, update only its
  expectations (goldens stay on `examples/`, Q38), and tell the lead what moved.
- **A changed engine rule** (anything Ali changes in plan §6): find the module in STATE role 9, write the
  failing test named after the rule, change the code, keep the goldens unless an ADR moves them.
  Writer-facing changes to `BuildResult` go to role 10 first.

Don't: revive `DeviceType.min_branch_mcb_a` as a rating input (ADR 0019 item 4); count inrush peaks
under `inrush_min_ms` (item 3); switch the default DC MCB from the iC60N (Q37) or drop the FGR-60F or
iC60N `dc_float` warnings (Q37, Q41); put CINC on the DC set (group E's AC main, ADR 0023 point 1); read
`catalogues.mcb` in DC code (pass `library.catalogues.dc_mcb` to the `engine/mcb.py` helpers).

## 12. Role 10: Excel workbook writer

**Next action:** after section 1, tell the lead you are ready and stay idle until assigned. The only
open item waits on Ali.

1. **Calc-sheet header fit in Excel** (M5, Q11; waiting on Ali through the lead's card, section 3 item 5).
   First check `docs/plan.md` open questions for an answer.
   - Overlap: raise `LINE_SPACING` (1.2) in `src/bomgen/sheets/header_footer.py`, e.g. to 1.4, and
     update the expected sizes in `tests/unit/sheets/test_header_footer.py` (failing test first).
     `fitting_size` floors, so at 1.4 the sizes become 15 pt at 49 %, 14 pt at 50 % and 9 pt at 78 %
     (checked 2026-10-29).
   - Fits: no code change; record the answer in Q11 (or ask the lead to) and drop the task.
   - Done: gate passes, PR open, Q11 says what Excel showed.

Likely future work: a new sheet column or sheet driven by an engine change (role 9 announces
`BuildResult` changes first; input fields come from role 2); if the spec gets updated for ADR 0020 or
Q40, check the sheet docstrings still cite the right section names. Don't: edit the spec; change the
Preview tab or loose-material editor (role 11), the engine or input models without the owner; hard-code
project text (such as a footnote) in the sheets; judge print layout from LibreOffice PDFs.
`tests/unit/writer/test_no_xlsx_in_repo.py` enforces no committed `.xlsx`.

## 13. Role 11: Desktop app

**Next action:** after section 1 (plus `for f in src/bomgen/app/ui/*.js; do node --check $f; done`),
ask the lead for the next task. Ali's v0.2.1 feedback decides the next app work. If Ali reports an app
bug, fix it test-first in a small PR. Also read the plan's M10 and M12–M18 sections and
[`docs/ui/editing.md`](../ui/editing.md).

### Map of the code

- **Python** (`src/bomgen/app/`): `api.py` is the pywebview `js_api`; each public `Api` method is an
  endpoint returning `{"ok": true, "data": …}` or `{"ok": false, "error": {"kind", "message"}}`, reshaping
  engine results with no business rules. `projects.py` (Home, Project, Settings, `brands`),
  `substations.py`, `network.py` (Network page, sizing result), `loose.py`, `library_edit.py` (device
  editor, pending set, `in_words`), `library_csv.py`, `output.py` (Checks and Build), `preview.py`,
  `editing.py` (edit replies `{written, issues, page}`, layout pre-checks), `catalogues.py`, `window.py`
  (the WebView2 window). `launcher.py` is role 6's. Writers live in `bomgen.io.fields` (role 2):
  `set_field`, `remove_field`, `insert_item`, `remove_item`, `move_item`, `validate_field`,
  `confirm_field`, `part_users`, `document_users`; each goes through `io.edit.edit_file`.
- **UI** (`src/bomgen/app/ui/`): plain scripts, no build step, loaded by `index.html` in order:
  `bridge.js icons.js data.js engine-stub.js ui.js screens-projects.js screens-project.js
  screens-layout.js screens-substation.js screens-panels.js screens-loose.js screens-library.js
  screens-libcsv.js screens-libedit.js screens-output.js screens-verify.js screens-preview.js app.js`.
  A later script overrides an earlier `SCREENS.x` (`screens-substation.js` replaces
  `screens-layout.js`'s `SCREENS.network`; `screens-libedit.js` wraps `SCREENS.library`). `ui.js` holds
  `App` helpers (`draftForm`, `changedField`, `changedCell`, `fixLine`, `route`, dialogs, toasts); `icon`
  is a global. `data.js` + `engine-stub.js` drive the no-project example pages. Styles: `tokens.css`
  (role 4's) and `styles.css`.
- **Tests** (`tests/unit/app/`): `test_app_*_api.py` per endpoint group; `test_app_ui_assets.py`
  asserts strings in the UI files; `test_every_endpoint_the_screens_call_exists` parses literal
  `Bridge.call('name', …)` calls.

### How to work

- One PR at a time; prepare the next as a local commit. TDD (for UI-only changes, an asserting test in
  `test_app_ui_assets.py`). Conventional commits (`fix(app): …`); never commit scratch scripts or
  screenshots.
- UI PRs: run a Playwright E2E (LESSONS role 11 "E2E without the window"), save screenshots to the
  project files folder `a11-screens/`, and tell the lead so role 4 can screen-check. Measure clipping,
  gaps and wrapping with `getBoundingClientRect`, not by eye.
- CHANGELOG lines belong to role 7; pass them through the lead.

Open ideas (none asked for): Add device and Change… could list the project's own library version instead
of the active one; undo for a dropped pending library device; one save-bar component for Loose material
and the device editor (today `screens-loose.js` and `screens-libedit.js` build their own with
`App.fixLine`); a smoke test driving the WebView2 window on the Windows CI runner.

Don't: put business rules in the UI; edit `launcher.py`, the spec, plan structure, ADRs, CHANGELOG,
`docs/ui/` or other roles' modules; use dynamic bridge calls (`Bridge.call(name)`).
