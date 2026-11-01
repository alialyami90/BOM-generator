# Changelog

All notable changes to this project are listed here, one entry per merged pull
request; a milestone split across several PRs gets one entry. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/alialyami90/BOM-generator/compare/v0.3.3...HEAD
[0.3.3]: https://github.com/alialyami90/BOM-generator/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/alialyami90/BOM-generator/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/alialyami90/BOM-generator/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/alialyami90/BOM-generator/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/alialyami90/BOM-generator/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/alialyami90/BOM-generator/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/alialyami90/BOM-generator/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/alialyami90/BOM-generator/releases/tag/v0.1.0
