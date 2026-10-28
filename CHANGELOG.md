# Changelog

All notable changes to this project are listed here, one entry per merged pull
request; a milestone split across several PRs gets one entry. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project will use [Semantic Versioning](https://semver.org/) from its first
tagged release.

## [Unreleased]

### Added

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
