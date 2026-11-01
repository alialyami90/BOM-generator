# CHECKPOINT

A dated log of where the project stood, newest first. Add a new entry at the top whenever work stops;
keep it short and point at [STATE.md](STATE.md) and [NEXT.md](NEXT.md) for detail.

## 2026-11-01: v0.3.3 released (A1, lead)

- **Base:** main `5ad88c5` (#294). Docs-only PR.
- **Done:** v0.3.3 is published with `bomgen-setup-0.3.3.exe` and psa-devices 1.11.0: M30 device
  tags (#287, ADR 0030 Accepted), larger fans (#292, ADR 0029 Accepted), console header 53.1 pt
  (#293). Docs: #288–#291. The audit's fix plan is complete.
- **Waiting:** Ali's feedback on v0.3.3; Q51, Q54 and Q55 open; ALI-14 (auto-layout rules into the
  spec) for a later spec PR.

## 2026-11-01: v0.3.2 released (A1, lead)

- **Base:** main `e887fac` (#280). Docs-only PR.
- **Done:** v0.3.2 is published with `bomgen-setup-0.3.2.exe`: the audit fixes M27, M28, M29, M31,
  M32, M33 and M34 (#270–#275, #277, #278, #281–#285). ADR 0028 was rejected and reverted (#285)
  before the release.
- **Waiting:** M30 tags (A3, ADR 0030); A4's docs catch-up; Ali's cards on ADR 0029, devices on
  generated panels, Q51, Q54 and Q55.

## 2026-10-31: v0.3.1 released (A1, lead)

- **Base:** main `f0fa53c` (#268). Docs-only PR.
- **Done:** v0.3.1 is published (release run 41241782759) with `bomgen-setup-0.3.1.exe` and
  `default.bomlib` (psa-devices 1.7.0). Since the last checkpoint: #264 handoff, #265 psa-devices
  1.7.0 (Hubbell fibre shelves), #266 ADR 0027 Accepted, #267 fix for "StopIteration:" on Settings
  and Parts of a blank substation (Ali's report), #268 version bump.
- **Waiting:** Q51, Q54 and Q55 open; Ali's testing feedback on v0.3.1.

## 2026-10-31: v0.3.0 released (A3, engine)

- **Base:** main `46fcbe2` (#263). Docs-only PR.
- **Done:** v0.3.0 is published (release run 41234995752) with `bomgen-setup-0.3.0.exe` and
  `default.bomlib` (psa-devices 1.6.0). Since the last checkpoint: #256 Nameplates tab, #257 and #259
  psa-devices 1.5.0 and 1.6.0, #258 2.5G/5G/25G port speeds (ADR 0027), #260 contractor return list,
  #261 changelog, #263 version bump. README Status and STATE.md §1 are updated.
- **Waiting:** ADR 0027 on a card to Ali; Q51, Q54 and Q55 open; Ali's testing feedback on v0.3.0.

## 2026-10-31: M19–M26 merged, handoff updated (A3, engine)

- **Base:** main `dfcf810` (#254). Docs-only PR.
- **Done:** part picking M19–M26 is merged: #238–#241, #243–#245, #247, #248, #250, #252 and #253. The
  shipped library is psa-devices 1.4.0. STATE.md §1, §9–§11 and NEXT.md §2–§4, §13 and §15 are
  updated.
- **Checked:** gate on `628ff1c`: ruff and format pass (319 files), mypy passes (240 files), pytest has
  2852 passed.
- **Waiting:** Q51 and Q54 are open. Next engine work is the model changes
  (step 4) in A4's plan.

## 2026-10-31: Device preview shows the AC branch MCB (A2, app)

- **Base:** main after #250. PR for review by A1.
- **Done:** an AC unit's PS1 cell shows its own AC branch MCB from M25 (#248), no more AC-only "—".
- **Checked:** gate passes; E2E with the gateway overridden to 230 VAC shows PSA1-C5 and PSA2-C6, no
  console errors. Screen in `/mnt/project-files/a11-screens/m25-ac-mcb/`.

## 2026-10-31: M23 follow-ups, rows collapse and Device picker (A2, app)

- **Base:** main after #247 (M24 app). PR for review by A1.
- **Done:** Parts rows collapse to a summary line at 20 or more; a category with more than 12 parts
  (the shipped library's network switches) opens the Device picker in the part select's place; Parts
  options carry supply, power and data quality.
- **Checked:** gate passes; E2E on the example covers the picker (search, no match, Esc, ↓ Enter pick
  into the save bar, Discard, L1 "The sizing picks the switch", outside click) and collapse with 20
  rows, with no console errors. Screens in `/mnt/project-files/a11-screens/m23-followups/`.
- **Next:** after A3's M25 (#248), the real AC MCB in the Device preview table.

## 2026-10-31: M24 Device preview page (A2, app)

- **Base:** main after #245 (M24 engine). PR for review by A1.
- **Done:** `app/device_preview.py` and the `device_preview` endpoint; `drag.js` shared by the board
  and the preview; `screens-device-preview.js`; Generate preview and Go to the row on Parts.
- **Checked:** gate passes; the M19 board drag E2E unchanged; the Device preview E2E on the example
  with generated panels covers Down, Unpin, Arrow Up, an A unit refused on a B panel, Esc, drag to
  pin with Undo, Go to the row and an overflow, with no console errors. Screens are in
  `/mnt/project-files/a11-screens/m24-device-preview/`.

## 2026-10-31: M23 Parts page (A2, app)

- **Branch** `claude/project-thread-ufgt03`, on main after #243 (`cable_manager`). PR for review by A1.
- **Done:** Parts replaces Network (`screens-parts.js`, `app/parts.py`, `io/parts_edit.py`); writers for
  overrides, SFP choices, part change (clears what described the old part), cable manager, row move and
  a new substation's first rows; time accessories as loose material items; `start_equipment` and the L1
  ranking payload removed; a ruamel emitter fix in `round_trip.py`.
- **Checked:** gate passes; Playwright E2E on the example (override, library value back, Reset all,
  SFP, part change, cable manager, move, remove and Undo, Use this instead, `#/network`), no console
  errors. Screens in `/mnt/project-files/a11-screens/m23-parts/`.
- **Next:** M24 Device preview (plan in A3's engine PR).

## 2026-10-30: repo audit done, fix PRs merged, spec at v2.1

- **Base:** origin/main `d7841e4` (#234). Gate at `f2234f7` (#227): ruff and format pass (291 files),
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
    the fix PRs now. Later in words: add his four behavioural commandments to `CLAUDE.md` (#233);
    re-review the spec draft and land it if it holds (#234, hand-edited `generator-spec-v2.md` to
    v2.1; the master Claude Doc still reads v2).
- **Waiting on Ali:** what comes after v0.2.1; Q11; Q23; the ASSUMED seeds.
- **Next:** NEXT.md §3 and the open items by area. Smallest ready tasks: screen-check #208; finding 30
  power figures; the `mcb_dc` fallback.

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
