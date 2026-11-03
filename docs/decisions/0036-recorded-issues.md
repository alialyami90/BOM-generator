# 0036. Recorded issues

- Status: Accepted (Ali, 2026-11-03)
- Date: 2026-11-03
- Spec sections: Output requirements (OUT-2, OUT-8); Inputs the tool needs (document register)

## Context

Today a build doesn't remember that it was issued. To highlight what changed since the last issue
(OUT-8, ADR 0016) the engineer picks the previous workbook on the Build page every time, and the
register holds only document number, rev and issue date, so prepared, checked and approved names
live outside the tool. Ali's engineering workflow review (2026-11-03) asks that each issue is
recorded, the next build compares automatically and a Revision History sheet carries the names;
the agent implementation plan reserves this ADR for milestone M66. The sheet itself is ADR 0035.

## Decision

1. **Issue record.** `substation.yaml` gets `issues:`, a list in issue order. Each record holds
   `rev`, `date`, `file` (the issued workbook, relative to `substation.yaml` when inside the
   project folder, else absolute), `sha256` (of the file as written), `description`, `prepared`,
   `checked`, `approved` (names as they were at issue) and `accepted_warnings` (a copy of the
   accepted warnings in force at issue, point 4). Revs are unique within a substation. The
   example has none, so golden values don't move.
2. **Build as issued.** A new Build page action next to Build. It asks for the description in a
   dialog, writes the workbook and its check report as Build does, hashes the file and appends
   the record with the register's rev, today's date and the names. It refuses when the register's
   rev is already recorded ("Rev 00 is already issued; change the document's rev in Settings ›
   Documents first") or when the check report has a failure. Plain Build stays and records
   nothing. The CLI gets `bomgen build --issue "<description>"` with the same rules.
3. **Automatic compare.** Every build compares with the latest record when its file exists and
   its hash matches, without a picker. When the file is missing or its hash differs, the build
   warns ("Rev 00's recorded file has changed since it was issued") and falls back to the picker
   as today. A file chosen in the picker, or `--compare` on the CLI, always wins over the record.
4. **Accepted warnings.** Checks gets "Accept with reason" on a warning (never on a failure). The
   acceptance is stored on the substation, `checks.accepted:` with check id, subject, reason, name
   and date, so it holds before the first issue and across builds. A matching warning shows as
   accepted with its reason and no longer counts as open; an acceptance no warning matches any
   more is shown as unused and kept until removed. The issue record copies those in force.
   (The plan put the list only on the record; it also needs a home before the first issue.)
5. **Names.** `RegisterEntry` gains optional `prepared`, `checked`, `approved`, edited per
   document in Settings › Documents. They print on the Revision History sheet only; page headers
   and footers stay as they are (Q67, Ali 2026-11-03).
6. **Previous issues outside the tool** keep working through the picker; a record can't be made
   for a file the tool didn't write.

## Consequences

- The second and later builds compare with no clicks, and the history sheet and record agree
  because both come from `issues:`.
- The hash catches an issued file edited or replaced after issue; moving the project folder keeps
  relative paths working, a file outside it needs the picker again.
- `issues:` and `checks.accepted:` are ordinary YAML, so a hand edit can change them; the record
  is a convenience, not a signature.
- New fields round-trip through `io/fields.py`, the schema export and `docs/ui/editing.md`.
