# BOM-generator (`bomgen`)

Generates the Substation SCADA / PSA Bill of Materials workbook (.xlsx): one BOM
sheet per cabinet plus the Power Consumption, Heat Dissipation and Heat
Calculations sheets, with live formulas, the specified formatting and print
setup, and page headers/footers.

- **Spec (source of truth):** [`docs/spec/generator-spec-v2.md`](docs/spec/generator-spec-v2.md)
- **Plan, milestones, open questions:** [`docs/plan.md`](docs/plan.md)
- **Design decisions:** [`docs/decisions/`](docs/decisions/)
- **Team:** the agents building the project and who owns what are in
  [`docs/agents.md`](docs/agents.md)
- **Changes:** [`CHANGELOG.md`](CHANGELOG.md)

## Status

Done:

- M0 (repository, spec, plan, CI) and M1 (input models, YAML loader, JSON
  Schemas, `examples/`, `bomgen validate`).
- M1b: projects that hold substations (ADR 0012), with the sizing and layout
  inputs of each substation (ADR 0013); `examples/` is one project with one
  substation.
- M1c: switch sizing and automatic panel layout (ADR 0013). `bomgen layout`
  sizes the L1 and L2 switches from the IED count and spares and writes the
  generated panel files; the example substation gives 3 L1 switches per side.
- M2: BOM groups A–D (enclosure, devices and tags, kit children, network
  accessories, housekeeping) and the loose-material table, as engine output;
  ADR 0014.
- M3: BOM groups E–H (AC and DC distribution, terminal strips, grounding),
  HWIO, assembly with separators and revision marks; the engine now builds
  every BOM group of the example cabinets.
- M4: power and heat. Power Consumption lines and blocks per cabinet plus the
  external equipment, heat dissipation, forced-ventilation airflow, the
  natural-convection rise and the line-up check; a panel with ventilation
  `auto` gets filters or fans from the heat check (plan Q4).
- M5: sheet models filled from the engine. One BOM sheet per cabinet and the
  Power Consumption, Heat Dissipation and Heat Calculations sheets, with live
  formulas that a golden test recalculates to the spec's totals.
- M6: the XlsxWriter workbook writer.
- M7: `bomgen build` writes one workbook per substation with its check report
  (ADR 0016), and `--compare` marks the cells changed since the previous issue
  (OUT-8).
- M8 and M8b: device-library update packages (`bomgen library …`) and project
  sharing and backup as `.bomproj` files (`bomgen project …`).
- M9: UI design and clickable prototype in [`docs/ui/`](docs/ui/README.md),
  reworked for projects, substations and the panels board.
- M10: the Windows desktop app, a pywebview window showing the approved UI
  through a Python bridge (ADR 0015), with the polish pass done (M10e).
  - Home lists the workspace's projects and recently opened folders; the
    Project page shows a project with export, backup, import (Keep both on a
    clash) and restore.
  - The Library screens browse the installed library with its device-database
    records, review and run a `.bomlib` import, and switch versions.
  - A substation's Settings, Network (inputs, result and L1 ranking) and the
    Panels board of the generated panels.
  - Checks, Preview and Build show the check report and every sheet as the
    engine computes it, and write the workbook.

  Projects and substations are read-only in the app until the project and
  substation writers exist: edit the YAML files, then open the project again.
- M11, built early (ADR 0009): the Windows installer and tag-driven releases.
  The installed app opens the desktop window, double-clicking a `.bomlib`
  imports it, and a `.bomproj` opens the app on that project.

Next: the project and substation writers, so the app can create and edit
projects and substations; not yet planned as a milestone. Who builds what is in
[`docs/agents.md`](docs/agents.md); the terms project, substation, side and
stream are defined in `docs/plan.md` → "Glossary".

To install the Windows app, see [`docs/install.md`](docs/install.md).

## Usage

A project is a folder: `project.yaml` (project info, library name and
version, document register, defaults, list of substations), a device library,
and one folder per substation under `substations/<id>/` with its
`substation.yaml` and `panels/`. See `docs/plan.md` → "Input file schemas" and
[`examples/`](examples/).

```bash
bomgen validate examples/project.yaml                        # the whole project
bomgen validate examples/substations/gis01/substation.yaml   # one substation
bomgen build examples/project.yaml                           # one workbook per substation, into out/
bomgen build examples/project.yaml --substation gis01 --out build/
bomgen build examples/project.yaml --substation gis01 --compare issued/Rev01.xlsx
bomgen schema                                                # write JSON Schemas to schemas/
```

`validate` builds nothing. It prints `OK:` with the substation, panel and part
counts, or each error with its file and path. `build` validates the same way,
then writes each substation's workbook, named from its document number and
revision (for the example, `VD-EL0009-861GISPSA-001_PSA_BOM_Rev02.xlsx`), and
prints its path and the check report (SFPs, DC mains, airflow, DI capacity).
The report is also written next to the workbook as `<name>.checks.json`, and a
failed check makes `build` exit 1 (`--no-checks` skips it). `--out` picks the
folder (default `out/`, git-ignored), `--substation` builds one substation of
a project, and `--compare` marks the cells changed since a previously issued
workbook (one substation at a time). An existing workbook is replaced only
once the new one is written, so a failed build keeps the old one. The JSON Schemas in
[`schemas/`](schemas/) let an editor check the YAML as you type (ADR 0010); a
test fails if they drift from the models, so run `bomgen schema` after changing
a model.

### Switch sizing and panel layout

`bomgen layout` sizes the L1 and L2 switches from the substation's equipment
and spares and lays out the 32U panels (ADR 0013). From the project folder:

```bash
bomgen layout --substation substations/gis01/substation.yaml --out out/layout   # look first
bomgen layout --substation substations/gis01/substation.yaml                    # write panels/
```

It prints the IED count, the switches per side and each panel's fill, then
any problems. Without `--out` it writes `panels/*.yaml` marked
`generated: true` and updates the `panels:` list in `substation.yaml`; it
refuses to overwrite hand-written panel files unless you pass `--force`. Once a
substation's panels are generated, `bomgen build` lays them out again before
each build (`--no-layout` builds the files as they are) and stops on layout
errors.

After a layout the annunciator is fed from panel 001, side A
(`fed_from: psa1` in its loose-material entry). `examples/` keeps its
hand-written panels and `fed_from: psa3` for the spec's values, so a layout of
it reports that psa3 is no longer written; on a copy with `fed_from: psa1`,
`bomgen layout --force` gives 3 L1 switches per side.

### Device-library update packages

A `.bomlib` package carries a device library to every installed copy
(ADR 0008). Libraries are installed per user, under `%LOCALAPPDATA%\bomgen\libraries`
on Windows and the XDG data directory elsewhere (override with
`BOMGEN_LIBRARY_HOME`).

```bash
bomgen library pack examples/library.yaml --name psa-devices --version 1.0.0
bomgen library import psa-devices-1.0.0.bomlib --dry-run   # show the part diff only
bomgen library import psa-devices-1.0.0.bomlib             # verify, install, activate
bomgen library list                                        # installed versions
bomgen library rollback psa-devices                        # back to the previous version
```

`pack --add data/device-db` includes the researched device database
([`data/device-db/`](data/device-db/README.md)) as reference data: pack checks
its records and import installs them with the library, for the app to show next
to the library's parts. The generator never builds from them.

### Sharing and backing up projects

A project (ADR 0012) travels as one `.bomproj` file: the project folder plus a
manifest with checksums and the library version it was built with.

```bash
bomgen project export examples/project.yaml    # writes jfgp2-pkg3.bomproj (the project id)
bomgen project import jfgp2-pkg3.bomproj       # unpacks into the workspace
bomgen project import jfgp2-pkg3.bomproj --rename-to jfgp2-pkg3-2   # keep both
bomgen project backup examples/project.yaml    # saves into examples/Backups/ (git-ignored)
```

Export leaves out `out/` and `Backups/`. The workspace is `BOMGEN_WORKSPACE`,
or `Documents/BOM Generator` in your home folder, unless `--workspace` names
one. Import refuses to replace a project with the same id unless you pass
`--force`, and then it backs the old one up first; `--rename-to` imports it
under a new id instead and keeps the existing project. If the project's library
version is not installed, import names the `.bomlib` to install.

## Development

Requires Python 3.12.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

ruff check . && ruff format --check .   # lint + format
mypy                                    # type-check (strict)
pytest                                  # tests
```

Working rules (TDD, one milestone per PR, conventional commits, never commit
generated .xlsx files) are in [`CLAUDE.md`](CLAUDE.md).

## CI

GitHub Actions runs lint, type-check and tests on pull requests and pushes to
`main`, and skips them for docs-only changes. Make **`ci-status`** the only
required status check; it always reports. Details in
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) and ADR 0006.
