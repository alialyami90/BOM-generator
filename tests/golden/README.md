# Golden tests

Build the workbook from `examples/` and compare it with the example values the
spec states (tags, MCB counts and ratings, terminal block quantities, power and
heat totals, airflow). Each expected value cites the spec section it comes from,
or the example workbook cell it was transcribed from. All tests here carry the
`golden` marker.

| Module | Milestone | What it checks |
| --- | --- | --- |
| `test_example_inputs.py` | M1 | `examples/` loads and validates from the CLI; panel identity, unit watts, L1 HWIO override, psa2 mirroring, DC spares, the L1 library example, breaker and terminal block codes, WS console size, design constants |

Tests that build BOM and calculation sheets arrive with milestone M2 onwards; see
`docs/plan.md`.
