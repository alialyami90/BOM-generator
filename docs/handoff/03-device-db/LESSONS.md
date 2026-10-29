# Role 3 lessons (append-only; mark replaced entries "superseded by ...")

## Research

- **Web budget.** The shared web budget is about 100 fetches an hour. Run research agents
  with at most ~35 fetches each, and plan a second pass an hour later rather than one big
  pass. Round 1 of M14 ran out; a second pass (resumed agents, ~25 fetches each) finished it.
- **`verified: true`** only when that exact code was read on a manufacturer or distributor
  page. Never invent a code or figure: leave it out and say so in `notes`
  (data/device-db/README.md).
- **iC60N on 125 V DC.** The iC60N 2P is rated to exactly 125 V DC; the float is about
  135–140 V. Q37 kept it as the default; the DC ranges are brand sets (findings 22–23).

## Library generation (M14)

- **Part ids** of alternatives: `<original>.<MAKE-SLUG>-<TIER>`, e.g.
  `SEL-2730M-EXT.MOXA-LOW`. Every original gets `alt_group: <its part_id>`.
- **No datasheet inrush or input range on originals in `examples/library.yaml`.** It moved
  the SEL branch MCBs from 2 A to 6 A and broke the goldens. Q38: they go into the shipped
  library only (`data/library/psa-devices.yaml`).
- **Do not copy `di_inputs`** to DI-module alternatives: it broke
  `test_di_module_inputs`. Logged as finding 31.
- **Rack part with unknown height:** leave `height_u` out. A5's loader requires
  `height_u > 0` exactly for rack parts, so 0 is rejected.
- **Normalise generated YAML** with `bomgen.io.round_trip` `dump_text(load_text(text))`
  and write block style. Flow-style output failed `tests/unit/test_round_trip.py`.
- **Check for existing keys before inserting.** A2 had already added `dc_rating_v` to
  `catalogues.mcb`; the generator wrote it twice.
- **The generator scripts are not in the repo.** They are in
  `/mnt/project-files/handoff/03-device-db/`: `library_entries.py` (run from the repo
  root against the pre-M14 library), `m14_merge.py`, `assemble.py` and `layout_data.py`.
  `library_entries.py` is not idempotent on the current file. The Q38 shipped library has a
  repo script (`data/library/build.py`, in the follow-up).

## Workflow

- **After a squash merge:** `git reset --hard origin/main`, commit, then
  `git merge -s ours origin/<branch> -m "chore: merge old branch history (already
  squash-merged)"` and push normally. Force-push is denied.
- **After fetching main:** run `pip install -e ".[dev]"`, because new dependencies
  (ruamel, pycel) failed a stale checkout.
- **Tests outside role 3's files.** Change them only with A1's approval. Assert the new
  composition and never loosen a test. List them in the PR body under "Tests outside A3's
  files", and ask the owner (A5, A8...) to review.
- **Full pytest took ~10 min** after #130 (superseded: ~4 min since #149, see below), because the example library is ~4,600
  lines. Run it in the background (foreground calls time out at 120 s or 600 s).

## 2026-10-28, after #161

- **Roles move to new threads after a reset.** Message the current thread: ROSTER.md
  names the role, and the coordinator gives the thread id. Ignore the retired thread, even
  if it answers. A retired A5 and the new B5 gave conflicting answers on #161, and the
  coordinator ruled for B5.
- **When another role lands the same fix first, merge main and take its version.** B5's
  #165 did this. Then check its new tests against your data: one assumed every shipped
  brand is AC-rated.
- **Never send placeholder text with `message_thread`.** Every call is delivered. Two
  stray messages ("unused", "placeholder-do-not-send") had to be retracted.
- **Since #149 the full pytest takes about 3–4 minutes**, down from about 11 minutes.

## 2026-10-29, retirement handover (B3 → C3)

- **A refresh keeps the name; a reset or retirement moves it to the next letter.** The
  2026-10-28-2 refresh stayed B3; this handover goes to C3.
- **The full reference lives in `archive/reference.md`.** That keeps STATE/NEXT/LESSONS
  inside the 250-line budget.
- **Check plan.md §6 before carrying a question forward.** Finding 24 (FGR-60F) and the
  iC60N float warning were settled by Q41 and Q37 while they still sat in NEXT.md.
