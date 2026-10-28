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

Power and heat arrive with M4, the generated panel layout in `layout/` with
M1c; see `docs/plan.md`.
