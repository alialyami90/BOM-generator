# Role 10 — next

Next action: re-run the gate on origin/main and record drift, then ask A1 in A1's thread for the next role-10 work, since both open tasks below are blocked (M5, M6 and M18's sheet side are merged).

## Tasks (priority order)

1. **Printer footnote on Power Consumption** (follow-up to M5; blocked on A2).
   - Goal: write the spec's printer footnote after NOTES ("Power Consumption sheet", item 5).
   - Files: `src/bomgen/sheets/power_sheet.py`, `tests/unit/sheets/test_power_sheet.py`. The input field is A2's (`src/bomgen/models/`, schemas, `examples/`).
   - Depends on: A2 adding an input field for the footnote text (name not decided; the reference workbook's text is "*Printer Power Consumption: 622 watts (Printing), …", Power Consumption row 98). Ask A2 to propose it; never hard-code it.
   - Failing test first: `test_printer_footnote_follows_the_notes`.
   - Done: gate passes; PR open for A1.
2. **Calc-sheet header fit in Excel** (M5; waiting on Ali).
   - If Ali reports the header overlaps the table, raise `LINE_SPACING` (now 1.2) in `src/bomgen/sheets/header_footer.py`, for example to 1.4, and update the expected sizes in `tests/unit/sheets/test_header_footer.py` (`fitting_size` floors the result, so sizes drop by about 1/7). Don't judge with LibreOffice (see LESSONS).
   - If it stays unanswered past the next checkpoint, put it to Ali on a decision card (recommend: keep 1.2 unless the preview shows overlap).

Carried forward: none from a previous NEXT.md (this is the first checkpoint).

## Don't do

- Don't edit the spec for ADR 0020 (A1 puts it to Ali).
- Don't change the Preview tab or loose-material editor (A11), the engine (A9) or input models (A2) without the owner's agreement; record cross-owner edits in the PR body.
- Don't hard-code project text (such as the printer footnote) in the sheets.
- Don't commit generated `.xlsx` files; build into `out/` or a temp dir (CLAUDE.md; `tests/unit/writer/test_no_xlsx_in_repo.py`).
