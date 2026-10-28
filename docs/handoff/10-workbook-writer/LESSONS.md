# Role 10 — lessons and small decisions (append-only)

## Decisions too small for an ADR

- **Formula plus cached result.** Every computed cell is `Formula(text, result)`; the writer stores the result so the file shows numbers before Excel recalculates (OUT-5). Rejected: formulas without results (blank in viewers, untestable without Excel).
- **Header size code before font code** (`&28&"Calibri,Bold"`), so text starting with a digit isn't read as part of the size. `&` in text is escaped as `&&`.
- **Calc-sheet header size** = largest size ≤ 20 pt whose three lines, scaled by the print scale, fit between header and top margins (`fitting_size`, plan Q11). Rejected: fixed 20 pt (overlapped the table at 49 % scale).
- **Heat Dissipation C:D header stays merged**, as in the reference workbook (C4:D4); the spec table lists both in one row.
- **HWIO total is summed in the sheet** (`bom_sheet._table_sheet`): the engine has no HWIO total.
- **Cabinet with no powered device**: no Heat Dissipation block, so Heat Calculations writes a typed 0 heat loss (A1 review of #48).
- **Loose Material sheet** uses the panel BOM layout; its header document is `loose_material.host_panel`'s (ADR 0020).
- **Atomic replace** (#69): temp file in the same folder + `os.replace`; on failure delete only the temp file.

## Failed approaches and what they taught

- **pycel reads cached values.** `ExcelCompiler.evaluate` returns the cached result when one exists, so a golden comparing evaluated with cached values tested nothing. Fix: evaluate every formula once, then `compiler.recalculate()` (A1 review of #48).
- **`startswith("=")` is not a formula test.** Text cells "=" in Heat Calculations were counted. Use openpyxl `cell.data_type == "f"`.
- **LibreOffice PDFs can't judge header fit**: they clip header text to the margin and ignore scale-with-document.
- **XlsxWriter quirks**: `set_header` silently drops strings > 255 chars (we raise `WriterError`); 3.2.9 raises `struct.error` on a truncated picture, 3.3.0 raises its own exception, and `UnsupportedImageFormat` can come before close; widths are stored as UI width + 5 px.
- **`close()` failure used to unlink the target**, deleting an issued workbook (fixed in #69).
- **GitHub shows these PRs "closed, not merged"** because A1 lands them as commits; check `git log origin/main`.
