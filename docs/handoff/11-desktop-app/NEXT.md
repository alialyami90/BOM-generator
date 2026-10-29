# NEXT: role 11, Desktop app

**Next action:** take the role over (steps below), then ask role 1 for the next task. Ali's feedback from testing v0.2.0/v0.2.1 decides the next app work; nothing is assigned. If Ali reports an app bug, fix it test-first in a small PR.

## Taking over (first hour)
1. Read, in order: [STATE.md](STATE.md), this file, [LESSONS.md](LESSONS.md), the latest `checkpoints/` file, [CLAUDE.md](../../../CLAUDE.md), [docs/agents.md](../../agents.md) (role 11), the plan's M10 and M12–M18 sections in [docs/plan.md](../../plan.md), and [docs/ui/editing.md](../../ui/editing.md).
2. Fresh container: `pip install -e ".[dev]"` (an old editable install gives false failures). Then the gate on main:
   `ruff check . && ruff format --check .`, `python -m mypy`, `python -m pytest -q` (about 6 minutes; use a 600000 ms timeout). The bare `pytest`/`mypy` binaries may fail in the container; use `python -m`.
3. Set your name in your ROSTER row. Record any drift from STATE.md in LESSONS.md.

## Map of the code (where to change what)
- **Python side** (`src/bomgen/app/`): `api.py` is the pywebview `js_api`. Each public method of `Api` is an endpoint returning `{"ok": true, "data": …}` or `{"ok": false, "error": {"kind", "message"}}`. Endpoints reshape engine results; they hold no business rules.
  - `projects.py` (Home, Project, Settings pages, `brands`), `substations.py` (substation pages), `network.py` (Network page, sizing result), `loose.py` (Loose material), `library_edit.py` (device editor, pending set, `in_words` error text), `library_csv.py` (CSV exchange), `output.py` (Checks and Build), `preview.py` (Preview), `editing.py` (edit replies `{written, issues, page}` and layout pre-checks), `catalogues.py` (the commodity catalogues on the Library screen), `window.py` (the WebView2 window). `launcher.py` is role 6's.
  - Writers live in `bomgen.io.fields` (role 2): `set_field`, `remove_field`, `insert_item`, `remove_item`, `move_item`, `validate_field`, `confirm_field`, `part_users`, `document_users`. Each goes through `io.edit.edit_file`, which checks the whole project before writing.
- **UI side** (`src/bomgen/app/ui/`): plain scripts, no build step, loaded by `index.html` in this order: `bridge.js icons.js data.js engine-stub.js ui.js screens-projects.js screens-project.js screens-layout.js screens-substation.js screens-panels.js screens-loose.js screens-library.js screens-libcsv.js screens-libedit.js screens-output.js screens-verify.js screens-preview.js app.js`.
  - **A later script overrides an earlier `SCREENS.x`.** For example `screens-substation.js` replaces `screens-layout.js`'s `SCREENS.network`, and `screens-libedit.js` wraps `SCREENS.library`. Check which file defines the screen you see last.
  - `ui.js` holds shared helpers on `App`: `draftForm`, `changedField`, `changedCell`, `fixLine`, `route`, dialogs, toasts. `icon` is a global. `data.js` + `engine-stub.js` drive the example (no project open) pages.
  - Styles: `tokens.css` (from `docs/ui/tokens.json`, role 4's) and `styles.css`.
- **Tests** (`tests/unit/app/`): `test_app_*_api.py` per endpoint group; `test_app_ui_assets.py` asserts strings in the UI files (a cheap guard for design decisions); `test_every_endpoint_the_screens_call_exists` parses literal `Bridge.call('name', …)` calls.

## How to work
- One PR at a time, one milestone or one review round each. Prepare the next PR as a local commit while one is open.
- TDD: the failing test first (for UI-only changes, an asserting test in `test_app_ui_assets.py`), then the change. Name tests after the rule.
- Before every commit: the gate above plus `for f in src/bomgen/app/ui/*.js; do node --check $f; done`.
- Conventional commits (`fix(app): …`, `feat(app): …`, `docs(handoff): …`). Never commit `.xlsx`, scratch scripts or screenshots.
- Restart your branch after each squash merge (force push may be denied; `git rebase origin/main` replays the whole history and conflicts):
  ```bash
  C=<commit of the next PR>; git fetch -q origin main <your-branch>
  OLD=$(git rev-parse origin/<your-branch>)
  git checkout -q -B <your-branch> origin/main
  git merge -q -s ours $OLD -m "chore: merge the already-squashed #N branch history (no changes)"
  git cherry-pick $C && git push -u origin <your-branch>
  ```
- After opening a PR: subscribe to its activity, assign alialyami90, message role 1 in its thread with the PR link, what it covers and the gate result. Role 1 reviews and merges; never ask Ali to merge.
- UI PRs: run a Playwright E2E (LESSONS "E2E without the window"), save screenshots to the project files folder (`a11-screens/`) and tell role 1 so role 4 can screen-check. Measure what a reviewer will check (clipping, gaps, wrapping) with `getBoundingClientRect`, not only by eye.
- CHANGELOG `Unreleased` lines belong to role 7; pass them through role 1.
- Ask Ali only on a decision card with a recommendation. Spec vs code disagreement: ask Ali before changing either.

## Open ideas (not ordered; none is asked for)
- Add device and Change… list the active library. Showing the project's own library version would avoid parts that the project then refuses.
- Undo for a dropped pending library device (today only the confirm dialog guards it).
- A design-level save-bar component shared by Loose material and the device editor, so all forms use `App.draftForm`'s bar markup (today `screens-loose.js` and `screens-libedit.js` build their own, using `App.fixLine`).
- The WebView2 window has never been driven by a test here; a smoke test on the Windows CI runner would catch bridge regressions the stub cannot.

## Don't do
- Business rules in the UI. A missing engine function goes to its owner (agents.md).
- Edit `launcher.py` (role 6), the spec, the plan structure or ADRs (role 1), CHANGELOG (role 7), `docs/ui/` (role 4) or other roles' modules.
- Dynamic bridge calls (`Bridge.call(name)`): the endpoint guard test needs literals.
