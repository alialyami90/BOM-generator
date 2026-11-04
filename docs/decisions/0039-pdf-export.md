# 0039. PDF export of the issued sheets

- Status: Accepted (Ali, 2026-11-04, Q73: both, built-in by default)
- Date: 2026-11-04
- Spec sections: Output requirements (OUT-1, OUT-6, OUT-7)

## Context

Review step 11 (plan M78): an issued BOM goes out as a PDF too, and today the engineer prints
the workbook to PDF by hand. Rendering a workbook exactly needs Excel. A built-in renderer
works on any PC and in the tests, but its pages are only close to Excel's. Q73 asked which to
use; Ali chose both, with the built-in renderer as the default.

## Decision

1. **Source.** *Export PDF* renders the workbook that was written, not the inputs. Both
   renderers then print the same issued file, revision highlights included. Each formula shows
   the result written with it (OUT-5).
2. **Built-in renderer (default).** `bomgen.pdf.render_pdf` reads the workbook with openpyxl
   and draws the chosen sheets with ReportLab, a new runtime dependency (BSD licence, pure
   Python). It follows each sheet's OUT-7 print settings: paper size, orientation,
   fit-to-width or scale, margins, print area and repeated title rows. It also keeps the column
   widths, row heights, merges, fills, fonts, borders, alignment and wrapping, the header and
   footer text with page numbers, and leaves out hidden columns and sheets. Header and footer
   pictures (the logo) are left out.
3. **Excel on the PC.** On Windows with Excel installed, the engineer can choose *Use Excel*
   for exact pages. `bomgen.pdf.excel_pdf` runs Excel through PowerShell's COM bridge, selects
   the chosen sheets and calls `ExportAsFixedFormat`, so no pywin32 is needed. Elsewhere the
   choice is disabled with its reason.
4. **The app.** After a build, the Build page has *Export PDF…*: the workbook's sheets, all
   ticked, and the renderer. It writes `<workbook name>.pdf` next to the workbook and asks
   before replacing one.

## Consequences

- Any PC gets a PDF without Excel. Its page breaks and fonts can differ slightly from Excel's,
  and the dialog says so.
- The Excel path can't run in CI. Its tests check the script it builds and its refusals, so a
  change in Excel's COM interface would only show on a Windows PC.
- ReportLab joins the installer's dependencies.
