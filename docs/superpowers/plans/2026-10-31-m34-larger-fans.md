# M34 Larger fans for hot cabinets Implementation Plan

**Goal:** A forced cabinet gets fans whose pair moves its required airflow (Heat Calculations,
"Rule for the tool"; audit 2026-10-31, ENG-6; ADR 0029).

**Tasks** (test first in each):

1. `Housekeeping.larger_fans: list[FanRef]`, reference-checked by the loader, exported and
   imported as `housekeeping.csv` rows with the role `larger_fan`; `bomgen schema` regenerated.
2. `thermal.choose_fan(heat_w, library, constants)`: fans sorted by airflow, the first whose
   pair passes the forced check with its own and the thermostats' heat added, else the largest.
3. The pipeline picks the fan per panel, `housekeeping(..., fan)` writes it in group D, and
   `heat_result` takes each panel's fan pair.

**Verify:** the gate, plus the example workbook unchanged (its library lists no larger fans).
