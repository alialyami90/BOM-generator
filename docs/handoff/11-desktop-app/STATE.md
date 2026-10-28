# STATE: role 11, Desktop app

- Outgoing name: A11. Successor: **B11**. Date: 2026-10-28.
- Work branch: `claude/project-thread-1345o0`, HEAD `f9bbccb` (PR #131). origin/main: `aad6094`.
- Role, owned files and rules: [docs/agents.md](../../agents.md) "A11 — Desktop app" (rights are keyed to the role number, so B11 = A11; Owns = `src/bomgen/app/` except `launcher.py`, `src/bomgen/app/ui/`, `tests/unit/app/`, the plan's M10 section). Other roles' current names: [ROSTER.md](../ROSTER.md); role 1 reviews and merges, role 4 reviews screens. Plan: [docs/plan.md](../../plan.md) "M10 — Windows desktop app", M16, M17 and M18 (A11 = app side).
- UI design source: [docs/ui/editing.md](../../ui/editing.md) (A4). Prototype: `docs/ui/prototype/`.

## Merged (A11 PRs)
- M10a–M10e: #28 to #81. Catalogues and blank plates: #93, #101. Loose Material Preview tab: #108. Board pins: #110.
- Editing endpoints over `io/edit` (M17a): #117. Board drag/drop, pin, delete, undo: #126. Keyboard moves and Move… dialog: #129.

## In review
- **#131** `feat(app): Loose material page with a save bar (M18, ADR 0022)`. Head `f9bbccb`. Opened 2026-10-28 ~20:45 UTC. CI at checkpoint (20:46 UTC): ruff and mypy green; pytest and "Build Windows installer" still running. Recheck. A1 has not reviewed yet. A4 approved the screenshots (`/mnt/project-files/a11-screens/loose-editor/`, project files, not in git). Needs a green "Build Windows installer" (touches `src/bomgen/app`).

## In progress / uncommitted
- None. The main checkout's working tree is clean. Local branches `kbd-moves`, `loose-editor` and `loose-page` exist only in the old container; they are superseded by #129 and #131, so ignore them.

## What works (evidence: tests in `tests/unit/app/`, plus Playwright E2E in this session)
- Board (`src/bomgen/app/ui/screens-panels.js`):
  - Drag and drop, pin, unpin, delete, restore, reset and undo (Ctrl+Z).
  - Alt+arrow moves. The Move… dialog uses `check_layout` → `{fits, issues, panels}`.
  - The board is read-only when no panel is generated (`d.generated` false), because Build ignores pins and deletes there.
- Bridge (`api.py`): `set_layout_*` refuse a change that adds layout errors (`editing.layout_check`).
- Loose page (`screens-loose.js`, `loose.py`) is in #131, not on main yet.

## Not wired yet (back ends on main, no UI)
- `io/panel_edit` (#112), `io/fields` (#115), library `edit` / `save_local_version` / CSV / `compare_alternatives` (#113, #114, #116, #120), `io/lifecycle` (#119: create/delete projects and substations).
- The shared save bar: editing.md "Save bar". The loose page has a page-local one.

## Verification (2026-10-28, on `f9bbccb`)
| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | clean |
| `python -m mypy` | no issues, 212 files |
| `python -m pytest -q` | 2422 passed, 0 failed, 0 skipped |
| `python -m pytest -q tests/golden` | 94 passed |
| `node --check src/bomgen/app/ui/*.js` | all pass |
| E2E (Playwright, scratchpad scripts, not in git; lost with the container) | board, keys, Move…, loose page: no console errors |

- Not run here: the Windows installer and the WebView2 window. CI's "Build Windows installer" covers the installer.
- `ruff` works bare; use `python -m pytest` and `python -m mypy`. The bare `pytest` and `mypy` binaries lack dependencies in this container.

## Blockers, risks, waiting on
- Waiting on A1: review and merge of #131 (since 2026-10-28).
- Waiting on A4: the shared save bar, editing.md "Save bar" (A4's #91 design). Until then, forms use page-local bars.
- Risk: the hand-written example substation is read-only on the board. To test edits, run `bomgen layout --substation … --force` first, after changing loose `fed_from: psa3` to `psa1` (see LESSONS).
- Spec and code disagreements: none open.
- Scope: every file A11 changed is in its Owns column. `docs/handoff/` is per the checkpoint rules.
