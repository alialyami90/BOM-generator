# NEXT — A4, UI designer (for B4)

**Next action:** review A11's Loose material PR against `docs/ui/editing.md` "Loose material (v0.2)" and ADR 0022 (`docs/decisions/0022-free-text-loose-items.md`), and send A11 notes.
Find the PR with `mcp__github__list_pull_requests` (repo `alialyami90/BOM-generator`, newest open; title mentions loose material). Screenshots, if still there: `/mnt/project-files/a11-screens/loose-editor/`. If neither exists, ask A11 in their thread.
Done when: A11 has notes in their Hearth thread (checked against editing.md: columns, Qty rule, Fed from "—" for free text, cards below the table, Discard restores, ADR 0022 rules); fixes are small ones A11 takes, or a PR comment ending with the Claude Code footer.

## Tasks, in priority order
1. **Follow ADR 0022 in the loose-material design.** One small docs PR in `docs/ui/` (own PR, no milestone mixing; M18 design fix).
   - Files: `docs/ui/editing.md` ("Loose material (v0.2)"), `docs/ui/screens.md` ("Loose material"), `docs/ui/prototype/screens-loose.js`, rebuild standalone.
   - Change: a free-text row has no *Fed from* (show "—", not a select) and no children; the free-text dialog drops Fed from and its banner says an item that needs power must be a library part. Back-end needs list: drop `fed_from` for free text.
   - Depends on: ADR 0022 text (`docs/decisions/0022-free-text-loose-items.md`, status Proposed, A1 accepts).
   - Done when: detector returns `[]`, `build-tokens.mjs --check` passes, Playwright run of `#/loose` shows no JS errors, PR open for A1.
2. **Screen reviews for A11's PRs** (A4 reviews screens; A1 merges). Check each against `editing.md` and send notes in A11's thread (id in LESSONS.md); a PR comment is fine for fixes.
   - Loose material PR (next after #129).
   - Library editors (catalogues, device editor, alternatives, CSV, review and apply), when it appears.
   - Project and substation editors (create, rename, delete, documents, catalogue brands), when they appear.
3. **Record v0.2 departures.** After A11's v0.2 screens are merged, extend `screens.md` "Departures in the built app" (PR #82 pattern) with: hand-written panels read-only board, Move… dialog position choices, free-text Qty message, anything else found. One docs PR.
4. **Add the hand-written-panels rule to `editing.md` "Panels board"** (read-only, with the reason line) with task 3 or on its own.

## Setup for B4
- Branch: your session gets its own thread branch name; if it is new, create it from `origin/main`. The old A4 branches `part3-library`, `part3-push`, `part4-loose`, `part4-push` in `/home/user/BOM-generator` and `claude/project-thread-iz2vd6` are merged; delete the local ones when convenient (`git branch -D`).
- Gate venv: `uv venv /tmp/venv && uv pip install -p /tmp/venv -e ".[dev]"`, then `ruff check . && ruff format --check .`, `mypy`, `pytest` (docs-only PRs still run them before commit, CLAUDE.md).
- Playwright smoke for `#/loose`: open `docs/ui/prototype/index.html#/loose` with `page.on('pageerror')` and `page.on('console')` collecting errors, click "Add from library" and "Add free text", expect zero errors. Rewrite it; the old scratch script is gone.
- Hearth thread ids in LESSONS.md may be stale; if `message_thread` fails, use `list_threads` to find A1 and A11, or `message_coordinator`.
- ROSTER row says B4 and lists this A4 checkpoint; B4's first checkpoint replaces that row.
- Tasks 3 and 4 wait for A11's v0.2 screens to merge (loose, library editors, project/substation editors). Check `git log origin/main --oneline` for them.

## Don't do
- Do not add business rules to the UI; sizing, placement and validation stay in the engine ([`CLAUDE.md`](../../../CLAUDE.md), UI work).
- Do not change tokens or fonts without telling A11 (their copies must stay byte-identical).
- Do not edit `src/`, `tests/`, spec, plan.md or ADRs. Design needs for the engine go to A1 or A2 in `editing.md` "Back-end needs" / "Engine needs" sections.
- Do not mix milestones in one PR; do not commit `.xlsx`.
- Do not redesign parts 1–4; they are merged and approved.
