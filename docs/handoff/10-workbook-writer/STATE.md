# Role 10 — Excel workbook writer: state

- Name: B10 → successor **C10**. Role 10; the rules `docs/agents.md` gives "A10" apply to every holder of role 10.
- Owns (the authoritative list is `docs/agents.md` → "Roles", role 10): `src/bomgen/sheets/`, `src/bomgen/writer/`, `src/bomgen/models/sheet.py`, `tests/unit/sheets/`, `tests/unit/writer/`, the plan's M5 and M6 sections, ADR 0020, the plans `docs/superpowers/plans/2026-10-28-m5-sheet-models.md` and `…-m6-excel-writer.md`, this folder and the role-10 ROSTER row.
- `tests/golden/test_workbook.py` sits in role 9's `tests/golden/`. Change it only with role 9's agreement or the lead's request, and say so in the PR body (#157 did this at A1's request).
- Date: 2026-10-29. Thread branch: `claude/project-thread-pcjgix`. Reset it to origin/main for each new piece of work.
- Verified on `032bbea` (origin/main, 2026-10-29). This checkpoint is a docs-only PR on top of it.

## Merged (all on main; check with `git log origin/main -- src/bomgen/sheets src/bomgen/writer`)

| PR | Commit | What |
| --- | --- | --- |
| #21 | e37d9a6 | M6: `models/sheet.py` sheet models, `writer/xlsx.py` (XlsxWriter, ADR 0003) |
| #48 | 02241ed | M5: `sheets/` (BOM, Power Consumption, Heat Dissipation, Heat Calculations, header/footer, `build_workbook`), pycel golden `tests/golden/test_workbook.py` |
| #69 | d01dcbe | Writer writes to `<stem>.tmp-<hex><suffix>` beside the target, then `os.replace`; failures raise `WriterError` (cause kept), target untouched |
| #96 | 4c97af7 | M18 sheet side, ADR 0020: Loose Material sheet; `output.sheet_names.loose_material`; revision compare falls back to host sheet table 1 for older issues |
| #157 | a21e675 | Power footnotes: each `substation.output.power_footnotes` entry (field from role 2, #152) is one row two rows below the NOTES, merged B:L, wrapped, 15 pt per line, inside the print area (Q40) |

Nothing has touched role-10 files since #157 (checked with the `git log` above on 032bbea).

- **Open PRs:** none.
- **Branches:** only the thread branch above. It holds nothing unmerged; this checkpoint is its only change.
- **Uncommitted changes:** none.

## What works (evidence: the verification table)

- `build_workbook(loaded, result, *, logo=None) -> WorkbookModel` (`sheets/workbook.py`). Sheet order: the panel BOMs, then Loose Material (only when `result.loose` is not None; since #123 the engine gives None when the table has no rows), then Power Consumption, Heat Dissipation and Heat Calculations.
- `write_workbook(workbook, path) -> Path` (`writer/__init__.py` → `writer/xlsx.py`). This is the only module that imports XlsxWriter.
- Every formula carries a cached result. `tests/golden/test_workbook.py` recalculates all 924 formula cells with pycel (`compiler.recalculate()`) and checks the spec totals: 2,177.5 W DC, 1,090.3 W AC, 3,267.8 W; airflow 391/391/172 vs 716; line-up 954.8 vs 2,148; console A = 4.848 m², ΔT = 6.96 °C. It also reopens the file and checks the printer footnote (text, `\n`, wrap, B:L merge, 30 pt height, print area).
- Callers (other owners): `src/bomgen/build.py` (role 2, `bomgen build`) and `src/bomgen/app/output.py` (role 11, the app's Build) call `build_workbook` and then `write_workbook`. `src/bomgen/app/api.py` exposes a `build_workbook` method for the Preview tab, which renders the `WorkbookModel`. A change to the sheet models' shape therefore reaches role 11's Preview.

## Verification (2026-10-29, on 032bbea, Linux container)

Setup: `uv venv && uv pip install -e ".[dev]"`. This container had Python 3.13.17, XlsxWriter 3.2.9 and openpyxl 3.1.5; the 2026-10-28 run had Python 3.12 and XlsxWriter 3.3.0. Both pass, and `pyproject.toml` pins only `XlsxWriter>=3.2`, `openpyxl>=3.1` and `pycel>=1.0b30`. The gate is CLAUDE.md "Before every commit".

| Command | Result |
| --- | --- |
| `ruff check . && ruff format --check .` | pass (345 files) |
| `mypy` | pass, 224 source files |
| `pytest` | 2672 passed, 0 failed, 0 skipped (about 6 minutes; 1082 warnings, from pycel and others, not errors) |
| `pytest tests/golden/` | 95 passed |
| `pytest tests/unit/sheets tests/unit/writer` | 139 passed |

Not run here: opening a workbook in real Excel (no Windows or Excel); the Windows installer.

## Decisions Ali made that shape role 10

- **Q36 → ADR 0020:** loose material is its own sheet, laid out like a panel BOM, under its host panel's document header. It overrides OUT-3 and the spec's sheet-4 loose table. Updating the spec text is the lead's to put to Ali.
- **Q40 (2026-10-28):** the power footnotes print. The print area ends after the last footnote row, not at the reference's A1:L97. Recorded in `docs/plan.md` → open questions.
- **Q11:** calc-sheet header size is computed (`fitting_size`, at most 20 pt). Excel fit is still unverified; see "Waiting on".

## Known limits and risks

- **Calc-sheet header fit in Excel is unverified.** `header_footer.fitting_size` gives 17 pt at a 49–50 % print scale and 11 pt at 78 % (`LINE_SPACING = 1.2`). LibreOffice ignores "scale with document" and clips every header, so its PDFs can't settle it. Only Excel's Print Preview can.
- **pycel 1.0b30** is a pre-release dev dependency. Its `ast` deprecation warnings are filtered in `tests/golden/test_workbook.py`.
- **`FORMULA_COUNT = 924`** in that golden moves whenever the layout adds or removes formulas. Update it and give the reason in a comment. #157 added text rows only, so the count didn't change.
- **Footnote height is estimated.** It is the number of `\n` lines plus wrapped overflow at about 255 characters (the B:L widths summed) × 15 pt. A very proportional font or a very long word could still clip; nobody has reported it.

## Spec vs code

- ADR 0020 overrides OUT-3 and the spec's loose table (see above). The spec text is not updated yet; the lead owns that.
- Q40 overrides the reference workbook's print area. The spec states no print area for Power Consumption beyond the reference, so nothing in the spec conflicts.

## Waiting on

- **Ali:** the Excel Print Preview check of calc-sheet headers (open since 2026-10-28). The lead (role 1) undertook to put it to Ali on a decision card; `docs/handoff/01-lead/NEXT.md` lists it. As of 032bbea no answer is recorded in `docs/plan.md`.
- Nothing else. The printer-footnote dependency on role 2 is closed (#152, then #157).

## How to contact people

- Other roles: message their project thread (titles in `docs/handoff/ROSTER.md`). The lead reviews and squash-merges every PR; never ask Ali to merge.
- Ali: only on a decision card with your recommendation marked.
