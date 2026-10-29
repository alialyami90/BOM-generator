# NEXT — role 2

**Next action:** none is assigned by the lead. First rerun the checks in README step 4.
Then ask the lead (role 1) whether anything is queued. Then take task 1.

## Tasks, in priority order

### 1. Compute the unset `mcb_dc` fallback instead of storing it (A1's note on #151)
- **Why:** when `mcb_dc` is unset, `resolve_catalogues` (`models/library.py`) copies the
  `mcb` brand into `Catalogues.mcb_dc`. A brand without `dc_rating_v` then sits in a
  field whose validator refuses it. Only `model_copy`, which skips validators, stops it
  failing. If anything re-validates a resolved library, a project that loads today would
  be refused.
- **Fix:**
  - Store `mcb_dc` in the resolved catalogues only when `mcb_dc` is written (a brand id or
    `default`). Otherwise leave it as the library's own `catalogues.mcb_dc`, or `None`.
  - `Catalogues.dc_mcb` already falls back to `mcb`.
  - Keep ADR 0023 point 2: `{mcb: brand}` with no `mcb_dc` must still size DC with that
    brand, even when the library carries its own `catalogues.mcb_dc`. So when `mcb` is
    written and `mcb_dc` is not, the resolver sets `mcb_dc` to `None` instead of
    copying.
  - When neither key is written, the library's own `catalogues.mcb_dc` still wins.
- **Tests first** (`tests/unit/test_library_alternatives.py`,
  `test_catalogue_choice_loader.py`):
  - `test_a_resolved_library_validates_again`: `Library.model_validate(resolved.model_dump())` does not raise.
  - Keep every existing ADR 0023 test green.
  - Golden values must not move.
- **Callers to check:** `engine/dc_dist.py`, `engine/mcb.py`, `checks.py`,
  `app/projects.py` and `io/references.py`. All of them read `catalogues.dc_mcb`, never
  `catalogues.mcb_dc` directly. Grep to confirm before you change the stored value.
- Not urgent: A1/B1 said it is not blocking.

### 2. Answer the app's questions on the writers
- Role 11 (desktop app) calls these:
  - `io/fields.py`, `io/edit.py`, `io/panel_edit.py`, `io/loose_edit.py`, `io/lifecycle.py`
  - `fields.part_users` and `fields.assumed_fields`
- A small API addition is role 2's work: one PR each, tests first, and a line in ADR 0021
  or 0022 when it changes a writer rule.

### 3. Q23 (waiting on Ali)
- Keep the default (the masters). Act only on Ali's answer, and record it in plan section 6.

### 4. If Ali answers the `generated_panels` defaults
- Change `_blank` in `io/lifecycle.py` and its test
  `test_a_blank_substation_seeds_generated_panels_so_equipment_can_be_added`.
- Drop the `# ASSUMED` mark on any value Ali confirms.

## Not tasks (by design, or other roles')
- The engine's DC sizing from `dc_mcb` is done (role 9).
- The writer side of `power_footnotes` is role 10's.
- `fed_from` accepts any panel id (ADR 0022 point 4).
- `bomgen layout` uses PyYAML (ADR 0021).
- `examples/library.yaml` device data is role 3's (Q38).
- `data/device-db/` is role 3's.
- `library_store/` is role 5's.

## Don't do
- Don't edit `engine/`, `sheets/`, `app/` or `library_store/`. Tell their owners.
- Don't change `examples/` values the golden tests check without the lead and a spec citation.
- Don't force-push: it is blocked here. To reuse the one branch after a squash merge, see LESSONS ("One push branch per session").
- Don't commit generated `.xlsx` files.
