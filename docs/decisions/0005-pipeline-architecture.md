# 0005. Pipeline: rule engine → sheet models → thin writer

- Status: Accepted (Ali, 2026-10-28)
- Date: 2026-10-28
- Spec sections: Data model and generation order; Relationships between sheets

## Context

The spec's generation order has 15 steps: derivation rules (steps 1–11), sheet
generation and headers (12–13), file writing (14) and a check report (15). The
calculation sheets must reference BOM cells with live formulas (OUT-5), so the
cell address of every BOM row must be known before the calculation sheets are
laid out.

## Decision (proposed)

Three layers, each testable on its own:

1. **Engine** (`bomgen.engine`): pure functions over pydantic models that
   produce `BomLine`s per panel, `PowerLine`/`HeatLine`s and heat-check results.
   Python computes every number too, so rules and golden values are tested
   without Excel.
2. **Sheet models** (`bomgen.sheets`): lay out each sheet as a grid of cells
   (value or formula, style token), merges, column widths, row heights, print
   setup and header/footer. Formulas are built from the resolved addresses of
   the source rows, e.g. `='1'!C8`.
3. **Writer** (`bomgen.writer`): translates sheet models to .xlsx. No business
   rules live here.

## Consequences

Engine tests stay fast and readable; writer tests only check translation. The
CLI and the Windows desktop app (ADR 0007) are both thin callers of the same
pipeline, so they always produce the same workbook. The
heat check's ventilation choice feeds back into groups D, E and G, so the
engine resolves ventilation before building those groups (see plan, step 4).
