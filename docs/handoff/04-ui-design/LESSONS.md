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
