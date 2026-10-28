# 0004. One BOM sheet per cabinet with a hidden HWIO column

- Status: Proposed (resolves a spec ambiguity; needs Ali's confirmation)
- Date: 2026-10-28
- Spec sections: Workbook map; Output requirements (OUT-3, OUT-4); Formatting → Panel BOM sheets

## Context

"Workbook map" describes hidden master sheets (Panel 1–3, Aux) plus visible
issued copies (1–4). "Output requirements" OUT-3/OUT-4 and "Data model and
generation order" ask for one BOM sheet per cabinet carrying the HWIO column
hidden, "so no separate master sheets are needed".

## Decision (proposed)

Follow OUT-3/OUT-4: one visible BOM sheet per cabinet, column H (HWIO) hidden,
H1 = `SUM(H3:Hn)`. Power Consumption references these sheets directly. Use the
issued-sheet formatting (title row height 90). Sheet names are configurable;
defaults are `1`, `2`, `3`, `4` as in the example's issued sheets.

## Consequences

No copy step and no risk of masters and issued sheets drifting apart. If Ali
prefers the master + copy layout, the writer can emit both from the same sheet
model; only sheet naming and Power Consumption references change.
