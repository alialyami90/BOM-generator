# LESSONS

Decisions too small for an ADR, and approaches that failed. Section 1 covers working practice; the
rest is grouped by code area. Append-only: add new entries at the end of the right section and mark a
replaced entry "superseded by …".

## 1. Working practice

### Ali's standing rules

- Don't ask Ali to merge ("Check the merge for conflicts and merge it"). PRs are squash-merged once
  they are conflict-free and CI is green.
- Every question to Ali goes on a decision card with one option recommended ("If u have questions to me
  prompt it in a cards always"). Record the answer as a plan §6 question.
- Only Ali accepts ADRs. Use the Superpowers skills.
- Releases come from main when a version bump merges (#153); nobody pushes tags.

### Git and branches

- Force-push is refused by the session's safety check, and a session may push only to its own branch.
- **Branch restart after a squash merge:**
  ```bash
  git fetch origin main <branch>
  git checkout -B <branch> origin/main      # then commit or cherry-pick the next change
  git merge -s ours origin/<branch> -m "chore: merge old branch history (already squash-merged)"
  git push -u origin <branch>               # a plain push now fast-forwards
  ```
  `git rebase origin/main` after a squash merge replays the whole branch history and conflicts.
- **Queued work on one branch:** while one PR is open, build the next on a local branch from
  `origin/main` (keep a patch backup in project files), then rebuild the push branch with the recipe.
- **Rebasing a test module both sides appended to:** take main's file, then add your appended tail from
  `git show <commit>`. Put new tests away from another open PR's insertion point, and check with
  `git merge-tree --write-tree HEAD origin/<other-branch>` before pushing.
- `docs/decisions/README.md` and `docs/plan.md` conflict when two milestones are open; keep every row in
  number order and both notes.
- The clone may be shallow: `git fetch --unshallow` before using old shas; `git fetch --tags` if
  `v0.2.x` tags are missing locally.

### Environment and the gate

- A fresh container has no `bomgen` installed: `pip install -e ".[dev]"`. Rerun it after pulling, since
  new dependencies (ruamel, pycel) break a stale install. `.[dev,app]` fails on Linux (pywebview's
  `proxy_tools` wheel); use `.[dev]`.
- The `mypy` and `pytest` on PATH (`/root/.local/bin`) run under another Python without pydantic
  ("Error importing plugin pydantic.mypy"). Use `python -m mypy` / `python -m pytest`, or a venv
  (`uv venv /tmp/venv && uv pip install -p /tmp/venv -e ".[dev]"`).
- **In a git worktree the editable install points at the main checkout**, so tests run the wrong `src/`.
  Run with `PYTHONPATH=src` and check `python -c "import bomgen; print(bomgen.__file__)"` first; a stale
  install has twice produced false test failures.
- The full suite took ~10 min after #130, ~2–4 min after #149's parse cache, and 5–7 min at 2672 tests;
  goldens take about 5–7 s. Run pytest in the background (foreground calls time out at 120 s or 600 s).
  `sleep` is blocked: use `run_in_background` or `timeout … until` loops. A grep for " passed" also
  matches ruff's "All checks passed!"; wait on `" in [0-9.]*s"`.
- ruff RUF001–003 reject en dash, ×, −, `›` and other ambiguous characters in code and comments. Write
  ASCII or escapes.
- Docs-only PRs skip lint, mypy and pytest in CI ("Detect code changes"); `ci-status` is the check that
  must be green. Still run ruff locally.
- A push cancels the previous run, whose `ci-status` then shows failure on the old sha. Check the newest
  run before fixing anything.

### PRs and GitHub

- PR body starts with the attribution block from the session's instructions (copy it from there, not
  from an older PR: #123 and #159 had wrong links, fixed with `update_pull_request`) and ends with the
  attribution footer. GitHub comments end with the Claude Code footer.
- Requesting Ali as reviewer fails ("Review cannot be requested from pull request author"); assign
  `alialyami90` instead. Subscribe to every PR you open so CI results arrive without polling.
- The GitHub MCP tools must be loaded with ToolSearch and the server drops often; reload and retry.
  `fields` on `list_pull_requests` keeps answers small.
- Some early PRs show "closed, not merged" because they landed as commits; check `git log origin/main`.
- Read a PR's own description for the "why" of a change before guessing (#178).
- Keep ADR edits in their own `docs(adr): …` PR, not mixed into a docs update (#167 → #170).

### Reviewing a PR

1. `git fetch -q origin main refs/pull/N/head:refs/remotes/pr/N` (wrap in `timeout 90` with retries;
   fetches sometimes hang).
2. `git merge-tree --write-tree origin/main pr/N` (prints a tree id when clean).
3. `git diff --stat origin/main...pr/N` for scope.
4. For each changed `.js` file: `git show pr/N:path > /tmp/c.js && node --check /tmp/c.js`, and read the
   template strings (#126 had `aria-label=""${…}` that no test catches).
5. `pull_request_read get_check_runs`; app, packaging, pyproject and release-workflow PRs also need a
   green "Build Windows installer".
6. Run the full gate yourself for engine or cross-area changes: in a scratch `git worktree` with
   `git merge --no-commit origin/main`, then ruff, `PYTHONPATH=src python3 -m mypy`,
   `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider`.
7. Merge with `merge_method: squash` and the reviewed head sha as `expectedHeadSha`. A 409 means the head
   moved: re-review.

- A spec disagreement found in review (#157's print area) goes to Ali on a card before merging, even
  when the code is right.
- Cross-area engine edits are fine when they are minimal guards (#122's `part_id is not None`).
- A screen check in the real app before merging UI PRs catches what tests can't (clipped selects, ids
  that wrap, a dialog opening over the wrong page). #207 failed its first check. Keep each UI PR to one
  screen area.
- When nits turn up after a PR is good, merge it and send the nits as one follow-up PR (#208).
- Release sequencing: hold other merges until a release is published; prepare the CHANGELOG while the
  last PR is open but open it only after that PR merges, so its wording matches the final squash.

### Keeping these docs honest

- Check what merged since STATE.md was written before trusting it: STATE has named shas that docs-only
  merges had moved past and PRs as open that had merged. Diff the paths you care about
  (`git log <old>..origin/main -- <paths>`) to tell docs-only drift from code drift.
- Run every check just before writing its result (a row loop once "printed nothing" until a rerun showed
  9 missing rows).
- Before carrying a question forward, check plan §6: finding 24 and the iC60N float warning were
  settled by Q41 and Q37 while still listed as open.
- A fresh reader of these docs is a good test; it has found short paths, missing setup steps and wrong
  branch ranges. Write full paths.

## 2. Input models and I/O

- Writers compare problems by (file, location, message), not by line; lines move with an edit (ADR
  0021 point 2).
- `Project.substations` stays required but may be empty (M17d). A `default_factory` would have hidden a
  misspelt key (the `test_*misspelt*` test caught it). The build refuses an empty substation.
- A loose item's "Designation" is the existing `tag`, so existing files load unchanged (ADR 0022 point 1).
- Removing the last loose item leaves `items: []`; `host_panel` and `title` are kept, and the engine
  prints no sheet without rows (#123).
- `validate_*` functions are dry runs of the writer: one code path, so the form's message is exactly what
  the save would report.
- Seeded defaults with no source get a `# ASSUMED` comment (`set_comment(node, key, "ASSUMED")`); the app
  highlights them through `fields.assumed_fields(file)`.
- `schemas/` is generated from the models; regenerate it with every model change. No test checks it.
- `model_copy` skips validators: anything built with `model_copy(update=...)` (like
  `resolve_catalogues`) can hold values the model would refuse. Prefer a property, or re-validate.
- Copy shared fixture dicts (`dict(ABB_MCB)`) before mutating them; one test leaked into the next.
- Suite speed: the cost was YAML parsing, not pydantic. Profile one slow test with
  `python -m cProfile -s cumtime -m pytest <test>` before adding fixtures. The parse cache is keyed by
  text, so it can't go stale; errors aren't cached, so each names its own file.

### ruamel.yaml round-trip traps (`io/round_trip.py`)

- Settings that make `examples/` dump byte-identical: `indent(mapping=2, sequence=4, offset=2)`, width
  4096, `_PaddedEmitter` for `{ a: 1 }`, and `null` written out.
- A comment after an entry is `ca.items[key][2]` (map) or `[0]` (seq); a flow collection's comment sits
  in its parent's slot; blank lines before a key may sit in `ca.items[key][1]`.
- Deleting or emptying produced invalid YAML: fixed by moving tails (`_take_tail`/`_put_tail`,
  `edit_document`) and writing empty containers in flow style. Double blank lines came from `[1]` lead
  comments (`_drop_blank_lead`). The comment column shifted when a value grew (`_shift_comment`).
- `mkstemp` makes files 0600: `write_atomic` keeps the old mode (new files 0644) and creates the parent.
- ruamel writes `&id001`/`*id001` when the same object is dumped twice (a `date` reused for three
  register entries). `_Representer.ignore_aliases` returns True for scalars only; ignoring aliases for
  lists and mappings broke the byte-identical round trip of `examples/library.yaml`, because ruamel drops
  `id\d+` anchor names on load.
- An empty collection is written in flow style (`[]`, `{}`) so the file stays valid; when it gains its
  first entry `set_entry` switches it to block style. Otherwise new nested mappings come out `{ a: 1 }`.

## 3. Device database and shipped library

- **Web budget:** about 100 fetches an hour. Run research with at most ~35 fetches per pass and plan a
  second pass an hour later (M14's first round ran out; a second pass finished it).
- `verified: true` only when that exact code was read on a manufacturer or distributor page. Never
  invent a code or figure: leave it out and say so in `notes`.
- The iC60N 2P is rated to exactly 125 V DC; the float is about 135–140 V. Q37 kept it as default; the DC
  ranges are brand sets (findings 22–23).
- No datasheet inrush or input range on originals in `examples/library.yaml`: it moved the SEL branch
  MCBs from 2 A to 6 A and broke the goldens (Q38: shipped library only).
- Don't copy `di_inputs` to DI-module alternatives: it broke `test_di_module_inputs` (finding 31).
- A rack part with unknown height leaves `height_u` out; the loader requires `height_u > 0` for rack parts.
- Normalise generated YAML with `dump_text(load_text(text))` and write block style; flow-style output
  failed `tests/unit/test_round_trip.py`.
- Check for existing keys before inserting: `dc_rating_v` was already on `catalogues.mcb` and the
  generator wrote it twice.
- When changing tests outside `data/`, assert the new composition, never loosen a test, and list them in
  the PR body.
- When the same fix lands elsewhere first (#165), merge main and take that version, then check its new
  tests against the data (one assumed every shipped brand is AC-rated).

## 4. UI design

### How to work

- **Impeccable:** run the launcher through `sh <skill-dir>/scripts/impeccable …` (direct exec is
  "permission denied"); `detect --json` on the app and prototype must return `[]`. If the binary is
  missing and npx is refused, check the craft floor by hand: no kickers, no side-stripe borders, no
  nested cards, no hard offset shadows, no gradient text.
- **Prototype checks:** vanilla JS in `docs/ui/prototype/` (`ui.js` App namespace, `ACTIONS` by
  `data-action`, `SCREENS`, hash routes, `engine-stub.js` stands in for the layout engine, `data*.js` is
  illustrative). Playwright: `NODE_PATH=$(npm root -g) node script.js` with
  `page.setDefaultTimeout(4000)` (failed clicks otherwise wait 30 s). Standalone file:
  `node docs/ui/tools/build-standalone.mjs`, copy `out/ui-prototype.html` to `/mnt/project-files/ui/`.
  Tokens: `node docs/ui/tools/build-tokens.mjs --check`.
- **Run the real app in Chromium:** serve `src/bomgen/app/ui` over HTTP, forward `/call` to
  `bomgen.app.api.Api`, and inject `window.pywebview.api` with Playwright `exposeFunction` (a `fetch`
  from the page is blocked by the app's CSP). Copy the example project into `BOMGEN_WORKSPACE`; import
  the library with `bomgen library import`. The scripts are in `/mnt/project-files/ui/harness/`
  (`README.md`, `serve.py`, `shoot.js`). The server serves the current checkout, so
  `git checkout --detach <pr-sha>` changes what you see; restart it when Python changed.
- **Polish cycle:** write ranked findings (`docs/ui/polish-v02.md` pattern), each tagged app fix or doc
  change (doc changes in the same PR as the findings); fix them in small PRs, one screen area each;
  screen-check each PR in the real app on its branch before merging.
- **Screen-check notes:** start with the verdict ("passes", or "not yet, hold the merge"); list failures
  with the exact symptom and a concrete CSS or wording fix; list what passed by item number; mark nits
  "not for this PR".

### Decisions

- **Three kinds of write** (`editing.md`): Form (save bar), Direct action (toast with Undo or backup),
  Pending set (library). A value is saved with its form; a record appears or disappears at once.
  Rejected: one save button for everything.
- **Pins** are the user's word for layout overrides; a pin may hold a position, and Pin here keeps an
  override equal to the automatic place. R7 stays fill-first, then overrides: "a pin holds".
- **Library edits are a pending set applied as a local version** (`1.4.0+local.1`), never in place, so a
  colleague can reproduce the workbook from the recorded version.
- **Alternatives are library parts linked by a group key**, shown as one comparison list with signed
  delta chips (never colour alone). Rejected: two-brand tabs per device.
- **"Use this instead"** hands the change to Network as an unsaved edit, reviewed and saved like any edit.
- **Loose material** has its own page and sheet (Q36, ADR 0020); `host_panel` names the document.
- **Catalogue brand:** project default on Overview; a substation may override.
- **Controls that cannot act are absent or disabled with a reason** (Ali: drag "doesn't work" because the
  grip showed without acting).
- **Changed marker** (`components.md`, #204): an unsaved edit is a 6 px warning-colour dot before the
  field label or at the start of a table cell, plus sr-only "changed"; a changed list gets a *Changed*
  badge. `#FFFF00` means "the workbook will show this as revised" and is wrong on a form. Rejected:
  yellow `td.changed` cells (briefly used in #146; check a reused class's meaning in the tokens and
  design language before reusing it).
- **Save bar, invalid state:** "N fields need fixing before you can save." is one control that jumps to
  the first error.
- **Errors in words** (`editing.md` "Validation"): model pattern and type errors are never shown raw;
  the bridge maps them (`library_edit.in_words`). An empty new list row is marked on the first save, not
  on Add.
- Choices show labels, not enum values ("Continuous", not `CONTINUOUS`); codes like VDC, L1 and RJ45 stay.
- **Substation name = BOM title line** (#191): no separate field, since the engine prints the name as
  the second title line.
- **Loose material copy** (#142): foot "Quantity is a whole number, or 1 Lot."; the free-text banner says
  there is no part, ordering code, make or model and it can't be fed from a cabinet, so an item needing
  power must be added to the library first. The Qty rule matches `_validate_quantity` (whole number ≥ 1
  or `1 Lot`).
- Number inputs are right-aligned with tabular figures. Row delete is one style: muted icon, danger on
  hover (`.btn--del`).

### Failed approaches

- A free-text loose item fed from a cabinet: the design predated ADR 0022, which refuses it.
- Detail-pane alternatives table at 400 px clipped its action column; the compact form drops columns.
- Loose page with a 300 px side card squeezed Qty and Fed from; cards moved below the table.
- Dialog inputs and library catalogue cells marked the page dirty (generic `data-dirty` handler); ignore
  `.dialog` and `data-lib-edit`.
- Menus positioned inside `#main` landed wrong; use `position: fixed` from the button's rect.
- Prototype Discard didn't restore edited lists; snapshot before the first edit.
- A dialog opened after async bridge calls landed on whatever page the user had moved to. Any
  async-opened overlay checks that the route and substation are unchanged and sets the trigger busy.
- Inline *Change…* beside the part id with fixed column widths broke the id mid-word and overflowed;
  fixed with `white-space: nowrap`, a wrapping `.part-line` and fitting widths.
- Six brand selects in 3 columns clipped the brand names; use 2 columns.
- A save bar with page padding under it floated above an empty band; the page is a flex column and the
  bar takes `margin-top: auto`.

## 5. Library store and packages

- **Edits are path-based JSON ops, not one function per field**, so the app's pending set maps onto ops
  and every model field is editable (ADR 0018 "Amendment: edit operations"). Device records use the same
  ops keyed by `part_id`; records stay in their file and new ones go to `device-db/local.yaml`, so
  unchanged files keep their bytes.
- **CSV import yields both a saved library and edit ops:** the CLI keeps the file's row order and saves at
  once; the app takes `edits` into its pending set.
- Row problems fail by default; `skip_invalid` makes them warnings and skips the rows (an existing device
  keeps its installed values). A missing table or column keeps installed values; a present table replaces
  that table's rows.
- A bad cell starting `=`, `+`, `-`, `@` gets "(probably an Excel formula)"; valid values are never
  flagged.
- Reserved CSV ids use a character `BrandId` forbids: `default_dc` (underscore) names
  `catalogues.mcb_dc` and can't clash with a brand id (`^[a-z0-9][a-z0-9-]*$`). Rejected: a separate
  `mcb_dc.csv` and `default-dc`.
- Every catalogue key must be in `_compare`'s list in `csv_import.py`, or its changes never reach the
  `changes` check or the app's edits (`mcb_dc` was missing until #179).
- Row messages go through `plain_message`; two places build row problems (`_Assembly.model_problems`
  and `_device_problems`); keep both on it.
- Pydantic union errors (`int | float`) come back once per member with the member as an extra loc
  segment; cut the loc where the data reaches a scalar and keep one message per location.
- String cells fed to strict pydantic number validators failed; fixed with a `_number` pre-parse.
  `StrictBool` is needed for `supply_ok`.
- A bulk `sed` stripped needed `type: ignore` comments; use a typed helper (`_device`) in tests.
- `write_bundle` creates missing folders and turns `OSError` into `LibraryPackageError`;
  `partial.unlink` in `finally` must suppress `OSError` (a file in the folder's place raised
  `NotADirectoryError`). After the version folder is swapped in, a failed `active` write removes the new
  folder and restores the `.replaced-<uuid>` one.
- Fetch and read main's copy of an ADR before amending it; it may have changed (#165 amended ADR 0018).

## 6. Windows installer and release

- **Self-test reads a build-time module manifest**, not the frozen app: `packaging/bomgen.spec` writes
  `bomgen_modules.txt` and `--self-test` imports every listed module. Walking the frozen app only sees
  what PyInstaller kept, so a dropped module would pass (proven with a fake module). Since #186
  `launcher.ui_files` also reads every `src`/`href` in index.html and `url()` in its stylesheets, so a new
  screen script needs no packaging change.
- After an expected non-zero exit in a pwsh step, reset `$global:LASTEXITCODE = 0` and end with `exit 0`.
- PowerShell reads `$name:` as a scope prefix: write `${LASTEXITCODE}:`. A unit test rejects the pattern
  (#57); learned because #55 merged before its Windows job finished.
- The frozen CLI skips `cli.main()`: `launcher.cli_main` calls the typer app directly, so setup in
  `main()` (UTF-8 console) must also run in `cli_main` (#70). Test with cp1252 stdout/stderr.
- `build` prints the workbook path first, then the check report; the smoke step takes line 1 as the path.
- A release made by hand blocks `gh release create` (an empty v0.1.0 was published in the UI first).
  Fix: delete the empty release (keep the tag) and "Re-run failed jobs"; the workflow now guards with
  `gh release view` then `upload --clobber` (#86).
- Tag name case matters: the workflow triggers on `v*`, and `V0.1.1` started nothing.
- Tag the commit the changelog covers. A retag reported as done may not be on GitHub (v0.1.1 stayed on
  the old commit because the old tag still existed); always check with `list_tags` or
  `git ls-remote origin refs/tags/<tag>`. From a phone: delete the tag in the UI, then publish a release
  with a new tag on the chosen commit.
- **Release from main, not tags (#153):** sessions can't push tags (HTTP 403), so tag releases stalled.
  Build, tag and release run in one workflow run because a tag made with `GITHUB_TOKEN` doesn't trigger
  other workflows. Rejected: a separate tagging workflow.
- **First-start default library is a launcher hook, not an installer `[Run]` step,** so the smoke test
  can use a temporary store and prove a reinstall changes nothing. Import only when `LibraryStore.list()`
  is empty, never force, never block the window; a double-clicked `.bomlib` skips it.
- A fast Windows job (about 90 s on a pip cache hit) is not a skipped one: check every step ran
  (`get_workflow_job`) and the log ends "Installed, verified and uninstalled".
- The first release from main (v0.2.0) worked end to end: plan 5 s, build/tag/publish about 3 min.
  Before opening a bump, check `list_tags` has no `v<version>` and `grep '^## \[<version>\]' CHANGELOG.md`.

## 7. Documentation and changelog

- **Changelog format.** Keep a Changelog; every merged PR number appears once (one milestone's PRs may
  share an entry, e.g. "(#44, #46)"), newest first in Added and Changed. Released sections
  `## [x.y.z] - YYYY-MM-DD` with link refs at the bottom (`compare/vA...vB`, `releases/tag/v0.1.0`).
  Rejected: per-milestone entries only (lost the fix PRs).
- **No changelog entry** for docs-only, handoff and chore PRs, version bumps (the heading records the
  version) and internal refactors with no user-facing change (#197).
- **Wording:** user-facing, no internal names; word each entry from the PR description and, for a
  release's last PR, from its final squash message (`git show -s --format=%B <sha>`). Wrap at about 78
  columns.
- Batch docs updates into one PR over a range of merges. Check `git log` for unlisted merges each time;
  docs once fell 42 PRs behind.
- **Verify commands on a copy:** `cp -r examples <scratch>/ex`. `bomgen layout` on the shipped example
  exits 1 by design (`fed_from: psa3`, plan M1c); `--force` rewrites `panels/`.
- **README-row coverage loop:**
  `for f in $(cd tests/unit && find . -name 'test_*.py'); do grep -q "$(basename $f)" tests/unit/README.md || echo "missing $f"; done`
  (same for `tests/golden`).
- **Link check loop:** for each doc, `grep -o '](\([^)#]*\))'`, drop http links, test
  `[ -e "$(dirname $f)/$l" ]`.
- A blank line inside a Markdown table ends it; check rendering after inserting rows.
- **Writing test-README rows:** read each module's docstring and test names first; a row says what is
  checked in plain words, not test names. `textwrap` breaks at hyphens ("screen-reader"), so hand-wrap.

## 8. Sizing and layout engine

The rules are in ADR 0013 and the design spec (R1–R10).

- **L1 model is ranked, then picked** (Ali): fewest per side, then fewest ports, then part_id. The
  `l1_switch` entry's `part_id` pins the model.
- **Each IED takes one A port and one B port** (Ali); port spare default stays 20 %.
- **Cable managers count** (Ali, Q32): 1U under each rack switch, firewall or patch panel.
- **Golden = what the rules give** (Ali): 3 L1 per side, demand 8, psa1 23U, psa2 19U after M12.
- **Annunciator after a layout is fed from panel 001** (Ali). `examples/` keeps psa3 for the hand-written
  goldens; the layout golden's fixture rewrites `fed_from: psa3` to `psa1`.
- **`with_layout` takes over `panels:` only once a listed file is `generated: true`**, keeping the spec
  goldens.
- **Size from kept units:** removed units leave the L2 demand and SFPs; when kept switches fall short,
  report `port-capacity`. Rejected: removal as layout-only.
- **`l2_ports` count once per entry**, as R2 says. The first `_side_ports` multiplied by unit count and
  was reverted.
- **`bomgen layout` rewrites `panels:` as text** to keep comments; it deletes stale generated files and
  only names hand-written ones. Rejected: a YAML round-trip, which drops comments.
- **Overrides apply after the fill (R7), in order; a later move of a unit replaces it.** Pins-first was
  rejected: it re-flows other devices, which the board contract forbids. A pin to the automatic place
  stays a pin.
- **Position** = 1-based place among rack devices; DIN-rail parts don't count; past the bottom means
  last; ties go by group order. A `PairMove` on an entry without A/B units is `stale-override`.
- **Blank plates (M12, Ali):** one under each rack block that ends in its active device, never under a
  cable manager. Plates have no BOM row (Q25).
- A CLI test growing the layout to psa4 clashed with the manual `ws` panel's sheet "4"; the test renames
  ws's sheet first.

## 9. BOM rule engine

- `loose_table` returns None when it has no rows (#123, ADR 0020). Rejected: an empty `LooseTable` that
  sheets and writer would each skip.
- `set_by` lists every condition that alone gives the rating, in order running, inrush, floor (ADR 0019
  item 5); PSA3-QCOD-1's annunciator at 1.04 A gives "running,floor".
- One `dc_float` MCB item, only when some panel has DC mains; a device without `input_v_max` gets no line.
- The spare branch rating is the largest used branch on its feed, or the floor when the feed has none.
- Revision rows match by tag; untagged rows (kit children) match under the tag above them, by
  description then order. Rejected: matching by position.
- ΣQ in the check report is the cabinet's own DC loads (ADR 0016), not the feed total.
- The MCB helpers (`rating_at_least`, `rating_above`, `mcb_line`) take the `McbCatalogue` to use (#154).
  Rejected: a `dc: bool` flag, which let a caller size from the wrong set silently.
- CINC stays on the AC set (#154): it is group E's "Main Auxiliary AC Supply" breaker. Check each
  breaker's group in the code (`ac_dist.py` vs `dc_dist.py`) before following a task note.
- #171 tests the shipped library in a module-scoped temp copy of `examples/` with the shipped file
  swapped in, instead of new goldens.
- Q30 and Q31: Ali kept every ADR 0014 default (#183), so no code change.
- When a model field the engine needs hasn't merged yet, stub it locally to run the tests and revert the
  stub before the PR; never commit a model change inside an engine PR.
- mypy (strict) rejected importing `BranchSizing` from `engine.dc_dist`; import models from
  `bomgen.models.calc`.
- A golden expecting `set_by == "floor"` for every branch failed on the annunciator; check what each
  example load is before writing the expected value.
- `resolve_catalogues(library, CatalogueChoice(...))` lets engine tests cover brand choices without the
  loader; `engine_factories.library(mcb_brands=[...])` fills `catalogue_brands.mcb`.

## 10. Excel workbook writer

- **Formula plus cached result:** every computed cell is `Formula(text, result)` so the file shows
  numbers before Excel recalculates (OUT-5).
- **Header size code before font code** (`&28&"Calibri,Bold"`); `&` in text is escaped as `&&`.
- **Calc-sheet header size** = largest size ≤ 20 pt whose three lines, scaled by the print scale, fit
  between header and top margins (`fitting_size`, Q11). Rejected: fixed 20 pt (overlapped at 49 %).
- Heat Dissipation C:D header stays merged, as in the reference (C4:D4).
- The HWIO total is summed in the sheet (`bom_sheet._table_sheet`); the engine has none.
- A cabinet with no powered device has no Heat Dissipation block, so Heat Calculations writes a typed 0.
- The Loose Material sheet uses the panel BOM layout; its header document is `host_panel`'s (ADR 0020).
- **Atomic replace** (#69): temp file in the same folder plus `os.replace`; on failure delete only the
  temp file. `close()` failure used to unlink the target, deleting an issued workbook.
- **Power footnotes** (#157): one row per entry, in file order, two blank rows below the NOTES (the
  reference has NOTES at B93–B95 and the footnote at B98); merged B:L, left/centre wrap
  (`styles.FOOTNOTE`); 15 pt per line because Excel doesn't autofit merged cells. No footnotes, no rows.
  Rejected: wrapping in narrow column B as the reference does. The field is a list of strings on the
  substation's `output` block (one string can't hold several; the printer isn't a BOM device). Print
  area includes them (Q40; the reference leaving it off is treated as a slip).
- **pycel reads cached values:** `ExcelCompiler.evaluate` returns the cached result, so a golden
  comparing evaluated with cached values tested nothing. Evaluate every formula once, then
  `compiler.recalculate()`.
- `startswith("=")` is not a formula test (text "=" cells); use openpyxl `cell.data_type == "f"`.
- LibreOffice PDFs can't judge header fit: they clip header text and ignore scale-with-document.
- XlsxWriter: `set_header` silently drops strings > 255 chars (we raise `WriterError`); 3.2.9 raises
  `struct.error` on a truncated picture, 3.3.0 its own exception; `UnsupportedImageFormat` can come
  before close; widths are stored as UI width + 5 px.
- A spec gap the reference "answers" can still be a disagreement (#157's print area went to Ali as Q40).
  Flag every departure from the reference workbook in the PR body.
- **Read Ali's reference workbook directly.** It is in the project files under `uploads/hearth/` (the
  file `dbc9ed74-…`; `file` reports "Microsoft Excel 2007+"). Copy it to a scratch dir as `.xlsx` for
  openpyxl and run Python with `-I` from another directory.

## 11. Desktop app

### Decisions

- **Bridge replies for edits** are `{written, issues, page}`, where `page` is the refreshed screen
  (`editing.edit_reply`): one round trip per edit.
- **Layout moves are pre-checked:** the bridge compares `layout_preview` errors before and after
  (`editing.layout_check`), because `io/edit` writers accept a move the layout can't take.
- **The board is read-only on hand-written panels:** Build ignores pins and deletes there; never draw an
  affordance that doesn't act. **Pin here passes the unit's current position**, or the layout could move
  it within the panel.
- **The loose page saves a draft through the writers in a fixed order:** removes (descending), sets,
  adds, host. Each step moves the draft onto the file, so a refusal leaves the rest to save again.
  Rejected: an ops log. Qty 1 is not written (model default). Fed-from on a free-text row shows "—".
  In-cell qty message: "Enter a number, or 1 Lot."
- **One shared draft form** (`App.draftForm(o)` in `ui.js`) owns the draft, checks, save bar, Ctrl+S
  and the reset on route change; a screen supplies `spec(key) -> [path, kind]`, `saved`, `check`,
  `write`, `done`.
- Re-render on a check reply only when the error state changes; a render while typing elsewhere drops
  keystrokes (lost a `power_margin` draft).
- Percentages show as % and are written as fractions rounded to 0.1 % (`toModel` kind `pct`). An empty
  field means null, which removes the key so the project or library value applies again.
- The model refuses equipment without its redundant L1 and L2 switches, so the first equipment is written
  in one go by `start_equipment` ("Add the core switches…").
- ISO date strings must become dates before `set_field` (`_dated()` in `api.py`), or YAML quotes them.
- Device records exist only for an installed library; a project whose `library.file` points to a folder
  copy has none, so the UI shows no badge.
- **Changed vs revision:** an unsaved edit gets the orange dot (`.chg`, `App.changedField(html)`,
  `App.changedCell(on)`); yellow `td.changed` means "differs from the last issued revision", Preview only.
- Model error text goes through `library_edit.in_words(key, message)`; add mappings there, not in JS.
- A list row with an empty cell is "unfinished" and not checked until save (`screens-libedit.js`).

### Failed approaches

- Dynamic bridge calls broke `test_every_endpoint_the_screens_call_exists`; always `Bridge.call('literal', …)`.
- A `//` comment in a one-line handler caused "Unexpected end of input"; use `/* */` and `node --check`.
- A refused drop with `dropEffect = 'none'` never fires `drop`; keep `'move'` and explain in the banner.
- Ctrl+S on a form ran before `change`; blur `document.activeElement` first.
- Calling `App.render()` synchronously from a `change` handler throws "Failed to set the 'innerHTML'
  property" (a blur during `innerHTML` fires `change`); queue it with `queueMicrotask(App.render)`.
- `icon` is a global in the UI scripts; destructuring it from `App` makes it undefined.
- Two class attributes on one element silently drop the second; build one `class="…"` string.
- Async click then navigation race: set `aria-busy`/`disabled`, and after the await return if
  `App.route()` or the substation changed. The hashchange handler calls `closeDialog()` before `render()`.
- Grid overflow: a `minmax(0, 1fr)` track doesn't stop a nested grid with an implicit `auto` column from
  growing; give it `grid-template-columns: minmax(0, 1fr)` and the item `min-width: 0` (`.net-grid`).
- Save bar at the window bottom: the page is a flex column with `min-height: 100%` and the bar
  `margin-top: auto`. Flex items don't collapse margins (the device editor tab panel moved 16 px).
- Ids never break: `white-space: nowrap` on part and row ids; `Change…` wraps under a long id.

### E2E and checking

- **Dead-code scan:** `pip install vulture && vulture src --min-confidence 80` is clean except
  `api.py` `FileDialogWindow.create_file_dialog(file_types=...)`, a Protocol parameter it cannot see
  used (audit 2026-10-30). Don't re-investigate it.

- E2E on the example needs generated panels: edit `fed_from: psa3` to `psa1` first.
- **E2E without the window:** pack `examples/library.yaml` with `bomgen library pack … --name
  psa-devices --version 1.0.0` and import it into `BOMGEN_LIBRARY_HOME`, or Home shows the first-run
  page. Bridge stub: `page.exposeFunction('__py', …)` plus an init script setting
  `window.pywebview = { api: new Proxy({}, { get: (_, n) => (...a) => window.__py(n, a) }) }`, backed by a
  line-based Python process over `Api(env=…)`.
- A dirty page opens the leave dialog on navigation; discard first before `location.hash = …`.
- Measure, then claim: in Playwright check a select's text width vs `clientWidth - 34`, a table's right
  edge vs the next column, `getClientRects().length > 1` for a broken id, the gap between `.savebar` and
  `#main`'s bottom.
- The app window's minimum is 1280×720 (`window.py` `MIN_SIZE`): screenshots at 1024 show a sideways-
  scrolled shell, not a narrow layout. Take 1280 and 1440.
- Playwright and toasts: several toasts can carry Undo at once; click `.toast:last-child
  [data-toast-undo]`, not the first `.toast button`.
- ruamel 0.19 kept the "- " flag through a flow mapping: after a first list item `- { a: 1 }  # note`
  the next block mapping came out on one line. `_PaddedEmitter` resets `no_newline` on "{" (M23).
- `test_every_endpoint_the_screens_call_exists` needs a literal endpoint name in every `Bridge.call`;
  a helper that passes the name in a variable fails it.
