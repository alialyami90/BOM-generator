# Changelog

All notable changes to this project are listed here, one entry per merged pull
request; a milestone split across several PRs gets one entry. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project will use [Semantic Versioning](https://semver.org/) from its first
tagged release.

## [Unreleased]

### Added

- BOM groups A–D as engine output: enclosure, devices and tags, kit
  children, network accessories, housekeeping kit and the loose-material
  table, with a golden test over every group A–D row; ADR 0014 (milestone M2,
  #22).
- Sheet models and the XlsxWriter workbook writer: cells, live formulas,
  styles, merges, print setup, page header and footer (milestone M6, #21).
- `bomgen project export|import|backup`: projects shared and backed up as
  `.bomproj` files with a checksummed manifest, overwrite refusal with a
  safety backup, and a library-version note naming the `.bomlib` to install;
  the zip container is shared with `.bomlib` (milestone M8b, #20).
- Device database: rack height and mounting kind per record, port roles for
  the library switches (#18).
- ADR 0012 (projects hold substations, `.bomproj` sharing) and ADR 0013
  (switch sizing and automatic panel layout), milestones M1b, M1c and M8b,
  Q24–Q28 resolved and the A8–A10 roles (#16).
- Windows installer and releases, built early: PyInstaller spec, per-user
  Inno Setup installer with `.bomlib` file association, frozen-app launcher
  with placeholders for the M10 window and `.bomlib` import, tag-driven
  release workflow that builds, smoke-tests and publishes the installer,
  `docs/install.md` and ADR 0009 (milestone M11, #2).
- M9 UI design in `docs/ui/`: design tokens, component and screen specs, a
  clickable HTML/CSS prototype and bundled fonts; ADR 0011 (#8).
- `docs/agents.md`: agent roles, file ownership, numbering and the review and
  merge flow (#3).
- Device-library update packages: `.bomlib` pack and verify, a per-user
  library store with import preview, downgrade refusal and rollback, and the
  `bomgen library pack|import|list|rollback` commands (milestone M8, #9).
- Changelog entries for #6 and #4 (#10); README and test READMEs for M8 and
  M9 (#11) and for M11 (#14).
- Device database in `data/device-db/`: datasheet facts and two alternative
  brands (low, mid, high part numbers) for every part in the example library,
  as reference data the generator does not read; findings in
  `docs/device-db-findings.md` (#6).
- `CHANGELOG.md`; README status and usage updated for M1 (#4).
- Input models for the device library, panels and project; YAML loader with
  relative file references, panel mirroring and readable errors; JSON Schemas
  in `schemas/`; `bomgen validate` and `bomgen schema`; `examples/`
  transcribed from the example workbook; ADR 0010 (milestone M1, #5, #7).
- Repository scaffold: `bomgen` package, tooling, working rules, generator spec
  v2, implementation plan, ADRs 0001–0008 and CI with docs-only gating
  (milestone M0, #1).

### Changed

- M9 prototype reworked for projects and substations: project page with the
  document register and backup and share, a Network screen and a Panels board
  per substation (#23).
- The installed app imports a double-clicked `.bomlib` through the library
  store and shows the change summary or the refusal; `.bomproj` files get a
  placeholder association; `BOMGEN_NO_DIALOGS=1` prints messages to stderr
  for unattended runs (M11, #15).
- `docs/agents.md` refreshed: merge order, next milestones, reserved ADR and
  open-question numbers (#13).
- Plan Q29 resolved: the example keeps the workbook's thermostat load and fan
  airflow; future library defaults use 0 W for the SK 3110 thermostat and
  460 m³/h for the SK 3243.100 fan with its outlet filter (#12).
