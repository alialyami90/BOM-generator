# M5 Sheet Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay out the engine's `BuildResult` as `SheetModel`s: one BOM sheet per cabinet (the loose-material table under its host), Power Consumption, Heat Dissipation and Heat Calculations, with live formulas built from resolved cell addresses, the "Formatting" styles, print setup and page header/footer.

**Architecture:** `bomgen.sheets` turns `BuildResult` + `LoadedSubstation` into a `WorkbookModel` (M6) and adds no rules of its own (ADR 0005). Each sheet module returns its `SheetModel` plus the row map the next sheet needs (BOM line → row, power line → row, heat block → total row), so every formula points at a resolved address. Every formula carries its engine-computed result as the cached value.

**Tech Stack:** Python 3.12, pydantic 2; `pycel` (dev) evaluates the written workbook in tests (plan Q15).

**Spec:** `docs/spec/generator-spec-v2.md` → "Columns of a panel BOM", "Power Consumption sheet", "Heat Dissipation and Heat Calculations sheets", "Formatting", "Output requirements"; plan M5, Q9, Q11, Q14, Q15, Q22; ADR 0004, 0005, 0012, 0014.

## Global Constraints

- No business rules in `sheets/`: numbers come from `BuildResult` (and `DesignConstants` for the constants written into formulas). A value the engine does not give is not invented here.
- OUT-5 formulas: SR.NO `=A{prev}+1` skipping separators; Power Consumption E–H `='<BOM>'!C|D|E|F<row>`, `J=F*I`, `N=I/V`, `O=N*<factor>`, `P=ROUNDUP(O,0)`, `Q=O*F`, `R=Q`, block total `=SUM(J..)*(1+margin)`, summary sums; Heat Dissipation C–I from Power Consumption, `J=(L*<btu>)/H`, `K=H*J`, `L=I*H`, totals `SUM`; Heat Calculations heat, airflow, line-up sum, area and ΔT.
- Sheet order (OUT-3): panels in `LoadedSubstation.panels` order, then the three calculation sheets named by `output.sheet_names`.
- Print areas are computed from the last used row (Q9): BOM `A1:G<last>`, Power Consumption `A1:L<last>`, Heat Dissipation `A1:M<last>`, Heat Calculations `A1:N<last>`.
- Page header/footer per "Output requirements"; every zone at the sheet's size, only the project name bold. BOM sheets 28 pt; a calculation sheet takes the largest size up to 20 pt (Q11) whose three lines, scaled with the sheet's print scale, fit between the header and top margins (`fitting_size`: 17 pt at 49–50 %, 11 pt at 78 %). Footer right `Rev <rev> – <issue date ISO>`.

## Layout decisions (where the spec gives a range or only an example)

- BOM rows: body height `max(30, 26.25 × lines)`; ordering code over 40 characters → at least 52.5 (switches); group H rows `26.25 × (lines + 2)` (78.75 for one line, 131.25 for three), white fill, left/wrap. Header row 26.25, 53.1 on the sheet hosting the loose table. Title row 90.
- Loose table: one blank row of 48.75 after the host's last row, then its own title (A:G, row 90) and header row; SR.NO restarts at 1.
- Merges (Q14): parent tag `B` over the parent and its children; with `merge_fg`, F and G each merged down over the run of children whose own cell is empty.
- Column H (HWIO) hidden, H2 "HWIO", H1 `=SUM(H3:H<last>)`; a line's HWIO written only when non-zero. Column I is a 4.57 spacer.
- Power Consumption: row 1 blank; per cabinet: title (A:L), blank, block label (B:C), blank, header, rows, TOTAL row, blank; blocks that are `None` are skipped; External Equipment after the cabinets; summary table; notes. Sizing headers N–R on the first header row only; M–N hidden.
- Heat Calculations: constants box J3:L5 (TMax, TInt, k as numbers, unit in L); forced working for cabinets whose ventilation is forced, natural for natural; the line-up check after the forced cabinets when `heat.line_up` is set; pass sentences are `IF` formulas.
- Titles use the panel's `cabinet_name` ("Power Consumption for PSA Cabinet - 001").

## Review Focus

1. A panel with no AC (or no DC) block, or a build without a loose table / external block, lays out without empty tables or dangling references.
2. Sheet names that need quoting (`1`, `Power Consumption`, names with `'`) are quoted in every reference (`'1'!C8`, `'O''Brien'!C8`).
3. A BOM line with `qty` "1 Lot" stays text; a `QtySum` is a formula with its sum as the cached value.
4. Every formula's cached result equals what pycel computes from the written file, so a reader that does not recalculate sees the right numbers.
5. No logo configured → header left zone is empty, not an `&G` without a picture.

---

### Task 1: Styles and grid helper
**Files:** `src/bomgen/sheets/__init__.py`, `styles.py`, `grid.py`; tests `tests/unit/sheets/test_grid.py`.
- `styles.py`: named `CellStyle` constants from "Formatting" (BOM title/header/body/designation/description/grounding/separator; calc title/block label/table header/data/total/summary/notes; heat-calc text) and `revised(style)`, `framed(style, top, bottom, left, right)` border helpers.
- `grid.py`: `quote_sheet(name) -> str` (always quoted, `'` doubled), `ref(sheet, row, col) -> str`, `SheetBuilder(name)` with `set(row, col, value, style)`, `merge(...)`, `height(row, h)`, `width(col, w, hidden=False)`, `box(r0, c0, r1, c1, outer, inner)` (re-borders cells already set), `last_row`, `build(print_setup, header_footer) -> SheetModel`.
- Tests: quoting (`1`, `Power Consumption`, `O'Brien`), `ref`, box borders (corner/edge/inner), merge-covered cells dropped and anchor style applied.

### Task 2: BOM sheet and loose table
**Files:** `sheets/bom_sheet.py`; tests `tests/unit/sheets/test_bom_sheet.py`.
- `bom_sheet(panel: PanelBom, loose: LooseTable | None, ...) -> BomSheet(model, rows: dict[LineRef, int])`.
- Tests: title text and merge A1:G1; header labels; SR.NO 1 then `=A{prev}+1` across a separator; separator rows before E/F/G/H, bordered and blank; qty int / "1 Lot" / `QtySum`; parent tag merge and F/G merge rules; hidden H with `SUM`; revised cells yellow; grounding row height/fill; loose table position, title, numbering restart; print setup (A4 portrait, fit 1×0, margins 1/1/3/2, repeat 1:2, area A1:G<last>, zoom 60).

### Task 3: Power Consumption
**Files:** `sheets/power_sheet.py`; tests `tests/unit/sheets/test_power_sheet.py`.
- `power_sheet(power, bom_rows, names, constants) -> PowerSheet(model, rows: dict[LineRef, int])`.
- Tests: block order and skipping; E–H references to the right BOM cell (incl. loose table on the host sheet); J/N/O/P/Q/R formulas; total `*1.25`; summary sums every DC total incl. external and every AC total; hidden M–N; landscape, scale 49, margins 1.8/1.9, area A1:L<last>.

### Task 4: Heat Dissipation and Heat Calculations
**Files:** `sheets/heat_diss_sheet.py`, `sheets/heat_calc_sheet.py`; tests `tests/unit/sheets/test_heat_sheets.py`.
- `heat_dissipation_sheet(heat, power_rows, ...) -> HeatDissSheet(model, totals: dict[str | None, int])`; `heat_calculations_sheet(heat, totals, ...) -> SheetModel`.
- Tests: C–I references into Power Consumption; J/K/L formulas, number format 0.00; TOTAL row sums; auxiliary block title; constants box; forced and natural working formulas; line-up sum over the forced cabinets; IF pass sentences.

### Task 5: Headers/footers and workbook assembly
**Files:** `sheets/header_footer.py`, `sheets/workbook.py`; tests `tests/unit/sheets/test_header_footer.py`, `tests/golden/test_workbook.py`.
- `build_workbook(loaded: LoadedSubstation, result: BuildResult, *, logo: Path | None = None) -> WorkbookModel`.
- Unit: BOM and calc header/footer strings from the register; no logo → no picture.
- Golden (writes to `tmp_path`, evaluates with pycel): sheet order; Power Consumption summary 2,177.5 / 1,090.3 / 3,267.8; airflow 391/391/172; Σ 954.8 vs 2,148; A 4.848, ΔT 6.96; every cached result equals pycel's value; merges A1:G1, B4:B7, F4:F6, G4:G6 on sheet `1`.
- Add `pycel` to the dev extra; docs: plan M5 section.
