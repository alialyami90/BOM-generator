# 0026. Device nameplates

- Status: Accepted (Ali, 2026-10-31)
- Date: 2026-10-31
- Spec sections: Workbook map; How each panel BOM groups its materials (group H); Derivation rules (device nameplates); Inputs the tool needs (housekeeping kits); Output requirements (OUT-3); Data model and generation order (steps 9 and 12)

## Context

Ali decided on 2026-10-31 (relayed by A1) that each panel BOM gets one "Device nameplate"
commodity row whose quantity is the panel's tagged devices, every unit with a tag, DIN rail
included and L1/L2 switches one per unit, and that a new workbook sheet lists every plate's text
per panel. The text is the short tag the MCB rows already print (L2_ESW_A01). The spec's example
workbook has no nameplates (plan Q53).

## Decision

1. **Which units:** every group B unit whose tag is set, one per unit of a multi-quantity row.
   Kit children, housekeeping parts, MCBs, strips and loose items get none. A tag override is
   printed as written (the WS console's `SRV/OAS/EAS`, `MONITOR`, `Keyboard & Mouse`).
2. **Plate text:** `engine.tags.short_tag`, the one function the DC and AC branch rows also use.
3. **Row:** the last row of group H, after the busbars, so no other row, SR.NO, merge or Power
   Consumption reference moves. Quantity is the plate count; make, model and ordering code come
   from the part; no tag, no HWIO, no power line. A panel without tagged units has no row.
4. **Part:** a new optional housekeeping role `catalogues.housekeeping.nameplate` (also on
   `catalogue_brands.housekeeping`), so the part follows the housekeeping brand choice (ADR 0017).
   Unset: no row and no sheet. The part is a plain `accessory`. The example and shipped libraries
   use NAMEPLATE-0828805, Phoenix Contact US-EMLP (60X30), ordering code 0828805, researched by
   A4 with its device-database record (`data/device-db/housekeeping.yaml`).
5. **Sheet:** "Nameplates" (`output.sheet_names.nameplates`), after Loose Material and before
   Power Consumption, laid out and printed like a panel BOM under the first panel's document:
   SR.NO, PANEL (cabinet number), PLATE TEXT, DEVICE (the group B description). Written only when
   some panel has plates. The app's Preview page data carries the plates per panel.

## Consequences

Golden values that move, all from the example library now naming the nameplate part:

- `tests/golden/expected_groups_e_h.py`: group H of each panel gains the nameplate row, psa1 and
  psa2 qty 11, psa3 qty 3, ws qty 3; cabinet 001 numbers 72 rows (was 71).
- `tests/golden/test_workbook.py`: the sheet list gains "Nameplates" after "Loose Material"; the
  WS console sheet prints A1:G46 (was G45); the formula count is 955 (was 924: 4 SR.NO formulas on
  the BOM sheets, 27 on the Nameplates sheet); new Nameplates sheet checks.
- `tests/golden/test_cli_build.py` sheet list and `tests/golden/test_revision_round_trip.py`
  table rows (72, 75, 63, 40).

The power and heat totals, airflow results, MCB counts and ratings, terminal quantities, HWIO
totals and the check report do not move. A revision rebuilt over an issue made before this change
marks the new row as revised, like any new row.
