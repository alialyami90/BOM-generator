# Lessons (append-only)

- **Edits are path-based JSON, not one function per field.** Why: the app's pending set maps onto
  ops, and every model field is then editable. Rejected: an `edit_device(...)` per field (explodes
  with each model change). See ADR 0018 "Amendment: edit operations".
- **CSV import yields both a saved library and edit ops.** The CLI keeps the file's row order and
  saves at once; the app takes `edits` into its pending set. Rejected: all-or-nothing only.
- **Row problems fail by default; `skip_invalid` makes them warnings and skips the rows**
  (an existing device keeps its installed values).
- **Partial CSV semantics:** a missing table or column leaves the installed values; a present table
  replaces that table's rows. Rejected: requiring every table.
- **Excel formulas:** a bad cell starting `=`, `+`, `-`, `@` gets "(probably an Excel formula)";
  valid values are never flagged (A1's review note on #116).
- **Failed approach:** string cells fed to strict pydantic number validators failed; fixed with a
  `_number` pre-parse. `StrictBool` is needed for `supply_ok`.
- **Failed approach:** a bulk `sed` that stripped needed `type: ignore` comments; use a typed helper
  (`_device`) in tests instead.
- **Shared container changes:** `write_bundle` creates missing folders and turns `OSError` into
  `LibraryPackageError`; `partial.unlink` in `finally` must suppress `OSError` (a file in the folder's
  place raised `NotADirectoryError` there).
- **Install rollback:** after the version folder is swapped in, a failed `active` write removes the
  new folder and puts the `.replaced-<uuid>` one back (`store.py` `install`).
- **PR mechanics:** branch name is fixed, so each PR is cherry-picked onto fresh `origin/main`, then
  `git merge -s ours origin/<branch>` so a plain push works. PR bodies start "Written by A5 ... for
  A1 to review.", assign `alialyami90`, subscribe to PR activity.
- **Drift:** none found; there was no earlier STATE.md to compare with.
