# Role 3 next (B3)

**Next action:** once A1 merges #130, rebuild the Q38 follow-up on your thread branch from origin/main and open its PR, with A6 and A1 as reviewers.

## 1. Q38 follow-up: shipped psa-devices library (M14)

- **Goal.** Ship `data/library/psa-devices.yaml`, which is `examples/library.yaml` plus
  each original's datasheet `inrush_a`/`inrush_ms`/`input_v_min`/`input_v_max` from
  `data/device-db/`. Point the release pack step at it. See plan.md §6 Q38 and §4 M14.
  A1 asked for it, and it must land before v0.2.0.
- **Files.**
  - New, role 3: `data/library/build.py` (generator), `data/library/psa-devices.yaml`
    (generated, never hand-edited) and `tests/unit/test_shipped_library.py`.
  - Changed: a regenerate note in `data/device-db/README.md`.
  - A6's files, assigned by A1: `.github/workflows/release.yml` (pack path, notes, PR
    paths `data/library/**`) and `tests/unit/test_packaging.py` (the pack path).
- **Depends on** #130 being merged, since the follow-up builds on its library. Ask A1 in
  the PR to add `data/library/` to agents.md row 3; A1 proposed the path.
- **Release.yml and test_packaging go to role 3.** A1 assigned them in a relay to A3 on
  2026-10-28 at about 20:24 UTC. That was later than plan.md Q38's "A6 points release.yml";
  A6 reviews.
- **Branch.** Use the branch your thread was given; push only there. If it is
  `claude/project-thread-0iv7xg` (squash-merged), use the reset + `merge -s ours` steps
  in LESSONS.md.
- **Source.** First check that it exists. Use, in this order:
  1. Local commit `372418c` on branch `followup-q38`, if the container still has it.
  2. Otherwise `/mnt/project-files/handoff/03-device-db/q38-shipped-library.patch`. It
     leaves out the generated YAML.
  3. If neither is there, rewrite it from the acceptance list below.

  Steps:
  1. `git fetch origin main` and `pip install -e ".[dev]"`.
  2. Branch from `origin/main`.
  3. `git am -3 <patch>`, or `git cherry-pick 372418c`. Resolve any conflicts in
     release.yml or test_packaging by hand.
  4. Run `python data/library/build.py`, then
     `git add data/library/psa-devices.yaml && git commit --amend --no-edit`.
  5. Run the gate. pytest takes about 11 min, so run it in the background.
  6. Push, then open the PR. Subscribe to it and assign alialyami90.
- **PR body must say:**
  - After any edit to `examples/library.yaml`, rerun `python data/library/build.py`, or the
    up-to-date test fails (tell A2).
  - Both #130 and this PR call the package 1.1.0. Releases come only from tags, and A1
    plans v0.2.0 after this PR, so no 1.1.0 is published from the example file.
- **Acceptance.**
  - The shipped file equals `build(example, datasheets())` from `data/library/build.py`.
  - It differs from the example only in those 4 keys, on originals only.
  - The example project builds with it, with no failed checks.
  - `release.yml` packs `data\library\psa-devices.yaml` as psa-devices 1.1.0.
  - The goldens are unchanged. Expected in the shipped build: the SEL branches go from 2 A to 6 A.
- **Tests (already written):**
  - `test_the_shipped_library_is_up_to_date_with_its_sources`
  - `test_the_shipped_library_is_the_example_plus_the_originals_datasheet_figures`
  - `test_the_originals_carry_their_datasheet_inrush_and_input_range`
  - `test_the_example_project_builds_with_the_shipped_library`
  - `test_packaging`'s pack-path assertion
- **Done when** the gate passes and the PR is open, watched, with A6 and A1 as reviewers.

## 2. Drive #130 to merge

If #130 is still open more than a day after 2026-10-28 20:40 UTC, ask A1 in A1's thread
what blocks it. While you wait, §3 and §4 may go ahead.

Answer review events on #130; A1 merges it after Ali re-tags v0.1.1. A1 and Ali are to
confirm the iC60N `dc_float` warning. When B2's #145 (`McbBrand.ac_rated`) is on main, add
`ac_rated: false` to `schneider-c60h-dc` in `examples/library.yaml` (on #130, or else in
the Q38 PR) and rebuild the shipped file. After #130 merges, tell Ali in one short reply.

## 3. Fill the gaps in findings 30–31 of `docs/device-db-findings.md` (reference data, no milestone)

- Item 30: find power figures for the 11 skipped alternatives, then add them as library
  parts. Use the web budget in LESSONS.md.
- Item 31: research `di_inputs` for the SEL-2244-2 alternatives.
- Item 24: the FGR-60F's input range tops out at 125 V. It needs Fortinet's confirmation;
  if they confirm it, record it in the findings doc.

Each needs a data/device-db PR first, then library entries. Regenerate the shipped library.

## 4. Ask A1 whether the M14 alternatives generator should live in the repo

Today it is `/mnt/project-files/handoff/03-device-db/library_entries.py`, outside the repo
and not idempotent. Ask A1 before adding it, since `examples/` is A2's.

## Don't do

- Don't put the originals' inrush or input range in `examples/library.yaml` (Q38). It
  moves the goldens.
- Don't change the default MCB set from iC60N (Q37).
- Don't edit `src/`. The MCB AC/DC split is A2's and the sizing is A9's (M15).
- Don't hand-edit `data/library/psa-devices.yaml`.
- Don't edit other roles' files without A1 assigning them. This covers `examples/` (A2),
  `release.yml` (A6) and the library_store tests (A5).
