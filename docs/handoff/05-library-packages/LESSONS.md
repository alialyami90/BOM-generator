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
- **Environment trap:** `pip show bomgen` is an editable install of `/home/user/BOM-generator`; a git worktree
  imports that checkout's `src`, not its own. Gate results from a worktree are wrong unless run with
  `PYTHONPATH=src`. I misreported 3 failures as main's; A1 corrected it. Check `bomgen.__file__` first.
- **Drift (B5, 2026-10-28):** none in code; main moved by docs only. The container had no
  install, and PATH `mypy` uses another Python (use `python -m mypy`). See STATE environment note.
- **Device records are edited like the library, keyed by `part_id`.** Why: one op format for the
  app's pending set. Rejected: a field-per-function record API. Records stay in their file; new
  ones go to `device-db/local.yaml`, so unchanged files keep their bytes.
- **Pydantic union errors** (`int | float`) come back once per member with the member as an extra
  loc segment; cut the loc where the data reaches a scalar and keep one message per location.
- **Another agent may change my files on main** (#165 by A1/B3 added `ac_rated` and amended ADR
  0018). Fetch and read main's ADR before amending it.
