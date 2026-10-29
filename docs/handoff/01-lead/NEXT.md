# Role 1 (lead): next

**Next action:** follow `docs/handoff/README.md` (fetch, status, gate). Then run
`list_pull_requests state=open` on `alialyami90/BOM-generator` and review and merge whatever
is ready, using the procedure in LESSONS.md → "Review procedure". Then repost the open
question to Ali (item 1).

1. **Ask Ali what comes after v0.2.1.** The old card (STATE → "Waiting on Ali") lives in the
   retired B1 thread, so his answer can't reach you. Post a fresh `request_decision` in your
   own thread: "What should the team do after v0.2.1?" with options "Test v0.2.1, send
   feedback" (recommended: everything he asked for in v0.2 shipped and no one has used it in
   the field yet), "I'll describe v0.3 now". Close the old card with `close_decision` (no
   `chose`) if you can; if not, ignore it.
2. **When Ali's feedback arrives:** write it into `docs/backlog.md` as numbered points (as
   for v0.2), propose milestones in `docs/plan.md` (next milestone after M18 is M19), give
   any decisions an ADR (0024 on) or a plan question (Q42 on), and brief each owning role
   per `docs/agents.md` → "Owns". One PR per milestone.
3. **One card for the ASSUMED seeds** (STATE → "Known gaps"): show Ali the cabinet number
   pattern, the enclosure and the document number/date defaults a new substation gets, and
   recommend "Keep them, edit per project in the app". If he changes them, role 2 owns
   `src/bomgen/io/lifecycle.py`.
4. **Spec catch-up** (STATE → "Known gaps"): when Ali has time, offer one card to bring the
   spec in line with ADRs 0017, 0019, 0020, 0022, 0023 and Q35–Q41, through the process in
   `docs/spec/`. Don't edit the spec without his go-ahead (CLAUDE.md).
5. **Excel header fit (Q11, role 10's one open item).** Only Excel's Print Preview shows
   whether the calc-sheet header's three lines overlap the table. Card for Ali: "Does the
   header on Power Consumption and Heat Dissipation overlap the table in Excel's Print
   Preview?" Options "It fits" (recommended: the size is computed to fit at the print scale)
   and "It overlaps". Pass the answer to role 10; its NEXT.md task 1 says what to change
   (`LINE_SPACING` 1.2 → 1.4 in `src/bomgen/sheets/header_footer.py`) and record it in Q11.
6. **Next release** (v0.2.2 or v0.3.0): STATE → "How a release happens". Hold other merges
   between the CHANGELOG merge and the published release.
7. **Checkpoints:** every role writes a docs-only checkpoint PR touching only its own
   `docs/handoff/NN-*` folder and its own ROSTER row. Merge them as they arrive; ROSTER rows
   don't conflict when each PR touches only its own row.

## Don't do

- Don't edit other roles' files. Send the fix request to the owner (agents.md "Owns").
- Don't bump the version outside a release PR: on main it publishes at once.
- Don't change golden values unless an ADR changes them (Q38 keeps `examples/` as the spec
  example; the shipped library is separate in `data/library/`).
- Don't merge app, packaging, pyproject or release-workflow PRs without a green "Build Windows
  installer".
- Don't mark ADRs Accepted; only Ali does.
- Don't ask Ali anything in plain text; always a card with one option recommended.
- Don't ask Ali to merge. He said: "Can you stop asking me for merges? Check the merge for
  conflicts and merge it".
