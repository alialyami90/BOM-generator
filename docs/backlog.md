# Backlog

Ali's feedback after each release, point by point, and the work done for each point. Keep this file
current: when a point's status or milestone changes, update its row here.

## v0.6: Ali's feedback on v0.5.0

Ali's six points from 2026-11-11, after testing the installed v0.5.0. Each was traced in the code
before it was planned; the causes, the checks that were run and the open questions are in
[`plan.md`](plan.md) "M82–M94" and questions Q74 to Q81.

| # | Point (Ali) | Milestone | Status |
| --- | --- | --- | --- |
| 1 | "Bug when opening substations dropdown menu." | M82 | Done on main (#397). Ali to confirm in the next release. |
| 2 | "I still cant override or select the SFP quantity." | M85, M86, M87, M88 | M85, M86 and M87 done on main (#398, #403, #408; psa-devices 1.18.0); M88 waits for ADR 0041. Four causes: no SFP rows on an L1 switch left to the sizing; 23 of the 27 SFP parts can never be chosen; the quantity is display-only; no SFP rows on a firewall or EXT switch. |
| 3 | "In the library you are listing devices along with their alternatives ... it should just show the applicable alts." | M83, M84 | Done on main (#399, #400), on Q74's recommended answer. The picker listed a whole category for every row: 26 switches on each switch row, 12 of them alternatives of another switch. |
| 4 | "The library list should remove duplicates. Example SEL-2731-EXT and SEL-2731 are same device." | M84, M93 | M84 done on main (#400): a part is named by its make and model, not its id (Q82). M93 planned (Q80). No SEL-2731 exists; 7 groups of true duplicates and 12 groups of one item copied per role were found. |
| 5 | "Monitors and KVMs are showing SFPs that shouldnt be there." | M89 | Done on main (#402 Parts, #404 Panels › Ports). Every row but the sized switches and the patch panel gets the "Link to the L2 switch" inputs, defaulting to 1G MM fibre. |
| 6 | "Review part selection for other inconsistencies like this." | M83, M90, M91, M92, M94, M96 | M83 and M90 done on main (#399, #409); M91 is PR #411, tested and waiting to merge; M92, M94 and M96 planned. The review's findings are listed under each milestone. |

## v0.4: engineer-controlled workflow

Ali's requests from 2026-11-03: a review of the engineering workflow from a SCADA engineer's view
([review](superpowers/specs/2026-11-03-engineering-workflow-review.md)), a plan for agents
([plan](superpowers/plans/2026-11-03-agent-implementation-plan.md)), and delivering it with the agent
team.

| # | Point (Ali) | Milestone | Status |
| --- | --- | --- | --- |
| 1 | Engineer-controlled workflow: every derived value shown with its rule and overridable, a design basis, panel detailing and network inputs, issue outputs and a reviewed library (2026-11-03). | M48–M69 | Planned in six workstreams ([`plan.md`](plan.md) "M48–M69"). |
| 2 | Plan the review points M48–M69 left out: notes, port budget and switch-count override, RedBox and media converter, steering common devices, PANEL row details, rack priority, overrides in Checks with reasons, PDF export, mark as revised, IED schedule sheet, library tags (2026-11-04). | M70–M81 | Planned ([`plan.md`](plan.md) "M70–M81"). |

## v0.3: Ali's feedback on v0.2.1

Ali's requests from 2026-10-28 to 2026-10-31, and the work done for each point. The milestones are
in [`plan.md`](plan.md) from "M19–M24" on, and the decisions are ADRs 0024 to 0030 and plan
questions Q42 to Q61. The audit of 2026-10-31 (point 10) checked every point; its ids (ALI-, APP-,
ENG-, DOC-) are in the Status column.

| # | Point (Ali) | Milestone | Status |
| --- | --- | --- | --- |
| 1 | Replace the network section with part picking: a part per role from a dropdown, a free-text part number for the BOM, overrides that change panels, MCBs, power and heat, an SFP model per media, a plus sign to add devices, MCB and terminal block brands, a cable manager per network device (2026-10-31). | M20, M22, M23 | Done in v0.3.0 (#239, #240, #244; ADR 0024). |
| 2 | Order the devices inside a panel by priority, and put the KVM and console at waist height, with the waist height and rack start in mm as settings (2026-10-31). | M21, M29 | Done: the engine in v0.3.0 (#241), the two settings on the project Overview in v0.3.2 (#274). |
| 3 | A preview of the devices before the layout: a table and a panel elevation, with the MCB per device (2026-10-31). | M24 | Done in v0.3.0 (#245, #247). |
| 4 | Drag and drop in both panel views (2026-10-31, Q50), single devices or an A/B pair (2026-10-28). | M19, M24 | Done (#238, #247). On the Panels board a pair moves together and Alt moves one unit, as it has since v0.2, so the audit's ALI-17 does not hold. Not yet checked by hand on Windows (ALI-8). |
| 5 | One AC branch MCB per VAC device, after the socket, raising CINC (2026-10-31, Q52). | M25 | Done in v0.3.0 (#248, #252; ADR 0025). |
| 6 | Device nameplates like the example's L2_ESW_A01 and L2_GPS_A01 (2026-10-31, Q53). | M26, M30 | The nameplate row and sheet in v0.3.0 (#253, #256; ADR 0026). Every device tag has level, type, side and number on main (#287; ADR 0030, Q56 to Q60). |
| 7 | Operator workstation, engineering workstation, DA server, KVM, console and annunciator as their own part rows (2026-10-31). | M23, M28, M30 | The rows are done (#244), and the three computer roles get the tags OWS, EWS and SRV (#287). KVM and console stay empty by Ali's choice. NAP-K55 can be picked since psa-devices 1.9.0 (#275). A panel-mounted annunciator: Q51. On main, an annunciator row goes to loose material with its wall-mount kit (M45, #311). |
| 8 | Review the contractor's consolidated library and use it in the app, v1 then v2 (2026-10-31). | M28 | Done: v1 in psa-devices 1.2.0 to 1.7.0, v2 in 1.8.0 and 1.9.0 (#270, #271, #275). What is still open is in `data/device-db/contractor-return-v2-2026-10-31.md` (#277). On main: the alternatives' power, DI counts and own descriptions, and tags for the contractor's switches, firewalls and fibre shelves, in psa-devices 1.12.0 to 1.15.0 (M41 to M44, #296 to #310). |
| 9 | Catch the spec up (2026-10-30). | docs | Spec v2.1 covers nameplates, part overrides and the new port speeds, and the tag section follows ADR 0030 (#288). *Done:* the auto-layout rules are in its "Automatic panel layout" section (ALI-14, M35). |
| 10 | Audit the specs and docs against the app (2026-10-31). | M27–M34 | Done ([audit](https://claude.ai/artifact/5JGc6RakHiQyFunApSao4H)). M27 to M29 and M31 to M34 shipped in v0.3.2, M30 in v0.3.3. The rest of the audit is M35 to M43 on main (below). |

### v0.3 roadmap

The audit's remaining points and the handoff's open items are milestones M35 to M47 in
[`plan.md`](plan.md) section 4, one PR each:

- M35: the spec's auto-layout rules.
- M36 to M39: the app's Catalogues tab, Settings YAML, Add a device and desktop conveniences.
- M40: the derived DC MCB choice.
- M41 to M44: library data, psa-devices 1.13.0 to 1.15.0.
- M45 to M47: the pre-release check's fixes.

## v0.2 (shipped in v0.2.0)

Ali's feedback after testing v0.1.0 (2026-10-28), and the work done for each
point; all ten shipped in [v0.2.0](https://github.com/alialyami90/BOM-generator/releases/tag/v0.2.0) (2026-10-29). The milestones' details are in
[`plan.md`](plan.md) → "M12–M18 (v0.2)". The terms MCB, catalogue and loose
material are as in the spec.

### Ali's points

| # | Point (Ali, 2026-10-28) | Milestone | Status |
| --- | --- | --- | --- |
| 1 | The Library screen doesn't list the MCBs, terminal blocks, auxiliary contacts or other accessories. List them, so an engineer can change the MCB brand. | M13, M16 | Done in v0.2.0. Catalogue tabs (#93), brand sets per project and substation (#97), the store side (#114, #116, #118, #120) and the app's library editor (#155, #166, #175, #178, #180); DC MCBs can take their own brand set (ADR 0023, #130). |
| 2 | A device's alternatives (e.g. for the SEL-2730M) are shown by tier, but they aren't library parts, so they can't be picked. Add them to the library. | M13, M14 | Done in v0.2.0. Alternatives are library parts with `alt_group` and `tier` (#97, #121), compared on the Alternatives tab (#180), and "Use this instead" puts one on an equipment row (#194, after the release). |
| 3 | Size each MCB from the equipment's own data, worked out by the program, not from Ali's example. Fill in the data needed for every researched device. | M14, M15 | Done in v0.2.0. Computed sizing with a 2 A floor (#103), float-voltage warnings (Q37, #109), the shipped psa-devices 1.1.0 with datasheet data (Q38), sizing pinned against it (#171); DC MCB brand apart from AC (Q39, ADR 0023). |
| 4 | Create projects and substations in the app, with no YAML or project file. Files are only for import, export and backup. | M17 | Done in v0.2.0. Create, rename and delete projects and substations in the app (#181, #182); a blank substation is seeded so it can take equipment (#189, #192). |
| 5 | Bundle the device library with the installer; it can still be updated separately. | M11 | Done in v0.1.1 (#86): the installer ships psa-devices 1.0.0 and a fresh install loads it on first start |
| 6 | Loose material belongs in its own sheet, not the substation settings; Preview doesn't show it; it must be customizable per project. | M18 | Done in v0.2.0. Its own sheet (#96) and Preview tab (#108), free-text items (#122, ADR 0022), and the Loose material page (#146). |
| 7 | Every setting, panel value and other field shown as a static example must be a real, editable value. | M17 | Done in v0.2.0. Project and substation fields and Settings (#185, #190), equipment rows (#188), and the documents register (#192) are all editable. |
| 8 | Panels board: a cable manager is a passive plate, so it can sit directly against the next device. The one-blank-plate gap is only between two active devices. | M12 | Done (#90, #101). |
| 9 | Drag and drop on the Panels board doesn't work. | M17 | Done in v0.2.0. Drag and drop with pins, deletes and undo (#126), and keyboard moves (#129). |
| 10 | Add and edit devices in the app, with every field editable. Export the library as a backup, and import one. Use CSV for both so engineers can work in Excel. Link alternatives in the CSV with a unique key, and show a list of all the alternatives for a device so they can be compared. | M16 | Done in v0.2.0. The library editor, CSV export and import, `.bomlib` backup and the alternatives comparison (#155, #166, #175, #178, #179, #180). |

### Order

All of it shipped in v0.2.0; v0.2.1 added the UI polish pass (`docs/ui/polish-v02.md`).
