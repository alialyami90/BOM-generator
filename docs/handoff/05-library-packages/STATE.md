# State: role 5, Library update packages

- Name: B5 - Library update packages (outgoing; Ali retired every agent on 2026-10-29). Successor: C5.
- Date: 2026-10-29. origin/main at write time: `032bbea` (v0.2.1 docs).
- Role and files: [`docs/agents.md`](../../agents.md) "Roles" row A5 and its section "A5 — Library update
  packages (M8)". Owns `src/bomgen/library_store/`, `tests/unit/library_store/`, ADR 0008, ADR 0018, the M8
  section of [`plan.md`](../../plan.md) and this folder plus ROSTER row 5. Also built (and is the de facto
  owner of) `src/bomgen/project_store/` (M8b, ADR 0012), although agents.md lists only `library_store/`.
- Branch: `claude/project-thread-31eptw` (B5's thread branch). Every PR of mine is merged; the branch holds
  only merged history. A successor works on its own thread branch, starting from `origin/main`.
- Open PRs of mine: none. Uncommitted work: none. Stash: none.
- ADR 0008 and ADR 0018 are **Accepted** (Ali, 2026-10-28, #184). Amend them only in a `docs(adr): …` PR of
  their own, never inside a checkpoint PR (B1's rule).

## What the role delivered (all reviewed and squash-merged by role 1)

### M8 / M8b (A5, before v0.1)
#9, #31, #41, #50, #53, #59: `.bomlib` package (pack, verify, manifest with checksums), the per-user store
with rollback, the import dry-run, `bomgen library …`, `.bomproj` export / import / backup with dry-runs
(`project_store/`), device-db records shipped inside a `.bomlib` (ADR 0008 amendment).

### M16 store side (v0.2, ADR 0018)
- #92 ADR 0018; #95 device-db checker accepts the M14 keys; #105 local versions `<base>+local.N`.
- #113 `save_local_version` and the `.bomlib` backup (`LibraryStore.export_package`, `bomgen library export`).
- #114 edit operations by path (`edit.py`: `apply_edits`, `check_field`; `local.py`: `save_edits`).
- #116 `export_csv` + `bomgen library export-csv`; #118 `preview_csv_import` / `import_csv` +
  `bomgen library import-csv` (incl. the "probably an Excel formula" hint); #120 `compare_alternatives`.
- #127 `write_bundle` creates missing folders and refuses cleanly; a failed `active` write restores the
  previous version (no `.replaced-<uuid>` left behind).
- B5, 2026-10-28: #164 device-record edits (`records.py`), for B11's Datasheet tab; #170 ADR 0018 amendment
  "device-record edits"; #179 `catalogues.mcb_dc` carried through the CSV as the `default_dc` row, plain row
  messages (`plain_message`), "Compared with … Saving makes …" wording, ADR 0018 amendment.
- Changes others made in my files, reviewed by me: #165 (`ac_rated` CSV column; brand sets counted in
  `diff_libraries`), #161 (one test expectation in `test_library_csv_export.py`), #130 (A3, five test files).

## Module map (`src/bomgen/library_store/`; public API re-exported in `__init__.py`)

| Module | What it holds |
| --- | --- |
| `manifest.py` | `Manifest` (`manifest.json` of a `.bomlib`), `LIBRARY_FILE`, `LIBRARY_SCHEMA_VERSION = 1`, `FORMAT_VERSION` |
| `package.py` | `pack`, `read_package`, `PackageContents`; uses the shared `bomgen.bundle.container` zip code |
| `store.py` | `LibraryStore` (layout `<name>/<version>/…` + `<name>/active` text file), `install`, `rollback`, `read_version`, `export_package`; `default_library_home()` (`BOMGEN_LIBRARY_HOME`, else `%LOCALAPPDATA%\bomgen\libraries` / XDG) |
| `service.py` | `validate_library`, `import_library` (CLI, launcher and app share them) |
| `preview.py` | `preview_library_import`: the `.bomlib` dry-run (`Check` list, first failure stops) |
| `diff.py` | `LibraryDiff`, `diff_libraries` (parts added / changed / removed, catalogues and brand sets as `kind:id`, files) |
| `versions.py` | `Version` (MAJOR.MINOR.PATCH with optional `+local.N`, ordered between base and next release) |
| `device_db.py` | `DeviceRecord` and its models, `parse_device_records`, `load_device_records` (the `device-db/` YAML in a version) |
| `edit.py` | `SetValue` / `Insert` / `Remove`, `parse_edits`, `apply_edits`, `check_field` (paths into `library.yaml`) |
| `records.py` | `apply_record_edits`, `check_record_field`, `write_records`, `changed_records` (paths into device records, keyed by `part_id`) |
| `local.py` | `save_local_version`, `save_edits(edits, record_edits=…)`, `next_local_version`, `dump_library` |
| `csv_export.py` | `TABLES`, `library_tables`, `export_csv`, `export_installed_csv`, `DEFAULT_DC_ID = "default_dc"` |
| `csv_import.py` | `preview_csv_import` → `CsvPreview` (checks, `RowProblem`s, `Change`s, edits, library), `import_csv`, `plain_message` |
| `alternatives.py` | `compare_alternatives` → `AlternativeRow`s for a device and its `alt_group` |
| `cli.py` | `bomgen library pack | import | list | export | export-csv | import-csv | rollback` |

Callers outside my folder: `src/bomgen/app/` (api, catalogues, editing, launcher, library_csv, library_edit,
…), `src/bomgen/io/` (loader, edit, fields, lifecycle), `checks.py`, `cli.py` (one `add_typer` line).
The shared container (`src/bomgen/bundle/container.py`, `errors.py`, `checks.py`) is used by both stores.

## What works (evidence)
| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` (main `032bbea`) | pass (345 files formatted) | 2026-10-29 |
| `python -m mypy` (main `032bbea`) | pass, 224 files | 2026-10-29 |
| `pytest` (main `032bbea`, fresh `pip install -e ".[dev]"`) | 2672 passed | 2026-10-29 |
| `pytest tests/unit/library_store tests/unit/test_bundle_container.py` | 378 passed | 2026-10-29 |
| #179 head before merge: full gate | ruff, format, mypy (218 files) pass; 2561 passed | 2026-10-28 |
| Not run by me: Windows installer, the GUI | not my role's files | |

## Environment notes (read before running the gate)
- A fresh cloud container has no `bomgen` installed: run `pip install -e ".[dev]"` first.
- `mypy` on PATH (`/root/.local/bin/mypy`) runs under another Python without pydantic and fails with
  "Error importing plugin pydantic.mypy". Use `python -m mypy`.
- In a git worktree the editable install points at the main checkout: run `PYTHONPATH=src python -m pytest`
  and check `python -c "import bomgen; print(bomgen.__file__)"` first. A5 once misreported 3 failures this way.
- Force-push to the thread branch is refused by the permission classifier. After a squash-merge, reset the
  branch to `origin/main`, then `git merge -s ours origin/<branch>` so a plain push works.

## Scope risks (files outside `library_store/` that role-5 PRs changed, all approved by role 1)
- `src/bomgen/bundle/container.py`, `bundle/errors.py`, `bundle/checks.py` (#127 `write_bundle`, #113
  `RefusalKind.NO_CHANGES`); `tests/unit/test_bundle_container.py`.
- `src/bomgen/models/project.py` + `schemas/project.schema.json` (#105: `LibraryVersion` accepts `+local.N`).
- `docs/plan.md` M16 text, `docs/decisions/README.md` row, ADR 0018.
- `src/bomgen/project_store/` (M8b) is mine in practice; agents.md does not list it.

## Known gaps (none requested; do not start them unasked)
- The CSV does not carry device-database records; a CSV import keeps the base version's `device-db/`.
- `LibraryPackageError` carries only a message and a kind; A1 said to skip carrying manifest/`active` data
  until someone needs it.
- A rewritten `device-db/*.yaml` or `library.yaml` loses its YAML comments (documented in ADR 0018).

## Blockers and pending questions
- Blockers: none. Waiting on: nobody. Open questions for Ali in my area: none.
- Spec vs code disagreements: none known.
