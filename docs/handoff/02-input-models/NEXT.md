# NEXT — role 2

**Next action:** write the failing test `test_a_brand_not_rated_for_ac_cannot_be_the_mcb_choice`, then add `McbBrand.ac_rated: bool = True` and the loader refusal (option (a), which A1 chose on 2026-10-28).

## Tasks, in priority order

### 1. A DC-only MCB brand must not size AC branches (M13 follow-up)
- **Why:** #130 adds `schneider-c60h-dc`, which is DC only. Its
  `magnetic_trip_multiple` is null, yet `McbCatalogue.magnetic_multiple` still returns
  5, the lower bound of curve C. `engine/ac_dist.py` uses the same
  `library.catalogues.mcb` for the AC branches. Nothing in the model marks a brand as
  DC only, so no check can catch it today.
- **Options put to A1 (2026-10-28, A1's thread):**
  - (a) Add `McbBrand.ac_rated: bool = true`. The loader then reports a located error
    when a substation picks an `ac_rated: false` brand for `catalogue_choice.mcb`.
    Every panel has AC branches, so no conditional is needed. A3 sets the flag on
    C60H-DC.
  - (b) Split `catalogue_choice.mcb` into an AC choice and a DC choice. This changes
    the schema and A9's engine, so it needs an ADR, and A1 assigns the number.
  - **Decided (A1, 2026-10-28): (a) now, with no ADR needed, and a readable message.**
    Whether (b) follows is Ali's call; A1 is asking him on a card and will pass the
    answer on.
- **Files for (a):** `src/bomgen/models/library.py` (`McbBrand`),
  `src/bomgen/io/references.py` (`catalogue_choice_issues`),
  `tests/unit/test_catalogue_choice_loader.py`, and the regenerated `schemas/`.
- **Depends on:** nothing. The test uses a fixture brand, so #130 does not need to merge
  first. Coordinate with A3 so it sets `ac_rated: false` on C60H-DC.
- **Tests first:** `test_a_brand_not_rated_for_ac_cannot_be_the_mcb_choice` and
  `test_mcb_brands_are_ac_rated_by_default`.
- **Done:** the gate passes and a PR is open for A1. Then tell A3 to set the flag in its
  data.

### 2. Review A11's use of the writers (M17/M18 app side)
- Answer questions on `io/edit.py`, `io/fields.py`, `io/panel_edit.py`,
  `io/loose_edit.py` and `io/lifecycle.py`. Small API additions A11 needs are A2's to
  make: one PR each, with tests and a paragraph in ADR 0021 or 0022.

### 3. Q23 (waiting on Ali)
- Keep the default (the masters). Act only when Ali answers, and record the answer in
  plan section 6.

## Not tasks (by design)
- `fed_from` accepts any panel id of the substation, and the layout reports a dropped
  one (`engine/layout.py`). See ADR 0022 point 4.
- `bomgen layout` writes generated panel files with PyYAML. Those files carry no hand
  comments (ADR 0021, Consequences).
- The default iC60N's `dc_float` WARN and #130's slower suite were raised on #130 for
  A1/A3. The data is A3's.

## Don't do
- Don't edit `engine/`, `sheets/` or `library_store/`; tell their owners (A9, A10, A5).
  The `part_id is not None` guards #122 added in `dc_dist.py`, `housekeeping.py`,
  `pipeline.py` and `kits.py` were the exception A1 agreed to.
- Don't change `examples/library.yaml` data: it is A3's under Q38 (examples keep the
  spec's values, and the golden values must not move).
- Don't re-open #122/#124 or redo the empty-loose-table change (A9 did it in #123).
