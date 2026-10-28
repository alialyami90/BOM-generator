# 0016. Check report and revision comparison

- Status: Proposed
- Date: 2026-10-28
- Spec sections: Data model and generation order (step 15); Output requirements
  (OUT-8); Derivation rules → DC distribution

## Context

Step 15 asks for a check report on SFPs, DC mains, airflow and DI capacity, and OUT-8
for yellow cells "changed since the previous revision". Plan Q3 keeps the 16 A mains
of 001/002 as `main_mcb_override_a` and says the report flags them; Q10 adds
`bomgen build --compare previous.xlsx`. The engine builds the report and the
comparison; the CLI only renders them and sets the exit code (plan M7).

## Decision

1. The report is a list of `CheckItem`s (check, status pass/warn/fail, panel, subject,
   message, the compared numbers), rendered as text or JSON. A failed item makes the
   build exit non-zero; a warning never does.
2. SFPs: the non-RJ45 allocations of a port plan, spares excluded, against the host's
   `sfp_slot` port groups × its units. An SFP fits a slot of its speed or faster. A
   host without a port inventory is a warning, not a failure.
3. DC mains: Q1/Q2 below ΣQ fails; a rating that differs from the rule (an override)
   is a warning naming the rule's rating (Q3). ΣQ is the cabinet's own DC loads, the
   panel's 125 V DC block on the Power Consumption sheet; loose loads fed from the
   panel through a QCOD are not in it. This gives the spec's ≈ 7.1 A and ≈ 1.5 A.
4. Ventilation: fans against the required airflow, natural convection against
   TMax − TInt, as the cabinet was built (plan Q4), then the line-up.
5. DI capacity: Σ `di_inputs` × units over every BOM row and kit child of the
   substation against Σ HWIO. With HWIO but no `di_inputs` in the library the check is
   a warning; with neither it is left out.
6. The library version a project recorded against the active one is a warning
   (`library_mismatch`, plan M8).
7. Revision comparison reads the previous workbook with openpyxl (already a runtime
   dependency, ADR 0003) from the values Excel last saved. A table starts at a row
   whose A–G are the BOM headers; its rows are those with a description. The panel
   table is the first on the panel's sheet, the loose table the second on its host's.
8. Rows match by tag and occurrence; rows without a tag match under the tag above
   them, by description, then in order. Cells compare as written: the sum's value,
   HWIO 0 blank, a kit child's tag blank (merged under its parent), text trimmed.
   Changed cells, and every cell of an added row, join the row's `revised` marks
   from `revision.highlight`; removed rows and dropped sheets are only reported.

## Consequences

- The comparison needs an issued workbook that Excel (or the generator) saved with
  cached values; a file whose formulas were never calculated reads as blanks.
- Renumbered SR.NO never marks a row: column A is not compared.
- Renaming a tag shows as one row removed and one added, highlighted in full.
