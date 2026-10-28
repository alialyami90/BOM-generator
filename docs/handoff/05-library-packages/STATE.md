# State: role 5, Library update packages

- Name: B5 - Library update packages. Date: 2026-10-28 (refreshed after #164).
- Role and files: [`docs/agents.md`](../../agents.md) "Roles" row A5 and its section. Owns
  `src/bomgen/library_store/`, ADR 0008, ADR 0018 (number assigned by A1), the M8 section.
- Branch: `claude/project-thread-31eptw` (B5's thread branch; reset to `origin/main` before each PR
  when there is no unmerged work). origin/main at write time: `1fe50d4`.
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
- B5: #164 device-record edits (`records.py`: `apply_record_edits`, `check_record_field`,
  `write_records`; `save_edits(record_edits=...)`), for B11's Datasheet tab. ADR 0018 amendment
  "device-record edits" in the checkpoint PR.
- Not mine but in my files: #165 (`ac_rated` CSV column, brand sets in `diff_libraries`).

## In review
- None of mine except this checkpoint PR. Reviewed B3's #161 library_store parts (now only one
  test expectation in `test_library_csv_export.py`, commit `7184f99`): fine, told B3.

## What works (evidence)
- Full gate on #164's head (`f319f64` base): 2479 passed. #164 merged with main (`0f4b3eb`):
  `tests/unit/library_store tests/unit/app` 585 passed.
- Public API is in `src/bomgen/library_store/__init__.py` (docstring lists it).

## Environment note (not a main failure)
- A fresh container has no `bomgen` installed: run `pip install -e ".[dev]"` first.
- `mypy` on PATH (`/root/.local/bin/mypy`) runs under another Python without pydantic and fails
  with "Error importing plugin pydantic.mypy"; use `python -m mypy`.
- In a git worktree run `PYTHONPATH=src python -m pytest` and check `bomgen.__file__`.

## Verification table
| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` (#164 head) | pass | 2026-10-28 |
| `python -m mypy` (#164 head) | pass, 214 files | 2026-10-28 |
| `pytest` (#164 head, fresh install) | 2479 passed | 2026-10-28 |
| `pytest tests/unit/library_store tests/unit/app` (#164 merged with `0f4b3eb`) | 585 passed | 2026-10-28 |
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
- Waiting on: nobody. B11 builds the Datasheet tab on #164; it may ask more.
- Spec vs code disagreements: none known.
- Unverified: how B11's app (#155, merged) calls `save_edits` / `check_field`; I have not read
  `src/bomgen/app/`. `catalogues.mcb_dc` has no CSV table; an import keeps it from the base
  (checked by hand on #161's head), so it cannot be edited in Excel. Not requested.
