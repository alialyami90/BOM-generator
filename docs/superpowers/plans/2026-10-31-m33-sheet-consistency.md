# M33 Sheet consistency Implementation Plan

**Goal:** The calculation sheets and the BOM agree, and the audit's untested rules get tests
(audit 2026-10-31: ENG-4, ENG-5, ENG-7, ENG-8, ENG-12, ENG-13 to ENG-15).

**Out of scope:** ENG-11 (sheet 4's header height) is a spec-versus-code question for Ali.
ENG-6 (fan upsizing) gets its own PR. ENG-1 (duplicate tags) isn't fixed here; its test is a
strict expected failure.

**Tasks** (test first in each):

1. **ENG-4, ENG-5 (ADR 0028, rejected by Ali on 2026-11-01 and reverted).** `PowerLine.branch_mcb_a` holds the row's own branch rating from
   `dc_dist.branch_sizing`; `power_sheet` writes it in P as a value, else `=ROUNDUP(O,0)`. Power
   lines take the part's `voltage_v`. The pipeline passes the fed loose items to `power_consumption`.
2. **ENG-8.** `checks.external_ac_checks` warns for each AC loose load, which External Equipment
   (DC only) leaves out of the totals.
3. **ENG-7.** With no forced-ventilation cabinet, the first natural-convection block starts at row
   7, so its coefficient box (I:M) stays clear of the constants box (J3:L5).
4. **ENG-12.** `bom_sheet` treats a group H row as grounding only when it has no part, so the
   nameplate row is a body row.
5. **ENG-13 to ENG-15.** Nameplate rules and the Nameplates sheet layout tested without the
   example; a VAC group B device through Power Consumption and Heat Dissipation; two units of one
   tag pattern in one panel (expected failure, ENG-1).

**Verify:** `ruff check . && ruff format --check .`, `mypy`, `pytest`; diff the example workbook
before and after (only the 16 own-branch P cells and the nameplate row heights change).
