# M8 Library Update Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Versioned `.bomlib` device-library packages that each Windows user can import, preview, list and roll back without admin rights.

**Architecture:** A self-contained package `bomgen.library_store` with pure parts (manifest, version parsing, pack/verify, diff) and one stateful part (the on-disk store). It reads `library.yaml` as plain YAML and diffs devices by `part_id`, so it does not depend on the M1 pydantic models; full schema validation is injected as a `validate(path)` callable that the CLI wires to the M1 loader once M1 is merged.

**Tech Stack:** Python 3.12 stdlib (`zipfile`, `hashlib`, `json`), pydantic v2 for the manifest, PyYAML, typer for the CLI.

**Spec:** ADR 0008 (`docs/decisions/0008-library-update-packages.md`) and plan M8 (`docs/plan.md`); generator spec "Inputs the tool needs → 1. Device library" for the `devices` / `catalogues` shape.

## Global Constraints

- Package file: zip, extension `.bomlib`, holding `manifest.json`, `library.yaml`, and optional extra files (e.g. `device-db/*.yaml`).
- Manifest fields: `format_version` (1), `name`, `version`, `schema_version`, `min_app_version`, `release_notes`, `created`, `files` (posix path → SHA-256 hex). `manifest.json` itself is not in `files`.
- Store root: `%LOCALAPPDATA%\bomgen\libraries` on Windows; `$XDG_DATA_HOME/bomgen/libraries` (or `~/.local/share/...`) elsewhere; `BOMGEN_LIBRARY_HOME` overrides both. Layout `<root>/<name>/<version>/` plus `<root>/<name>/active` (a text file with the version; no symlinks, they need admin on Windows).
- Import refuses: bad zip, missing/invalid manifest, a file not in the manifest, a manifest file missing from the zip, checksum mismatch, unsafe path, schema version ≠ supported (`LIBRARY_SCHEMA_VERSION = 1`), `min_app_version` > `bomgen.__version__`, a downgrade below the active version, a version already installed — the last two unless `force`.
- No signatures (plan Q18 default).
- Never write `.xlsx`; tests write only under `tmp_path`.

## Review Focus

1. Zip entries with `../`, absolute, drive-letter or backslash paths must be rejected before anything is extracted (zip-slip).
2. A package whose uncompressed size exceeds 64 MiB is rejected (zip bomb).
3. A failed import (validator raises, bad file) leaves the store exactly as it was: no partial version directory, `active` unchanged.
4. Versions compare numerically: `1.10.0` > `1.9.0`.
5. A corrupt `active` file or one naming a version that is not installed gives a readable error, and `list` still works.

---

### Task 1: Version and manifest

**Files:** Create `src/bomgen/library_store/{__init__.py,errors.py,versions.py,manifest.py}`; Test `tests/unit/library_store/test_library_manifest.py`.

**Produces:** `LibraryPackageError(Exception)`; `Version` (frozen, ordered, `parse(text) -> Version` accepting `MAJOR.MINOR.PATCH` only, `__str__`); `Manifest` (pydantic, `extra="forbid"`, frozen) with the constraint fields, `name` matching `^[a-z0-9][a-z0-9._-]*$`, `version`/`min_app_version` validated by `Version.parse`, `files` keys validated by `is_safe_member(path) -> bool`; constants `FORMAT_VERSION = 1`, `LIBRARY_SCHEMA_VERSION = 1`, `MANIFEST_NAME = "manifest.json"`, `LIBRARY_FILE = "library.yaml"`.

- [ ] Tests: `test_versions_compare_numerically` (1.10.0 > 1.9.0), `test_version_rejects_non_semver` ("1.2", "v1.2.3", "1.2.3-beta"), `test_unsafe_member_paths_rejected` (`../x`, `/x`, `C:/x`, `a\\b`, `a/../b`, empty), `test_manifest_rejects_unknown_fields`, `test_manifest_rejects_unsafe_library_name` (`../evil`, `My Lib`).
- [ ] Run, see them fail; implement; run, pass; commit `feat(library-store): add package manifest and versions`.

### Task 2: Library document and diff

**Files:** Create `src/bomgen/library_store/diff.py`; Test `tests/unit/library_store/test_library_diff.py`.

**Produces:** `parse_library(data: bytes) -> dict[str, Any]` (YAML mapping; `devices` a list of mappings with unique string `part_id`; raises `LibraryPackageError`); `LibraryDiff` dataclass (`added`, `removed`: sorted part ids; `changed: dict[str, list[str]]` part id → sorted changed field names; `catalogues_changed`: sorted catalogue keys; `files_added/changed/removed`: sorted extra-file paths; `is_empty`; `summary_lines() -> list[str]`); `diff_libraries(old: Mapping | None, new: Mapping, old_files: Mapping[str, str] = {}, new_files: Mapping[str, str] = {}) -> LibraryDiff` (`library.yaml` is excluded from the file lists).

- [ ] Tests: `test_diff_lists_added_removed_and_changed_parts` (changed lists field names, e.g. `unit_power_w`), `test_diff_reports_changed_catalogues`, `test_diff_against_nothing_adds_every_part`, `test_diff_lists_changed_extra_files`, `test_parse_library_rejects_duplicate_part_ids`, `test_parse_library_rejects_non_mapping`.
- [ ] Fail → implement → pass → commit `feat(library-store): diff libraries by part id`.

### Task 3: Pack and verify

**Files:** Create `src/bomgen/library_store/package.py`; Test `tests/unit/library_store/test_library_package.py`.

**Consumes:** Task 1, `parse_library`.
**Produces:** `PackageContents` (frozen dataclass: `manifest`, `files: dict[str, bytes]` incl. `library.yaml`); `pack(library: Path, out: Path, *, name: str, version: str, release_notes: str = "", extra_dirs: Sequence[Path] = (), min_app_version: str = bomgen.__version__, created: datetime | None = None) -> Manifest` (extra dir `d` stored under `d.name/`, files sorted, fixed zip timestamps so equal inputs give equal bytes; validates `library.yaml` with `parse_library`); `read_package(path: Path, *, app_version: str = bomgen.__version__) -> PackageContents` enforcing every refusal in Global Constraints except the store ones, plus `MAX_UNCOMPRESSED_BYTES = 64 * 1024**2`.

- [ ] Tests: `test_pack_then_read_round_trips`, `test_pack_is_deterministic`, `test_pack_carries_extra_directories`, `test_tampered_file_is_rejected` (rewrite a member with other bytes), `test_unlisted_file_is_rejected`, `test_missing_listed_file_is_rejected`, `test_unsafe_member_is_rejected`, `test_schema_version_mismatch_is_rejected`, `test_newer_min_app_version_is_rejected`, `test_not_a_zip_is_rejected`, `test_oversized_package_is_rejected` (monkeypatch the limit low).
- [ ] Fail → implement → pass → commit `feat(library-store): pack and verify .bomlib packages`.

### Task 4: Installed-library store

**Files:** Create `src/bomgen/library_store/store.py`; Test `tests/unit/library_store/test_library_store.py`.

**Consumes:** `read_package`, `diff_libraries`, `parse_library`.
**Produces:** `default_library_home(env: Mapping[str, str] = os.environ, platform: str = sys.platform) -> Path`; `InstalledLibrary(name, active: str | None, versions: list[str])`; `ImportResult(manifest, previous: str | None, diff: LibraryDiff)`; `LibraryRef(name, version)` and `library_mismatch(recorded: LibraryRef, active: LibraryRef | None) -> str | None`; `LibraryStore(root: Path)` with `list() -> list[InstalledLibrary]`, `active_version(name) -> str | None`, `library_file(name, version=None) -> Path`, `preview_import(path, *, force=False) -> ImportResult`, `import_package(path, *, force=False, validate: Callable[[Path], None] | None = None) -> ImportResult`, `rollback(name, to: str | None = None) -> str`.

Install = extract into `<root>/<name>/.incoming-<random>/`, run `validate`, `os.replace` into `<version>/`, then write `active` via temp file + `os.replace`. Any failure removes the temp dir. Rollback without `to` picks the highest installed version below the active one.

- [ ] Tests: `test_import_installs_and_activates`, `test_import_reports_diff_against_active`, `test_import_refuses_downgrade_unless_forced`, `test_import_refuses_reinstall_unless_forced`, `test_failed_validation_leaves_store_unchanged`, `test_preview_import_changes_nothing`, `test_rollback_activates_previous_version`, `test_rollback_to_named_version`, `test_rollback_without_older_version_fails`, `test_corrupt_active_pointer_is_reported`, `test_default_home_is_localappdata_on_windows`, `test_default_home_env_override`, `test_library_mismatch_message`.
- [ ] Fail → implement → pass → commit `feat(library-store): per-user store with import and rollback`.

### Task 5: CLI and docs

**Files:** Create `src/bomgen/library_store/cli.py` (`library_app: typer.Typer`); create or modify `src/bomgen/cli.py` to `app.add_typer(library_app, name="library")`; `pyproject.toml` console script; update `docs/plan.md` M8 and ADR 0008; Test `tests/unit/library_store/test_library_cli.py`.

Commands: `pack LIBRARY --name --version [--notes] [--add DIR]... --out FILE`; `import FILE [--force] [--dry-run]`; `list`; `rollback NAME [--to VERSION]`. Store root from `BOMGEN_LIBRARY_HOME` / default. Errors print one line to stderr and exit 1.

- [ ] Tests: `test_cli_pack_import_list_rollback` round trip through `CliRunner` with `BOMGEN_LIBRARY_HOME=tmp_path`, `test_cli_import_dry_run_installs_nothing`, `test_cli_rejects_tampered_package_with_exit_1`.
- [ ] Fail → implement → pass → ruff, mypy, pytest → commit `feat(cli): add library pack/import/list/rollback`.

### Added after review and merge of M1

- `LibraryPackageError.kind` (`RefusalKind`) so the UI can react to refusals; `preview_import(validate=...)`.
- Extra directories pack only `*.yaml` / `*.yml`; Windows-unsafe member names and case collisions are refused.
- `app.add_typer(library_app, name="library")` in `bomgen.cli`; `import` validates with `load_library` (`tests/unit/library_store/test_library_wiring.py`).
