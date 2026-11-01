# 0028. Power Consumption follows the branch MCB

- Status: Rejected (Ali, 2026-11-01, kept the spec formula)
- Date: 2026-10-31
- Spec sections: Power Consumption sheet → Formulas; Relationships between sheets; ADR 0019; ADR 0025

## Context

"Relationships between sheets" says the branch MCB ratings from Power Consumption's sizing
columns set the ratings in BOM group F. The Formulas section gives P = ⌈O⌉ with V = 125 for DC
and 230 for AC. Both sentences predate ADR 0019 (branch sizing by running current, inrush and the
2 A floor) and ADR 0025 (one AC branch per VAC device), so the sheet and the BOM disagree:

- Every example device has P = 1 A while its Q1.n/Q2.n prints 2 A (the floor). With the
  shipped library, SEL-3555 and SEL-3355 have P = 1 A against a 6 A branch sized for inrush
  (audit 2026-10-31, ENG-4).
- Branch sizing divides by the part's own `voltage_v`, but Power Consumption always divided by the
  system voltage, so a 120 VAC gateway showed `=I/230` beside a branch sized at 120 V (ENG-5).

A1 decided on 2026-10-31 to keep the spec's intent (the sheet and group F agree) and to record
the change here.

## Decision

1. **P is the row's own branch MCB.** A row that has its own branch prints the rating its branch
   gets from `dc_dist.branch_sizing` as a value: a group B unit with one or two power supplies or
   a VAC supply (ADR 0025), and a loose load fed from a panel's QCOD. A formula can't repeat the
   ADR 0019 sizing, because it reads the catalogue's trip curve. Rows on a shared circuit
   (housekeeping, lamps, fans, kit children) keep `=ROUNDUP(O,0)`.
2. **V is the part's own voltage.** Column C and the divisor in N use the part's `voltage_v`, and
   the system voltage only when the part gives none, as branch sizing already does.

## Consequences

- In the example, the 16 own-branch P cells go from 1 to 2 and become values, so the golden
  formula count goes from 955 to 939. No spec golden value moves: every example part is drawn at
  125 V or 230 V already, and P doesn't feed Q, R or any total.
- The spec's Formulas line (P = ⌈O⌉, V = 125/230) needs a note pointing here once Ali accepts.
- P is now a value on most rows, so editing W in Excel doesn't change it; the BOM's group F
  rating, which P now mirrors, doesn't change in Excel either.

## Outcome

Ali rejected this decision on 2026-11-01 and kept the spec formula. Both decisions were
reverted: P is `=ROUNDUP(O,0)` on every row, and V is the system voltage (125 V DC, 230 V AC),
as the spec's Formulas line gives. The golden formula count is back to 955.
