# CHECKPOINT

A dated log of where the project stood, newest first. Add a new entry at the top whenever work stops;
keep it short and point at [STATE.md](STATE.md) and [NEXT.md](NEXT.md) for detail.

## 2026-10-30: repo audit done, five fix PRs merged, spec v2.1 draft with Ali

- **Base:** origin/main `723507a` (#228). Gate at `f2234f7` (#227): ruff and format pass (291 files),
  mypy pass (224 files), pytest 2669 passed; `python data/library/build.py` no diff; every UI script
  parses; Playwright walk of every screen with and without the bridge, no console errors.
- **Open PRs, unmerged branches, uncommitted work: none.**
- **Done today:**
  - Audit of code and documents ([Claude Doc](https://claude.ai/artifact/DXyJnufrHguPCCVWgeLGPh)): 14 findings, a six-PR plan, a four-role
    team recommendation with models and effort (NEXT.md §1).
  - #227 app: the prototype's `data.js`, `engine-stub.js` and example screens no longer ship; no
    bridge means "could not reach its engine", never illustrative data.
  - #228 app: `min_branch_mcb_a` read-only in the device editor with the ADR 0019 note; Library card
    says "Sized by the engine".
  - #229 plan: status after v0.2.1, §2 tree from the code, Q1–Q41 in order; backlog v0.3 intake table.
  - #230 UI docs: v0.2 departures, hand-written-panels rule, `docs/ui/README.md` status.
  - #231 docs: two-PR release steps in `packaging/README.md`, README library version 1.1.0, ruff count,
    vulture note in LESSONS.md.
  - Ali's decisions (cards): remove the prototype fallback from the app; catch the spec up now; start
    the fix PRs now.
- **Waiting on Ali:** review of the [Spec v2.1 draft](https://claude.ai/artifact/Q2SsFCKM4y7vHhAJjkir43); what comes after v0.2.1; Q11; Q23;
  the ASSUMED seeds.
- **Next:** land the spec as v2.1 once reviewed (NEXT.md §3 item 3); then NEXT.md §3 and the open items
  by area. Smallest ready tasks: screen-check #208; finding 30 power figures; the `mcb_dc` fallback.

## 2026-10-29: v0.2.1 released, everything merged

- **Base:** origin/main `032bbea` (#212), v0.2.1 released (#211, tag on `1678343`). Gate on that tree:
  ruff and format pass (345 files), mypy pass (224 files), pytest 2672 passed, goldens 95 passed.
- **Open PRs, unmerged branches, uncommitted work: none.**
- **Done today:**
  - v0.2 app work merged (#166–#201): every field editable (#185, #188, #190, #192), "Use this
    instead" (#194), the shared draft form (#197), follow-ups #198–#201.
  - 15 ADRs accepted (#184); Q30, Q31, Q40, Q41 resolved (#183); backlog marked done (#202).
  - **v0.2.0** released from main with no hand-pushed tag (#193 changelog, #195 bump, tag `f65a5fe`).
  - UI polish audit (#204, `polish-v02.md`, the Changed marker) and all 16 fixes (#205–#208), each
    screen-checked except #208.
  - **v0.2.1** released (#209 changelog, #211 bump, published 03:17 UTC).
  - README status for v0.2.1 and 9 missing unit-test rows (#212).
  - Engine: DC breakers from `catalogues.dc_mcb` with CINC and AC on `mcb` (#154); shipped-library
    sizing tests (#171, SEL branches 6 A, others 2 A, goldens unchanged).
  - Models: `part_users` (#163), `delete_project` safety (#182), writers' block style and no scalar
    anchors (#187), `generated_panels` seeded for a blank substation (#189).
  - Library store: device-record edits (#164), ADR 0018 amendment (#170), `mcb_dc` in the CSV (#179).
  - Installer: self-test checks every UI file (#186).
  - Workbook: printer footnote on Power Consumption (#157, Q40).
- **Waiting on Ali:** what comes after v0.2.1; Q11 header fit in Excel; Q23; the ASSUMED seeds.
- **Next:** NEXT.md section 3 (questions for Ali), then the open items by area. Smallest ready tasks:
  screen-check #208 and record the v0.2 departures in `screens.md`; finding 30 power figures; the
  `mcb_dc` fallback.

## 2026-10-28: v0.2 back end merged, v0.1.1 released

- **Base:** origin/main moved from `9313db1` (pytest 2414 passed, goldens 94) to `ad7d137` (pytest 2525
  passed, goldens 94) during the day.
- **Done:**
  - Models: M13 (#97, #104); M17 writers (#106, #112, #115, #119); M18 loose items (#122, #124, ADR
    0022); `ac_rated` guard (#145); parse-once YAML cache (#149; suite 2:10 → 1:04); `mcb_dc` (#151,
    Q39, ADR 0023); `output.power_footnotes` (#152).
  - Device database: M14 research (#121) and library entries (#130: 279 alternatives with `alt_group`
    and `tier`, plus brand sets); Q38 shipped library and `build.py` (#161).
  - Library store: M16 store side (#92, #95, #105, #113, #114, #116, #118, #120) and two store fixes
    (#127).
  - Installer: v0.1.0 published, default library installed on first start and v0.1.1 (#86, from
    `135d7ee`); release from main (#153).
  - Engine: M15 branch MCB sizing (#103, ADR 0019); DC float checks (#109); no loose table without rows
    (#123).
  - Sizing and layout: blank plates (#90, M12); pin positions (#100, M17 engine).
  - Workbook: Loose Material sheet (#96, ADR 0020).
  - UI design: v0.2 parts 1–4 (#91, #94, #99, #102); Loose material follows ADR 0022 (#142).
  - App: board drag (#126), Move… dialog (#129), Loose material page (#146), Library device editor
    (#155).
- **Notable:** the first v0.1.1 re-tag never reached GitHub because the old tag still existed; tags are
  now created by the release workflow. v0.1.1 was held for its changelog (run 40765665083 cancelled
  before publish).
- **Open at end of day:** #157 waited on Ali's print-area card (answered as Q40); #171 and #166 merged
  the next morning.

## Before 2026-10-28: v0.1 (M0–M11)

Engine groups A–H (#22, #36), power and heat (#44, #46), check report and revision comparison (#58,
#67), sizing and layout (#19), sheet models and Excel writer (#21, #48, #69), `.bomlib` packages and
the per-user store (#9, #31, #41, #50, #53, #59), the device database (#6, #18, #30, #40, #42), the UI
design and prototype (M9, #82 departures), the desktop app (M10, #117 and earlier) and the Windows
installer with release workflow (#2, #15, #38, #47, #55, #57, #70, #84). v0.1.0 was released from a
tag (run 40736513114).
