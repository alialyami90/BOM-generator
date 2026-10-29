# Role 3 next (C3)

**Next action:** rerun the README step 4 checks, then do finding 30. That means sourced power figures for the 11 skipped alternatives in `data/device-db/`, opened as a data PR for B1.

## 0. First, on any resume

1. Run `git fetch origin main`, `git checkout -B <your thread branch> origin/main`, then
   `pip install -e ".[dev]"`.
2. Run the gate: `ruff check . && ruff format --check .`, `python3 -m mypy`,
   `python3 -m pytest -q`. pytest takes about 6 min, so run it in the background.
3. Run `python data/library/build.py` and check that `git status` is clean. If it is not,
   someone edited the example library or device-db without regenerating. Regenerate, and
   add the result to your next PR.
4. Check that `/mnt/project-files/handoff/03-device-db/` still has the generator
   (reference.md §3).

## 1. Finding 30: power figures for 11 skipped alternatives (reference data)

- **Goal.** Give each alternative listed in `docs/device-db-findings.md` item 30 a sourced
  `unit_power_w` with `power_basis` and `power_note`, as README "Electrical data for the
  library (M14)" describes. If a datasheet gives inrush, add that too.
- **Records:**
  - `data/device-db/network.yaml`: `SEL-2730M-EXT`, the Siemens low tier
    (SCALANCE XR324-4M EEC; use the 125 V DC code 6GK5324-4GG10-4JR2, finding 27).
  - `data/device-db/sel-automation.yaml`:
    - `SEL-3555-GW` and `SEL-3555-RTAC`: Hitachi low and high tiers (RTU540 is
      discontinued and 560CMG10 was not found; finding 27, so a replacement model may
      be needed).
    - `SEL-2488`: the Arbiter mid tier (1202B/C).
    - `SEL-2240`: Hitachi low and high.
    - `SEL-3355`: Siemens IPC427E, IPC647E and IPC847E (IPC647E is 2U).
- **Rules.**
  - Never invent a figure. Set `verified` per the README.
  - Use at most ~35 web fetches per run (LESSONS.md).
- **Then:**
  1. Update finding 30.
  2. Run the gate. `test_device_db.py` covers the power basis.
  3. Open the PR for B1.
- **Second PR (needs B2's OK for `examples/`):** add the now-powered tiers as library parts
  using the rules in reference.md §3. Then run `python data/library/build.py`, commit both
  files, and check that the goldens and B9's `test_engine_shipped_library.py` are unchanged.

## 2. Finding 31: `di_inputs` for the SEL-2244-2 alternatives

- **Goal.** For each SEL-2244-2 alternative, record the module's digital input count in
  `data/device-db/sel-automation.yaml`, then set `di_inputs` on its library part. This
  follows the same two-PR route as §1, with B2's OK for `examples/`.
- **Why it matters.** Without `di_inputs`, a project that picks one of these modules has
  no input count for it (finding 31). Check how the engine uses `di_inputs` (B9) before
  you rely on it.

## 3. Ask B1 whether the M14 generator should move into the repo

- **Where it is.** Today the generator lives only in project files and is not idempotent.
- **Suggestion.** Make it idempotent (skip existing part ids) and add it under
  `data/device-db/tools/` (role 3's folder). That needs the ruff and mypy gate to pass.
- **When.** Ask before §1's second PR, since that PR would use it.

## Don't do

- **Example library.**
  - Don't put the originals' inrush or input range in `examples/library.yaml` (Q38); it
    moves the goldens.
  - Don't change the default MCB set from iC60N (Q37).
  - Don't research a DC-rated firewall to replace the FGR-60F (Q41).
- **Generated file.** Don't hand-edit `data/library/psa-devices.yaml`.
- **Other roles' files.** Don't edit them without B1 assigning them:
  - `src/` (B2 models, B5 library_store, B9 engine)
  - `examples/` (B2)
  - `release.yml` and ADR 0009 (B6)
  - other roles' tests
- **Version.** Don't bump psa-devices without B1, B2 and B6 agreeing (STATE.md risks).
