# LESSONS — A4, UI designer (append-only)

## How to work
- **Thread ids** (Hearth `message_thread`): A1 `cmsg_01CGuLumA5u5e7gSGbisWmMi3nTuZbpZkUB1t4T5nt6GfE`; A11 (desktop app, thread "Show library catalogues in the app") `cmsg_01CGuLumA5u5e7gSGbisWmMiWeWKSTZqDbuAfYdwHEZoYc`; A8 `cmsg_01CGuLumA5u5e7gSGbisWmMiHgm9Qm4pLo8R5GdLXizMMu`. Messages are capped at 2000 characters: put long notes in a file under `/mnt/project-files/ui/` and link it.
- **Impeccable.** The skill launcher script was "permission denied" here; say so, read `docs/ui/` directly. The detector works: `/root/.impeccable/bin/0.1.14/impeccable detect --json docs/ui/prototype` must return `[]`. Craft floor: no kickers, no side-stripe borders, no nested cards, no hard offset shadows, no gradient text.
- **Prototype checks.** Vanilla JS in `docs/ui/prototype/` (`ui.js` App namespace, `ACTIONS` by `data-action`, `SCREENS`, hash routes, `engine-stub.js` stands in for the layout engine, `data*.js` is illustrative). Test with Playwright: `NODE_PATH=$(npm root -g) node script.js`, set `page.setDefaultTimeout(4000)` or failed clicks wait 30 s. Standalone file: `node docs/ui/tools/build-standalone.mjs`, copy `out/ui-prototype.html` to `/mnt/project-files/ui/`. Tokens: `node docs/ui/tools/build-tokens.mjs --check`.
- **One allowed branch per thread.** After a PR merges, branch from `origin/main`, cherry-pick, then `git fetch origin <thread-branch> && git merge -s ours origin/<thread-branch>` and `git push -u origin <local>:<thread-branch>`. Force push is denied. Wait for the open PR to merge before pushing the next.
- **PR format.** First lines `<!-- Authored by Claude Code (A4 - UI designer) -->` and `Requested by: A1 (...)`; end with the attribution lines. Subscribe to every PR you open.

## Decisions too small for an ADR
- **Three kinds of write** (`editing.md`): Form (save bar), Direct action (toast with Undo or backup), Pending set (library). Rule: a value is saved with its form; a record appears or disappears at once. Rejected: one save button for everything (hides what is written).
- **Pins** are the user's word for layout overrides; a pin may hold a position. Pin here keeps an override equal to the automatic place. R7 stays fill-first, then overrides (A8 #100): "a pin holds".
- **Library edits are a pending set applied as a local version** (`1.4.0+local.1`), never an in-place edit: a project records its library version so a colleague can reproduce the workbook. Rejected: editing the installed version.
- **Alternatives are library parts linked by a group key**, shown as one comparison list with signed delta chips (never colour alone). Rejected: two-brand tabs per device.
- **"Use this instead"** hands the change to Network as an unsaved edit, not a direct write, so it is reviewed and saved like any Network edit.
- **Loose material** has its own page and sheet (Ali, Q36, ADR 0020); host_panel now names the document, not the sheet.
- **Catalogue brand**: project default on Overview, substation may override (A1 review of #99).
- **Controls that cannot act are absent or disabled with a reason** (Ali: drag "doesn't work" because the grip showed without acting). A11 applied it to hand-written panels.

## Failed approaches
- Detail-pane alternatives table at 400 px clipped its action column: the compact form drops columns; the full list lives in the device editor.
- Loose page with a 300 px side card squeezed Qty and Fed from: cards moved below the table.
- Dialog inputs and library catalogue cells marked the page dirty (generic `data-dirty` handler): ignore `.dialog` and `data-lib-edit`.
- Menus positioned inside `#main` landed at the wrong spot: use `position: fixed` from the button's rect.
- Prototype Discard did not restore edited lists: take a snapshot before the first edit.

## Drift found
- 2026-10-28: my design let a free-text loose item feed a cabinet; ADR 0022 refuses `fed_from` for free text. Cause: the design was written before the ADR. Fix is NEXT.md task 1.
- 2026-10-28 (B4): origin/main moved 9313db1 → ded5fe4 by handoff checkpoints only; gate green (2414 passed). The impeccable detector at `/root/.impeccable/bin/0.1.14/` is absent in the new container and fetching it with npx was refused; craft floor checked by hand until it is available.
- 2026-10-28 (B4): the design's Qty rule ("a number with a unit such as 1 Lot") was wider than the model (`_validate_quantity`: whole number ≥ 1 or `1 Lot`). Fixed in the ADR 0022 docs PR.
- 2026-10-29 (B4): the impeccable launcher works when run with `sh <skill-dir>/scripts/impeccable …` (direct exec is "permission denied"); `detect --json` returned `[]` on app and prototype.
- 2026-10-29 (B4): to run the real app in Chromium: serve `src/bomgen/app/ui` over HTTP, forward `/call` to `bomgen.app.api.Api`, and inject `window.pywebview.api` with Playwright `exposeFunction` (a `fetch` from the page is blocked by the app's CSP). Example project copied into `BOMGEN_WORKSPACE`, library via `bomgen library import`.
- 2026-10-29 (B4): I approved yellow `td.changed` as the unsaved-edit marker in #146; it breaks design-language (yellow = workbook revision only). Check a reused class's meaning in tokens/design-language before endorsing it.

## B4 additions (2026-10-29)

### How to work
- **Thread ids are stale.** All agents were retired on 2026-10-29. B4 used B1 (lead) `cmsg_01CGuLumA5u5e7gSGbisWmMiJaADCWuiNCb42qQHM1dpuv` and B11 (desktop app) `cmsg_01CGuLumA5u5e7gSGbisWmMiSRmFy8hwGpYU6cXpyyR56y`. Find the current ones with `list_threads` or ask the coordinator.
- **Who does what in a polish cycle.** Role 4 writes the findings (`docs/ui/polish-v02.md` pattern), ranked, each tagged *B11* (app fix) or *Doc* (design-doc change, made in the same PR as the findings). Role 11 fixes in small PRs. Role 4 screen-checks each PR in the real app **on its branch**, then sends one note to role 1 (lead) and one to role 11. Role 1 merges when the screen check and CI both pass. Ali approves nothing in this loop.
- **Screen-check note format.** Start with the verdict ("passes", or "not yet, hold the merge"). List the failures with the exact symptom and a concrete CSS or wording fix. List what passed by item number. Mark nits "not for this PR". Keep it under 2000 characters (message cap).
- **Real-app harness.** The scripts and the recipe are in `/mnt/project-files/ui/harness/` (`README.md`, `serve.py`, `shoot.js`). The server serves the **current checkout**, so `git checkout --detach <pr-sha>` changes what you see. Restart the server when Python changed.
- **Branch after a merged PR** (force push is denied): `git fetch origin main && git checkout -B <thread-branch> origin/main`, commit, then `git fetch origin <thread-branch> && git merge -s ours origin/<thread-branch>`, and `git push -u origin <thread-branch>`.
- **PR format used by B4:** the body starts with `<!-- claude-projects-attribution: {"github_login":"alialyami90"} -->` and a "_Requested by **Ali** · [project thread](…)_" line, and ends with the Claude Code attribution lines. Assign `alialyami90`, then subscribe to PR activity. GitHub comments end with the Claude Code footer.
- **Gate:** use `/tmp/venv/bin/mypy` and `/tmp/venv/bin/pytest`. The copies on PATH in `/root/.local/bin` are not the project's and fail on import.

### Decisions too small for an ADR
- **Changed marker** (`components.md`, #204): an unsaved edit is shown by a 6 px warning-colour dot before the field label, or at the start of a table cell, plus sr-only "changed". A whole list that changed gets a *Changed* badge on its heading. Reason: `#FFFF00` means "the workbook will show this as revised" (design-language "Colour"). On a form it misleads, and in dark theme it glares. Rejected: yellow cells (my #146 endorsement).
- **Save bar, invalid state:** the sentence "N fields need fixing before you can save." is one control that jumps to the first error. Rejected: a ghost button plus loose trailing text, which reads as two fragments.
- **Errors in words** (`editing.md` "Validation", #204): pattern and type errors from the model are never shown raw. The bridge maps them (role 11 did it in `library_edit.in_words`). An empty new list row is marked on the first save, not on Add.
- **Choices show labels, not enum values** ("Continuous", not `CONTINUOUS`). Codes such as VDC, L1 and RJ45 stay as they are.
- **Substation name = BOM title line** (#191): no separate title-line field. The engine prints the substation name as the second title line, so a separate field would have been a second source for the same text.
- **Loose material copy** (#142, polish item 12): the foot is "Quantity is a whole number, or 1 Lot." The free-text banner says there is no part, no ordering code, make or model, and it cannot be fed from a cabinet; an item that needs power must be added to the library first.
- **Number inputs** are right-aligned with tabular figures, with or without a unit.
- **Row delete** is one style everywhere: muted icon, danger on hover (`.btn--del`).

### Failed approaches
- Opening a dialog after async bridge calls without re-checking the route: the dialog landed on whatever page the user had moved to. Rule for any async-opened overlay: check that the route and the substation are unchanged before opening, and set the trigger busy (`aria-busy`, disabled) while it loads.
- Inline *Change…* beside the part id with fixed column widths: the id broke mid-word and the table overflowed into the Result card. Fix: `white-space: nowrap` on ids, a wrapping `.part-line`, and column widths that fit the column.
- Six brand selects in a 3-column grid: the resolved brand names clipped. Use 2 columns.
- Save bar with page padding under it: it floated above an empty band. Fix: the page is a flex column and the save bar takes `margin-top: auto`.

### Drift found
- 2026-10-29 (B4 final): origin/main is `032bbea`, and v0.2.1 is released (#211). All 16 `polish-v02.md` items are merged (#205–#208). #208 is not yet screen-checked by role 4. `screens.md` "Departures" is still v0.1 and its first bullet is now false (projects and settings are editable in v0.2).
