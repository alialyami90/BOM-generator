# NEXT — role 2

**Next action:** none assigned. Check A1's thread and the open PRs, then take task 1.

## Tasks, in priority order

### 1. Compute the unset `mcb_dc` fallback instead of storing it (A1's note on #151)
- **Why:** `resolve_catalogues` copies the `mcb` brand into `Catalogues.mcb_dc` when
  `mcb_dc` is unset. A brand without `dc_rating_v` then sits in a field whose validator
  refuses it, and only `model_copy` keeps it from failing. If anything re-validates a
  resolved library, a project that loads today would be refused.
- **Fix:** store `mcb_dc` only for a written `mcb_dc`. `Catalogues.dc_mcb` falls back to
  `mcb`. Check that a library's own `catalogues.mcb_dc` still wins when neither key is
  written, and that `{mcb: brand}` with no `mcb_dc` still sizes DC with that brand
  (ADR 0023 point 2). That may need the resolver to clear `mcb_dc` when `mcb` is written.
- **Tests first:** `test_a_resolved_library_validates_again` plus the existing ADR 0023
  examples.
- Not urgent: A1 said not blocking. Agree timing with A1.

### 2. Review role 11's use of the writers (M17/M18 app side)
- Answer questions on `io/edit.py`, `io/fields.py`, `io/panel_edit.py`, `io/loose_edit.py`
  and `io/lifecycle.py`. Small API additions are role 2's: one PR each, with tests and a
  paragraph in ADR 0021 or 0022.

### 3. Q23 (waiting on Ali)
- Keep the default (the masters). Act only when Ali answers. Record the answer in plan §6.

## Not tasks (by design)
- The engine's switch to `catalogues.dc_mcb` is role 9's. The writer side of
  `power_footnotes` is role 10's.
- `fed_from` accepts any panel id (ADR 0022 point 4). `bomgen layout` uses PyYAML (ADR 0021).
- The plan example's brand id `c60h-dc` (should be `schneider-c60h-dc`): A1 fixes it.

## Don't do
- Don't edit `engine/`, `sheets/` or `library_store/`; tell their owners.
- Don't change `examples/library.yaml` data: it is role 3's under Q38.
- Don't force-push: it's blocked here. To reuse the one branch after a squash merge, reset it
  on main and `git merge -s ours origin/<branch>` before pushing (LESSONS).
