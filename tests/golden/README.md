# Golden tests

Build the workbook from `examples/` and compare it with the example values the
spec states (tags, MCB counts and ratings, terminal block quantities, power and
heat totals, airflow). Each expected value cites the spec section it comes from,
or the example workbook cell it was transcribed from. All tests here carry the
`golden` marker.

| Module | Milestone | What it checks |
| --- | --- | --- |
| `test_example_inputs.py` | M1, M1b | `examples/` loads and validates from the CLI as one project with one substation; panel identity, unit watts, L1 HWIO override, psa2 mirroring, DC spares, the L1 library example, breaker and terminal block codes, WS console size, design constants; the substation's equipment, port plans, layout inputs and rack heights match the hand-written panels |
| `test_engine_groups_a_d.py` | M2 | every group A–D row of the example cabinets and the loose-material table; expected rows in `expected_groups_a_d.py` |
| `test_engine_groups_e_h.py` | M3 | every group E–H row of the example cabinets, separators, SR.NO 1…71 on cabinet 001, DC branches, incoming and main ratings, aux contacts, HWIO totals 17/17/6; expected rows in `expected_groups_e_h.py` |
| `test_engine_power_heat.py` | M4 | power totals and blocks per cabinet and for the external equipment, required airflow, the line-up check, the WS console's natural convection |
| `test_workbook.py` | M5 | the written workbook: sheet order, BOM merges, every formula recalculated with pycel to the value the writer cached (Q15), power totals and airflow from the recalculated sheets |
| `test_cli_build.py` | M7 | `bomgen build` on the project, one substation of it and its `substation.yaml` writes the OUT-2 file name with every sheet; the check report, `--no-checks`, exit 1 on a failed check, `--compare` |
| `test_check_report.py` | M7 | the example's step 15 check report: no failed check, ΣQ per cabinet, the 16 A mains of 001 and 002 as warnings (Q3), ventilation, DI capacity, SFPs |
| `test_revision_round_trip.py` | M7 | the written example workbook reads back as its build, and a changed description is highlighted in the next issue (OUT-8) |
| `layout/test_layout_golden.py` | M1c | design rule R10: the example substation's sizing, generated panels and port plans match `layout/expected_panels.yaml` (3 L1 switches per side), no layout issues, psa1 feeds the annunciator |

