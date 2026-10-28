# LESSONS — role 2 (append-only)

## Decisions too small for an ADR
- **Writers compare problems by (file, location, message), not by line.** Lines move
  with an edit, so comparing lines would block sound edits. (ADR 0021 point 2.)
- **`Project.substations` stays required but may be empty** (M17d). A
  `default_factory` would have hidden a misspelt key, and the
  `test_*misspelt*` test caught it. The build refuses an empty substation ("has no
  panels yet").
- **A loose item's "Designation" is the existing `tag`.** No new key, so existing files
  load unchanged. (ADR 0022 point 1.)
- **Removing the last loose item leaves `items: []`.** `host_panel` and `title` are
  kept, and the engine prints no sheet without rows (#123).
- **`validate_*` functions are dry runs of the writer.** One code path, so the form's
  message is exactly what the save would report.

## ruamel.yaml round-trip (traps found while building `io/round_trip.py`)
- Settings that make `examples/` dump byte-identical: `indent(mapping=2, sequence=4,
  offset=2)`, width 4096, `_PaddedEmitter` for `{ a: 1 }`, and `null` written out.
- A comment after an entry is `ca.items[key][2]` (map) or `[0]` (seq). A flow
  collection's comment sits in its parent's slot. Blank lines before a key may sit in
  `ca.items[key][1]`.
- Failures, and what fixed them:
  - Deleting or emptying produced invalid YAML. Fixed by moving tails (`_take_tail` /
    `_put_tail`, `edit_document`) and writing empty containers in flow style.
  - Double blank lines came from `[1]` lead comments. Fixed by `_drop_blank_lead`.
  - The comment column shifted when a value grew. Fixed by `_shift_comment`.
- `mkstemp` makes files 0600. `write_atomic` keeps the old mode (new files get 0644)
  and creates the parent folder (A1 review on #106/#112).

## Testing
- Copy shared fixture dicts (`dict(ABB_MCB)`) before mutating them: one test leaked
  into the next.
- The suite is slow (2 min on main). Run the module under test first, then the whole
  suite, in the background, before you commit.
