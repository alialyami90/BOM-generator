# 0035. Issue sheets

- Status: Proposed
- Date: 2026-11-03
- Spec sections: Workbook map; Output requirements (OUT-3, OUT-5, OUT-7, OUT-8); Formatting

## Context

Ali's engineering workflow review (2026-11-03) asks for four outputs a SCADA engineer issues with
the BOM today by hand: a summary BOM for procurement, a spare parts list, a cable schedule and a
revision history. The agent implementation plan (Phase E, milestones M63 to M66) adds them as
workbook sheets and reserves this ADR for the sheet set: their order, columns and when each is
written. OUT-3 fixes today's sheet order and the Workbook map lists today's sheets; neither has
these four.

Plan rule 4 says golden values don't move unless an ADR says so. A sheet written in every
workbook would move `tests/golden/test_workbook.py` (sheet list, formula count) and
`tests/golden/test_cli_build.py` (sheet list).

## Decision

1. **Four optional sheets, after Heat Calculations, in this order:** Summary BOM, Spare Parts,
   Cable Schedule, Revision History. Names are configurable as new `output.sheet_names` keys
   `summary_bom`, `spare_parts`, `cable_schedule`, `revision_history`, defaults as written above.
2. **When each is written.**
   - *Summary BOM:* when the substation asks for it in `output.include` (new, a set of
     `summary_bom`, `spare_parts`, `cable_schedule`, `revision_history`). Unset means today's
     workbook: no summary. The Build page has a checkbox per optional sheet and saves the choice.
   - *Spare Parts:* when the spares policy (M64, design basis) yields any line or the substation
     has spare overrides or extras, and `output.include` doesn't leave it out.
   - *Cable Schedule:* when any loose material row carries cable data (M65), and `output.include`
     doesn't leave it out.
   - *Revision History:* when the substation has at least one recorded issue or the document has
     prepared, checked or approved names (ADR 0036), and `output.include` doesn't leave it out.
   So the example, with none of these inputs, builds today's workbook and golden values don't
   move.
3. **Layout.** Each sheet uses the BOM header and footer under the substation's main document
   (`substation.document`), A4, Calibri and the calculation-sheet table styles, page-break
   preview, repeating title rows. Columns:
   - *Summary BOM* (landscape): SR.NO, DESCRIPTION, QUANTITY, MAKE, MODEL, ORDERING CODE, WHERE
     USED. One line per (make, model, ordering code) across every panel and the loose material;
     free-text loose items group by description; a "1 Lot" or other text quantity stays its own
     line. WHERE USED lists `sheet: tag (qty)` per source, e.g. `001: PSA1-L1-ESW-A11 to A16 (6)`.
   - *Spare Parts* (landscape): SR.NO, DESCRIPTION, INSTALLED QTY, SPARE QTY, MAKE, MODEL,
     ORDERING CODE, BASIS (the rule text, e.g. "10% of 27, min 1 = 3").
   - *Cable Schedule* (landscape): SR.NO, FROM, TO, TYPE, LENGTH, QTY, MAKE, MODEL, ORDERING CODE.
   - *Revision History* (portrait): REV, DATE, DESCRIPTION, PREPARED, CHECKED, APPROVED; one row
     per recorded issue, then the current revision when it isn't recorded yet.
4. **Live formulas (OUT-5).** SR.NO is a formula as on the BOM sheets. A Summary BOM quantity is a
   formula summing the source BOM quantity cells (`='1'!D12+'2'!D12`); Spare Parts INSTALLED QTY
   references the Summary BOM quantity when that sheet is written, else is the summed value.
5. **Revision comparison (OUT-8)** stays on the BOM and Loose Material tables. The four new sheets
   are not compared or highlighted; a changed quantity shows on the BOM sheet it comes from.
6. **CSV.** After a build the app can export the Summary BOM as CSV (UTF-8 with BOM, the sheet's
   columns, quantities as values) for procurement systems.
7. **Spec.** Each milestone adds its own sheet's row to the Workbook map and its name to OUT-3's
   order, in its PR, with Ali's go-ahead: M63 adds "then Summary BOM when `output.include` names
   it (ADR 0035)". The spares percentage (Q65) and cable lengths (Q66) are asked when M64 and M65
   start.

## Consequences

- The workbook stays the one issued file; procurement, spares and cables read from the same build
  as the BOM, so they can't drift from it.
- Opt-in for the Summary BOM keeps every golden value; a project that wants it ticks one box once.
  Each sheet gets its own golden test from a second example input, never by editing gis01.
- The summary sums across sheets with formulas, so a hand edit to a BOM quantity in Excel carries
  through; a formula per line references up to one cell per panel, which is fine at this size.
- Four more sheet names to keep unique and within Excel's 31 characters; the existing
  `ExcelSheetName` check and the duplicate-name check cover them.
