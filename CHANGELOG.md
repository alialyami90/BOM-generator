# Changelog

All notable changes to this project are listed here, one entry per merged pull
request; a milestone split across several PRs gets one entry. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- The Library list shows each device once (M84): the Devices table opens on the 94 originals,
  each with its alternatives folded under it by make and tier, and *List every part* shows all
  parts flat. A search that finds an alternative opens its original on it. A part is named by its
  make and model with its role under it ("EXT switch", "L2 switch", "Gateway", "RTAC"); the
  library id moves to the detail pane.
- The part picker on Parts offers the parts that fit each row (M83): an L1, L2 or external switch
  row lists only switches of its level, alternatives appear only for the row's own part, and
  obsolete parts are left out. A part is named by its make and model, not by its library id, and
  an alternative says which part it replaces ("Low-tier alternative to Ruggedcom RST-2228").
  *Search all parts* in the picker lists the whole category, where a switch also says its level.
  *Add a device › Switch* offers external switches only.
- The shipped library's Cisco and Moxa SFP alternatives carry the speed and media of the part
  they replace (M85), so Parts offers them for a link and a switch can take one; before, 23 of the
  27 SFP parts could never be chosen. Two single-mode parts listed in the 100M multimode group
  stay out until they are researched. A Cisco or Moxa switch now picks its own make's SFP
  automatically. psa-devices 1.18.0.

### Fixed

- The substation list in the left rail stays open (M82). The click that opened it ran the switch
  itself, which redrew the window and shut the list unless the mouse button was held; on Home,
  Project or Library it jumped to Panels. A list now acts only when a choice is made. Preview's
  group filter had the same fault.

## [0.5.0] - 2026-11-04

### Added

- Switch counts and port budget (M72): the Parts Result card lists each switch level's ports on
  the busier side (all, reserved, kept spare, in use, free) with the rule behind them, and its L1
  and L2 switch counts are derived values: `network.l1_per_side` and `l2_per_side` add switches
  above the sizing's count; a lower count stops the sizing and names the shortfall (Q72).
- RedBox and media converter roles (M73, ADR 0038): library categories `redbox` and
  `media_converter` and equipment roles of the same names, sized as any other device, tagged,
  stacked with the network devices and linked to the L2 switches by their own L2 link. Parts'
  Add a device offers both. PRP and HSR stay refused.
- Rack priority per row (M76): `priority` (1 to 4) on an equipment row replaces its category's
  stack order in the panel; Parts has a Rack priority select on each row.
- Steer a common device to a panel (M74): `panel_hint` on a common equipment row puts its units
  in that panel when they fit, without pinning them; otherwise they go where there is room and the
  layout warns. Parts has a Panel select on each common row (ADR 0013, amended).
- PANEL row details and nameplate text (M75). An enclosure's `ip_rating` and `colour` end the
  PANEL row's description; the design basis tagging's `nameplate_pattern` sets each category's
  plate text from `{tag}`, `{full_tag}` and `{purpose}` (unset prints today's tag text). The
  panel editor's Enclosure tab and the Design basis tab edit them.
- Panel notes and miscellaneous rows (M70). A panel's `notes` (`generated_panels.notes_by_panel`
  on a generated panel) are the engineer's own and never printed; `options.misc_items` print
  last in group H, one "1 Lot" row each. The panel editor has Notes on the Document tab and the
  rows on Options.
- Row notes (M71, ADR 0035 amendment): `note` on equipment rows (Parts › BOM text), hand-written
  panel rows (the panel editor) and loose items. A note is never printed on a BOM sheet; Preview
  shows a Notes column, and Build can add a Notes sheet listing every noted row.
- IED Schedule sheet (M80, ADR 0035 amendment): Build can add a reference sheet of the IED
  schedule, one row per IED row and port need with each side's ports, then totals per speed, media
  and landing as formulas, so the L1 switch count can be audited. Preview has the tab.
- Function tags on library parts (`tags`, plan M81): a `tags` column in the CSV (split by `|`), a
  *Function tags* field in the device editor, and Library search and the part picker match them.
  psa-devices 1.17.0 tags every part with its category, a switch's Purdue level and its largest
  port group, such as "Network switch", "L2 switch" and "24-port".
- PDF export (M78, ADR 0039, Q73): after a build, *Export PDF…* writes the chosen sheets of the
  workbook as a PDF next to it, with each sheet's page setup, header and footer. The built-in
  renderer needs no Excel; on Windows with Excel, *Use Excel* prints exact pages.
- Mark as revised (M79, ADR 0036 amendment): Preview can mark a BOM row as revised, with a reason,
  when the compare can't see the change. The row is highlighted yellow, *Build as issued…* lists the
  compare's changes and the marked rows before writing, and the issue records the marks and clears
  them (`revision_marks`, `issues[].marked`).
- Overrides in Checks (M77, ADR 0040): Checks lists every override a build applied, with its
  automatic value, in an *Overrides* group. One below the automatic value warns until it carries a
  one-line reason, given on the Checks row or the panel editor and stored with the override
  (`options.override_reasons`, `spares_list.reasons`). Recording an issue keeps the risky
  overrides, and the Revision History sheet prints them in an OVERRIDES column. The fan choice,
  the grounding busbars and the cable managers' count show their rule.

## [0.4.0] - 2026-11-04

The engineer-controlled workflow: milestones M48 to M69 of the
[agent implementation plan](docs/superpowers/plans/2026-11-03-agent-implementation-plan.md)
(ADRs 0031 to 0037, questions Q62 to Q71). Every new input is unset in the example, so it builds
as in v0.3.4.

### Added

- External links (`network.external_links`): links to the control centre, a PCC or a third party,
  each with its count, speed, media, landing (L2 or the external switch), firewall, sides and cable
  length. A link on L2 adds to the L2 demand and puts its SFPs on the L2 switches; a link on EXT goes
  on the external switch's port plan. Parts edits them, the Result card lists them, and Checks fails
  a firewall link without a firewall row or an EXT link without an external switch (M61, Q64).
- An IED schedule (`network.ied_schedule`) as an alternative to the IED count: rows by bay and
  IED type with ports per side by count, speed and media, dual or single attachment, landing on
  L1 or L2. The L1 switches are sized against their port groups per speed and media, ports on SFP
  slots become L1 downlinks (and SFPs), L2 rows add to the L2 demand, and a sizing error names the
  speed and media no switch serves ("1G RJ45"). The example keeps `ied_count` (M60a, ADR 0034).
- Parts: a Quick count / IED schedule switch with the schedule's table (bay, IED, qty, ports per
  side, attachment, landing, notes), Add a row, remove with Undo and Import CSV… with a review of
  the rows and the skipped ones; the Result card shows the IED ports per speed and media on each
  side, and a schedule no L1 switch serves names what does not fit (M60b, ADR 0034).
- Library parts carry a lifecycle state (draft, reviewed, released, obsolete; released by
  default), an obsolete part's successor, and a source for each sized figure: power, inrush,
  height, maximum input voltage and ports, each from a datasheet, the contractor, a measurement or
  assumed. `devices.csv` exports and imports them as `state`, `successor` and `source_<field>`
  (`kind|ref|date`). Nothing in a BOM changes (M67a, ADR 0037).
- psa-devices 1.16.0: every part says where its power, inrush, height, input voltage and ports
  come from: the device database's datasheet, the contractor's cited document, or assumed with
  the reason. Checks warns when a picked part's power or inrush is assumed (M67b, ADR 0037).
- The device editor shows a part's state, its successor when obsolete, and a Sources table beside
  the sized figures; changing a figure asks for its source before you save. Library marks draft,
  reviewed and obsolete parts and filters to *Assumed values*; Parts badges an assumed power or
  inrush (M67c, ADR 0037).
- Library has a Review tab for draft and reviewed parts (mark reviewed, release, or send back with
  a note) and a Health tab: parts by state, assumed figures, parts with no alternative, obsolete
  parts that projects on this PC still use, and brand sets missing an MCB rating or a housekeeping
  role (M68).
- Parts can propose a saved override to the library: the value goes into the library's pending
  changes with its source and a note naming the project, and the part waits in Library › Review
  (M69).

- The panel editor's main MCB shows the engine's rating with the rule it came from ("10 A: next
  standard size above 7.1 A, minimum 6 A"); click it to type your own, *Use automatic* to go back
  (M48). Part overrides on Parts use the same derived-value look, and leaving a value with Tab now
  closes its input.
- Parts shows the SFPs on each switch's BOM rows as links, spare and extra, with the total and the
  rule behind it. Set the spare to replace the project's spare SFPs for that speed and media, or add
  extra SFPs; the BOM quantity stays a formula such as `=6+3+2`, and Checks warns when the extras
  need more slots than are free (M49).
- Parts › Network fine tuning has *Most panels*: the layout opens no panel past it, and Panels lists
  each device that doesn't fit with the rack units it is short (M62).
- Each Parts row has *BOM text*: purpose, tag, type code, first number and HWIO points, with the
  generated tags as placeholders. A first number of 21 on the L1 row prints PSA1-L1-ESW-A21 onward,
  and a tag another unit already has is flagged on the row (M59).
- A generated panel can have its own enclosure and kind: the panel editor's Enclosure tab gains
  *All generated panels* / *This panel only* and a Kind select, and cable entry gains Bottom (M50).
- New substation, for a blank one, asks for its cabinets and documents: cabinet number, name and tag
  prefix patterns, the enclosure and cable entry, and the BOM, power and heat document numbers,
  filled in from the previous substation. What you type is written without the ASSUMED mark, and
  Checks warns while a document number is still TBD (M51).
- A substation can state its design basis in `design_basis`: DC and AC voltage feed the design
  constants unless the substation sets its own, and `tagging` sets the side letters and first
  numbers that device tags use. Unset, everything builds as before (M52a, ADR 0031).
- Settings has a *Design basis* tab first: DC and AC voltage, time sync, Purdue scope, tag side
  letters and first numbers, and notes. Design constants say *From the design basis* on a voltage
  it sets (M52b).
- Settings › General has *Save as template…*: the design basis, brands, spares, panel look, parts
  and loose items go to `templates/` in the project folder, and New substation can start from it
  with no panels, documents or quantities (M55).
- `project.yaml` can hold client vendor lists (allowed brand sets, makes and parts, banned parts),
  and a design basis names one. Parts lists its parts first and marks a part off the list; Checks
  warns about it, and about a draft or obsolete part with its successor. Nothing stops a build
  (M53a, ADR 0031). Project › *Vendor lists* adds and edits them: makes, brand sets per catalogue,
  allowed and banned parts (M53b).
- Checks compares the substation with its design basis: a DC part rated outside its DC voltage
  fails; an AC part at another voltage, a Purdue level out of scope, a GPS clock with no time
  sync, and EXT devices with no firewall warn. *Go to the field* opens the Design basis tab (M54).
- The panel editor's Options tab shows the AC and DC spare breaker ratings with the rule behind
  them; click one to set your own. Grounding busbars are checkboxes from the library's catalogue.
  *Alarm on branch MCB trip* can be switched per Parts row and per hand-written panel row, over the
  library's value (M58).
- The panel editor has a Terminals tab: each terminal strip with its block type and its quantity,
  shown with the rule behind it ("2 x 6 AC MCBs = 12"); click a quantity to set your own, or pick
  another block type. *Spare terminals* (Project › Overview, Parts › Network fine tuning) adds a
  share to each wiring strip, rounded up: 10% makes X3-AC 14 and X4-DC1 36 in Cabinet 001 (M57).
- A panel's housekeeping kit is now an input: the number of lamps, fans, thermostats and filters,
  a heater or hygrostat (from the library's new heater and hygrostat roles), and whether the smoke
  detector is supplied, only wired to terminals, or left out. Housekeeping breakers are sized from
  the part's AC watts when it gives them, never below the spec's rating, and a panel can set its
  own. With nothing set every BOM is as before (M56a, ADR 0032).
- The panel editor's Options tab has *Cabinet housekeeping*: the lamp, fan, thermostat and filter
  counts with the spec's kit as placeholders, heater and hygrostat, and each housekeeping breaker
  with the rule behind it; click one to set your own. Library › Catalogues › Housekeeping lists the
  heater, hygrostat and smoke detector roles (M56b).
- A hand-written panel's Devices rows take a tag, type code and first number, with the generated
  tag as placeholder and a shared tag flagged on the row (M59). Moving, adding or removing a device
  there no longer writes the page's own fields into the panel file.
- A Summary BOM sheet for procurement (M63, ADR 0035): every part totalled by ordering code across
  the cabinets and the loose material, with where it is used. Turn it on with the switch on Build;
  Preview shows it as a tab, and *Export summary as CSV* writes the same lines for a purchasing
  system. Each quantity is a formula over the BOM sheets, so a hand edit in Excel carries through.
- Recorded issues (M66a, ADR 0036): `bomgen build --issue "<description>"` records the rev, date,
  file hash and the prepared, checked and approved names in `substation.yaml`; the next build
  compares with that issue on its own, or warns and builds without it when the file has changed.
  A Revision History sheet lists every recorded issue and the current revision. Warnings accepted
  in `checks.accepted` show their reason in the check report and stop counting as open.
- Spare Parts (M64a, ADR 0035): the design basis `spares_policy` gives each Summary BOM line in
  its categories a spare quantity (percent of installed, rounded up, at least the minimum), and
  `spares_list` overrides a quantity, leaves a line out or adds an item. The workbook then gets
  a Spare Parts sheet after the Summary BOM, with the rule as a live formula and its text in BASIS.
  `minimum_per_part` defaults to 1 (Q65).
- The app has a Spares page under Loose material (M64b): the policy it follows, each line's spare
  quantity to set by hand or reset, *Leave out*, *Put back* and *Add item…*. Preview has a Spare Parts
  tab.
- Cable Schedule (M65a, ADR 0035): a loose material row can carry cable data
  (`cable: { from_tag, to_tag, length_m, media, speed }`); the workbook then gets a Cable
  Schedule sheet after the Summary BOM listing each such row with its quantity as a formula on
  the Loose Material sheet.
- Cable suggestions (M65b, Q66, Q71): `suggest_cables` lists the patch cords the port plans call
  for, one per link counted once at its upper end (L2 downlinks, L3 uplinks, external links; the
  L1 A-B interlinks once from side A), 2 m in a cabinet and 5 m between cabinets unless the design
  basis `cables` says otherwise, and an external link at its own `cable_length_m`. A library cable
  part (`media`, `length_m`) of the media and length is picked, else the cord is free text with a
  warning. Accepting appends them as loose rows with cable data; nothing is written before.
- Loose material has *Suggest cables…* (M65c): a review of the suggested cords with their ends,
  length class and warnings, each row ticked, added in one write. Rows that are cables get From,
  To and Length columns to edit, and Preview has a Cable Schedule tab.
- The app records issues too (M66b, ADR 0036). Build has *Build as issued…*: it asks for a
  description, builds, then records the rev unless a check failed. Without a chosen previous issue
  every build compares with the last recorded one, or says why it can't. Checks has *Accept…* on
  a warning (a reason and an optional name) and lists acceptances no warning matches any more,
  each with *Remove*. The register has Prepared, Checked and Approved per document. Preview shows
  the Revision History tab.

### Changed

- Changing a library part's power, inrush, height, input voltage or ports now needs that
  figure's source in the same change, in the device editor or a CSV import; *assumed* counts.
  Each save writes who changed the part, when and the note. A library saved this way opens only in
  this release or later (M67b, ADR 0037).

## [0.3.4] - 2026-11-01

### Added

- Desktop conveniences (M39, APP-25 to APP-28). When the window comes back
  into focus and someone else changed a project file, the app reloads it and
  says so, or, over unsaved changes, asks: Reload (lose my changes) or Keep
  mine. Home offers Restore deleted project… for 30 days. F6 moves between
  the rail, the page and the status bar, and Ctrl+O opens a project folder.
  Project › Overview offers Record <active version> in this project when the
  recorded library differs, with Undo.
- Add a device on Parts offers Monitor and Keyboard and mouse (M38, APP-23),
  and the rail shows "Not set up" on Parts until a substation has its first
  parts, or how many rows name a part the library lacks (APP-24). A
  generated panel's Enclosure tab edits the numbering every generated panel
  shares: the cabinet name, cabinet number, tag prefix and sheet name
  patterns, where {n} is the panel number (ALI-5, ALI-13).
- Library › Catalogues edits every brand set (M36, APP-20). A switch picks
  MCBs, aux contacts, terminal blocks, busbars or housekeeping; one tab per
  brand with the default marked; rows are edited in place, with Add rating or
  Add row and a per-row remove; housekeeping roles pick a library part. Add
  brand… copies another brand's rows, and Make default swaps a brand with the
  default set. Every edit is a pending change, and one the library refuses
  stays in the table with the reason.
- The installer ships psa-devices 1.12.0 with SEL's -2 generation computers:
  SEL-3555-2 and SEL-3355-2 at 45 W, SEL-3560E and SEL-3560S at 35 W. Each is
  SEL's typical figure (25-50 % load) with its SEL-9331 supplies, as Ali
  chose for plan Q54.
- Settings › YAML can be edited. Each change is checked as you type, with
  the problem on its line, and "Apply to form" drafts the Settings fields
  from the text once it has no errors; Revert puts the saved file back. The
  Design constants table says "Default" on each unchanged row (M37).
- `data/device-db/tools/library_entries.py`, the M14 generator, is in the
  repo. It turns the device database's alternative tiers into shipped-library
  parts, appends only the ones the library lacks to
  `data/library/additions.yaml`, and lists the powered tiers it skips for want
  of a power figure.
- The device database has power figures for two more alternatives (finding
  30): the SCALANCE XR324-4M EEC, now under its 125 V DC code
  6GK5324-4GG10-4JR2, at 42 W, and the Arbiter 1202B/C at 30 W. The nine
  that publish none say so (`power_basis: not_given`). The SEL-2244-2 Siemens
  alternatives give their digital input count, `di_inputs` (finding 31).
- The installer ships psa-devices 1.13.0. It adds the SCALANCE XR324-4M EEC
  (42 W) and Arbiter 1202B/C (30 W) alternatives and six Weidmüller and Brady
  nameplate alternatives, and the SEL-2244-2 Siemens alternatives count 16,
  32 and 32 digital inputs (M41c).
- The device database records that no datasheet publishes inrush for the
  parts that lack it (M42, ALI-9, finding 32): the Finder and Weidmüller
  interposing-relay alternatives say `inrush_basis: not_given` with the
  documents searched, and their branches stay sized from running current and
  the 2 A floor.
- The installer ships psa-devices 1.14.0. 51 alternatives that printed their
  original's description now give their own ports, power, supply, digital
  inputs or product name (M43), for example the SCALANCE XR324-4M EEC as
  "8 MM Ports, 16 RJ45" and the SoftMaker suites under their own names. A
  figure the device database lacks is left out of the text.
- The installer ships psa-devices 1.15.0. The contractor's switches (Cisco
  IE-4010-16S12P and C9300-24T-A, RUGGEDCOM RST2228-28SFP-HV, SEL-2743 and
  SEL-2744), the eight FortiGates and the 21 Hubbell FEUR fibre shelves now
  carry a tag type and level, so they print with a tag and a nameplate. The
  automatic L1 pick, the IE-4010, prints L1-ESW-A11 like the RST2228. The
  NAP-K55 annunciator ships its LPA37-696 wall-mount kit as a loose item
  (M44).

### Fixed

- A link to the L2 switch at a speed and media the library has no SFP for
  is now a problem on its Parts row, which Checks and Build list with Go to
  the row, instead of "The engine stopped" (M46). The Parts row warns too.
- A substation's annunciator row now goes to loose material with its
  wall-mount kit, fed from panel 001, instead of into a rack (M45, design
  §10). The checks warn when a switch, firewall, gateway or other device that
  should carry a tag prints without one (untagged_device).
- Editing a generated panel numbering pattern in the panel editor drops its
  "# ASSUMED" mark, and rows written by Start parts and Add a device put id,
  part_id and role before the seeded L2 link, as hand-written rows do (M47).
- A substation that picks an MCB brand without a DC brand no longer stores
  that brand as its DC set: the DC branches still size with it (ADR 0023),
  and the resolved library validates again when the brand has no DC rating
  (M40).

## [0.3.3] - 2026-11-01

### Added

- The installer ships psa-devices 1.11.0, whose housekeeping catalogue lists
  two larger fans for ADR 0029: Rittal SK 3244.500 (485 m³/h, 80 W) and
  SK 3244.100 (520 m³/h, 138 W), each at 60 Hz with one SK 3243.200 outlet
  filter, the 460 m³/h basis. They fit the same 292 mm cut-out and outlet
  filter as the SK 3243.100. The 630 m³/h SK 3245.500 is left out because it
  is IP 51.

### Changed

- Every device with a level is tagged level, type, side and number (M30,
  ADR 0030): the time server's plate reads L2_GPS_A01, the
  gateways PSA1-L2-GW-A01 and PSA2-L2-GW-B01, and the EXT switch and
  firewall PSA1-EXT-ESW-A01 and PSA1-EXT-FW-A01. A panel with no LAN uses
  side A. The operator workstation, engineering workstation and DA server
  get OWS, EWS and SRV, so they no longer share one tag. The check report
  fails a tag that two devices share. The installer ships psa-devices
  1.10.0: gateway, GPS, RTAC and workstation parts are L2.

### Fixed

- The console's BOM sheet has a 53.1 pt header row, as the spec's
  Formatting gives for sheet 4, the example's WS console (plan Q61, audit
  ENG-11). The other panel sheets keep 26.25.

## [0.3.2] - 2026-11-01

### Added

- Parts rows set each device's link to the L2 switch (M31): ports, speed
  (10M, 100M, 1G, 10G) and media (MM, SM, RJ45) on one line under the row's
  data, and an RTAC row its COM ports used. The sized switches and the patch
  panel have no link line. They save with the rest of Parts.
- A device added on Parts, or picked when a substation starts, comes with
  its link to the L2 switch filled in by category (M31, audit ENG-3):
  gateways, firewalls and workstations 1 x 1G, the GPS clock 1 x 100M, the
  RTAC 2 x 1G, and a firewall two MM SFPs (fewer if it has fewer SFP
  slots). A changed part takes
  the new part's link unless the row was edited. The check report warns
  about a networked device with no L2 link.
- Hand-written panels in the panel editor (M32b). Add hand-written panel… on
  Panels asks for a name, cabinet number, kind and first device, writes
  `panels/<id>.yaml` listed last in `manual_panels`, and opens it on Devices.
  A hand-written panel edits the cabinet's name, number, sheet, tag prefix,
  kind and side with its enclosure, the devices (add, reorder, remove,
  quantity, purpose, HWIO), options with "Use the default" and the document;
  its port plans stay in its file. Delete panel… lists what still names the
  panel instead of deleting it, and a delete can be undone.
- A library can list `larger_fans` in its housekeeping catalogue. A cabinet
  that the catalogue fan pair can't cool gets the smallest larger fan whose
  pair can, still two fans with the same AC branches and terminals (ADR 0029,
  Proposed). A library without the list builds as before.
- The installer ships psa-devices 1.8.0 from v2 of the contractor's library:
  the FortiGate 600F and 601F firewalls (230 V AC, now with their voltage and
  load type), and the Hager NCN 2P set is DC rated, 250 V with the two poles
  in series (6 kA; 15 kA at 125 V) and a DC magnetic multiple of 7, so it can
  be chosen as `mcb_dc`. Hager MCN stays an AC set.
- The installer ships psa-devices 1.9.0. The shipped library now applies
  overrides from `data/library/additions.yaml` to the example's parts, and
  `examples/library.yaml` and the goldens keep the issued workbook. With them,
  the SK 3110 thermostat draws 0 W and each fan gives 460 m³/h with the SK
  3243.200 outlet filter, which replaces SK 3238.200 (plan Q29). NAP-K55 takes
  0U. The gateway tags drop the example's `DHPCC`. The five contractor
  switches carry Purdue levels as a design call: L2 for those with 10G
  uplinks, L1 for the 1G bay switches.
- Device preview on a substation with no panel files offers "Lay out panels"
  (APP-15). The project Overview edits the waist height and rack start, each
  marked Assumed with Confirm until it is written (APP-19).
- The panel editor for generated panels (M32a; APP-3, APP-4). Each panel opens
  from the Panels list or its board column, with Enclosure, Options (for every
  generated panel or this one only, with Own value and "Use the shared
  value"), Port plans (the device's own, with the engine's SFPs and cables
  under each; the L1 and L2 switch plans are read-only) and Document, saved to
  `substation.yaml` through the save bar. Devices lists each unit with its
  origin and "Show on Device preview"; YAML is read-only. The Panels header
  has Undo and Reset to automatic. A located problem now opens where it is
  fixed: Checks, and Panels and Device preview when they cannot show, say
  "Go to the row", "Go to the field", "Open the panel" and so on (APP-7), and
  an unknown part names the installed library by name and version instead of
  `library.yaml`.

### Changed

- `data/device-db/contractor-return-v2-2026-10-31.md` and its CSV list what v2
  of the contractor's library leaves open: 10 asks for the contractor, and 193
  configured codes, code identities and the Q54 power choice that are ours.
- `data/device-db/contractor-2026-10-31/` holds v2 of the contractor's
  library, their answer to the return list: 1045 devices (was 991), 112 port
  groups, `contractor_responses.csv` with a status for each of the 270 asks,
  and a new `power_measurements.csv`. Reference only; nothing the generator
  reads changes.

### Fixed

- A new substation works from its first parts to Build (audit 2026-10-31,
  M27). Device preview no longer hangs on a blank substation. Saving its
  first parts lays out its panels. Checks and Build say what is missing, parts
  or panels, instead of "You can build". Build counts the engine warnings that
  Checks lists. A device's own loose items, such as the SEL-2488 antenna kit,
  reach the Loose Material sheet without a loose material block. New
  substations' panels get the spec's 40 XIP terminals.
- The check report names AC loose loads, which the DC-only External
  Equipment block leaves out of the totals. When no cabinet has
  fans, the steel coefficient box no longer lands on the constants box. The
  device nameplate row is a normal BOM row, not a tall white grounding row.
- Leaving Parts, Settings or the project Overview with unsaved changes asks
  first: Keep editing, Discard changes or Save and leave. This applies to a
  link, another substation and another project, and the status bar says
  "Unsaved changes" (M29; audit 2026-10-31 APP-6).
- The first Loose material save no longer reports "Not saved" (APP-5).
  "Save the parts" also saves the IED count (APP-16). The rail's Panels count
  follows a layout (APP-17).
- Checks and Build name every engine check and the device it is about
  (APP-13). A substation that does not load keeps its name (APP-14). The copy
  reads "3 L1 switches" and "Add an RTAC" (APP-18).

## [0.3.1] - 2026-10-31

### Added

- The installer ships psa-devices 1.7.0 with 21 Hubbell FEUR fibre shelves
  from the contractor's 2026-10-31 delivery (12, 24 and 48 positions, LC, SC
  and ST, MM, OM3 and SM, plus the unloaded FEURFSPD), each its own
  alternative group. The delivery's `fiber_patch_panel` becomes the library's
  `patch_panel` (#265).

### Fixed

- Settings and Parts open on a new, blank substation again; in 0.3.0 they
  showed "StopIteration:" because the Parts page sized SFPs for switches the
  substation did not have yet (#267).

## [0.3.0] - 2026-10-31

### Added

- `data/device-db/contractor-return-2026-10-31.md` and its CSV list what goes
  back to the contractor after the 2026-10-31 delivery: 270 asks over
  undelivered worklist parts, missing fields, configured ordering codes, three
  SEL management-port speeds, the Q54 power figures and Hager DC ratings (#260).
- The installer ships psa-devices 1.6.0 with the FortiGate 401G and 701G
  firewalls from the contractor's 2026-10-31 delivery, each its own
  alternative group. Their 2.5G, 5G and 25G ports are listed as on the
  datasheet and are never sized for SFPs (ADR 0027, #259).
- A port group can give 2.5G, 5G and 25G ports (ADR 0027 proposed). They are
  descriptive only: an equipment entry's `l2_speed` and an SFP choice refuse
  them, so they never become an SFP pick (#258).
- The installer ships psa-devices 1.5.0 with two Hager MCB brand sets from the
  contractor's 2026-10-31 delivery: `hager-mcn-2p` (MCN 2P C, 6 kA) and
  `hager-ncn-2p` (NCN 2P C, 10 kA), 1 to 16 A. Hager gives no DC rating, so
  they are AC sets: a project refuses one as `mcb_dc`, and the check report
  warns when one feeds the DC branches through `mcb` (#257).
- App: the Preview page shows the Nameplates sheet (M26, ADR 0026) as a tab
  after Loose Material, one row per plate with its panel, plate text and
  device (#256).
- Device nameplates (M26, ADR 0026): each panel BOM ends with one
  nameplate row whose quantity is its tagged devices, and a new Nameplates sheet
  after Loose Material lists every plate's text (the tag as the MCB rows print
  it) per panel. The library names the part as the housekeeping role
  `nameplate`; the example uses Phoenix Contact US-EMLP (60X30). The example's
  BOM sheets each gain that row, and the installer ships psa-devices 1.4.0
  with the part and the role (#253).
- The installer ships psa-devices 1.3.0 with twelve parts researched in the
  contractor's 2026-10-31 delivery, each its own alternative group:
  C9300-24T-A, IE-4010-16S12P, RST2228-28SFP-HV, SEL-2743 and SEL-2744
  switches, FG-121G, FG-60F, FG-70F and FGR-70F firewalls, SEL-3530-4 and
  SEL-3350-1 RTACs and the SEL-2407 clock (`data/library/additions.yaml`).
  The switches have no Purdue level yet, so they are not L1/L2 picks (#251).
- App: Device preview shows an AC unit's own AC branch MCB (M25, ADR 0025) as
  its PS1, in place of the "—" it showed before (#252).
- App: Parts rows collapse to a one-line summary at 20 or more rows ("1 U ·
  77 W · 125 VDC · 2 overrides"), and a category with more than 12 parts picks
  its part with the Device picker: search, up to 8 matches with make, model,
  supply, power and data quality, keyboard ↑ ↓ Enter Esc. Parts options carry
  the supply, rated power and data quality (M23 follow-ups, #250).
- Every AC-powered device unit in a panel gets its own AC branch MCB in group E,
  after the socket and before the spare, sized like the DC branches from the AC
  catalogue; CINC is raised to carry them (M25, ADR 0025). The
  example has no AC device, so its BOM is unchanged (#248).
- App: the Device preview page (M24), after Parts in the rail. It draws a
  front view of each panel from the engine's device preview, with cable
  managers, the waist line and DIN-rail parts. A table lists each unit with
  its part, BOM part number, panel, U, watts, supply and branch MCBs. A unit
  can be pinned by dragging it, or with Up 1 U and Down 1 U, and unpinned;
  each move is checked live and can be undone. Parts gets "Generate preview",
  and a warning's "Go to the row" lands on that row. The Panels board and the
  preview share one pointer-drag helper (#247).
- Device preview engine (M24): `engine.preview.device_preview` lays out the
  substation, builds it in memory and lists every generated unit with its
  panel, top U, branch MCBs, terminal strips and overridden values, plus the
  layout and check issues; nothing is written. A layout override can pin a
  unit by its top U (`top_u`, exclusive with `position`); a pin that leaves
  the rack or overlaps another is a layout error (ADR 0013 amended). Branch
  MCB records name the unit and feed they serve (#245).
- App: the Parts page replaces Network (M23). Each device row picks its
  library part and can carry a BOM part number, this design's overrides of the
  part's height, power, supply, voltage, supplies, inrush and load type (a value
  equal to the library is not written), an SFP choice per speed and media, a
  Cable manager switch on network rows and, on the time server, accessories
  written as loose material items. Changing a part clears its overrides, SFP
  choices and part number. Rows move up or down, are added by category and
  removed with Undo; a new substation starts from a setup card. `#/network`
  opens Parts. The L1 ranking and the Change… dialog are gone (#244).
- A switch, patch panel, firewall or gateway can have or not have a cable
  manager (`cable_manager` on the equipment entry or panel row): the layout
  gives or drops its 1U manager and the BOM counts it accordingly; unset keeps
  today's rule (#243).
- Generated panels stack their devices by priority: time server on top, then
  network, then servers and workstations, then the rest, keeping equipment
  order within each. A KVM or console sits with its bottom edge at waist
  height (`defaults.layout`, U18 with the assumed 1000 mm and 200 mm), and
  every unit gets a top U. A panel too short for that is a layout error (M21,
  ADR 0013 amended, #241).
- Panels: a board of hand-written panels has "Lay out panels from the
  equipment". After a confirmation it writes the generated panel files as
  `bomgen layout --force` does, copying each file it replaces to
  `panels/hand-written-<date-time>/` first, and the board becomes draggable
  (M19, #238).
- A substation's equipment entry can carry its own BOM part number
  (`ordering_code`), overrides of the library part's height, power, supply,
  voltage, power supplies, inrush and load type, and an SFP choice per port
  speed and media on the L1 and L2 switches. The loader builds a derived part
  for that substation only, so the layout, MCB sizing, power and heat use the
  overridden values; the library is not changed. The check report warns about
  a device with no part number. New Parts page roles, the `kvm` and `console`
  categories, and `defaults.layout` waist height and rack start (ADR 0024,
  #239).

### Changed

- The installer ships psa-devices 1.2.0. The SEL-2730M-EXT gets its
  datasheet inrush (8 A per feed) and the IPR-2903685 relay its coil range
  (179.4–317.4 V AC), both cited in the contractor's 2026-10-31 delivery.
  Original parts take their make from the device database: IPR-2903685,
  IPR-BASE-2900934, IPR-SUPP-2900944 and IPR-BRACKET-2900954 print Phoenix
  Contact, FGR-60F and FR-TRAN-SX Fortinet, ZENON-V12 COPA-DATA and
  MS-OFFICE-2021 Microsoft. The example library and the goldens are unchanged
  (#249).
- The device editor shows "Minimum branch MCB" read-only, marked deprecated,
  with the reason: branch MCBs are sized from the rated power and inrush
  current (ADR 0019), so typing a value there changed nothing (#228).

### Fixed

- A rack-mounted firewall in a generated panel gets its cable manager row on
  the BOM; the layout already gave it the 1U (ADR 0013, Q32, #243).
- Dragging a device on the Panels board works in the installed app. The board
  now drags with pointer events instead of HTML5 drag-and-drop, which never
  reached the page in the Windows app; the drop rules, the live green or red
  panel and Esc to cancel are unchanged (M19, #238).
- The installed app no longer carries the design prototype's illustrative
  substation, library and checks. When the window cannot reach the Python
  engine it says so on every page, with Try again, instead of showing example
  figures as if they were real (#227).

## [0.2.1] - 2026-10-29

### Added

- Network › Equipment: Change… on a row with a part picks a new part, with the
  part's alternatives listed first and their power change per unit; the pick
  is an unsaved edit, checked and saved with the rest, and the row shows
  "Was X" (#199).
- The device editor's Parts picker shows each part's make and model next to
  its id (#200).
- Use this instead: Use… on an Alternatives row lists the open substation's
  equipment rows that use the device, and choosing one opens Network with the
  new part as an unsaved edit (#194).

### Changed

- The v0.2 polish pass (`docs/ui/polish-v02.md`):
  - Unsaved edits get the changed marker (a dot and a hidden "changed")
    instead of the revision yellow, which is kept for Preview's revised
    cells. Number inputs are right-aligned, "N fields need fixing" is one
    control that moves to the first invalid field, and a route change closes
    an open dialog (#205).
  - The device editor gives list errors in words ("Pick a part from the
    library.") and only once a new row is saved, shows choices as labels
    (Continuous, Serial port, DIN rail), labels the Datasheet height "Height
    in the datasheet" and gives Power input a text area; row delete buttons
    share one style (#206).
  - Network equipment rows keep the part id on one line with Change… after it,
    the Role column shows whole names, and Change… shows a busy state and
    opens only if you are still on that Network page. Settings names the
    resolved brand ("Same as the project (Schneider Acti9 2P)", "Same as AC
    branches") in a two-column Catalogue brands form and shows document keys.
    Register rows are two lines with singular or plural wording, the project
    path is cut with an ellipsis, the save bar is pinned to the window's
    bottom edge on every page, and Loose material's table foot and free-text
    banner are reworded (#207).
- The Loose material library picker shows each part's data-quality badge,
  "N fields need fixing" moves to the first invalid field on every draft
  form, dialog errors name the fields, a free-text item's Fed from "—" has
  screen-reader text, and the save toast reads "Saved N changes" (#201).

### Fixed

- An id in a table's second line no longer breaks at a hyphen, and the device
  editor's tab panel is back at its offset from before #207 (#208).
- Deleting a device added in the pending changes and not applied yet says it
  is dropped from the pending changes, without the in-use warning (#198).

## [0.2.0] - 2026-10-29

### Added

- Project and substation settings in the app (M17c): on the Project page the
  client, logo, shared defaults and catalogue brands (DC MCBs can follow the
  AC branches); on Network the IED count, topology, ring size and spares, with
  a setup card for a new substation, and equipment rows edited, added and
  removed with Undo; every Settings tab but YAML (name, brands, documents,
  output and design constants with Reset); and the document register (edit in
  place, Confirm an assumed date, add and remove with Undo, each row's users).
  A blank substation starts with **Add the core switches…**. Changes are
  checked by the model as they are typed and saved from a save bar or Ctrl+S
  (#185, #188, #190, #192).
- Create, rename and delete projects and substations in the app (M17d): New
  project… on Home, New substation… and Create from this… on the Project page,
  Rename… keeps folders and ids, and a delete saves a backup or a `.bomproj`
  first (#181).
- The app's library editor (M16): Edit device opens the device with
  Identity, Electrical, Ports and mounting, Parts it brings, Datasheet and
  Alternatives tabs, checked field by field. Edits wait in a pending set shown
  on the library pages until Review and apply saves them as the next
  `+local.N` version. Add device… starts a blank device or a copy, Delete…
  queues a removal, and an In use banner names the open substation's rows.
  The Alternatives tab compares a device with its group (power, inrush and
  height deltas), and Export… and Import… write CSV tables or a `.bomlib`
  backup and bring edited CSV rows in through a review step (#155, #166, #175,
  #178, #180).
- The shipped library (Q38, M14 follow-up): `data/library/psa-devices.yaml`,
  generated by `data/library/build.py`, is the example library plus each
  original part's datasheet inrush and DC input range; the installer now packs
  it as psa-devices 1.1.0 instead of `examples/library.yaml`, which stays the
  spec's example. With it the SEL-3555 and SEL-3355 branches size to 6 A.
  Schneider C60H-DC is marked DC only (`ac_rated: false`) (#161).
- Device-database records can be edited: `apply_record_edits` and
  `check_record_field` use the library's edit operations on `device-db/`
  records, and `save_edits` saves them in a `+local.N` version, alone or with
  library edits; ADR 0018 amended (M16, #164).
- `part_users` lists the rows that use a part: equipment, panel rows, loose
  items and the library parts that bring it (#163).
- DC MCBs can come from their own brand set: `catalogue_choice.mcb_dc` picks a
  DC-rated set for the DC mains, branches, spares and QCOD circuits and their
  sizing; unset, the DC set follows `mcb`, so existing projects do not change.
  ADR 0023, plan Q39 (#151, #154).
- Library data (M14): the example library is psa-devices 1.1.0, with the
  researched alternatives as parts in each device's `alt_group` and DC-rated
  MCB brand sets (Schneider C60H-DC, ABB S200M UC, Siemens 5SY5) with their
  aux contacts, plus further terminal block, busbar and housekeeping sets;
  iC60N stays the default (#130).
- Power footnotes: `output.power_footnotes` on a substation lists free-text
  footnotes, and the Power Consumption sheet prints each one on its own merged,
  wrapped row two rows below the NOTES, inside the print area; the example
  carries the reference workbook's printer footnote (#152, #157).
- The app's Loose material page (M18): add library or free-text items, edit,
  move and remove them, with per-field messages and a save bar; ADR 0022
  (#146).

### Changed

- The frozen app's `--self-test` checks every script, stylesheet and font the
  UI loads, so a release fails on a missing UI file; ADR 0009 updated (#186).
- Tests build the example project with the shipped library and pin its MCB
  sizing: 6 A for the SEL-3555 and SEL-3355 branches and their spares, 2 A
  elsewhere, and the FGR-60F and iC60N float-voltage warnings (M15, #171).
- Releases: a merged PR that bumps the version releases from `main`, after
  checking that `CHANGELOG.md` has the version's section and
  `pyproject.toml` agrees; a hand-pushed tag still works. ADR 0009 amended
  (#153).
- Each input file is parsed once per text and cached, roughly halving the
  test suite's time (#149).
- A DC-only MCB brand (`ac_rated: false`) is refused as the
  `catalogue_choice.mcb`, which also sizes the AC branches, and the error
  names the AC-rated brands (#145).

### Fixed

- A new blank substation is seeded with `generated_panels`, so it can take
  its first equipment rows; `cabinet_number` and the enclosure are marked
  `# ASSUMED` (#189).
- The YAML writers write a new mapping in block style and repeated values in
  full, without `&id001` anchors (#187).
- Deleting a project refuses a folder holding `.git`, the home folder or a
  drive root, and removes only the files its `.bomproj` keeps (#182).
- A library's default DC MCB set (`catalogues.mcb_dc`) survives a CSV export
  and import, and CSV row problems read as plain messages with an example;
  ADR 0018 amended (#179).
- A library CSV export and import keeps a brand's `ac_rated` flag (a new
  last column of `mcb.csv`), and a library diff counts added, changed and
  removed brand sets, so a brand-only edit can be saved (#165).

## [0.1.1] - 2026-10-28

### Added

- The installer ships the default device library, and the app loads it into
  an empty library store on first start (#86).
- Panels board editing for generated panels (M17): drag and drop moves a
  device to another panel or position (a pair moves together; Alt moves
  one unit), pins hold a unit where it is, units can be deleted, and Undo
  (Ctrl+Z) reverses each change. Alt+arrow keys move the selected unit
  within its panel or to the neighbouring one, and the Move… dialog shows
  each panel's rack space after the move. Pinned units and their positions
  are shown on the board. `DeviceMove` and
  `PairMove` take an optional `position` (1 = top), and every override pins
  its units; ADR 0013 amended (#100, #110, #126, #129).
- Library: the Library screen shows the catalogues (#93). Devices gain
  `alt_group` and `tier`, so alternatives are ordinary library parts, and
  further MCB brand sets live in `catalogue_brands`, chosen with
  `catalogue_choice` on the project defaults or a substation; ADR 0017
  (#97). An edited library is saved as a local version (`+local.N`) with a
  `.bomlib` backup, through edit operations by path with per-field
  validation (#105, #113, #114). `bomgen library export-csv` and
  `import-csv` exchange a library as CSV tables for Excel; the import is a
  dry run first and names a cell that starts like a formula; ADR 0018
  (#116, #118). Comparison rows set a device beside its alternatives
  (M16, #120).
- Branch MCBs are sized from device data (M15, ADR 0019): running current
  and inrush against the MCB's magnetic trip multiple, with a 2 A floor;
  inrush shorter than 10 ms is ignored. Devices gain `inrush_a` and
  `inrush_ms`, and the MCB catalogue gains `trip_curve`, AC and DC trip
  multiples, `dc_rating_v` and a `codes` map (#97, #103).
- The check report warns when an MCB's DC rating or a DC-fed device's
  `input_v_max` is below the battery float voltage (`dc_float_v`, 140 V).
  Device types gain `input_v_min` and `input_v_max` (#104, #109).
- Loose material (M18): the table has its own Loose Material sheet after
  the cabinet BOMs, read by Power Consumption and the revision comparison
  (ADR 0020), and its own Preview tab in the app (#96, #108). A loose item
  can be free text with a description instead of a library part
  (ADR 0022, #122).
- File writers (M17, ADR 0021): projects, substations and hand-written
  panel files can be created, edited and deleted without hand-editing YAML.
  Edits keep the files' own style and comments, are checked before they are
  written, and are written atomically only when they add no new problem.
  `io/round_trip.py`, `io/edit.py`, `io/panel_edit.py`, `io/fields.py`,
  `io/lifecycle.py` and `io/loose_edit.py` hold the writers, and the app
  exposes them as editing endpoints (#106, #112, #115, #117, #119, #122).
- Device database: M14 electrical data for the alternatives and the MCB
  brand sets, and the checker accepts the tier, inrush and input-range
  keys (#95, #121).

### Changed

- Version 0.1.1; the release workflow's publish step attaches to a release
  that already exists (#86).
- A cable manager may sit directly against the device below it; a blank
  plate now goes only under a rack block that ends in its active device.
  The example's generated panels drop from 29U/25U to 23U/19U, and the BOM
  is unchanged; ADR 0013 R5 amended (M12, #90).

### Fixed

- The Panels board draws blank plates where the engine counts them (#101).
- No loose-material table is written when it has no rows (#123).
- A loose item with neither a part nor a description gets a clearer
  message (#124).
- Library store: writing a package creates its folder, and a failed write
  leaves no `.replaced` folder behind (#127).

## [0.1.0] - 2026-10-28

### Added

- Desktop app Network result, L1 ranking and Panels board, read-only: the
  network plan per side, the L1 switches in the engine's order and each
  generated panel's units, blank plates and layout issues; every substation
  screen is now connected (milestone M10c, #78).
- Desktop app Preview: each panel sheet and the three calculation sheets as
  the engine computes them, through `preview_substation` (milestone M10d,
  #71).
- Network sizing and automatic panel layout: `bomgen layout` sizes the L1 and
  L2 switches from the IED count and spares, fills the 32U panels and writes
  generated panel files; `bomgen build` lays out again a substation whose
  panels were generated, unless `--no-layout`, and stops on layout errors;
  after a layout the annunciator is fed from panel 001 (side A); the example
  substation gives 3 L1 switches per side; golden test of the generated panels
  (milestone M1c, #19).
- Desktop app Checks and Build screens: the substation's problems and the
  check report, and a build that refuses with `has_errors`, `file_exists`
  (asks before replacing), `file_open`, `bad_name`, `bad_folder`,
  `bad_previous`, `engine` or `write` (milestone M10d, #65).
- `bomgen build` prints the check report, writes it as `<name>.checks.json`
  and exits 1 when a check fails (`--no-checks` skips it); `--compare` marks
  the cells changed since a previous issue; the FGR-60F gets its 2 SFP slots
  (milestone M7, #62).
- Check report and revision comparison in the engine: SFPs against slots, DC
  mains against ΣQ, airflow and natural convection, DI capacity against HWIO,
  and the changed cells since a previous issue; ADR 0016 (milestone M7, #58).
- Desktop app Substation settings and Network inputs, read-only (milestone
  M10c, #60).
- Desktop app Keep both on a clashing import, and the restore review on
  `preview_backup_restore` (#63), which checks a restore's refusals before
  the import checks (#59).
- `bomgen build`: one workbook per substation of a project, or for one
  `substation.yaml`, into `--out` (default `out/`), named per OUT-2; `--substation`
  builds one; a golden test builds the example (first part of milestone M7,
  #51).
- `bomgen project import --rename-to ID` imports a `.bomproj` under a new
  project id and keeps the existing project; the dry-run suggests a free id;
  ADR 0012 amendment (#53).
- Library parts carry `di_inputs`, the hardwired digital inputs one unit
  provides, for the check report's DI capacity check (#52).
- Desktop app Home, Project page and Backup and share on the project store:
  the workspace's projects and recently opened folders with their status,
  export, backup, import and restore reviews; the Project page is read-only
  until project writers exist (milestone M10b, #49).
- Sheet models filled from the engine: one BOM sheet per cabinet with the
  loose-material table under its host, and the Power Consumption, Heat
  Dissipation and Heat Calculations sheets, every computed cell a live formula
  with its cached result; a golden test recalculates the written workbook with
  pycel (milestone M5, #48).
- Desktop app Library screens on the installed library store: browse with the
  device-database records, import review and import, versions (milestone
  M10b, #45).
- Power and heat engine: Power Consumption lines, blocks and summary, heat
  dissipation, forced-ventilation airflow, natural convection and the line-up
  check; ventilation `auto` is decided from the heat check; ADR 0014
  (milestone M4, #44, #46).
- BOM groups E–H as engine output: AC and DC distribution, terminal strips
  (including the devices' own strips), grounding busbars and revision marks;
  `pipeline.build` builds groups A–H in two passes; golden test over every
  group E–H row; plan Q34 (milestone M3, #36).
- Device-database records travel in a `.bomlib`: pack checks them, import
  installs them with the library and `bomgen.library_store.device_db` loads
  them (#41).
- Desktop app shell: the approved UI in a pywebview window with a Python
  bridge (`bomgen.app.window`, `bomgen.app.api`) and the `app` extra; it
  refuses to open without its UI files or WebView2; ADR 0015 (milestone M10a,
  #28).
- Import dry-runs for libraries and projects that list every check and write
  nothing, and listing and restoring project backups, for the desktop app
  (#31).
- Projects hold substations: `project.yaml` carries project info, library
  name and version, the document register, defaults and the substation list;
  `substations/<id>/substation.yaml` carries the former project settings plus
  equipment, network, spares and layout inputs; the library gains rack heights,
  port roles and enclosure heights; `bomgen validate` takes either file;
  `examples/` becomes one project with one substation, golden values unchanged
  (milestone M1b, #27).
- Equipment purpose, HWIO points and per-unit port plans in the substation
  inputs, with the example equipment in cabinet 001's group B order (#34).
- BOM groups A–D as engine output: enclosure, devices and tags, kit
  children, network accessories, housekeeping kit and the loose-material
  table, with a golden test over every group A–D row; ADR 0014 (milestone M2,
  #22).
- Sheet models and the XlsxWriter workbook writer: cells, live formulas,
  styles, merges, print setup, page header and footer (milestone M6, #21).
- `bomgen project export|import|backup`: projects shared and backed up as
  `.bomproj` files with a checksummed manifest, overwrite refusal with a
  safety backup, and a library-version note naming the `.bomlib` to install;
  the zip container is shared with `.bomlib` (milestone M8b, #20).
- Device database: rack height and mounting kind per record, port roles for
  the library switches (#18).
- ADR 0012 (projects hold substations, `.bomproj` sharing) and ADR 0013
  (switch sizing and automatic panel layout), milestones M1b, M1c and M8b,
  and Q24–Q28 resolved (#16).
- Windows installer and releases, built early: PyInstaller spec, per-user
  Inno Setup installer with `.bomlib` file association, frozen-app launcher
  with placeholders for the M10 window and `.bomlib` import, tag-driven
  release workflow that builds, smoke-tests and publishes the installer,
  `docs/install.md` and ADR 0009 (milestone M11, #2).
- M9 UI design in `docs/ui/`: design tokens, component and screen specs, a
  clickable HTML/CSS prototype and bundled fonts; ADR 0011 (#8).
- Device-library update packages: `.bomlib` pack and verify, a per-user
  library store with import preview, downgrade refusal and rollback, and the
  `bomgen library pack|import|list|rollback` commands (milestone M8, #9).
- Changelog entries for #6 and #4 (#10); README and test READMEs for M8 and
  M9 (#11) and for M11 (#14).
- Device database in `data/device-db/`: datasheet facts and two alternative
  brands (low, mid, high part numbers) for every part in the example library,
  as reference data the generator does not read; findings in
  `docs/device-db-findings.md` (#6).
- `CHANGELOG.md`; README status and usage updated for M1 (#4).
- Input models for the device library, panels and project; YAML loader with
  relative file references, panel mirroring and readable errors; JSON Schemas
  in `schemas/`; `bomgen validate` and `bomgen schema`; `examples/`
  transcribed from the example workbook; ADR 0010 (milestone M1, #5, #7).
- Repository scaffold: `bomgen` package, tooling, working rules, generator spec
  v2, implementation plan, ADRs 0001–0008 and CI with docs-only gating
  (milestone M0, #1).

### Changed

- Version 0.1.0, the first release (#84).
- Changelog release heading for 0.1.0 (#85).
- Desktop app polish from the design review's findings: a compact Panels board header, one
  "not available yet" line under each page's subtitle, a pulsing Build busy
  bar, a neutral "Partial" badge and smaller fixes across the screens
  (milestone M10e, #81).
- `docs/ui/` records the departures the built app made from the design (#82).
- Changelog, README status for M10c and test READMEs for #75–#79 (#80).
- The app's Build runs the shared build sequence; `BuildOutcome.sheets`
  carries the workbook's sheet names (#79).
- One build sequence, `bomgen.build.build_substation`, for `bomgen build` and
  the app; the caller lays out first (#76, #77).
- Changelog, README and test READMEs for #71–#74 (#75).
- The app's Checks, Build and Preview run the same automatic layout as
  `bomgen build`, so generated panels give the same workbook; layout errors
  block Build and Preview and warnings show in Checks (#73).
- Plan: M7 is done and `--sheet-name` is dropped, since the inputs name the
  sheets; M10d lists every Build refusal (#74).
- Changelog, README and test READMEs for #19 and #49–#70 (#72).
- The frozen CLI writes UTF-8 to the console; the release smoke tests read the
  workbook path from the first line of `bomgen build` and check its report
  (#70).
- The CLI prints the check report correctly on a Windows console (#68).
- Workbooks are replaced atomically, so a failed replace never deletes the
  workbook already at that path (#69).
- Q34 resolved by Ali; ADR 0014 accepted (#66, #67).
- The import clash banner leads the review dialog (#64).
- The release workflow's installed-build step parses on PowerShell (#57).
- The release workflow builds the example workbook with the frozen and the
  installed CLI (#55).
- Desktop app: `show_in_folder` opens only files the app listed; the
  recent-projects list lives in its own app home (`BOMGEN_APP_HOME`); the
  import review reads `can_import` (#54).
- Library and project store messages state the situation; the command to run
  moves to `LibraryPackageError.hint` (#50).
- Changelog, README and test READMEs for #42–#48 (#56).
- The release workflow validates the example project with the frozen and the
  installed CLI (#47).
- `data/device-db/README.md` explains how to ship the records in a `.bomlib`
  (#42).
- Changelog, README and test READMEs for #36–#41 (#43).
- `data/device-db/README.md` states the field rules readers can rely on, with
  tests for them (#40).
- The installed app opens the desktop window and a double-clicked
  `.bomproj`; the frozen bundle carries the UI files (M10a and M11, #38).
- `*.bomproj` packages and `Backups/` folders are git-ignored; Q34 taken
  (#39).
- Changelog, README and test READMEs for #17 and #24–#35 (#37).
- The `l1_switch` role takes an optional part: the tool ranks the library's
  L1 switches and picks one unless the engineer pins it; layout checks report
  every problem with its location; FOPP-96SM is 1U, NAP-F23 and KEYTEK-KBM 0U
  (#33).
- ADR 0013 records Q32 (cable managers count against the 32U as a block under
  each switch, firewall or patch panel), Q33 (FOPP-96SM is 1U) and the L1
  switch selection rule (#25, #29); the device database and the UI design
  follow (#30, #32).
- Q32 and Q33 resolved (#26, #35).
- Changelog, README and test READMEs for #14–#23, and the plan glossary (#17).
- M9 prototype reworked for projects and substations: project page with the
  document register and backup and share, a Network screen and a Panels board
  per substation (#23).
- The launcher's self-test fixture names a module that will never exist
  (#24).
- The installed app imports a double-clicked `.bomlib` through the library
  store and shows the change summary or the refusal; `.bomproj` files get a
  placeholder association; `BOMGEN_NO_DIALOGS=1` prints messages to stderr
  for unattended runs (M11, #15).
- Plan Q29 resolved: the example keeps the workbook's thermostat load and fan
  airflow; future library defaults use 0 W for the SK 3110 thermostat and
  460 m³/h for the SK 3243.100 fan with its outlet filter (#12).

[Unreleased]: https://github.com/alialyami90/BOM-generator/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/alialyami90/BOM-generator/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/alialyami90/BOM-generator/compare/v0.3.4...v0.4.0
[0.3.4]: https://github.com/alialyami90/BOM-generator/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/alialyami90/BOM-generator/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/alialyami90/BOM-generator/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/alialyami90/BOM-generator/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/alialyami90/BOM-generator/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/alialyami90/BOM-generator/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/alialyami90/BOM-generator/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/alialyami90/BOM-generator/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/alialyami90/BOM-generator/releases/tag/v0.1.0
