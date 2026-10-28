# STATE — A4, UI designer (role 4)

- Name: A4 - UI designer. Successor: B4 - UI designer. Date: 2026-10-28.
- Owns: `docs/ui/` and the M9 section of plan.md ([`docs/agents.md`](../../agents.md), roles table). Writes no Python.
- origin/main at checkpoint: `9313db1` (#129). Checkpoint branch: `docs/handoff-a4-ui` (docs-only worktree).
- My working checkout `/home/user/BOM-generator` is on local branch `part4-push` at `1ef30b1`, clean, with the old
  local branches `part3-library`, `part4-loose`, `part3-push`; all their content is merged. Safe to delete.

## Merged (all docs-only, inside `docs/ui/`)
| PR | What |
| --- | --- |
| #82 | "Departures in the built app" (screens.md) |
| #91 | v0.2 part 1: `editing.md` (three kinds of write, save bar, validation, create/rename/delete, field inventory) |
| #94 | v0.2 part 2: Panels board pins, drag contract, keyboard, editable panel editor |
| #99 | v0.2 part 3: Library editors (pending set, catalogues and brands, device editor, alternatives comparison, CSV export/import, review and apply) and the back-end needs table for the generated-panel editor |
| #102 | v0.2 part 4: Loose material page on its own sheet (ADR 0020), substation catalogue brand, #99 review fixes |

## In review / in flight (other roles)
- A11 built the board drag and drop (#126) and the Move… dialog (#129); I reviewed both against `editing.md` (notes sent, fixes taken).
- A11 has the Loose material page built locally, PR to follow #129. Screenshots: `/mnt/project-files/a11-screens/loose-editor/` (01–05, 03b-invalid). **I owe a screen review of it.**
- A11's library-catalogues thread ("Show library catalogues in the app") will build my part 3 screens; no PR seen yet.
- No PR of mine is open. No question to Ali is open.

## What works (evidence from this session)
- Prototype opens and runs all four v0.2 parts; checked in Chromium with Playwright, no console errors (scratch scripts were in `/tmp`, gone).
- `impeccable detect --json docs/ui/prototype` returned `[]` and `node docs/ui/tools/build-tokens.mjs --check` said "up to date" on the checkpoint worktree.
- Tokens, fonts and `tokens.css` unchanged by v0.2, so A11's copies stay byte-identical.

## Drift and known gaps (design vs built or ADR)
1. **Free-text loose items.** My design (`editing.md` "Loose material (v0.2)", `screens.md`, prototype `screens-loose.js`) lets a free-text row have *Fed from*. ADR 0022 (Proposed) refuses `fed_from` and `children` on a free-text item. A11 built "—" for Fed from there and changed the banner. **Docs and prototype must follow ADR 0022.**
2. **Hand-written panels.** A11's board is read-only when the substation's panels are hand-written (Build uses panel files, so a pin would not change the BOM). `editing.md` "Panels board" does not say this.
3. **Move… dialog** differs from my sketch: Position is top, bottom or where the layout puts it, not a numbered select. Accepted in review.
4. Free-text Qty message in the built app is "Enter a number, or 1 Lot." (shorter than mine; model accepts a whole number or `1 Lot`). Accepted.
5. "Departures in the built app" (screens.md) covers v0.1 only; v0.2 departures are not recorded yet.

## Verification (this session)
| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` (worktree at 9313db1) | passed, 270 files formatted | 2026-10-28 |
| `mypy` (venv with `uv pip install -e ".[dev]"`) | no issues in 210 source files | 2026-10-28 |
| `pytest` | 2414 passed, 0 failed, 0 skipped (139 s) | 2026-10-28 |
| `impeccable detect --json docs/ui/prototype` | `[]` | 2026-10-28 |
| `build-tokens.mjs --check` | up to date | 2026-10-28 |
Not run: golden tests separately (role does not touch engine, sheets or writer); the Windows app (GUI).

## Waiting on
- A1: accept ADR 0022 and merge this checkpoint PR. A11: Loose material PR, library editor PR.

## Scope check
All 5 merged PRs changed files only under `docs/ui/`. This checkpoint adds `docs/handoff/04-ui-design/` and changes only the role 4 row of `docs/handoff/ROSTER.md` (shared skeleton from #133, merged into this branch).
