# Role 10 — next

Next action: follow `docs/handoff/README.md` step 4 (fetch, status, log, the gate) on origin/main and record any drift in LESSONS.md. Then tell the lead (role 1, current name in ROSTER.md) in its thread that you are ready, and stay idle until it assigns work. Role 10 has no open PR, no unmerged branch and no task you can start alone: the only open item waits on Ali.

## Tasks (priority order)

1. **Calc-sheet header fit in Excel** (M5, Q11; waiting on Ali through the lead).
   - Why: the header size is computed so its three lines fit between the header and top margins at the sheet's print scale, but only Excel's Print Preview shows whether it overlaps the table.
   - First check `docs/plan.md` → open questions and the lead's handoff to see whether Ali has answered.
   - If Ali reports an overlap: raise `LINE_SPACING` (now 1.2) in `src/bomgen/sheets/header_footer.py`, for example to 1.4. Then update the expected sizes in `tests/unit/sheets/test_header_footer.py`. `fitting_size` floors its result, so at 1.4 the sizes become 15 pt at 49 %, 14 pt at 50 % and 9 pt at 78 % (checked 2026-10-29). Write the failing test first.
   - If Ali reports it fits: no code change. Record the answer in the plan's Q11 entry (or ask the lead to, since plan structure is the lead's) and drop this task.
   - If it is still unanswered and the lead hasn't sent a card: ask the lead to send one. Recommend keeping 1.2 unless the preview shows an overlap.
   - Done: gate passes; PR open for the lead; the plan's Q11 says what Excel showed.

Carried forward from the 2026-10-28 NEXT.md: task 2 (header fit). Task 1 there (printer footnote) is done (#157, Q40).

## Likely future work (not assigned; wait for the lead)

- Any new sheet column or sheet driven by an engine change: role 9 announces `BuildResult` changes to role 10 first (`docs/agents.md` → A9). New input fields come from role 2; never add one yourself.
- If the spec gets updated for ADR 0020 or Q40, check that the sheet docstrings still cite the right section names.

## Don't do

- Don't edit the spec for ADR 0020 or Q40 (the lead puts spec changes to Ali).
- Don't change the Preview tab or loose-material editor (role 11), the engine (role 9) or input models (role 2) without the owner's agreement. Record any cross-owner edit in the PR body.
- Don't hard-code project text (such as a footnote) in the sheets. It comes from inputs.
- Don't commit generated `.xlsx` files. Build into `out/` or a temp dir (CLAUDE.md; `tests/unit/writer/test_no_xlsx_in_repo.py` enforces it).
- Don't judge print layout from LibreOffice PDFs (LESSONS).
