# 0008. Device library updates as `.bomlib` packages

- Status: Proposed
- Date: 2026-10-28
- Spec sections: Inputs the tool needs → 1. Device library

## Context

Ali wants each installed copy's device database to be updatable by sharing an
update package. The device library is the input the spec keeps separate from
panels and project settings, so it can be versioned on its own.

## Decision (proposed)

- A `.bomlib` file is a zip with `manifest.json` (name, version, schema
  version, minimum app version, release notes, SHA-256 per file) and
  `library.yaml` plus any assets. Optional Ed25519 signature (plan Q18).
- Each install keeps libraries under
  `%LOCALAPPDATA%\bomgen\libraries\<name>\<version>\` with an `active`
  pointer; previous versions stay for rollback.
- Import (app, double-click, or `bomgen library import`) verifies checksums,
  the schema version and the signature if enabled, shows the parts added,
  changed and removed, and refuses downgrades unless forced.
- Projects record the library name and version used; rebuilding with a
  different version is reported by the check report.
- The full library ships in every package (no deltas): it's small text, and
  full snapshots make rollback and support simple.

## Consequences

Library updates need no new installer and no admin rights. A project built on
one PC can be reproduced on another by importing the same library version.

## Implementation notes (M8)

Code: `src/bomgen/library_store/`.

- The `active` pointer is a text file holding the version, not a symlink:
  symlinks need admin rights or Developer Mode on Windows.
- `BOMGEN_LIBRARY_HOME` overrides the store root (tests, portable installs).
  Outside Windows the root is `$XDG_DATA_HOME/bomgen/libraries`.
- Library schema version starts at 1. Import accepts only the version this
  build reads; a package needing a newer app (`min_app_version`) is refused.
- Extra directories (for example `data/device-db/`) are packed with
  `bomgen library pack --add <dir>`, stored under the directory's name and
  checksummed like `library.yaml`. Only `*.yaml` / `*.yml` files are packed.
  The import summary lists changed files.
- Import checks every member path (no absolute, `..`, drive or backslash
  paths), caps the uncompressed size at 64 MiB, and verifies all checksums
  before writing anything. It extracts into a temporary directory, runs the
  library validator, then moves the version into place and updates `active`;
  a failure leaves the store unchanged. `--dry-run` shows the diff only.
- Rollback activates the newest installed version older than the active one,
  or the version given with `--to`. Re-importing an installed version, or an
  older one, needs `--force`.
- No signature yet (plan Q18 default). The manifest has `format_version` so a
  signature field can be added later without breaking old packages' readers.
- `bomgen library import` validates the package's library with the same loader
  the build uses (`bomgen.io.loader.load_library`) before anything is installed;
  `--dry-run` runs the same check.
- Refusals raise `LibraryPackageError` with a `kind` (`RefusalKind`: invalid
  package, incompatible, validation failed, downgrade, already installed, not
  installed, store damaged) so the desktop app (M10) can word them and offer
  remedies without parsing messages. Mapping kinds to screen copy is an M10 item.

