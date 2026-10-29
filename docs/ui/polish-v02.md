# v0.2 polish findings

The impeccable polish and audit pass over the app screens that are new since v0.1, as CLAUDE.md asks
at the end of M10. The M10e pass (v0.1 screens) is in project files `ui/m10e-polish-findings.md`.

- **What was checked:** the real app on origin/main `de69ec0`, run in Chromium against the Python
  `Api` with the example project and the shipped `psa-devices-1.0.0.bomlib`, at 1280×800, light
  theme with dark spot checks. Screens: Project (Overview, Substations, Documents), substation
  Settings (General, Documents, Output, Design constants), Network (Equipment rows, Change…),
  Library (Devices with Edit, Add, Delete) and the device editor (all six tabs, dirty and invalid
  states), and Loose material.
- **Detector:** `impeccable detect --json` returns `[]` on `src/bomgen/app/ui` and on
  `docs/ui/prototype`.
- **Who fixes what:** **App** is an app fix. **Doc** is a design-doc change; the doc changes are in
  the same PR as this file. Ranked most important first. Do 1–12; 13–16 are optional if cheap.

## Fix first

1. **Unsaved edits are painted with the workbook's revision yellow.** *App; Doc (done).*
   - Where: Project › Documents cells, Settings › Documents, Loose material cells, and the whole
     input on device editor fields (`.changed`, `.field.changed`).
   - Why it matters: `#FFFF00` exists only to show what the workbook will highlight as revised
     (design-language "Colour"; `tokens.json`, `highlight.yellow`). On a form it reads as
     "revised", and in dark theme it is a glaring block.
   - The #146 review pointed the app at `td.changed`; that was a mistake.
   - Fix: use the new **Changed marker** in `components.md` (a warning dot before the label or at
     the start of the cell, plus sr-only "changed"). Keep `.changed` yellow for Preview's revised
     cells only.
2. **Raw model errors on library list fields.** *App.*
   - What happens: *Add* on Child parts shows "String should match pattern
     '^[A-Za-z0-9][A-Za-z0-9._+-]*$'" at once, before anything is typed.
   - Fix the message: map pattern and type errors to words ("Pick a part from the library."; see
     editing.md "Validation").
   - Fix the timing: an empty new row is marked on the first save attempt, not on Add.
   - Fix the line: the error has no gap between icon and text and does not line up with the
     table. Use the same `.err` layout as the fields.
3. **Enum values shown as labels.** *App; Doc (done).*
   - Examples: Load type "CONTINUOUS"; Research status "partial", while the Library table says
     "Partial"; Mounting "rack"; Terminals › Per "serial_port", which is also clipped.
   - Fix: map each choice to a label, the way `catName` already does for categories.
4. **Network › Equipment: the Role select is clipped** ("Fibre pat", "L2 switch" cut).
   *App.* Give the column a minimum of 150px; the A and B column can be narrower.

## Then

5. **Number inputs without a unit are left-aligned**, while those with a unit are right-aligned.
   *App.*
   - Examples: HWIO points, Digital inputs and Fibre cores in the device editor; Spare SFPs and
     Spare AC branches on Network and on Project › Shared defaults.
   - The figures zig-zag down the form. Right-align every number input with tabular figures.
6. **Save bar, invalid state.** *App; Doc (done).*
   - "1 field needs fixing" is a separate ghost button with a gap before "before you can save.",
     so it reads as two fragments.
   - Make the sentence one control (components.md "Save bar").
7. **Settings › General, Catalogue brands.** *App.*
   - Six selects read "Same as the project (Library default)", and the DC one is clipped ("…(as
     the AC branch").
   - Name the resolved brand, as editing.md has it: "Same as the project (ABB S200)". For DC, use
     "Same as AC branches".
8. **Device editor › Datasheet.** *App; Doc (done).*
   - Its Height duplicates Ports and mounting › Height, which has a different meaning. Label it
     "Height in the datasheet", with the help text in editing.md.
   - *Power input* is one line and clips the datasheet text. Make it a two-column textarea.
9. **Settings › Documents.** *App.* The register select clips the document number
   ("VD-EL0009-861GISPSA-0…"), and the next column shows it anyway. Make the option label the
   register key alone.
10. **Project › Documents (register).** *App.*
    - Drop the mono key repeated under the key input.
    - Put *Confirm* on the same line as the *Assumed date* badge, so a row is two lines, not three.
    - Inside a substation group, drop the "gis01:" prefix in Used by.
    - Banner grammar: "The issue dates of 3 documents are assumed."
11. **Network › Equipment rows are three lines** because *Change…* has its own line. *App.* Put
    *Change…* at the end of the part-id line.
12. **Loose material wording, left open from #146.** *App.* Use this exact text:
    - Table foot: **"Quantity is a whole number, or 1 Lot."** It now reads "Quantity: A whole
      number, or 1 Lot."
    - The free-text dialog's banner: **"A free-text item has no part, so the sheet shows no
      ordering code, make or model for it, and it cannot be fed from a cabinet. An item that
      needs power must be added to the library first."** It now ends "Add the part to the
      library to get them."

## Optional

13. **Design constants:** the Default column says "Default" on every unchanged row. *App.* Leave
    it empty there, and keep "Changed from 125" with Reset on changed rows.
14. **Row delete icons:** action blue on Network, Loose material and the device editor lists, but
    muted on Project › Documents. *App.* Use one style everywhere: muted, danger on hover.
15. **A dialog survives a route change.** *App.* With Change part… open, Back (or any hash change)
    shows the next page with the old dialog still over it. Close the overlay on `hashchange`.
16. **Project page header.** *App.* The folder path wraps mid-word over two lines, and it is also
    in the status bar. *New substation…* sits alone on a band above the tabs. Truncate the path to
    one line with a `title` tooltip, and put the page action on the title row.

## Checked and fine

- Loose material layout and behaviour after #146 and #201 (wording aside, item 12).
- The In use banner and the Delete dialog wording.
- The pending bar.
- Change part… (the dialog itself).
- The Output tab's Result line.
- The Library table's neutral *Partial* badge.
- Focus rings.
- The device editor's leave dialog.

No token changes.
