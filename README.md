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

Milestones M0 (repository, spec, plan, CI) and M1 (input models, YAML loader,
JSON Schemas, `examples/`, `bomgen validate`) are done. The rule engine, sheet
models and Excel writer (M2–M7) come next; `bomgen build` arrives with them.
An installable Windows desktop app with shareable device-library update
packages follows (see the plan, M8–M11).

## Usage

Inputs are three YAML sets (device library, panel definitions, project
settings); see `docs/plan.md` → "Input file schemas" and
[`examples/`](examples/).

```bash
bomgen validate --project examples/project.yaml   # check the inputs, build nothing
bomgen schema                                     # write JSON Schemas to schemas/
```

`validate` prints `OK:` with the panel and part counts, or each error with its
file and path. The JSON Schemas in [`schemas/`](schemas/) let an editor check
the YAML as you type (ADR 0010); a test fails if they drift from the models, so
run `bomgen schema` after changing a model.

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
