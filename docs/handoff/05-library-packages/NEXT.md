# Next

**First action: rerun the README step 4 drift check and record any drift, then answer A11's questions on the Library editors (via A1 or A11's thread) from the code and ADR 0018.** Nothing else is requested; do not invent code work.

## Tasks in priority order
1. Answer A11 (M16 app side, [`docs/ui/editing.md`](../../ui/editing.md)). Facts to give:
   - edits are JSON ops `set | insert | remove` with a `path` list (string = mapping key or the
     item's `part_id` / brand `id`; int = list position); `apply_edits` / `check_field` /
     `save_edits` in `edit.py` and `local.py`;
   - `preview_csv_import` returns `checks`, `problems` (table, row, column, message, key),
     `changes`, `edits` (the same changes as edit ops for a pending set) and `library`;
     `skip_invalid=True` turns row failures into warnings;
   - alternatives are only the `alt_group` key; `compare_alternatives` gives the rows.
   Done when A11 has what it needs; no code unless a real gap appears.
2. If a gap appears, one small PR per gap, tests first, named after the rule; gate passes, PR open
   for A1. Files: `src/bomgen/library_store/` and its tests only.
3. Run the gate with `PYTHONPATH=src` when in a worktree (see STATE environment note).

## Optional, not requested (A1 said skip until someone needs it)
- `LibraryPackageError` carrying manifest and `active` data.

## Don't do
- No edits to `src/bomgen/app/`, `models/`, `io/`, `engine/` or `data/device-db/` (A11, A2, A9, A3).
- No new model fields without A2; a new model field needs its CSV column in the same PR
  ([ADR 0018](../../decisions/0018-library-csv-exchange.md) Consequences).
- No ADR without a number from A1.
- Never commit generated `.xlsx`; one milestone per PR.
