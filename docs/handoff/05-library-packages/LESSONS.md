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
- **Reserved CSV ids use a character `BrandId` forbids.** `default_dc` (underscore) names
  `catalogues.mcb_dc`, so it can never clash with a brand id (`^[a-z0-9][a-z0-9-]*$`). Rejected: a separate
  `mcb_dc.csv` (one more table for one row) and `default-dc` (a valid brand id).
- **Every catalogue key must be in `_compare`'s list** in `csv_import.py`, or a change to it never reaches
  the `changes` check or the app's edits (`mcb_dc` was missing until #179).
- **Row messages go through `plain_message`** (example values for number, whole number, bool and choice
  errors; "Input should be" → "Must be"). Two places build row problems: `_Assembly.model_problems`
  (catalogues) and `_device_problems` (devices); keep both on `plain_message`.
- **Split ADR edits from checkpoints.** B1 refused an ADR amendment inside a checkpoint PR (#167 → #170).
- **Push mechanics:** force-push is refused; after a squash-merge reset the branch to `origin/main` and
  `git merge -s ours origin/<branch>` before pushing. A plain `git push` then works.
- **Read the reviewer's PR body for the "why".** B1 relayed "wording of the changes check"; the reason
  (rows go to the pending set, not saved) was only in #178's body. Read the source PR before guessing.
