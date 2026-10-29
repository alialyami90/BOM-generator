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
- **Power footnotes** (#157): one row per `output.power_footnotes` entry, in file order, two blank rows below the NOTES (the reference has NOTES at B93–B95 and the footnote at B98). Each row is merged B:L with left/centre wrap (`styles.FOOTNOTE`), so the `\n` in the text breaks the line. The height is 15 pt per line, because Excel doesn't autofit a merged cell; a line longer than the summed B:L widths (about 255 characters) counts as more than one line. No footnotes means no rows, so older layouts don't change. Rejected: wrapping in the single narrow column B (as the reference does), which would show only a sliver.
- **Footnote field shape** was agreed with role 2 before coding: a list of strings on the substation's `output` block, empty by default, blank entries refused. Rejected: one string (it can't hold several footnotes) and a device-level field (the printer isn't a BOM device and its watts aren't in any total).
- **Print area includes the footnotes** (Q40, Ali chose "Print it"). The reference's print area stops at row 97 and leaves its footnote off the printout; we treat that as a slip.

## Failed approaches and what they taught

- **pycel reads cached values.** `ExcelCompiler.evaluate` returns the cached result when one exists, so a golden comparing evaluated with cached values tested nothing. Fix: evaluate every formula once, then `compiler.recalculate()` (A1 review of #48).
- **`startswith("=")` is not a formula test.** Text cells "=" in Heat Calculations were counted. Use openpyxl `cell.data_type == "f"`.
- **LibreOffice PDFs can't judge header fit**: they clip header text to the margin and ignore scale-with-document.
- **XlsxWriter quirks**: `set_header` silently drops strings > 255 chars (we raise `WriterError`); 3.2.9 raises `struct.error` on a truncated picture, 3.3.0 raises its own exception, and `UnsupportedImageFormat` can come before close; widths are stored as UI width + 5 px.
- **`close()` failure used to unlink the target**, deleting an issued workbook (fixed in #69).
- **GitHub shows these PRs "closed, not merged"** because A1 lands them as commits; check `git log origin/main`.
- **A spec gap the reference "answers" can still be a disagreement.** #157 put the footnote in the print area, which differs from the reference; the lead held the merge for a card to Ali (Q40). Flag every departure from the reference workbook in the PR body so the lead can catch it early.
- **Read Ali's reference workbook directly.** It is in the project files under `uploads/hearth/` (the file `file` reports as "Microsoft Excel 2007+"; at handover, `dbc9ed74-…`). It has no extension, so copy it to a scratch dir as `.xlsx` before openpyxl will open it, and run Python with `-I` from a different directory. It is the source for exact cell text, rows, heights and styles.
- **Requesting Ali as reviewer fails** on PRs the session opens, because GitHub counts Ali as the author. Assigning works. Either way, the lead reviews.

## Drift log

- 2026-10-28 (B10 start): origin/main had moved 9313db1 → 502f564 with docs-only commits; gate unchanged (2414 passed). The thread branch differs per session (B10: `claude/project-thread-pcjgix`, A10: `…-yh0t8s`); use the one your session names.
- 2026-10-29 (B10 final): origin/main 032bbea; 2672 passed. The container had Python 3.13 and XlsxWriter 3.2.9 instead of 3.12 and 3.3.0; everything still passes.
