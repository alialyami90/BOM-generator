# Role 10 — Excel workbook writer: state

- Name: A10 → successor **B10** (thread "B10 - Excel workbook writer"). Role 10; rules for "A10" in `docs/agents.md` apply to B10.
- Owns (authoritative list: `docs/agents.md` → "Roles", role 10): `src/bomgen/sheets/`, `src/bomgen/writer/`, `src/bomgen/models/sheet.py`, `tests/unit/sheets/`, `tests/unit/writer/`, the plan's M5–M6 sections, ADR 0020, this folder and the role-10 ROSTER row. `tests/golden/test_workbook.py` sits in A9's `tests/golden/`; change it with A9's agreement.
- Date: 2026-10-28. Thread branch: `claude/project-thread-yh0t8s` (reset to origin/main for each new piece of work).
- Code verified on `9313db1` (then origin/main). This checkpoint is a docs-only PR on top of `aad6094` (#133); see the checkpoint file for its PR number.

## Merged (all on main; GitHub lists them "closed", check with `git log origin/main`)

| PR | Commit | What |
| --- | --- | --- |
| #21 | e37d9a6 | M6: `models/sheet.py` sheet models, `writer/xlsx.py` (XlsxWriter, ADR 0003) |
| #48 | 02241ed | M5: `sheets/` (BOM, Power Consumption, Heat Dissipation, Heat Calculations, header/footer, `build_workbook`), pycel golden `tests/golden/test_workbook.py` |
| #69 | d01dcbe | Writer writes to `<stem>.tmp-<hex><suffix>` beside the target, then `os.replace`; failures raise `WriterError` (cause kept), target untouched |
| #96 | 4c97af7 | M18 sheet side, ADR 0020: Loose Material sheet; `output.sheet_names.loose_material`; revision compare falls back to host sheet table 1 for older issues |

In review: none. In progress: none. Uncommitted changes: none (only this checkpoint).

## What works (evidence: verification table)

- `build_workbook(loaded, result, *, logo=None) -> WorkbookModel` (`sheets/workbook.py`); sheet order: panel BOMs, Loose Material (only when `result.loose` is not None), Power Consumption, Heat Dissipation, Heat Calculations.
- Every formula has a cached result; `tests/golden/test_workbook.py` recalculates all 924 formula cells with pycel (`compiler.recalculate()`) and checks the spec totals (2,177.5 W DC, 1,090.3 W AC, 3,267.8 W; airflow 391/391/172 vs 716; line-up 954.8 vs 2,148; console A = 4.848 m², ΔT = 6.96 °C).
- Callers: `src/bomgen/build.py` (A2) and `src/bomgen/app/output.py` (A11) call `build_workbook` then `write_workbook`.

## Verification (2026-10-28, on 9313db1, Linux container)

Setup: `uv venv && uv pip install -e ".[dev]"` (Python 3.12; XlsxWriter 3.3.0, pycel 1.0b30, openpyxl 3.1.5). The gate is CLAUDE.md "Before every commit".

| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | pass |
| `mypy` | pass, 210 files |
| `pytest` | 2414 passed, 0 failed, 0 skipped |
| `pytest tests/golden/` | 94 passed |
| `pytest tests/unit/sheets tests/unit/writer` | 133 passed |

Not run here: opening the workbook in Excel (no Windows/Excel); the Windows installer.

## Known limits and risks

- Calc-sheet header size comes from `header_footer.fitting_size` (17 pt at 49–50 %, 11 pt at 78 %; plan Q11). Fit in Excel is **unverified**: LibreOffice ignores "scale with document" and clips every header, so its PDFs can't show it. Ali was asked in this role's thread (M5 result message, 2026-10-28, with the example workbook attached) to check Excel Print Preview; no answer. Not on a decision card.
- pycel 1.0b30 is a pre-release dev dependency; its Python 3.12 `ast` deprecation warnings are filtered in `tests/golden/test_workbook.py`.
- `FORMULA_COUNT = 924` in that golden moves whenever the layout adds or removes formulas; update it with the reason.

## Spec vs code

- ADR 0020 (Ali, Q36) overrides OUT-3 and the spec's sheet-4 loose table; spec text update is A1's to put to Ali.
- Power Consumption sheet item 5 "printer footnote" after NOTES is not written: no input field carries the text. Waiting on A2 (an input field) since 2026-10-28; agreed with A1 as a follow-up.

## Waiting on

- Ali: Excel Print Preview check of calc-sheet headers (since 2026-10-28). No issue or card exists.
- A2: an input field for the printer footnote (since 2026-10-28; agreed in A1's review of #48 and A1's #48 merge note), then role 10 writes it. No issue exists.
- Contact other roles by messaging their project thread (titles in ROSTER.md); A1 reviews and merges.
