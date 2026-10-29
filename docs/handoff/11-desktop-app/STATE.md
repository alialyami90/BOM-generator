# STATE: role 11, Desktop app

- Last holder: **B11** (2026-10-28 to 2026-10-29; took over from A11). Retired by Ali on 2026-10-29 with every other agent. The next holder takes the role by number: B11's rights = A11's = role 11.
- Date of this state: 2026-10-29. origin/main at writing: `032bbea` (v0.2.1 released as `1678343`, #211).
- Work branch of the last holder: `claude/project-thread-apbolc`. **A successor cannot push there** (each session may push only to its own designated branch). Start from `origin/main` on your own branch.
- Role, owned files and rules: [docs/agents.md](../../agents.md) "A11 — Desktop app".
  - Owns `src/bomgen/app/` (**except `launcher.py`**, role 6), `src/bomgen/app/ui/`, `tests/unit/app/`, the plan's M10 section, this folder and the role-11 ROSTER row.
  - Does not own: the spec, ADRs and plan structure (role 1), CHANGELOG (role 7), `io/` writers (role 2), library store and CSV (role 5), engine modules (roles 8–10), `docs/ui/` design (role 4).
  - Other roles' current names: [ROSTER.md](../ROSTER.md). Role 1 reviews and merges every PR; role 4 screen-checks UI PRs.
- UI design source: [docs/ui/editing.md](../../ui/editing.md) (editing screens), [docs/ui/screens.md](../../ui/screens.md), [docs/ui/components.md](../../ui/components.md), tokens in `docs/ui/tokens.json` → `src/bomgen/app/ui/tokens.css`. Prototype: `docs/ui/prototype/`. Last audit: [docs/ui/polish-v02.md](../../ui/polish-v02.md) (all 16 items done).

## Open PRs and branches
- **None open.** Every B11 PR is merged. No uncommitted or unpushed work exists anywhere.
- Scratchpad E2E scripts (`p1.js`…`p6.js`, `bridge2.py`, workspaces `wsp1`–`wsp3`) lived in the session scratchpad and are gone with it; LESSONS.md says how to rebuild them. Screenshots of the last PRs are in the project files folder `a11-screens/` (not in git).

## Merged (B11 PRs, oldest first)
- Loose material page (M18): #146 (replaced A11's #131).
- Library editing (M16 app side): device editor and pending set #155; lists, Add device, Delete, In use #166; Datasheet tab #175; export and CSV import #178; Alternatives #180.
- Create, rename and delete projects and substations (M17d): #181.
- Every field editable (M17c; blocked v0.2.0): Overview and Network inputs with the setup card #185; equipment rows #188; Settings tabs and the shared `App.draftForm` #190; document register and "Add the core switches" #192.
- c2 "Use this instead" from Library to Network: #194. Overview and Network onto `App.draftForm`: #197.
- Follow-ups: Delete on an unapplied device #198; Change-part picker on Network #199; make and model in the parts datalist #200; B4's #131 notes 4–8 on Loose material #201. Handoff checkpoint #203.
- **v0.2 polish pass (B4's audit `polish-v02.md`), released in v0.2.1:**
  - #205 items 1, 5, 6, 15: unsaved edits get the changed dot (`.chg`, `App.changedField`/`changedCell`), not the revision yellow (which stays for Preview only); "N fields need fixing" is a button (`App.fixLine`); numbers are tabular and right-aligned (`.input--num`); a route change closes an open dialog.
  - #206 items 2, 3, 8, 14: device editor lists show model errors in words (`library_edit.in_words`); unfinished list rows are not checked until save; choice labels in words (`choiceName`); datasheet height named and explained; muted delete buttons (`.btn--del`).
  - #207 items 4, 7, 9–13, 16 plus B4's and B1's extras: two-line Network equipment rows with Change… inline (`.part-line`), Role column 170px, Change… busy state and route-race guard, "Spare DC branches / per feed"; Settings brand options name the resolved product (`projects.brands` returns `{id, name, product}`), "Same as AC branches" for DC, document options show the key, empty Default cells on unchanged constants, Catalogue brands in a 2-column form; register two-line rows, "Used by" without the substation prefix, singular/plural banner; project path on one line with a tooltip; save bar flush with the window bottom (page is a flex column); B4's #146 Loose wording.
  - #208 B4's re-check nits: ids in a table sub line never break; device editor tab panel offset restored.

## What works (evidence: tests in `tests/unit/app/`, plus Playwright E2E per PR)
- Every v0.2 field is editable in the app: Overview, Settings (General, Documents, Output, Constants), Network inputs and equipment, document register, Loose material, library devices and datasheets. Panels are edited on the board (generated panels) and are read-only for hand-written panels.
- Forms share `App.draftForm` (`ui.js`): the draft holds only changed fields; each is checked by the model through a `check_*` endpoint; one save bar, Ctrl+S, reset on route change; the "N fields need fixing" button focuses the first bad field. Prefixes: `po-` Overview, `st-` Settings, `n-` Network, `rg-` register. Loose material and the device editor keep their own save bars (multi-step saves).
- Library pending set: edits collect, then Review and apply writes a new local library version. A device added in the set and then deleted goes at once.
- Alternatives: Library tab, compact comparison, Use this instead (→ Network draft), Change… on each Network equipment row (alternatives first).
- Checks, Preview and Build, Backup and share, CSV import/export, project import, backup restore.

## Verification (last run 2026-10-29 on `2d74d45`, the #208 commit; same tree as main's app code)
| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | clean |
| `python -m mypy` | no issues, 224 files |
| `python -m pytest -q` | 2672 passed, 0 failed (about 5.5 minutes) |
| `node --check src/bomgen/app/ui/*.js` | all pass |
| E2E (Playwright, headless, bridge stub) | each PR; no console errors |

- Not run here: the Windows installer and the WebView2 window. CI's "Build Windows installer" covers them on every PR.

## Blockers, risks, waiting on
- **Waiting on Ali's feedback from testing v0.2.0/v0.2.1.** B1 said new feature work waits on it. Nothing past v0.2 is planned.
- Risk: the Change… and Add device pickers list the **active** library. A project pinned to an older library version refuses a part it lacks; the model's message then shows on the row.
- Risk: undo for a dropped pending library device does not exist; the confirm dialog is the only guard.
- Spec and code disagreements: none open. Open questions for role 11: none.
