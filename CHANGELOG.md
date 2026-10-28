# Changelog

All notable changes to this project are listed here, one entry per merged pull
request; a milestone split across several PRs gets one entry. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-10-28

### Added

- The installer ships the default device library, and the app loads it into
  an empty library store on first start (#86).

### Changed

- Version 0.1.1; the release workflow's publish step attaches to a release
  that already exists (#86).

## [0.1.0] - 2026-10-28

### Added

- Desktop app Network result, L1 ranking and Panels board, read-only: the
  network plan per side, the L1 switches in the engine's order and each
  generated panel's units, blank plates and layout issues; every substation
  screen is now connected (milestone M10c, #78).
- Desktop app Preview: each panel sheet and the three calculation sheets as
  the engine computes them, through `preview_substation` (milestone M10d,
  #71).
- Network sizing and automatic panel layout: `bomgen layout` sizes the L1 and
  L2 switches from the IED count and spares, fills the 32U panels and writes
  generated panel files; `bomgen build` lays out again a substation whose
  panels were generated, unless `--no-layout`, and stops on layout errors;
  after a layout the annunciator is fed from panel 001 (side A); the example
  substation gives 3 L1 switches per side; golden test of the generated panels
  (milestone M1c, #19).
- Desktop app Checks and Build screens: the substation's problems and the
  check report, and a build that refuses with `has_errors`, `file_exists`
  (asks before replacing), `file_open`, `bad_name`, `bad_folder`,
  `bad_previous`, `engine` or `write` (milestone M10d, #65).
- `bomgen build` prints the check report, writes it as `<name>.checks.json`
  and exits 1 when a check fails (`--no-checks` skips it); `--compare` marks
  the cells changed since a previous issue; the FGR-60F gets its 2 SFP slots
  (milestone M7, #62).
- Check report and revision comparison in the engine: SFPs against slots, DC
  mains against ΣQ, airflow and natural convection, DI capacity against HWIO,
  and the changed cells since a previous issue; ADR 0016 (milestone M7, #58).
- Desktop app Substation settings and Network inputs, read-only (milestone
  M10c, #60).
- Desktop app Keep both on a clashing import, and the restore review on
  `preview_backup_restore` (#63), which checks a restore's refusals before
  the import checks (#59).
- `bomgen build`: one workbook per substation of a project, or for one
  `substation.yaml`, into `--out` (default `out/`), named per OUT-2; `--substation`
  builds one; a golden test builds the example (first part of milestone M7,
  #51).
- `bomgen project import --rename-to ID` imports a `.bomproj` under a new
  project id and keeps the existing project; the dry-run suggests a free id;
  ADR 0012 amendment (#53).
- Library parts carry `di_inputs`, the hardwired digital inputs one unit
  provides, for the check report's DI capacity check (#52).
- Desktop app Home, Project page and Backup and share on the project store:
  the workspace's projects and recently opened folders with their status,
  export, backup, import and restore reviews; the Project page is read-only
  until project writers exist (milestone M10b, #49).
- Sheet models filled from the engine: one BOM sheet per cabinet with the
  loose-material table under its host, and the Power Consumption, Heat
  Dissipation and Heat Calculations sheets, every computed cell a live formula
  with its cached result; a golden test recalculates the written workbook with
  pycel (milestone M5, #48).
- Desktop app Library screens on the installed library store: browse with the
  device-database records, import review and import, versions (milestone
  M10b, #45).
- Power and heat engine: Power Consumption lines, blocks and summary, heat
  dissipation, forced-ventilation airflow, natural convection and the line-up
  check; ventilation `auto` is decided from the heat check; ADR 0014
  (milestone M4, #44, #46).
- BOM groups E–H as engine output: AC and DC distribution, terminal strips
  (including the devices' own strips), grounding busbars and revision marks;
  `pipeline.build` builds groups A–H in two passes; golden test over every
  group E–H row; plan Q34 (milestone M3, #36).
- Device-database records travel in a `.bomlib`: pack checks them, import
  installs them with the library and `bomgen.library_store.device_db` loads
  them (#41).
- Desktop app shell: the approved UI in a pywebview window with a Python
  bridge (`bomgen.app.window`, `bomgen.app.api`) and the `app` extra; it
  refuses to open without its UI files or WebView2; ADR 0015 (milestone M10a,
  #28).
- Import dry-runs for libraries and projects that list every check and write
  nothing, and listing and restoring project backups, for the desktop app
  (#31).
- Projects hold substations: `project.yaml` carries project info, library
  name and version, the document register, defaults and the substation list;
  `substations/<id>/substation.yaml` carries the former project settings plus
  equipment, network, spares and layout inputs; the library gains rack heights,
  port roles and enclosure heights; `bomgen validate` takes either file;
  `examples/` becomes one project with one substation, golden values unchanged
  (milestone M1b, #27).
- Equipment purpose, HWIO points and per-unit port plans in the substation
  inputs, with the example equipment in cabinet 001's group B order (#34).
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

- Version 0.1.0, the first release (#84).
- Changelog release heading for 0.1.0 (#85).
- Desktop app polish from A4's findings: a compact Panels board header, one
  "not available yet" line under each page's subtitle, a pulsing Build busy
  bar, a neutral "Partial" badge and smaller fixes across the screens
  (milestone M10e, #81).
- `docs/ui/` records the departures the built app made from the design (#82).
- Changelog, README status for M10c and test READMEs for #75–#79 (#80).
- The app's Build runs the shared build sequence; `BuildOutcome.sheets`
  carries the workbook's sheet names (#79).
- One build sequence, `bomgen.build.build_substation`, for `bomgen build` and
  the app; the caller lays out first (#76, #77).
- Changelog, README and test READMEs for #71–#74 (#75).
- The app's Checks, Build and Preview run the same automatic layout as
  `bomgen build`, so generated panels give the same workbook; layout errors
  block Build and Preview and warnings show in Checks (#73).
- Plan: M7 is done and `--sheet-name` is dropped, since the inputs name the
  sheets; M10d lists every Build refusal (#74).
- Changelog, README and test READMEs for #19 and #49–#70 (#72).
- The frozen CLI writes UTF-8 to the console; the release smoke tests read the
  workbook path from the first line of `bomgen build` and check its report
  (#70).
- The CLI prints the check report correctly on a Windows console (#68).
- Workbooks are replaced atomically, so a failed replace never deletes the
  workbook already at that path (#69).
- Q34 resolved by Ali; ADR 0014 accepted (#66, #67).
- The import clash banner leads the review dialog (#64).
- `docs/agents.md`: A9 owns the check report and revision modules; ADR 0016
  taken (#61).
- The release workflow's installed-build step parses on PowerShell (#57).
- The release workflow builds the example workbook with the frozen and the
  installed CLI (#55).
- Desktop app: `show_in_folder` opens only files the app listed; the
  recent-projects list lives in its own app home (`BOMGEN_APP_HOME`); the
  import review reads `can_import` (#54).
- Library and project store messages state the situation; the command to run
  moves to `LibraryPackageError.hint` (#50).
- Changelog, README and test READMEs for #42–#48 (#56).
- The release workflow validates the example project with the frozen and the
  installed CLI (#47).
- `data/device-db/README.md` explains how to ship the records in a `.bomlib`
  (#42).
- Changelog, README and test READMEs for #36–#41 (#43).
- `data/device-db/README.md` states the field rules readers can rely on, with
  tests for them (#40).
- The installed app opens the desktop window and a double-clicked
  `.bomproj`; the frozen bundle carries the UI files (M10a and M11, #38).
- `*.bomproj` packages and `Backups/` folders are git-ignored; Q34 taken
  (#39).
- Changelog, README and test READMEs for #17 and #24–#35 (#37).
- The `l1_switch` role takes an optional part: the tool ranks the library's
  L1 switches and picks one unless the engineer pins it; layout checks report
  every problem with its location; FOPP-96SM is 1U, NAP-F23 and KEYTEK-KBM 0U
  (#33).
- ADR 0013 records Q32 (cable managers count against the 32U as a block under
  each switch, firewall or patch panel), Q33 (FOPP-96SM is 1U) and the L1
  switch selection rule (#25, #29); the device database and the UI design
  follow (#30, #32).
- `docs/agents.md`: the A11 desktop app role, ADR 0015 taken, Q32 and Q33
  resolved (#26, #35).
- Changelog, README and test READMEs for #14–#23, and the plan glossary (#17).
- M9 prototype reworked for projects and substations: project page with the
  document register and backup and share, a Network screen and a Panels board
  per substation (#23).
- The launcher's self-test fixture names a module that will never exist
  (#24).
- The installed app imports a double-clicked `.bomlib` through the library
  store and shows the change summary or the refusal; `.bomproj` files get a
  placeholder association; `BOMGEN_NO_DIALOGS=1` prints messages to stderr
  for unattended runs (M11, #15).
- `docs/agents.md` refreshed: merge order, next milestones, reserved ADR and
  open-question numbers (#13).
- Plan Q29 resolved: the example keeps the workbook's thermostat load and fan
  airflow; future library defaults use 0 W for the SK 3110 thermostat and
  460 m³/h for the SK 3243.100 fan with its outlet filter (#12).

[Unreleased]: https://github.com/alialyami90/BOM-generator/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/alialyami90/BOM-generator/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/alialyami90/BOM-generator/releases/tag/v0.1.0
