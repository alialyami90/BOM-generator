# NEXT — B4, UI designer (for C4)

**Next action:** screen-check #208 on `origin/main` in the real app (NEXT task 1), then open the
v0.2 departures PR (task 2). Both are small. No PR or review is waiting on role 4 right now.

## Tasks, in priority order
1. **Screen-check #208 on main** (role 11, "keep row ids whole and the device editor's tab offset", `dce6277`).
   - Network › Equipment: a row id in the cell sub line (for example `ext-fw` on FGR-60F) stays on one line; the part id (for example `RST2228-L1-24MM`) never breaks, and *Change…* drops under it when there is no room.
   - Library › any device › Electrical: the first field row sits as close under the tabs as on the other tabs; the save bar meets the window bottom on short and long tabs.
   - Done when: the result is sent to the lead (role 1) and the desktop-app role (11) in one note each. If it fails, give the exact symptom and the CSS fix you suggest; role 11 fixes, role 1 merges.
2. **Record the v0.2 departures in `docs/ui/screens.md` "Departures in the built app"** (one docs PR, PR #82 pattern; no milestone mixing).
   - **Remove or rewrite the first bullet** ("Projects, substations and settings are read-only"): v0.2 made them editable, so it is now wrong.
   - Add, after checking each against the app on main:
     - Panels board is read-only for hand-written panels (with the reason line the app shows).
     - Move… dialog: Position is top, bottom, or where the layout puts it, not a numbered select.
     - Unsaved edits use the Changed marker (warning dot plus sr-only "changed"), never the revision yellow; yellow stays only in Preview for revised cells.
     - Network equipment: *Change…* sits at the end of the part-id line and wraps under it when narrow.
     - Catalogue brands on Settings › General are a 2-column form, and each "Same as the project (…)" option names the resolved brand.
     - Settings › Documents: the register select shows the register key only.
     - Project › Documents register rows are two lines (Confirm on the *Assumed date* line), and Used by drops the substation prefix inside its group.
     - Design constants: the Default column is empty on unchanged rows.
     - Any other difference you find while walking every v0.2 screen against `editing.md`, `screens.md` and the prototype.
   - Done when: PR open for role 1, gate green, `impeccable detect --json docs/ui/prototype` returns `[]` (the prototype is untouched, so this is a sanity check).
3. **Add the hand-written-panels rule to `docs/ui/editing.md` "Panels board: drag, drop, pin, delete"**: when the substation uses hand-written panels, the board is read-only. Say why (Build uses the panel files, so a pin would not change the BOM) and how the board says so (one-line banner, no grips, no pin or delete actions; LESSONS "Controls that cannot act are absent or disabled with a reason"). Can go in the same PR as task 2.
4. **The small wording nits in STATE "Drift" item 4.** Check each on main. Send role 11 the ones that are still there, in one note. Do not file `polish-v02.md` again; it is complete.
5. **Then, design work only on request.** The v0.2 design (parts 1–4, the Loose ADR 0022 fix, the polish pass) is merged and built. A new screen or flow starts with the `impeccable` skill, a section in `editing.md`/`screens.md`/`components.md`, and a prototype screen, as CLAUDE.md "UI work" says.

## Setup for C4
- **Branch:** your session has its own thread branch. Create it from `origin/main`. After each merged PR, use the reset recipe in LESSONS "Branch after a merged PR". Force push is denied.
- **Gate venv:** `uv venv /tmp/venv && uv pip install -p /tmp/venv -e ".[dev]"`. Then run `ruff check . && ruff format --check .`, `/tmp/venv/bin/mypy` and `/tmp/venv/bin/pytest`. Use the venv binaries: the `mypy`/`pytest` on PATH (`/root/.local/bin`) are not the project's and fail.
- **Impeccable:** `sh <skills>/impeccable/scripts/impeccable detect --json <dir>`. Run it through `sh`, because direct exec is "permission denied". Find the skill dir with `ls /root/.claude/skills/synced/*/impeccable`.
- **Real-app harness:** for screen checks, use the recipe in LESSONS "Run the real app in Chromium". Rewrite the two scratch scripts; they lived in the session scratchpad and are gone.
- **Prototype checks:** `docs/ui/tools/build-standalone.mjs`, `docs/ui/tools/build-tokens.mjs --check`, and Playwright with `page.on('pageerror')`. See LESSONS "How to work".
- **Who is who:** every agent was retired on 2026-10-29, so all thread ids in LESSONS are stale. Find the current lead (role 1) and desktop-app owner (role 11) in `docs/handoff/ROSTER.md` and with `list_threads`, or ask the coordinator.
- **Ali's standing rules:** all approvals and merges go to the lead (role 1), never to Ali. Ask Ali only on a decision card (`request_decision`), with your recommendation marked.
- **ROSTER:** row 4 names C4 and links this checkpoint. Edit only that row.

## Don't do
- Do not add business rules to the UI; sizing, placement and validation stay in the engine ([`CLAUDE.md`](../../../CLAUDE.md), "UI work").
- Do not change tokens or fonts without telling role 11: the app's copies of `tokens.css` and the fonts must stay byte-identical to `docs/ui/`.
- Do not use `#FFFF00` (`highlight.yellow`) for anything but the workbook's revised cells (design-language "Colour"). Unsaved edits use the Changed marker (`components.md`).
- Do not edit `src/`, `tests/`, the spec, `plan.md` (except the M9 section) or ADRs. Engine needs go to role 1 or 2 in `editing.md` "Back-end needs".
- Do not mix milestones in one PR, and do not commit `.xlsx`.
- Do not redesign v0.2 parts 1–4; they are merged, approved and built.
