# 0020. Loose material on its own sheet

- Status: Accepted (Ali, Q36, 2026-10-28)
- Date: 2026-10-28
- Spec sections: Workbook map (sheets Aux and 4); How each panel BOM groups its
  materials ("Loose material"); Power Consumption sheet (item 4); Formatting
  (loose-material title row); Output requirements (OUT-3)

## Context

The spec puts the loose-material table on the WS console's BOM sheet. It sits under
the console's rows and has its own grey title block and header row ("Workbook map",
"How each panel BOM groups its materials", "Formatting"). OUT-3 repeats this: "loose
material as a second table on the WS console sheet". M5 built it that way, using the
substation's `loose_material.host_panel` to choose the sheet.

Ali's v0.2 feedback (backlog point 6) asks for loose material to stand on its own. On
2026-10-28 Ali answered Q36 with "Its own sheet". That answer overrides the spec
sections above until the spec is updated.

## Decision

1. The loose-material table goes on its own sheet, "Loose Material" by default. Its
   name is set with `output.sheet_names.loose_material`, like the calculation sheets.
   The sheet is written only when the substation has loose material.
2. Sheet order is the cabinet BOM sheets in panel order, then Loose Material, then
   Power Consumption, Heat Dissipation and Heat Calculations.
3. The sheet uses the panel BOM layout and styles:
   - the grey title block merged over A:G in row 1, with the header row in row 2;
   - the lines from row 3, with SR.NO from 1;
   - the hidden HWIO column H with its `SUM` in H1;
   - the same print setup: A4 portrait, one page wide, BOM margins, rows 1–2
     repeated, print area A1:G<last>.
   The WS console sheet keeps only the console's own table.
4. The header and footer are the BOM sheets' header and footer, with "Bill of Materials
   for <sheet name>" as the second line. The document number, revision and date come
   from `loose_material.host_panel`'s document. `host_panel` therefore now names the
   document the loose material is issued under, no longer the sheet it is printed on.
5. Live references follow the rows. Power Consumption's "External Equipment" block
   points at the Loose Material sheet (`='Loose Material'!C4` and so on).
6. Revision comparison (OUT-8, ADR 0016) compares the loose rows with the previous
   issue's Loose Material sheet. A previous issue from before v0.2 has no such sheet,
   so the comparison falls back to the second table on the host panel's sheet, where
   v0.1 printed it.

## Consequences

- The WS console sheet is shorter and prints alone, and the loose list can be issued
  and revised separately from the console's BOM.
- Workbooks no longer match the spec's sheet 4 or OUT-3 until the spec is updated.
  The goldens that cite those sections now cite this ADR.
- `host_panel` stays required, so existing substation files load unchanged. It still
  chooses the header document, and the engine still uses it to validate input.
- Showing and editing the list in the app (Preview and the substation editor) is M18's
  app side (A11) and is not part of this change.
