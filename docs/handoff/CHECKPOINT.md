# CHECKPOINT

A dated log of where the project stood, newest first. Add a new entry at the top whenever work stops;
keep it short and point at [STATE.md](STATE.md) and [NEXT.md](NEXT.md) for detail.

## 2026-11-10: agents and the CLI handoff in the repo, where work runs

- **Base:** main `d980714` (#393). Docs-only PR. No code change since v0.5.0.
- **Done:** `.claude/agents/`, `HANDOFF.md` and [CLI-HANDOFF.md](CLI-HANDOFF.md) are committed,
  so a cloud session sees them; until now they were only on Ali's PC. NEXT.md §1 "Where work
  runs" records the split: cloud sessions and GitHub Actions for the work, Ali's Windows PC for
  what needs Excel or a person at the screen. NEXT.md §3 no longer lists Q54 as open.
- **Agents revised (Ali, 2026-11-10):** the main session is the lead developer and
  orchestrator and the `lead` agent is gone (`CLAUDE.md` "Agents", with the rules for a
  dispatched agent). The agent files now list owned files, not finished milestones.
  `panel-notes` became `panel-detailing`; new are `panel-layout` (layout engine, Panels board,
  Device preview), `device-research` (sourced `data/device-db/` records) and `ui-design`
  (`docs/ui/`, audits). Agents commit only; the lead pushes, merges and writes these files and
  the changelog.
- **Not done:** the gate was not run on the PC (no `bomgen` install there yet).
  `README.md` Status still says v0.4.0 and the status line of `docs/plan.md` stops at v0.3.3.
- **Next:** unchanged: Ali's field tests of v0.5.0 (PDF export with Excel, drag and drop), then
  the open ends in STATE.md §1.

## 2026-11-04: v0.5.0 released (Lead)

- **Base:** main `6bc9721` (#392). Docs-only PR.
- **Done:** the changelog section (#391) and the version bump (#392) published v0.5.0 with
  `bomgen-setup-0.5.0.exe` (36 MB) and `default.bomlib` from psa-devices 1.17.0. It ships
  M70–M81 (the entry below).
- **Next:** Ali's field tests of v0.5.0 (PDF export with Excel, drag and drop), then the open ends
  in STATE.md §1.

## 2026-11-04: Phase G done, M70–M81 merged (Lead)

- **Base:** main `9b25f6b` (#389). Docs-only PR.
- **Done:** all twelve review-point milestones are on main (#373–#389): W1 M81; W2 M71, M78,
  M79, M80; W3 M70, M75; W4 M72, M73, M74, M76; the lead's M77. ADRs 0038–0040 Accepted, Q72
  and Q73 answered, Ali keeps panel notes off the workbook. STATE.md §1 lists the set and the
  open ends; `CHANGELOG.md` `[Unreleased]` has one entry each; `tests/unit/README.md` lists the
  six modules the workstreams left out.
- **Next:** release v0.5.0 (NEXT.md), then Ali's field tests (PDF export with Excel, drag and
  drop) and his review list.

## 2026-11-04: W2 phase G, M78 PDF export merged (W2)

- **Done:** M78 (#388, ADR 0039 Accepted, Q73 answered "both, built-in by default"). `bomgen.pdf`
  renders the written workbook. `render_pdf` (ReportLab, new runtime dependency) follows each sheet's
  paper, orientation, fit or scale, margins, print area, title rows, merges, fills, borders and
  scaled header/footer. `excel_pdf` drives Excel through PowerShell COM on Windows. Build has
  *Export PDF…* (sheets, renderer, `<workbook>.pdf`). `pypdf` joins the dev extras. Golden
  unchanged. Screenshots and two rendered pages in `/mnt/project-files/a11-screens/m78/`.
  W2's M71, M78, M79 and M80 are all done.
- **Left for later:** the Excel path is untested on a real PC (CI is Linux), so try it once on
  Windows with Excel. The built-in renderer leaves out the header logo picture, and uses
  Helvetica for Calibri, so wrapping can differ slightly from Excel's.

## 2026-11-04: W2 phase G, M71, M80 and M79 merged; M78 waits on Q73 (W2)

- **Done:** M71 row notes (#373): `note` on equipment, hand-written panel and loose rows, never
  printed on a BOM sheet; Preview's Notes column and an optional Notes sheet (`output.include`
  `notes`). M80 IED Schedule sheet (#382): optional, one row per schedule row and port need, side
  ports as formulas and SUMIFS totals per speed, media and landing (`ied_schedule`). M79 Mark as
  revised (#383, ADR 0036 amendment): `revision_marks` (panel, tag, columns, reason) highlight a row
  like OUT-8, *Build as issued…* shows the change list (`issue_changes`) before writing, and the
  issue keeps them as `issues[].marked` and clears them. Golden unchanged. Screenshots in
  `/mnt/project-files/a11-screens/m71/` and `m79/`. `tests/unit/README.md` now lists W2's M63–M80
  modules.
- **Waiting:** M78 PDF export needs Ali's Q73 card (built-in renderer recommended, Excel on the PC,
  or both); ADR 0039 and Q73 stay with W2. A second W2 checkpoint follows M78.
- **Left for later:** six unit test modules from other workstreams are still missing from
  `tests/unit/README.md` (`test_app_derived_values`, `test_overrides`, `test_redbox_and_converter`,
  `test_rules_text`, `test_health`, `test_ied_csv`).

## 2026-11-04: W1 phase G, M81 function tags merged (W1)

- **Done:** M81 function tags (#376): `DeviceType.tags` (trimmed, no blank tag; a saved library
  leaves out empty tags and needs this app version when tags are used), one `devices.csv` cell
  split by `|`, a *Function tags* field (one per line) on the device editor's Identity tab, and
  Library search and the part picker match tags. `data/library/build.py` tags every shipped part
  with its category, a switch's Purdue level and its largest port group ("Network switch",
  "L2 switch", "24-port"): psa-devices 1.17.0. No ADR or Q. Golden unchanged. Screenshots in
  `/mnt/project-files/a11-screens/m81-tags/`.
- **Left for later:** the Library detail pane does not show a part's tags; the port tag counts
  the largest port group, not uplinks or slots.

## 2026-11-04: W4 phase G, M72, M74, M76 and M73 merged (W4)

- **Done:** M72 port budget and switch-count override (#375): the Parts Result card lists each
  level's ports on the busier side with their rule, and `network.l1_per_side`/`l2_per_side` add
  switches above the sizing (Q72 answered "only above"; a lower count fails sizing). M74
  `panel_hint` steers a common row to a panel without pinning, with a `panel-hint` warning (#377,
  ADR 0013 amended). M76 `priority` 1–4 per row replaces the category's stack order, a select on
  the row's Panel line (#380). M73 `redbox` and `media_converter` categories and roles (#384, ADR
  0038 Accepted): sized as other, tagged, priority 2, cable manager allowed but off, 1 L2 port by
  default; PRP and HSR stay refused. Golden unchanged. Screenshots in
  `/mnt/project-files/a11-screens/m72-switch-counts/`, `m74-panel-hint/`, `m76-rack-priority/`.
- **Left for later:** psa-devices has no RedBox or media converter part yet (library intake,
  ADR 0037); their nameplate pattern is not in the Design basis list (M75 `PLATES`).

## 2026-11-04: M77 overrides in Checks merged (Lead)

- **Done:** `engine/overrides.py` lists every override (panel options, terminals, part values and
  SFP counts, layout moves, the spares list, switch counts) as the Checks *Overrides* group; a risky
  one (below its automatic value) warns until it has a reason, stored in `options.override_reasons`
  or `spares_list.reasons` and set from the Checks row or the derived value's reason line
  (`set_override_reason`). Recorded issues keep the risky overrides, printed in the Revision
  History OVERRIDES column. Rule texts for the fan, grounding busbars and cable managers. ADR 0040
  Accepted; Ali keeps panel notes off the workbook (plan coverage table). The example's five
  overrides add five passes to the golden check counts.
- **Next:** W1 M81; W2 M71, M78 (ADR 0039, Q73), M79, M80; W4 M73 (ADR 0038), M76. Then a
  v0.4.1 changelog and the handoff.

## 2026-11-04: W3 phase G, M70 and M75 merged (W3)

- **Base:** main `ecce117` (#378). Docs-only PR.
- **Done:** M70 panel notes and miscellaneous rows (#374): `Panel.notes` (never printed;
  `generated_panels.notes_by_panel` on a generated panel, a mirror's own), `options.misc_items`
  printed last in group H as "1 Lot", Notes on the Document tab and the rows on Options. M75 PANEL
  row details and nameplate text (#378): `Enclosure.ip_rating` and `colour` end the PANEL row's
  description; the design basis tagging's `nameplate_pattern` per category with `{tag}`,
  `{full_tag}` and `{purpose}`. Spec sentences only, no ADR or Q. Screenshots in
  `/mnt/project-files/a11-screens/m70/` and `m75/`.
- **Left for later:** the socket pick list (M56 plan, gap 11).

## 2026-11-04: v0.4.0 released, M48–M69 done (Lead)

- **Base:** main `65837a3` (#370). Docs-only PR.
- **Done:** the changelog section (#369) and the version bump (#370) published v0.4.0 with
  `bomgen-setup-0.4.0.exe` and `default.bomlib` from psa-devices 1.16.0. All five workstreams'
  milestones are merged (the entries below). `plan.md` marks M48–M69 Done and plans M70–M81 with a
  coverage table of the workflow review (#364).
- **Next:** hand out M70–M81 one PR each (owners in `plan.md`); ADR 0038 and Q72 are the next free
  numbers, given out by the lead one at a time.

## 2026-11-04: W5 Setup and design basis, M51–M55 merged (W5)

- **Base:** main `7540497` (#366). Docs-only PR.
- **Done:** ADR 0031 design basis accepted (#330). M51 New substation › *Cabinets and documents*
  step instead of ASSUMED seeds (#333, Q62: prefill, previous substation first). M52 design basis
  in two PRs: M52a model, loader voltages and tagging (#338: side letters, first numbers), M52b
  Settings › *Design basis* tab (#341). M55 substation templates in `templates/` of the project
  folder (#344, Q63). M53 vendor lists in two PRs: M53a model, `vendor_list` and `part_state`
  checks, Parts chips and picker order, the Design basis select (#350); M53b Project › *Vendor
  lists* tab (#366). M54 `design_basis_checks` with *Go to the field* (#358). Screenshots in
  `/mnt/project-files/a11-screens/` (`m51`… `m55`, `m53`, `m54`).
- **Left for later:** a hand-written panel's tags and port-plan keys do not follow new side
  letters. The example library has no input ranges, so the design basis DC check bites only with
  the shipped library (`psa-devices`). Catalogue brand sets off a vendor list warn once per
  catalogue, not per line.

## 2026-11-04: W2 Issue outputs, M63, M66, M64 and M65 merged (W2)

- **Base:** main `23a5a6c` (#362). Docs-only PR.
- **Done:** M63 Summary BOM (#324, ADR 0035). M66 recorded issues and Revision History in two PRs,
  M66a engine and CLI (#349), M66b app (#351, ADR 0036, Q67). M64 spares list in two PRs, M64a
  engine and sheet (#356), M64b Spares page and Preview tab (#357). M65 cable schedule in three
  PRs: M65a cable data on loose rows and the sheet (#355), M65b suggestions from the port plans
  (#361, Q66 lengths per link class, Q71 once at the link's upper end: the example gives 40 MM
  and 4 SM cords), M65c Suggest cables dialog, cable columns and Preview tab (#362). Screenshots
  in `/mnt/project-files/a11-screens/` (`m64b`, `m65c` and earlier W2 folders).
- **Answered (2026-11-04):** Q65, percent with a minimum of one: `minimum_per_part` defaults to 1.
- **Left for later:** the library has no LC patch cords with `media` and `length_m`, so every
  suggested cord is free text with a warning until such parts are added. Catalogue lines (MCBs,
  terminal blocks) have no category, so they get spares by override only.

## 2026-11-04: W4 Parts and network, M60 and M61 merged (W4)

- **Base:** main `b63ccda` (#353). Docs-only PR.
- **Done:** M60 IED schedule in two PRs (ADR 0034): M60a model and sizing (#343, per-side pools,
  fixed ports by speed and media, SFP slots by speed, L1 count the max of the sides, overflow onto
  slots as L1 downlinks), M60b Parts screen IED table and CSV import (#348, `io/ied_csv.py`).
  M61 external links (#353, Q64): `network.external_links`, EXT links on the L2 and external
  switch port plans, the `external_link` check, the Parts links table. Screenshots in
  `/mnt/project-files/a11-screens/m60-ied-schedule/`, `m61-external-links/`.
- **Waiting:** Ali's cards on Q70 (quick IED count on mixed-media L1 switches) and Q64 (external
  links as their own list). Both ship the recommended option. W2's M65 can start (it waited on M61).

## 2026-11-03: W3 Panel detailing, M50, M58, M57, M56 merged (W3)

- **Base:** main `26b9f4a` (#345). Docs-only PR.
- **Done:** M50 per-panel enclosure and kind (#322), M58 grounding, spare breaker ratings and alarm
  on branch trip (#332), the M59 follow-up with tag fields on hand-written panel rows (#334), M57
  Terminals tab (#336, ADR 0033), M56 housekeeping as inputs in two PRs, M56a engine (#340) and
  M56b panel editor and Library roles (#345, ADR 0032). Spec sentences for M50, M58, M57 and M56
  are in. Screenshots in `/mnt/project-files/a11-screens/m50/`, `m58/`, `m59-hand-written/`,
  `m57/`, `m56/`.
- **Answered (2026-11-04):** THF when the kit changes. Ali chose the built option: the spec's 12 or
  5, plus 3 per fan and 2 per thermostat beyond the spec's kit (`engine/terminals.py` `_thf`); a
  heater or hygrostat brings its library part's own strips. No code change.
- **Left for later:** the socket as a pick list from the library's sockets (M56 plan, gap 11).

## 2026-11-03: W1 Library, M67, M68, M69 merged (W1)

- **Base:** main `9b77f6f` (#342). Docs-only PR.
- **Done:** ADR 0037 accepted (Ali, card). M67 record lifecycle and sources in three PRs: M67a model,
  CSV and schema (#331), M67b the source rule on saves, who/when/note stamps, every shipped part
  sourced in psa-devices 1.16.0 and the `part_source` check (#335), M67c the device editor, Library
  and Parts screens (#337). M68 Library › Review and Health (#339). M69 Propose for the library from
  Parts (#342). Screenshots in `/mnt/project-files/a11-screens/m67c-lifecycle/`,
  `m68-review-health/`, `m69-propose/`.
- **Answered 2026-11-04:** Q69, `assumed` naming the workbook, as shipped. Was: Ali's card on Q69 (seven original parts carry the example workbook's power, which
  their datasheet does not state; they ship as `assumed` until he answers).

## 2026-11-03: W4 Parts and network, M49, M62, M59 merged (W4)

- **Base:** main `0370d1d` (#326). Docs-only PR.
- **Done:** M49 SFP spare and extra per switch (#323), M62 panel cap `layout.max_panels` (#325),
  M59 BOM text per row on Parts (#326). Screenshots in `/mnt/project-files/a11-screens/m49-sfp/`,
  `m62-panels/`, `m59-bom-text/`.
- **Waiting:** M60 and M61 wait on M52 and on Ali accepting ADR 0034. W3 to add tag, type code and first
  number to hand-written panel rows in the panel editor (the rest of M59).

## 2026-11-01: v0.3.4 released (A1, lead)

- **Base:** main `b930913` (#314). Docs-only PR.
- **Done:** v0.3.4 is published with `bomgen-setup-0.3.4.exe` and psa-devices 1.15.0: the v0.3
  roadmap M35–M47 (#297–#313), including the fixes from a fresh-project pre-release check
  (recheck clean).
- **Waiting:** Ali's answers on the "v0.3.4 review list" Claude Doc and his Windows drag-and-drop
  test (ALI-8).

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
