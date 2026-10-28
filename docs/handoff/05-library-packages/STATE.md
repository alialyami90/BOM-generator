# State: role 5, Library update packages

- Name: A5 - Library update packages (outgoing); successor B5. Date: 2026-10-28.
- Role and files: [`docs/agents.md`](../../agents.md) "Roles" row A5 and its section. Owns
  `src/bomgen/library_store/`, ADR 0008, ADR 0018 (number assigned by A1), the M8 section.
- Branch: `claude/project-thread-gq1gxg` (HEAD `23b3ca4`; the branch name is fixed by the thread, so each PR
  is cherry-picked onto fresh `origin/main` and `merge -s ours` joins the old history; a successor
  may also just reset the branch to main when it has no unmerged work). Checkpoint branch:
  `claude/a5-handoff-checkpoint`. origin/main at write time: `aad6094`.
- Nothing uncommitted, no stash, no open PR of mine.

## Merged (all reviewed and merged by A1)
- M8 / M8b earlier: #9, #31, #41, #50, #53, #59 (`.bomlib` package, store, import preview,
  `.bomproj` export/import/backup, dry-runs).
- M16 store side ([`plan.md`](../../plan.md) M16, [ADR 0018](../../decisions/0018-library-csv-exchange.md)):
  #92 ADR 0018; #95 device_db checker accepts M14 keys; #105 local versions `+local.N`;
  #113 `save_local_version` + `.bomlib` backup (`export_package`, `library export`);
  #114 edit operations by path (`edit.py`: `apply_edits`, `check_field`, `save_edits`);
  #116 `export_csv` + `library export-csv`; #118 `preview_csv_import` / `import_csv` +
  `library import-csv` (incl. "probably an Excel formula" hint); #120 `compare_alternatives`;
  #127 `write_bundle` creates missing folders and refuses cleanly; a failed `active` write
  restores the previous version (no `.replaced-<uuid>`).

## In review
- None of mine. A3's #130 (M14 library entries) changed five of my test files; I reviewed them
  and told A3 they are fine (1093 library_store + device_db tests pass on its head `87eee46`).

## What works (evidence)
- `pytest tests/unit/library_store tests/unit/test_bundle_container.py`: 344 passed on main
  `9313db1` (2026-10-28). `pytest tests/golden`: 94 passed.
- Public API is in `src/bomgen/library_store/__init__.py` (docstring lists it).

## Environment note (not a main failure)
- My first full `pytest` run (in a git worktree) showed 3 failures in
  `tests/unit/app/test_app_edit_api.py` (`'Api' object has no attribute 'check_layout'`). The cause was
  a stale editable install: `bomgen` imported from another checkout (`/home/user/BOM-generator/src`,
  an older tree), not from the worktree. A1 reports main passes 2414 in CI. In a worktree or any other
  checkout, run `PYTHONPATH=src python -m pytest` and check `python -c "import bomgen;print(bomgen.__file__)"`.

## Verification table
| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` (main `9313db1`) | pass | 2026-10-28 |
| `mypy` (main `9313db1`) | pass, 210 files | 2026-10-28 |
| `pytest` (main `9313db1`, worktree, stale editable install) | 2411 passed, 3 failed: environment, see note | 2026-10-28 |
| `pytest tests/golden` | 94 passed | 2026-10-28 |
| Not run: Windows installer, GUI | n/a (not my role's files) | |

## Scope risks (files outside `library_store/` that my PRs changed, all approved by A1)
- `src/bomgen/bundle/container.py`, `bundle/errors.py`, `bundle/checks.py` (shared container; #127
  `write_bundle`, #113 `RefusalKind.NO_CHANGES`); `tests/unit/test_bundle_container.py`.
- `src/bomgen/models/project.py` + `schemas/project.schema.json` (#105 `LibraryVersion` pattern
  accepts `+local.N`).
- `docs/plan.md` M16 text, `docs/decisions/README.md` row, ADR 0018.
- `src/bomgen/project_store/` was built by me for M8b though agents.md lists only `library_store/`.

## Blockers, risks, assumptions
- ADR 0008 and ADR 0018 stay "Proposed" until Ali accepts them (A1's ruling); leave them as they are.
- Waiting on: nobody. A11 is wiring the Library editors and will ask questions.
- Spec vs code disagreements: none known.
- Unverified: that A11's app code uses `check_field`, `save_edits` and `preview_csv_import`
  as documented (I have not read `src/bomgen/app/`).
