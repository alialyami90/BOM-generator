# Next

**First action: run the drift check in [`../README.md`](../README.md) step 4 (with `pip install -e ".[dev]"` and
`python -m mypy`, see STATE "Environment notes") and record any drift in LESSONS.md. Then wait for requests
from role 1 (lead) or role 11 (desktop app).** Nothing is requested; the role's milestones (M8, M8b, M16
store side) are all done and on main. Do not invent code work.

## When a request arrives
1. A question about the store, the edit ops or the CSV: answer from the code and ADR 0018 (its amendments
   at the end win over the decision text). Facts that are asked often:
   - Edits are JSON ops `{"op": "set" | "insert" | "remove", "path": [...], "value": ..., "index": ...}`. A
     string segment is a mapping key or, in a list, the item's `part_id` (devices) or `id` (catalogue
     brands); an int is a position. `apply_edits` / `check_field` (`edit.py`), `save_edits` (`local.py`).
   - Device records: the same ops keyed by `part_id` (`["SW-1", "datasheet", "weight_kg"]`);
     `apply_record_edits` / `check_record_field` (`records.py`); `save_edits(..., record_edits=...)`. Changed
     records stay in their `device-db/` file; new ones go to `device-db/local.yaml`.
   - `preview_csv_import(source, store, name, base=None, skip_invalid=False)` returns `CsvPreview`:
     `checks`, `problems` (`RowProblem`: table, Excel row, column, plain message, key), `rows`, `diff`,
     `changes` (per value), `edits` (the same changes as edit ops, for the app's pending set), `library`,
     `base`. `skip_invalid=True` turns row failures into a warning and skips those rows.
   - CSV tables: one file per table (ADR 0018 table). `catalogue_id` `default` is `catalogues.<kind>`,
     `default_dc` is `catalogues.mcb_dc`, any other id is a brand. A missing table keeps the installed
     rows; a present table replaces them; a missing column keeps the installed values.
   - Alternatives are only the `alt_group` key on devices; `compare_alternatives` gives the rows.
2. A bug or gap in my files: one small PR per gap, failing test first, named after the rule; full gate;
   PR body starts with the attribution block and "Written by C5 … for B1 to review"; assign `alialyami90`;
   subscribe to the PR; tell role 1 the number in its thread.
3. A new model field (A2/role 2 adds it): the CSV needs its column in the same PR, or a follow-up of mine
   right after ([ADR 0018](../../decisions/0018-library-csv-exchange.md) Consequences). The round-trip test
   with every field set (`test_a_device_with_every_field_set_survives_the_round_trip`) catches a missing one.

## Optional, not requested (only if someone asks)
- `LibraryPackageError` carrying manifest and `active` data.
- CSV tables for device-database records.

## Don't do
- No edits to `src/bomgen/app/` (role 11), `models/`, `io/` (role 2), `engine/` (roles 8, 9) or
  `data/device-db/`, `data/library/` (role 3).
- No new model fields yourself; ask role 2.
- No ADR changes inside a checkpoint PR; ADR edits go in their own `docs(adr): …` PR.
- No new ADR without a number from role 1. Never commit generated `.xlsx`; one milestone per PR.
- Never ask Ali to merge; ask Ali only on a decision card with a recommendation.
