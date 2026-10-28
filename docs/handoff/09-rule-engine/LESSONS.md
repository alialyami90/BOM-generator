# LESSONS: role 9 (append-only; mark replaced entries "superseded by …")

## Decisions too small for an ADR
- 2026-10-28, `loose_table` returns None when it has no rows (#123). This follows ADR 0020:
  the sheet is written only while it has rows. Rejected: an empty `LooseTable` that the
  sheets and the writer would each have to skip, which puts the rule in three places.
- 2026-10-28, `set_by` lists every condition that alone gives the rating, in the order
  running, inrush, floor (ADR 0019 item 5). PSA3-QCOD-1's annunciator at 1.04 A gives
  "running,floor". Rejected: only the binding condition, because ties hide why a rating
  holds.
- 2026-10-28, there is one `dc_float` MCB item, and only when some panel has DC mains. A
  device without `input_v_max` gets no line. Rejected: one line per MCB or per device,
  which would flood the report with unknowns.
- 2026-10-28, the spare branch rating is the largest used branch on its feed, or the
  floor when the feed has none (`dc_dist.py`). It keeps the ADR 0019 rule that spares repeat
  the largest rating.
- M7, revision rows match by tag, and untagged rows (kit children) match under the tag
  above them, by description and then in order. Rejected: matching by position, because
  one inserted row would mark every row below it.
- M7, ΣQ in the check report is the cabinet's own DC loads (ADR 0016), not the feed total.

- 2026-10-28, the MCB helpers (`rating_at_least`, `rating_above`, `mcb_line`) take the
  `McbCatalogue` to use (#154). Rejected: a `dc: bool` flag or keeping `library` and
  reading `dc_mcb` inside, which let a caller size from the wrong set silently.
- 2026-10-28, CINC stays on the AC set (#154): it is group E's "Main Auxiliary AC Supply"
  breaker (ADR 0023 point 1). A1's task note had listed it with the DC items.

## Failed approaches and what they taught
- M15 was written before A2's #97 (the M13 fields) merged. A local stand-in patch kept in
  the scratchpad let the tests run. It was never committed and was reverted before the
  PR. Lesson: when a field is missing, wait for its owner or stub it locally, and never
  commit another role's model change.
- mypy (strict) rejected importing `BranchSizing` from `engine.dc_dist`, where it was not
  re-exported. Import models from `bomgen.models.calc`.
- A golden that expected `set_by == "floor"` for every branch failed on the annunciator.
  Check what each example load actually is before writing the expected value.
- #123 conflicted with A2's #122 in `tests/unit/engine/test_engine_pipeline.py`. Lesson: put
  new tests away from another open PR's insertion point, and check with
  `git merge-tree --write-tree HEAD origin/<their-branch>` before pushing.
- Merges of `docs/decisions/README.md` and `docs/plan.md` conflicted while M13 and M15 were
  both open. Resolve by keeping every row in number order and both notes.
- The first attribution URL in #123's body was wrong (fixed with `update_pull_request`).
  Copy the attribution lines from the session's instructions, not from an older PR.

## Working notes
- 2026-10-28, B9 resume drift: none in code. The stash was not in the new container (as
  expected), and ruff formats more files (309) after other roles' merges.
- 2026-10-28, `resolve_catalogues(library, CatalogueChoice(...))` lets engine tests cover the
  brand choices without the loader; `engine_factories.library(mcb_brands=[...])` fills
  `catalogue_brands.mcb`.
- Run the tools as `python -m ruff|mypy|pytest`. The full suite takes about 2 minutes,
  golden about 7 s.
- Drift at this checkpoint: none (first checkpoint for role 9; no earlier STATE/NEXT).
- 2026-10-28 validation by a fresh reader found these gaps, now fixed: short paths, what
  `test_cli_build.py` and `kits.py` belong to, the gate run on a commit other than HEAD, the
  stash being local, and no fallback when A1 assigns nothing. Write full paths.
- 2026-10-28, A1: only Ali accepts ADRs. The checkpoint's draft task to mark ADR 0016 and
  0019 Accepted was dropped; A1 offers Ali a batch card instead.
- 2026-10-28, #141 conflicted on ROSTER.md with the neighbouring rows that merged first.
  Merge main and keep main's rows, changing only role 9's row.
