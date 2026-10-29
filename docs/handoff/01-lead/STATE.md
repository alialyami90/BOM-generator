# Role 1 (lead): state

- Name: B1 - Lead developer. Ali retired every agent on 2026-10-29 (13:50 UTC). The next
  holder of this role starts with no history: read this file, then NEXT.md, then LESSONS.md,
  then the latest `checkpoints/` file.
- Repo: `alialyami90/BOM-generator`, default branch `main`. B1's branch for its own docs PRs
  was `claude/project-thread-bf49ch` (restarted from main before each PR).
- origin/main at this checkpoint: 032bbea (#212), plus the role-handoff PRs merged on 2026-10-29
  (see the checkpoint file for the list).
- Releases: v0.1.0, v0.1.1, **v0.2.0** (tag on f65a5fe, #195) and **v0.2.1** (tag on 1678343,
  #211, published 2026-10-29 03:17 UTC with `bomgen-setup-0.2.1.exe`, 29.7 MB, and
  `default.bomlib` built from psa-devices 1.1.0):
  https://github.com/alialyami90/BOM-generator/releases/tag/v0.2.1.
  Check any tag with `git ls-remote origin 'refs/tags/v0.2*'`.

## How a release happens (ADR 0009, amended by #153)

1. Role 7 opens a docs PR with a `## [x.y.z] - YYYY-MM-DD` CHANGELOG section and updates the
   compare links at the bottom of CHANGELOG.md. No agent names in it. Version bumps, docs,
   chore and refactor PRs get no entry.
2. Role 6 opens the bump PR: `pyproject.toml` `version`, `src/bomgen/__init__.py`
   `__version__`, and `tests/test_package.py`. Nothing else.
3. Role 1 merges the bump once CI and "Build Windows installer" are green. The merge on main
   runs `release.yml`, which tags, builds and publishes. Nobody pushes tags by hand.
4. Role 6 follows the run and reports the release URL and assets.
5. Hold all other merges from the CHANGELOG merge until the release is published, so the
   tag matches the changelog.

## Where the product stands

- v0.1: M0–M11 (engine, sheets, checks, desktop app, installer). See README "Status".
- v0.2 (Ali's ten points on v0.1.0, `docs/backlog.md`, all marked "Done in v0.2.0"; milestones
  M12–M18 in `docs/plan.md` → "M12–M18 (v0.2)"): layout fixes, alternatives as library parts
  with per-project/substation brand sets (ADR 0017), separate DC MCB brand (ADR 0023), shipped
  library psa-devices 1.1.0 in `data/library/` (Q38), branch MCB sizing from running and
  inrush current (ADR 0019), in-app library editing with local versions and CSV (ADR 0018),
  in-app project/substation/panel editing with round-trip writers (ADR 0021), loose material
  sheet and page (ADR 0020, ADR 0022).
- v0.2.1: UI polish pass from B4's audit `docs/ui/polish-v02.md` (items 1–16, all done in
  #205–#208), plus #194, #198–#201.
- ADRs: 0001–0023 are all Accepted (Ali accepted the last 15 in #184). Next free ADR: **0024**.
- Open questions: Q1–Q41 all resolved. Next free question: **Q42**. The number table is in
  `docs/agents.md` → "Numbers"; keep it current when you hand one out.

## Open PRs

None at 032bbea apart from the role-handoff PRs, which this checkpoint merges. Run
`list_pull_requests state=open` to confirm.

## Waiting on Ali

- Decision card in B1's thread, message `cmsg_01CGuLumA5u5e7gSGbisWmMi8kT7H49pypGPBmn8yWT6TM`:
  "What should the team do after v0.2.0?" Options: "Test v0.2.0, send feedback" (recommended),
  "Polish only, release v0.2.1" (since done anyway), "I'll describe v0.3 now". Unanswered. The
  card only reaches the thread that posted it; a new lead in a new thread must repost it
  (or a fresh one about v0.2.1) and close the old one with `close_decision`.
- Next feature work waits on his testing feedback on v0.2.1 (README "Status" says so).
- Q11 header fit in Excel Print Preview (role 10): no card sent yet; NEXT item 5.

## Known gaps and risks (not blocking, worth raising with Ali)

- **Spec is behind the code.** The spec master is a Claude Doc (`docs/spec/` explains how to
  update it). The v0.2 overrides are recorded only in ADRs and plan questions: ADR 0017, 0019,
  0020, 0022, 0023, and Q35, Q37, Q38, Q39, Q40, Q41. Updating the spec needs Ali, through the
  process in `docs/spec/`.
- **ASSUMED seed values.** `src/bomgen/io/lifecycle.py` `_blank` seeds a new substation with
  `generated_panels`, a cabinet number pattern `f"{substation_id.upper()}-PSA-{{n:04d}}"`, the
  example's Rawabi Fixed Frame enclosure and document numbers/dates, all with an `ASSUMED`
  YAML comment (#189, #192). No source gives these; ask Ali once on a card whether they are
  right for his projects.
- B4's two layout nits from #207 were fixed in #208; no known UI defects remain open.
- The Windows installer and GUI can't be run in the Linux sessions; the CI job "Build Windows
  installer" (which also runs the launcher self-test, #186) is the check for them.

## Threads (route work here while they exist)

Ali retired all of these on 2026-10-29. Kept for reading history with `read_thread`.

| Role | Thread id |
| --- | --- |
| B1 lead (this role) | `cmsg_01CGuLumA5u5e7gSGbisWmMiJaADCWuiNCb42qQHM1dpuv` |
| B2 input models | `cmsg_01CGuLumA5u5e7gSGbisWmMi6PZvzPso7corbrGkzwhE7j` |
| B3 device db (titled A3) | `cmsg_01CGuLumA5u5e7gSGbisWmMiMn4Ay5kTA4wLV22n9mEuru` |
| B4 UI design | `cmsg_01CGuLumA5u5e7gSGbisWmMi9aAhgzZ2TPaUfJEPHXE2iF` |
| B5 library packages | `cmsg_01CGuLumA5u5e7gSGbisWmMiTNDc3q6MynAdyRny37PKC3` |
| B6 installer and release | `cmsg_01CGuLumA5u5e7gSGbisWmMiHdmiF2zR4D9rPGYUSRQDkT` |
| B7 lead assistant | `cmsg_01CGuLumA5u5e7gSGbisWmMi1Z9DLRFEw35bgfG7ruFWKo` |
| B8 sizing and layout | `cmsg_01CGuLumA5u5e7gSGbisWmMiWrgyedtbG3UzCXSmJ5mdJm` |
| B9 rule engine | `cmsg_01CGuLumA5u5e7gSGbisWmMiEVdwRwy2F5RdK8ptK2QkGn` |
| B10 workbook writer | `cmsg_01CGuLumA5u5e7gSGbisWmMi5oJH7cuxNZWDrjADGPLnRU` |
| B11 desktop app | `cmsg_01CGuLumA5u5e7gSGbisWmMiSRmFy8hwGpYU6cXpyyR56y` |

New holders get new threads from the coordinator. Give each role your thread id in your first
message, or they keep writing to the old lead.

## Verification

| Command | Result | Date |
| --- | --- | --- |
| `ruff check . && ruff format --check .` | All checks passed; 345 files formatted | 2026-10-29 |
| `PYTHONPATH=src python3 -m mypy` | no issues in 224 source files | 2026-10-29 |
| `PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider` | 2672 passed, 0 failed (329 s) | 2026-10-29 |
| `pytest tests/golden` | 95 passed | 2026-10-29 |

Run on 032bbea. CI on #211 (the v0.2.1 bump): ruff, mypy, pytest, "Build Windows installer"
all green.
