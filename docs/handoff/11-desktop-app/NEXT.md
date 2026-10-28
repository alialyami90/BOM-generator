# NEXT: role 11, Desktop app

**Next action:** drive #131 (Loose material page) to green and merged: handle CI and A1's review. Then start task 2 on a branch restarted from main.

Order set by role 1 (2026-10-28): loose page → Library editors → project and substation creation. One PR at a time on `claude/project-thread-1345o0` (a task may span several PRs, one after another). Prepare the next PR on a local branch while one is open.

How to restart the branch after a squash merge:
`git fetch origin main claude/project-thread-1345o0 && git checkout -B claude/project-thread-1345o0 origin/main`, then cherry-pick the commits of the next PR (prepared on a local branch, not yet on main), then `git merge -s ours origin/claude/project-thread-1345o0 -m "chore: merge the already-squashed #N branch history (no changes)"`, then `git push -u`.
Force push is denied. Use the `-s ours` merge only when the remote branch holds nothing but already-squashed history (check `git log origin/main..origin/claude/project-thread-1345o0` against the merged PR).
E2E: write a Playwright script in the scratchpad (Chromium is preinstalled; `NODE_PATH=$(npm root -g) node x.js`) that starts a line-based Python bridge over `bomgen.app.api.Api` and exposes the endpoint names as `window.pywebview.api`; list every endpoint the screens call.

## 1. #131 Loose material page (M18)
- Done when CI is green (including "Build Windows installer") and A1 has merged it.
- If role 1 asks for changes, or rejects the design, discuss it in role 1's thread (role 4 for screen design); otherwise edit `src/bomgen/app/loose.py`, `screens-loose.js` and `tests/unit/app/test_app_loose_api.py`.

## 2. Library editors (M16, app side)
- Design: editing.md "Library editing (v0.2)", which covers the pending set, the Catalogues tab, the Device editor, Alternatives and Export and import. Prototype: `docs/ui/prototype/screens-libedit.js` and `data-lib.js`.
- Back ends (owner A5):
  - `library_store/edit.py`: `parse_edits`, `apply_edits`, `check_field`.
  - `library_store/local.py`: `save_local_version`, `save_edits`.
  - `csv_export.export_installed_csv`, and `csv_import.preview_csv_import` / `import_csv`.
  - `alternatives.compare_alternatives`.
  - `LibraryStore.export_package`.
- Files: `src/bomgen/app/api.py`, a new `src/bomgen/app/library_edit.py`, `ui/screens-library.js` and `tests/unit/app/test_app_library_api.py`.
- Split into small PRs:
  - (a) device edit and save as a local version;
  - (b) CSV export and import;
  - (c) the alternatives comparison.
- Tests first, for example:
  - `test_an_edited_device_is_saved_as_a_new_local_version`
  - `test_check_field_reports_the_models_message`
  - `test_csv_export_then_import_round_trips`
  - `test_compare_alternatives_lists_the_group`
- Done when the gate passes, E2E shows no console errors, A4 has looked at the screens and a PR is open for A1.

## 3. Project and substation creation (M17d, app side)
- Design: editing.md "Creating" and "Deleting and undoing".
- Back end (role 2, #119): `io/lifecycle.py` (`create_project`, `create_substation`, `delete_substation`, `delete_project`).
- Files: `api.py`, `ui/screens-projects.js`, `ui/screens-project.js` and `tests/unit/app/test_app_projects_api.py`.
- Tests first: `test_new_project_creates_the_folder_and_opens_it`, `test_new_substation_from_blank_opens_on_network`, `test_delete_substation_backs_up_first`.

## 4. Settings fields and hand-written panels (M17b/c, app side) — blocked on role 4's shared save bar (#91 design); ask role 4 before starting
- Wire `io/fields` (`set_field`, `validate_field`, `document_users`, `assumed_fields`, `confirm_field`, `file_fingerprint`) and `io/panel_edit` into the Settings, Network and Panel screens.
- The shared save bar comes from A4's #91 design. Use editing.md "Field inventory", "Validation" and "When the file changes behind the app".

## Don't do
- Business rules in the UI. A missing engine function goes to its owner (agents.md).
- Edit `launcher.py` (A6), the spec, plan structure or ADRs (A1), or other roles' modules.
- Commit `.xlsx` files, or the scratchpad E2E scripts and screenshots.
- Ask Ali to merge. A1 merges.
