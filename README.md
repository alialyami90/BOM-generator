# BOM-generator (`bomgen`)

Generates the Substation SCADA / PSA Bill of Materials workbook (.xlsx): one BOM
sheet per cabinet plus the Power Consumption, Heat Dissipation and Heat
Calculations sheets, with live formulas, the specified formatting and print
setup, and page headers/footers.

- **Spec (source of truth):** [`docs/spec/generator-spec-v2.md`](docs/spec/generator-spec-v2.md)
- **Plan, milestones, open questions:** [`docs/plan.md`](docs/plan.md)
- **Design decisions:** [`docs/decisions/`](docs/decisions/)
- **Project state and next steps:** [`docs/handoff/`](docs/handoff/)
- **Changes:** [`CHANGELOG.md`](CHANGELOG.md)

## Status

v0.3.3 is released ([`CHANGELOG.md`](CHANGELOG.md)). The rest of the v0.3
roadmap, M35 to M47 in `docs/plan.md`, is on `main` for the next release.

Done in v0.1:

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

  Since v0.2 projects, substations, panels and the library are edited in the
  app (M16–M18, below).
- M11, built early (ADR 0009): the Windows installer and releases from
  `main` when a merged PR bumps the version
  ([`packaging/README.md`](packaging/README.md)).
  The installed app opens the desktop window, double-clicking a `.bomlib`
  imports it, and a `.bomproj` opens the app on that project.

Done in v0.2 (Ali's feedback on v0.1.0, tracked in
[`docs/backlog.md`](docs/backlog.md); milestones in `docs/plan.md` →
"M12–M18 (v0.2)"):

- M12: a cable manager sits directly against the next device; the
  blank-plate gap is only between two active devices.
- M13: alternatives are library parts (`alt_group`, `tier`), and further MCB
  brand sets are chosen per project or substation with `catalogue_choice`
  (ADR 0017); the DC branches can use their own DC-rated set with
  `catalogue_choice.mcb_dc` (ADR 0023). The Library screen shows the
  catalogues.
- M14: the installer ships psa-devices 1.1.0 from `data/library/`, with the
  researched alternatives as parts, DC-rated MCB brand sets and the originals'
  datasheet figures (plan Q37, Q38).
- M15: branch MCBs sized from each device's running and inrush current
  (ADR 0019), with DC float-voltage checks.
- M16: library editing in the app and on the command line: the device editor
  with its Datasheet and Alternatives tabs, local versions (`+local.N`) with
  `.bomlib` backups, and CSV export and import for Excel (ADR 0018).
- M17: create, rename, edit and delete projects and substations in the app:
  project and substation settings, Network inputs and equipment rows, the
  document register, and the Panels board's drag and drop, pins, deletes,
  undo and keyboard moves (ADR 0021).
- M18: loose material on its own sheet and Preview tab (ADR 0020), with
  free-text items and the app's Loose material page (ADR 0022).

Done in v0.3 (Ali's request to replace the Network section with part picking;
milestones in `docs/plan.md` → "M19–M24 — Part picking, panel priority and
preview"):

- M19: the Panels board drags with pointer events, and hand-written panels
  can be laid out.
- M20: an equipment row can override its part's values, carry a BOM part
  number and choose its SFPs, as derived parts (ADR 0024).
- M21: generated panels stack devices by priority, with a KVM or console at
  waist height.
- M22 and M23: the Parts page replaces Network, with a cable manager switch
  per network device and the Device picker for long part lists.
- M24: the Device preview page draws each panel's front view and lists every
  unit with its U, branch MCBs and strips; units are pinned by dragging.
- M25: every AC-powered device gets its own AC branch MCB, and CINC carries
  them (ADR 0025).
- M26: device nameplates, one BOM row per panel and a Nameplates sheet
  (ADR 0026).
- The installer ships psa-devices 1.10.0: researched switches, firewalls,
  RTACs and a clock, Hager AC MCB sets, Hubbell fibre shelves and the
  nameplate part. 2.5G, 5G and
  25G ports are listed but never sized for SFPs (ADR 0027).
- v0.3.1: Settings and Parts open on a new, blank substation (they showed
  "StopIteration:" in 0.3.0).
- v0.3.2: a new substation works from its first parts to Build, the panel
  editor, L2 link inputs on Parts, an unsaved-changes prompt, larger fans for
  hot cabinets and Power Consumption fixes.
- v0.3.3: every device tag has level, type, side and number (L2_GPS_A01) with
  a duplicate-tag check (ADR 0030), larger Rittal fans in psa-devices 1.11.0
  (ADR 0029), and the console sheet's 53.1 pt header row.

On `main` for the next release (the v0.3 roadmap, M35 to M47):

- M35: the spec's "Automatic panel layout" section.
- M36: Library › Catalogues edits every brand set: MCBs, aux contacts,
  terminal blocks, busbars and housekeeping.
- M37: Settings › YAML can be edited and applied to the form, and the design
  constants show their defaults.
- M38: Add a device offers a monitor and a keyboard and mouse, the rail shows
  "Not set up" on Parts, and a generated panel's Enclosure tab edits the
  panel numbering.
- M39: the app reloads a project file changed on disk, Home restores a
  deleted project, and F6 and Ctrl+O work.
- M41 to M44: psa-devices 1.15.0, with the alternatives' own power, inputs
  and descriptions, and tags for the contractor's switches, firewalls and
  fibre shelves.
- M45: an annunciator row goes to loose material with its wall-mount kit,
  and an `untagged_device` check warns for a networked device with no tag.
- M47: an edited panel-numbering pattern is no longer marked ASSUMED.

The terms project, substation, side and stream are defined in `docs/plan.md` →
"Glossary".

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
bomgen library pack data/library/psa-devices.yaml --name psa-devices --version 1.15.0
bomgen library import psa-devices-1.15.0.bomlib --dry-run   # show the part diff only
bomgen library import psa-devices-1.15.0.bomlib             # verify, install, activate
bomgen library list                                        # installed versions
bomgen library rollback psa-devices                        # back to the previous version
bomgen library export psa-devices                          # back up the active version as a .bomlib
```

`pack --add data/device-db` includes the researched device database
([`data/device-db/`](data/device-db/README.md)) as reference data: pack checks
its records and import installs them with the library, for the app to show next
to the library's parts. The generator never builds from them.

To edit a library in Excel (ADR 0018), export it as CSV tables, edit them and
import them again. The import is saved as a local version of the one it came
from (for example `1.1.0+local.1`) and activated; the release version stays
installed.

```bash
bomgen library export-csv psa-devices                      # writes psa-devices-1.15.0-csv.zip
bomgen library export-csv psa-devices --out csv/           # or one .csv file per table
bomgen library import-csv psa-devices csv/ --dry-run       # every check and what would change
bomgen library import-csv psa-devices csv/ --notes "new SEL alternatives"
```

The tables are UTF-8 with a byte order mark, so Excel opens them as written;
`--tables devices` or `--tables catalogues` exports one group. The import
reads files Excel saved with semicolons and decimal commas, warns about a cell
that starts like a formula, and refuses rows with a problem unless you pass
`--skip-invalid`.

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
