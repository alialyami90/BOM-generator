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
