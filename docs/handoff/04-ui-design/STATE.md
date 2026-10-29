# STATE — B4, UI designer (role 4)

- Name: B4 - UI designer. Successor: C4 - UI designer. Date: 2026-10-29. Reason: Ali retired every agent.
- Owns: `docs/ui/` (design docs, `tokens.json`, fonts, prototype, tools), the M9 section of `docs/plan.md`,
  this folder, and ROSTER row 4 ([`docs/agents.md`](../../agents.md), roles table). Writes no Python.
- origin/main at this checkpoint: `032bbea` (#212, README status for v0.2.1). Released version: 0.2.1 (#211).
- Thread branch: `claude/project-thread-7hk4h2`. It is reset onto `origin/main` for each new PR (see
  LESSONS "Branch after a merged PR"). Nothing unmerged lives on it apart from this checkpoint.
- **No PR of mine is open** after this checkpoint merges. **No question to Ali is open.**

## What role 4 has delivered (all merged, all docs-only inside `docs/ui/` unless noted)
| PR | Who | What |
| --- | --- | --- |
| #82 | A4 | "Departures in the built app" for v0.1 (`screens.md`) |
| #91 | A4 | v0.2 part 1: `editing.md` (three kinds of write, save bar, validation, create/rename/delete, field inventory) |
| #94 | A4 | v0.2 part 2: Panels board pins, drag contract, keyboard, editable panel editor |
| #99 | A4 | v0.2 part 3: Library editors (pending set, catalogues and brands, device editor, alternatives, CSV, review and apply) |
| #102 | A4 | v0.2 part 4: Loose material page on its own sheet (ADR 0020), substation catalogue brand |
| #142 | B4 | Loose material design follows ADR 0022: a free-text item has no Fed from and no children; Qty is a whole number ≥ 1 or `1 Lot` |
| #191 | B4 | The substation name is the BOM title's second line; the separate "Title line" field is gone (docs and prototype) |
| #204 | B4 | `polish-v02.md` (16 ranked findings on the v0.2 app), the **Changed marker** in `components.md` (replaces yellow for unsaved edits), save-bar invalid sentence as one control, validation wording rules in `editing.md` |

## Reviews done for the desktop app (role 11), all fixed and merged
- #131 Loose material (A11) against ADR 0022; notes taken, then #142 aligned the design.
- #146 Loose material follow-ups. **My mistake there:** I endorsed yellow `td.changed` for unsaved cells; #204 item 1 reversed it.
- Polish fixes from `polish-v02.md`, each screen-checked in the real app (see "How to verify"):
  - #205 (items 1, 5, 6, 15) passed on main `da84991`. Found a race: Network *Change…* opened its dialog after two bridge calls, so it could land on the next page. Fixed in #207.
  - #206 (items 2, 3, 8, 14) passed on its branch `f27bc7c`.
  - #207 (items 4, 7, 9–13, 16, plus the race, the Spares DC label and the save bar meeting the window bottom). First pass `c3ce633` failed: Role select still clipped, the table hit the Result card, part ids broke mid-id, and brand names clipped. Re-check `e4b5294` passed.
  - #208 (B11) took my two last nits: row ids no longer break at a hyphen, and the editor tab offset is restored. **I have not screen-checked #208 on main**: it is small, but check it first (NEXT task 1).
- With #205–#208 merged, **all 16 items of `polish-v02.md` are done**. The file stays as the record.

## Drift and known gaps (design docs vs the built app)
1. **`screens.md` "Departures in the built app" is v0.1-only and partly wrong now.** Its first bullet says projects, substations and settings are read-only; v0.2 made them editable. The v0.2 departures are not recorded. (NEXT task 2.)
2. **Hand-written panels.** The built Panels board is read-only when the substation uses hand-written panels (Build uses the panel files, so a pin would not change the BOM). `editing.md` "Panels board: drag, drop, pin, delete" does not say so. (NEXT task 3.)
3. **Prototype vs app.** The prototype (`docs/ui/prototype/`) shows the v0.2 screens as designed, not as built. It does not draw the Changed marker or the #205–#208 polish. By the house rule in `screens.md` "Departures", the prototype is not changed to match the app; the departures list records the differences instead.
4. **Polish nits never filed** (all minor, not in `polish-v02.md`):
   - The device editor save bar reads "1 unsaved change · added to pending changes" *before* saving. The wording is odd; "added to pending changes" is true only after Save. Check editing.md "Pending set" wording and send it to role 11 if it is still there.
   - Project › Overview shows "psa-devices 1.1.0" in the Home table while the header badge says "psa-devices 1.0.0". This was in my test workspace after a local library edit, so it may be correct (recorded version vs active version). Not investigated.
   - Catalogue brand option "Same as the project (Library default)" uses a capital L mid-sentence.

## Verification (this checkpoint)
| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` on `032bbea` | passed, 345 files formatted | 2026-10-29 |
| `mypy` | no issues in 224 source files | 2026-10-29 |
| `pytest` | 2672 passed, 0 failed (410 s) | 2026-10-29 |
| `impeccable detect --json` on `src/bomgen/app/ui` and `docs/ui/prototype` | `[]` (run at #204, `de69ec0`) | 2026-10-29 |
| Real-app screen checks of #205, #206, #207 | passed (screenshots were in the session scratchpad, gone) | 2026-10-29 |
Not run: golden tests separately (role 4 does not touch the engine); the Windows GUI itself (pywebview); `build-tokens.mjs --check` (tokens unchanged since A4's check).

## Waiting on
- Role 1 (lead) to merge this checkpoint PR. Nothing else.

## Scope check
This checkpoint changes only `docs/handoff/04-ui-design/` and the role 4 row of `docs/handoff/ROSTER.md`.
