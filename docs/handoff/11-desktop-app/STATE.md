# STATE: role 11, Desktop app

- Current name: **B11** (since 2026-10-28; took over from A11). Date of this state: 2026-10-29.
- Work branch: `claude/project-thread-apbolc`. B11's session can push only here, and force push is denied. origin/main: `9708db8`.
- Role, owned files and rules: [docs/agents.md](../../agents.md) "A11 — Desktop app". Rights are keyed to the role number, so B11 = A11.
  - Owns `src/bomgen/app/` (except `launcher.py`), `src/bomgen/app/ui/`, `tests/unit/app/` and the plan's M10 section.
  - Other roles' current names: [ROSTER.md](../ROSTER.md). Role 1 (B1) reviews and merges; role 4 (B4) reviews screens.
- UI design source: [docs/ui/editing.md](../../ui/editing.md). Prototype: `docs/ui/prototype/`.

## Merged (B11 PRs)
- Loose material page (M18): #146.
- Library editing (M16 app side):
  - device editor and pending set: #155;
  - lists, Add device, Delete, In use: #166;
  - Datasheet tab: #175;
  - export and CSV import: #178;
  - Alternatives: #180.
- Create, rename and delete projects and substations (M17d): #181.
- Every field editable (M17c; this was what blocked v0.2.0):
  - Overview and network inputs, with the setup card: #185;
  - equipment rows: #188;
  - Settings tabs and the shared `App.draftForm`: #190;
  - document register, and "Add the core switches": #192.
- c2 "Use this instead", from Library to Network: #194.
- Overview and Network moved onto `App.draftForm`: #197.
- Follow-ups:
  - Delete on an unapplied device: #198;
  - the Change-part picker on Network: #199;
  - make and model in the parts datalist: #200;
  - B4's #131 notes 4–8 on Loose material: #201.

## In review
- None, apart from this checkpoint (docs only).

## In progress / uncommitted
- None.

## What works (evidence: tests in `tests/unit/app/`, plus Playwright E2E in this session)
- Every v0.2 field is editable in the app: Overview, Settings (General, Documents, Output, Constants), Network inputs and equipment, document register, Loose material, library devices and datasheets. Panels are edited on the board.
- Forms share `App.draftForm` (`ui.js`):
  - The draft holds only the changed fields, and the model checks each one through a `check_*` endpoint.
  - It has one save bar, Ctrl+S, and a reset on route change.
  - The "N fields need fixing" count focuses the first bad field.
  - Prefixes: `po-` Overview, `st-` Settings, `n-` Network, `rg-` register.
- The library pending set: edits collect, then Review and apply writes a local version.
  - A device added in the set and then deleted goes at once, with its edits.
- Alternatives: the Library tab, the compact comparison, Use this instead (→ Network draft), and Change… on each Network equipment row (alternatives first).

## Verification (2026-10-29, on `3cf65f8`, the #201 commit before the #200 squash; app tests rerun on the new base)
| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | clean |
| `python -m mypy` | no issues, 224 files |
| `python -m pytest -q` | 2653 passed, 0 failed |
| `node --check src/bomgen/app/ui/*.js` | all pass |
| E2E (Playwright, scratchpad scripts, not in git) | each PR above; no console errors |

- Not run here: the Windows installer and the WebView2 window. CI's "Build Windows installer" covers them.

## Blockers, risks, waiting on
- Waiting on B4's impeccable polish audit of the new screens. B1 routes its fixes to B11.
- Nothing past v0.2 is planned; B1 is asking Ali.
- Risk: the Change… and Add device pickers list the **active** library. A project pinned to an older version refuses a part it lacks; the model's message shows on the row.
- Spec and code disagreements: none open.
