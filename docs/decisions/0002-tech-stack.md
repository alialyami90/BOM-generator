# 0002. Tech stack: Python 3.12, pydantic, YAML, typer

- Status: Accepted (set by the project brief)
- Date: 2026-10-28
- Spec sections: Inputs the tool needs; Data model and generation order

## Context

The brief fixes the stack and asks for proposals before deviating.

## Decision

- Python 3.12, `src/` layout, package `bomgen`, built with hatchling.
- Inputs are YAML files validated into `pydantic` v2 models (device library,
  panels, project settings).
- CLI with `typer`: `bomgen build --project project.yaml --out out.xlsx` and
  `bomgen validate`.
- `pytest` for tests, `ruff` for lint and formatting, `mypy --strict`.
- The .xlsx writer library is decided separately in ADR 0003.

## Consequences

Pydantic gives schema validation and error messages for free, and its JSON
Schema export can back editor completion for the YAML files and a future UI.
