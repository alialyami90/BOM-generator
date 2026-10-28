# 0012. Projects hold substations; sharing by `.bomproj` export

- Status: Accepted (Ali, project thread, 2026-10-28)
- Date: 2026-10-28
- Spec sections: Overview; Inputs the tool needs → 3. Project settings; Data
  model and generation order (entity Project)

## Context

Ali's projects have several substations. Each substation has one system with
its own panels, BOM, calculation sheets and workbook. The project carries the
project info, the document list and data shared by its substations. Engineers
need to share a project with each other and keep backups. Today's inputs
(`project.yaml` + `panels/*.yaml`) describe one system only. Full design:
`docs/superpowers/specs/2026-10-28-substations-and-auto-layout-design.md`.

## Decision

- A **project** is a folder with `project.yaml` (project info, installed
  library name and version, document register, default constants and spares,
  list of substations) and `substations/<id>/`. A **substation** folder holds
  `substation.yaml` (today's `project.yaml` content plus `equipment`,
  `network`, `spares`, `layout`; ADR 0013), its `panels/` and its `out/`.
  Substation constants and spares override the project defaults key by key.
- The **document register** lives on the project and lists documents per
  substation (every key names its substation); panels and calculation sheets
  reference a register key for their header (Q24).
- **Create substation from template** copies a substation folder, renames
  ids, cabinet numbers and tag prefixes, and clears layout overrides.
- **Sharing and backup** use one `.bomproj` file: a zip of the project folder
  without `out/`, plus `manifest.json` (format version, project id, library
  name and version, app version, SHA-256 per file). Export writes it, import
  unpacks it into the workspace and warns before overwriting a project id, and
  a backup is an export into the project's `Backups/` folder. The container,
  checksum and path checks reuse the `.bomlib` code (ADR 0008); the manifest's
  library version answers Q21: import names the `.bomlib` to install when the
  versions differ.
- `bomgen validate` and `bomgen build` accept a project or a substation file;
  the home page of the app lists projects.

## Consequences

- A2 owns the new models and loader (milestone M1b); A5 the `.bomproj`
  commands (M8b); A6 the `.bomproj` file association; A4 the home, project and
  substation screens. The library stays one installed copy per machine, never
  part of a project.
- Today's `examples/` become one example project with one substation; the
  hand-written panels and every golden value stay valid.
- Two engineers editing the same project exchange whole files; there is no
  merge. Import overwrites after a warning, and the backup folder is the undo.
