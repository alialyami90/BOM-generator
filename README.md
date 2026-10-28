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
- M2: BOM groups A–D (enclosure, devices and tags, kit children, network
  accessories, housekeeping) and the loose-material table, as engine output;
  ADR 0014.
- M6: sheet models and the XlsxWriter workbook writer.
- M8 and M8b: device-library update packages (`bomgen library …`) and project
  sharing and backup as `.bomproj` files (`bomgen project …`).
- M9: UI design and clickable prototype in [`docs/ui/`](docs/ui/README.md),
  reworked for projects, substations and the panels board.
- M10a: the desktop app shell, a pywebview window showing the approved UI
  through a Python bridge (ADR 0015); its screens still show the prototype's
  example data.
- M11, built early (ADR 0009): the Windows installer and tag-driven releases.
  Double-clicking a `.bomlib` imports it; the installed app does not open the
  window or a `.bomproj` yet.

Next: M1c (switch sizing and automatic panel layout, `bomgen layout`), M3–M4
(groups E–H, HWIO, power and heat), M5 (sheet models filled from the engine)
and the remaining M10 screens. `bomgen build` arrives with them. Who builds
what is in [`docs/agents.md`](docs/agents.md); the terms project, substation,
side and stream are defined in `docs/plan.md` → "Glossary".

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
bomgen schema                                                # write JSON Schemas to schemas/
```

`validate` builds nothing. It prints `OK:` with the substation, panel and part
counts, or each error with its file and path. The JSON Schemas in
[`schemas/`](schemas/) let an editor check the YAML as you type (ADR 0010); a
test fails if they drift from the models, so run `bomgen schema` after changing
a model.

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
([`data/device-db/`](data/device-db/README.md)) as reference data.

### Sharing and backing up projects

A project (ADR 0012) travels as one `.bomproj` file: the project folder plus a
manifest with checksums and the library version it was built with.

```bash
bomgen project export examples/project.yaml    # writes jfgp2-pkg3.bomproj (the project id)
bomgen project import jfgp2-pkg3.bomproj       # unpacks into the workspace
bomgen project backup my-project/project.yaml  # saves into my-project/Backups/
```

Export leaves out `out/` and `Backups/`. The workspace is `BOMGEN_WORKSPACE`,
or `Documents/BOM Generator` in your home folder, unless `--workspace` names
one. Import refuses to replace a project with the same id unless you pass
`--force`, and then it backs the old one up first. If the project's library
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
