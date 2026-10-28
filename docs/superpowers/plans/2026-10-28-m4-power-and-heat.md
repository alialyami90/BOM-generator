# M4 Power and Heat Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derive the Power Consumption, Heat Dissipation and Heat Calculations results from the built BOM, and let the heat check choose each `auto` panel's ventilation.

**Architecture:** Result models in `models/calc.py` (frozen, `OutputModel` from `models/output.py` so `models/bom.py` can hold them in `BuildResult`). `engine/power.py` turns powered BOM rows into `PowerLine`s with a `LineRef` back to the row; `engine/thermal.py` holds the heat blocks, the forced and natural checks, the line-up check and the ventilation rule. `pipeline.build()` decides ventilation inside each panel's first pass and computes power and heat after the tables.

**Tech Stack:** Python 3.12, pydantic v2 (frozen models), pytest.

**Spec:** "Power Consumption sheet" (layout, columns, formulas), "Heat Dissipation and Heat Calculations sheets" including "Rule for the tool", "Data model and generation order" steps 4 and 12. Plan M4, Q4, Q8.

## Global Constraints

- Values only; formulas and cell references are the sheet layer's (A10, M5).
- Power lines in BOM order; V from the supply type (125 V DC, 230 V AC constants).
- Block total = (1 + margin) × Σ J; heat has no margin; unit heat = W × 3.41.
- `auto` ventilation is decided from the heat without the ventilation parts (Q4).

## Review Focus

1. A powered row with a non-count quantity (`"1 Lot"`, `=a+b`) → `EngineError`.
2. Rows `excluded_from_power` and unpowered parts give no power line.
3. The external block holds the loose table's DC loads only.
4. The line-up check lists only the fan-ventilated cabinets; none when no cabinet has fans.

---

### Task 1: Power models and lines

**Files:** Create `src/bomgen/models/calc.py`, `src/bomgen/engine/power.py`; Tests `test_engine_calc_model.py`, `test_engine_power.py`.

- [x] Columns J, N, O, P, Q per line; block totals with margin; summary DC (with external), AC, total.
- [x] Commit `feat(engine): power consumption lines, blocks and summary`.

### Task 2: Heat checks and ventilation choice

**Files:** Modify `src/bomgen/engine/thermal.py`; Test `test_engine_thermal.py`.

- [x] Forced airflow `P × k / (TMax − TInt)`, surface `1.8 H (W + D) + 1.4 W D`, ΔT, line-up sum, `choose_ventilation`, heat blocks, `ventilation_heat_w`, `heat_result`.
- [x] Commits `feat(engine): heat checks and the ventilation choice`, `feat(engine): heat dissipation blocks`.

### Task 3: Pipeline and golden

**Files:** Modify `src/bomgen/models/bom.py`, `src/bomgen/engine/{pipeline.py,housekeeping.py}`; Create `tests/golden/test_engine_power_heat.py`.

- [x] `BuildResult.power` and `.heat`; `auto` ventilation feeds groups D, E and G.
- [x] Golden: 2,177.5 / 1,090.3 / 3,267.8 W; 391/391/172 m³/h vs 716; Σ 954.8 vs 2,148; WS A 4.848 m², ΔT 6.96 °C; ventilation forced ×3, natural on the console.
