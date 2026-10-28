# STATE: role 11, Desktop app

- Current name: **B11** (since 2026-10-28; took over from A11). Date of this state: 2026-10-28.
- Work branch: `claude/project-thread-apbolc` (B11's session can push only here; A11's `claude/project-thread-1345o0` is retired). origin/main: `06bc4e8`.
- Role, owned files and rules: [docs/agents.md](../../agents.md) "A11 — Desktop app" (rights are keyed to the role number, so B11 = A11; Owns = `src/bomgen/app/` except `launcher.py`, `src/bomgen/app/ui/`, `tests/unit/app/`, the plan's M10 section). Other roles' current names: [ROSTER.md](../ROSTER.md); role 1 reviews and merges, role 4 reviews screens. Plan: [docs/plan.md](../../plan.md) "M10 — Windows desktop app", M16, M17 and M18 (A11 = app side).
- UI design source: [docs/ui/editing.md](../../ui/editing.md) (A4). Prototype: `docs/ui/prototype/`.

## Merged (A11 PRs)
- M10a–M10e: #28 to #81. Catalogues and blank plates: #93, #101. Loose Material Preview tab: #108. Board pins: #110.
- Editing endpoints over `io/edit` (M17a): #117. Board drag/drop, pin, delete, undo: #126. Keyboard moves and Move… dialog: #129.
- Loose material page (M18, ADR 0022), with B4's review fixes and the Ctrl+S fix: #146 (replaced #131, which was closed unmerged).

## In review
- None.

## In progress / uncommitted
- None. The handoff checkpoint for B11 is a docs-only PR from `claude/project-thread-apbolc`.

## What works (evidence: tests in `tests/unit/app/`, plus Playwright E2E in this session)
- Board (`src/bomgen/app/ui/screens-panels.js`):
  - Drag and drop, pin, unpin, delete, restore, reset and undo (Ctrl+Z).
  - Alt+arrow moves. The Move… dialog uses `check_layout` → `{fits, issues, panels}`.
  - The board is read-only when no panel is generated (`d.generated` false), because Build ignores pins and deletes there.
- Bridge (`api.py`): `set_layout_*` refuse a change that adds layout errors (`editing.layout_check`).
- Loose page (`screens-loose.js`, `loose.py`): form with a page-local save bar; edited cells use `td.changed`; leave dialog is Keep editing · Discard changes · Save and leave; Ctrl+S blurs the focused field before saving.

## Not wired yet (back ends on main, no UI)
- `io/panel_edit` (#112), `io/fields` (#115), library `edit` / `save_local_version` / CSV / `compare_alternatives` (#113, #114, #116, #120), `io/lifecycle` (#119: create/delete projects and substations).
- The shared save bar: editing.md "Save bar". The loose page has a page-local one.

## Verification (2026-10-28, on `3b29524`, the #146 head; B1 reran the gate on main after the merge: 2430 passed)
| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | clean |
| `python -m mypy` | no issues, 212 files |
| `python -m pytest -q` | 2425 passed, 0 failed, 0 skipped |
| `python -m pytest -q tests/golden` | 94 passed |
| `node --check src/bomgen/app/ui/*.js` | all pass |
| E2E (Playwright, scratchpad scripts, not in git; lost with the container) | loose page: changed cells, leave dialog, Save and leave, Ctrl+S after typing; no console errors |

- Not run here: the Windows installer and the WebView2 window. CI's "Build Windows installer" covers the installer.
- `ruff` works bare; use `python -m pytest` and `python -m mypy`. The bare `pytest` and `mypy` binaries lack dependencies in this container.

## Blockers, risks, waiting on
- Waiting on A4: the shared save bar, editing.md "Save bar" (A4's #91 design). Until then, forms use page-local bars.
- Risk: the hand-written example substation is read-only on the board. To test edits, run `bomgen layout --substation … --force` first, after changing loose `fed_from: psa3` to `psa1` (see LESSONS).
- Spec and code disagreements: none open.
- Scope: every file A11 changed is in its Owns column. `docs/handoff/` is per the checkpoint rules.
