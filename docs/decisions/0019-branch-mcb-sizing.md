# 0019. Branch MCBs sized from device data

- Status: Proposed
- Date: 2026-10-28
- Spec sections: Derivation rules → DC distribution (group F), Breaker part numbers;
  Data model and generation order (steps 7 and 15)

## Context

The spec sizes the DC branch MCBs (Q1.n, Q2.n, QCOD-n) by example: every branch in
the workbook is 2 A. Until v0.1 the engine took the larger of 1.3 × the running
current and a hand-typed per-device `min_branch_mcb_a` (plan Q7). Ali asked for each
MCB to be sized from the equipment's own data, worked out by the program (backlog
point 3). For Q35 he chose "Computed, 2 A floor". M13 (ADR 0017) adds the data:
`DeviceType.inrush_a` and `inrush_ms`; `trip_curve`, `magnetic_trip_multiple`,
`magnetic_trip_multiple_dc` and the `magnetic_multiple` property (the explicit AC value,
otherwise the curve's lower bound) on the MCB catalogue; and
`ConstantOverrides.min_branch_mcb_a = 2`.

## Decision

1. A branch MCB, whether Q1.n, Q2.n or QCOD-n, is the smallest catalogue rating that
   meets every condition that applies:
   - (a) **running**: at least `current_factor` (1.3) × W ÷ V of one unit;
   - (b) **inrush**: at least `inrush_a` ÷ the catalogue's `magnetic_multiple`, when the
     device has an inrush figure and the catalogue has a trip curve or multiple;
   - (c) **floor**: at least the design constant `min_branch_mcb_a` (2 A).
2. Condition (b) divides by the AC multiple, which is 5 on the C curve, as Ali's answer
   states, even though the branches are 125 V DC. `magnetic_trip_multiple_dc` is not
   used. The DC threshold is higher, so the AC value never sizes an MCB that trips on
   the inrush. Sizing from the DC value would mean a new question to Ali.
3. `inrush_ms` does not enter the rule. Ali's rule compares the peak only.
4. `DeviceType.min_branch_mcb_a` is deprecated. It still parses and is reported, but
   it no longer sets a rating.
5. Each sizing records the numbers behind it: the running need, the inrush, the
   multiple and the inrush need, the floor, the rating, and every condition that alone
   gives that rating (`set_by`, in the order running, inrush, floor). The
   cabinet's sizings travel in `BuildResult.branch_mcbs`, one per MCB tag; spares
   repeat the largest rating and are not listed.
6. The check report has one `branch_mcb` line per branch MCB with those numbers. A
   line passes, or warns when:
   - the library's deprecated `min_branch_mcb_a` is above the computed rating, because
     the library asked for a bigger breaker than it now gets;
   - the device has an inrush figure but the catalogue has no trip curve, so (b)
     could not be checked.

## Consequences

- Every example device runs below 1.04 A and has no inrush figure, so every example
  branch stays at 2 A. The golden tests do not change.
- Datasheet inrush peaks for switch-mode supplies are often 20 to 60 A for under a
  millisecond. With such figures in M14's library data, a C-curve set gives 6 A or
  10 A branches. That is the rule working as chosen. If Ali finds it too large, the
  answer is a DC multiple (item 2) or a duration rule (item 3), as a new question.
- Spares still repeat the largest branch rating on their feed.
