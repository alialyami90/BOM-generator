# Role 3 next (B3)

**Next action:** fill finding 30. Find datasheet power figures for the 11 skipped alternatives, record them in `data/device-db/`, and open a data PR for A1.

## 1. Finding 30: power figures for 11 skipped alternatives (reference data, then M14 data)

- **Goal.** Each alternative listed in finding 30 gets a sourced `unit_power_w` with
  `power_basis` in `data/device-db/` (README "Electrical data for the library (M14)").
  Then add it as a library part.
- **Files.**
  - First PR: `docs/device-db-findings.md` (item 30) and the records the item lists:
    - `data/device-db/network.yaml`: SEL-2730M-EXT, Siemens low.
    - `data/device-db/sel-automation.yaml`: SEL-3555-GW and RTAC (Hitachi), SEL-2488
      (Arbiter mid), SEL-2240 (Hitachi low and high) and SEL-3355 (Siemens IPCs).
  - Second PR: `examples/library.yaml` (A2/B2's file, ask A1 first) and the regenerated
    `data/library/psa-devices.yaml`.
- **Depends on** nothing for the first PR. The second PR needs A1's OK to edit
  `examples/`. Web budget: about 35 fetches per run; the limit was observed during M14 and
  is not documented (LESSONS.md).
- **Acceptance.**
  - Every new figure cites a source, and `verified` follows the README rule.
  - `tests/unit/test_device_db.py` passes, including
    `test_a_powered_alternative_says_where_its_power_figure_comes_from`.
  - The goldens are unchanged.
- **Tests:** the existing device-db tests cover it. Add a failing test first only if a new
  rule appears.
- **Done when** the gate passes and the PR is open for A1.

## 2. Finding 31: `di_inputs` for the SEL-2244-2 alternatives

Research the input count per module, then add it to the device-db records and the library
entries, in the same way as §1.

## 3. Finding 24: FGR-60F at 125 V DC

Look for Fortinet's statement on the 12–125 V input range at float voltage. Record the
answer in the findings doc, or say that none was found.

## 4. Ask A1 whether the M14 alternatives generator should live in the repo

Today it is `/mnt/project-files/handoff/03-device-db/library_entries.py`, outside the repo
and not idempotent. Ask A1 before adding it, since `examples/` is A2/B2's.

## Regenerating the shipped library

After any change to `examples/library.yaml` or `data/device-db/`:
1. Run `python data/library/build.py`.
2. Commit `data/library/psa-devices.yaml` along with the change.
3. Run `tests/unit/test_shipped_library.py`.

## Don't do

- Don't put the originals' inrush or input range in `examples/library.yaml` (Q38). It
  moves the goldens.
- Don't change the default MCB set from iC60N (Q37).
- Don't hand-edit `data/library/psa-devices.yaml`.
- Don't edit `src/`: library_store is B5's, models are B2's, and the engine is B9's.
- Don't edit other roles' files without A1 assigning them. This covers `examples/`
  (B2), `release.yml` and ADR 0009 (B6), and the library_store tests (B5).
