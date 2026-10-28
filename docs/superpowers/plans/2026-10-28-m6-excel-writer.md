# M6 Excel Writer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translate library-agnostic sheet models into one .xlsx file with XlsxWriter: values, live formulas, styles, merges, widths, heights, hidden columns, print setup, page-break preview, page header/footer with the logo picture, full recalculation on load.

**Architecture:** `bomgen.models.sheet` defines frozen pydantic value objects (`WorkbookModel` → `SheetModel` → `Cell`, `CellStyle`, `Merge`, `PrintSetup`, `HeaderFooter`). `bomgen.writer.xlsx.write_workbook()` is the only code that imports XlsxWriter (ADR 0003, ADR 0005). No business rules, layout or spec values live here: M5 (`bomgen.sheets`) builds the models, including the named styles of "Formatting".

**Tech Stack:** Python 3.12, pydantic 2, XlsxWriter 3.2 (write), openpyxl 3.1 (read back in tests).

**Spec:** `docs/spec/generator-spec-v2.md` → "Formatting", "Output requirements"; `docs/plan.md` → M6; ADR 0003, 0005.

## Global Constraints

- The writer module is the only place that imports `xlsxwriter` (ADR 0003).
- OUT-1: one .xlsx, no macros. OUT-5: formulas are written as formulas; the workbook recalculates fully on open (`fullCalcOnLoad="1"`).
- OUT-7: A4, orientation, scale or fit-to-page, margins, print area, repeat rows, page-break preview.
- Header/footer: same on first and following pages (no different first page, no odd/even), page numbering restarts per sheet (Excel default), `&G` logo in a zone.
- Lengths in the model follow the spec's units: widths in Excel character units as Excel's UI shows them, heights in points, margins in cm.
- Rows and columns in the model are 1-based (row 1 = Excel row 1, column 1 = A).
- Tests write only to `tmp_path`; no `.xlsx` is ever committed (CLAUDE.md).

## Review Focus

1. Text that starts with `=` or looks like a number or URL (descriptions, "1 Lot", ordering codes) stays text: only `Formula` cells become formulas.
2. A header or footer longer than Excel's 255-character limit raises `WriterError` (XlsxWriter only warns and drops it).
3. A missing logo file raises `WriterError` naming the path, and leaves no partial output file.
4. `&` in header/footer text (e.g. "R&D") is escaped to `&&` so it is not read as a control code.
5. Any XlsxWriter call that reports an error (e.g. a string over 32,767 characters is truncated) raises `WriterError` instead of writing a silently wrong file.

---

### Task 1: Sheet model

**Files:**
- Create: `src/bomgen/models/sheet.py`
- Test: `tests/unit/writer/test_sheet_model.py`

**Interfaces:**
- Produces (all frozen, `extra="forbid"`):
  - `Formula(text: str, result: int | float | str | None = None)`; `text` must start with `=`.
  - `CellValue = str | int | float | Formula | None` (strict: bools rejected, floats finite).
  - `Font(name="Calibri", size=11.0, bold=False, underline: Literal["none","single"]="none", color="#000000")`
  - `Alignment(horizontal: Literal["general","left","center","right"]="general", vertical: Literal["top","center","bottom"]="bottom", wrap=False)`
  - `BorderStyle` StrEnum `none|thin|medium`; `Borders(left, right, top, bottom)` + `Borders.all(style)`.
  - `CellStyle(font=Font(), fill: Color | None = None, alignment=Alignment(), borders=Borders(), number_format="General")`; hashable. `Color` = `#RRGGBB` (upper-cased).
  - `Cell(value: CellValue = None, style: CellStyle | None = None)`
  - `Merge(first_row, first_col, last_row, last_col)`; spans ≥ 2 cells.
  - `ColumnFormat(width: float | None = None, hidden=False)`, `RowFormat(height: float | None = None)`
  - `CellRange(first_row, first_col, last_row, last_col)` (print area)
  - `PrintSetup(paper: Literal["A4"]="A4", orientation: Literal["portrait","landscape"]="portrait", scale: int | None = None, fit_to_width: int | None = None, fit_to_height: int | None = None, margins: Margins = Margins(), center_horizontally=False, print_area: CellRange | None = None, repeat_rows: tuple[int, int] | None = None, page_break_preview=True, zoom: int | None = None)`; scale and fit-to-page exclusive; scale and zoom 10–400.
  - `Margins(left_cm=1.0, right_cm=1.0, top_cm=3.0, bottom_cm=2.0, header_cm=0.8, footer_cm=0.8)`
  - `HFRun(text="", field: Literal["page","pages"] | None = None, font="Calibri", bold=False, size: int = 11)` (whole points, 1–409); `HFZone(lines: tuple[tuple[HFRun, ...], ...] = (), image: Path | None = None)`; `HeaderFooter(header_left/center/right, footer_left/center/right: HFZone)`.
  - `SheetModel(name: ExcelSheetName, cells: dict[tuple[int, int], Cell], merges: tuple[Merge, ...], columns: dict[int, ColumnFormat], rows: dict[int, RowFormat], print_setup: PrintSetup, header_footer: HeaderFooter | None)`
  - `WorkbookModel(sheets: tuple[SheetModel, ...])`, at least one sheet.

- [ ] **Step 1: Write failing tests** — accepted defaults; rejected: formula without `=`, bool and NaN values, bad colour, row/col 0 or beyond 1,048,576 / 16,384, single-cell merge, overlapping merges, a value or style on a non-anchor cell of a merge, scale with fit-to-page, zoom 5, duplicate sheet names ignoring case, empty workbook, image in more than one zone of the same header.
- [ ] **Step 2: Run** `pytest tests/unit/writer/test_sheet_model.py` → fails on import.
- [ ] **Step 3: Implement** the models; reuse `ExcelSheetName` from `bomgen.models._base`.
- [ ] **Step 4: Run** the tests → pass; `ruff`, `mypy` clean.
- [ ] **Step 5: Commit** `feat(sheet-model): library-agnostic workbook and sheet models`.

### Task 2: Writer — cells, styles, workbook

**Files:**
- Create: `src/bomgen/writer/__init__.py`, `src/bomgen/writer/xlsx.py`
- Modify: `pyproject.toml` (`"XlsxWriter>=3.2"` in dependencies)
- Test: `tests/unit/writer/test_xlsx_cells.py`, shared fixtures in `tests/unit/writer/conftest.py` (`write_and_open(model, tmp_path) -> openpyxl.Workbook`, `tiny_png(path)`)

**Interfaces:**
- Produces: `write_workbook(workbook: WorkbookModel, path: Path) -> Path` (creates parent directories, returns `path`); `WriterError(Exception)`; both re-exported from `bomgen.writer`.

- [ ] **Step 1: Failing tests** — `test_sheets_written_in_model_order`; `test_numbers_and_text_keep_their_type`; `test_text_starting_with_equals_stays_text` ("=24+3" as `str`, "1 Lot", "http://x"); `test_formula_written_live_with_cached_result` (`=A3+1` read back; `data_only=True` gives the result); `test_workbook_recalculates_fully_on_open` (`fullCalcOnLoad="1"` in `xl/workbook.xml`); `test_font_fill_alignment_border_number_format_round_trip` (24 bold, `FF1F497D`, single underline, fill `FFA6A6A6` solid, centre/centre/wrap, thin and medium borders, `0.00`); `test_styled_blank_cell_keeps_its_border` (separator rows); `test_overlong_text_raises_writer_error` (40,000 chars); `test_creates_missing_parent_directory`.
- [ ] **Step 2: Run** → fail.
- [ ] **Step 3: Implement.** Open XlsxWriter with `strings_to_numbers`, `strings_to_formulas`, `strings_to_urls` all `False`; dispatch on the value type (`write_formula`/`write_string`/`write_number`/`write_blank`); cache one `Format` per distinct `CellStyle`; raise `WriterError` on any negative XlsxWriter return code.
- [ ] **Step 4: Run** → pass. **Step 5: Commit** `feat(writer): write cell values, formulas and styles with XlsxWriter`.

### Task 3: Writer — merges, widths, heights, hidden columns

**Files:** Modify `src/bomgen/writer/xlsx.py`; Test `tests/unit/writer/test_xlsx_layout.py`

- [ ] **Step 1: Failing tests** — `test_merges_written` (A1:G1, B4:B7); `test_merged_anchor_keeps_value_style_and_formula`; `test_merge_border_applies_to_every_cell` (G1 has the thin border); `test_column_widths_match_excel_ui_width` (XML width = pixel-rounded width + 5 px padding, i.e. `(int(w*7+0.5)+5)/7` ± 0.01 for 12.29 and 53.71); `test_hidden_column` (H hidden); `test_row_heights` (90, 26.25).
- [ ] **Step 2–4:** `merge_range(..., "", fmt)` then write the anchor's typed value over it; `set_column` with `{"hidden": True}`; `set_row`.
- [ ] **Step 5: Commit** `feat(writer): merges, column widths, row heights, hidden columns`.

### Task 4: Writer — print setup and view

**Files:** Modify `src/bomgen/writer/xlsx.py`; Test `tests/unit/writer/test_xlsx_print.py`

- [ ] **Step 1: Failing tests** — `test_a4_portrait_fit_to_one_page_wide` (paperSize 9, fitToWidth 1, fitToHeight 0, fitToPage); `test_landscape_with_scale` (50); `test_margins_in_cm` (1.0/1.0/3.0/2.0 cm → inches); `test_centred_horizontally`; `test_print_area_and_repeat_rows` (`'1'!$A$1:$G$71`, `$1:$2`); `test_page_break_preview_with_zoom` (view `pageBreakPreview`, zoom 60).
- [ ] **Step 2–4:** `set_paper(9)`, `set_portrait/landscape`, `fit_to_pages`/`set_print_scale`, `set_margins` (cm / 2.54), `center_horizontally`, `print_area`, `repeat_rows`, `set_page_view(2)`, `set_zoom`.
- [ ] **Step 5: Commit** `feat(writer): A4 print setup, print area, repeat rows, page-break preview`.

### Task 5: Writer — page header and footer with logo

**Files:** Modify `src/bomgen/writer/xlsx.py`; Test `tests/unit/writer/test_xlsx_header_footer.py`

**Interfaces:** `render_zone(code: Literal["&L","&C","&R"], zone: HFZone) -> str` (private helper, tested through the file).

- [ ] **Step 1: Failing tests** — `test_header_three_zones_with_bold_28pt_first_line` (centre text "Project\nBill of Materials for 861-GIS01-PSA-0001\nSupplier Doc # D-1", font `Calibri,Bold`, size 28; right "Rev : 0"); `test_footer_page_of_pages` (`Page &P of &N`); `test_logo_picture_in_left_zone` (`&G` in left header, `xl/media/image1.png` and a VML drawing in the zip); `test_ampersand_in_text_is_escaped`; `test_header_over_255_chars_raises`; `test_missing_logo_raises_and_writes_no_file`; `test_header_margins_written` (header/footer margin cm → inches); `test_no_different_first_or_odd_even_pages`.
- [ ] **Step 2–4:** Render runs as `&"Calibri,Bold"` / `&<size>` / text with `&`→`&&` / `&P` / `&N`; lines joined by `\n`; zone image → `&G` plus `image_left|center|right`; check every image path exists before `Workbook()` is created; raise when a rendered string exceeds 255 characters.
- [ ] **Step 5: Commit** `feat(writer): page header and footer with logo picture`.

### Task 6: Repo hygiene, docs

**Files:** Test `tests/unit/writer/test_no_xlsx_in_repo.py`; Modify `docs/plan.md` (M6 section status), `tests/unit/README.md` row (via A7 if A1 prefers).

- [ ] **Step 1:** `test_no_xlsx_tracked_in_git` (`git ls-files '*.xlsx' '*.xlsm'` is empty; skip when git is unavailable).
- [ ] **Step 2:** Full gate: `ruff check . && ruff format --check . && mypy && pytest`.
- [ ] **Step 3: Commit** `test(writer): no generated workbook is tracked` and `docs(plan): M6 delivered`.
