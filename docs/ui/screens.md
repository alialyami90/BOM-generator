# Screens, flows and states

Layouts and behaviour for every screen in the desktop app, in the prototype's
route form (`prototype/index.html#/…`). Components are in
[`components.md`](components.md); the approved scope is in [`brief.md`](brief.md).
**v0.2:** every value is editable; how values are saved, validated, created and deleted is in
[`editing.md`](editing.md), which also lists every field. Where this file and `editing.md` differ on
editing behaviour, `editing.md` is newer.

## Map

```
Home (all projects) ─ Project ─┬─ Overview · Substations · Documents · Backup and share
                               └─ Substation ─ Settings · Network · Panels (board, list, panel editor)
Library (import, versions)         └─ Checks ─ Preview ─ Build        (each per substation)
```

A **project** holds the document register, the project information, shared
defaults and the substations. A **substation** has one system: its network,
panels, checks and workbook. The first substation can be copied to start the next.

| Route | Screen | Purpose |
| --- | --- | --- |
| `#/home` | Home | All projects on this PC; first-run guidance when no library is installed |
| `#/project/<tab>` | Project | `info`, `substations`, `documents`, `share` |
| `#/settings/<tab>` | Substation settings | Substation-only settings (general, documents used, output, constants, loose material, YAML) |
| `#/network` | Network | IED count, topology, equipment, spares, the engine's sizing result |
| `#/panels` | Panels | The Board and List views of the generated panels |
| `#/panels/<id>/<tab>` | Panel editor | One cabinet; generated panels are read-only, hand-written ones are editable |
| `#/library`, `#/library/import` | Library, Import and versions | Browse the installed devices; review and install a `.bomlib` |
| `#/checks`, `#/preview/<sheet>`, `#/build` | Verify and issue | For the open substation |

The rail has three groups. Top: Home and Library, always reachable. **Project**:
one item that opens the project page, with its status. **Substation**: a
switcher (a select that lists the project's substations) over Settings, Network
and Panels, then **Verify and issue** (Checks, Preview, Build). The substation
items are disabled until a substation is open.

## Primary flows

**1. First run.** Home shows four numbered steps. "Install a library…" opens
Library → Import update. After a successful import, New project and Import
project file become available.

**2. New project, first substation, next substations.** Home → New project
(name, client, folder, first substation). The project page opens on Substations.
"Create from this…" on a substation row opens New substation: choose to start
blank or from a copy, then id, name, first cabinet number and tag prefix. A copy
keeps equipment, network, spares, constants and loose material; it does not copy
manual layout changes, build output or document numbers.

**3. Open, fix, build.** Open a project → open a substation (Panels) → Checks
shows the problem list → "Go to field" opens the screen that owns the field →
fix → "Run checks again" → Preview → Build. Build is disabled while errors exist
and says why. The project's document register is edited once, on the project
page, and every substation's headers read from it.

**4. Adjust the panels.** Network sets the IED count, topology, equipment and
spares; the layout engine places the devices in panels. The Panels board shows
the result, and the engineer moves, deletes or resets (see Panels below). Each
change is saved as an override and the layout runs again.

**5. Back up and share.** Project → Backup and share. "Export project…" writes one
`.bomproj` file (a zip of the project folder without `out/` and `Backups/`, with a
manifest and checksums). "Back up now" saves the same kind of file into the
project's `Backups` folder. "Import project file…" and "Restore…" open the same
review dialog: contents, library version, integrity and path checks, and, when
the project already exists, a choice between keeping both and replacing (a
backup is made first). Double-clicking a `.bomproj` file starts the app with the
review dialog open and a banner on Home.

**6. Update the device library.** Library → Import update… → choose the package →
review verification and changes → "Import and activate x.y.z". The previous version
stays installed. Projects built with the previous version show a warning in
Checks until rebuilt.

**7. Edit as YAML.** Records with a YAML tab (substation settings, hand-written
panels, generated panels read-only) offer the file's source. Errors show on the
line. "Apply to form" is available only when the YAML is valid.

## Screens

### Home
- **Layout:** title and three actions (New project primary, Open folder and
  Import project file secondary); a table of projects (name and path, client,
  substations, library used, last opened, status); an info banner about library
  updates. A `.bomproj` launch adds a banner above the table.
- **New project:** a dialog with name, client, device library (default: the active one) and an
  optional first substation; the folder is shown, not asked for. Creating opens the new
  substation's Network page.
- **Behaviour:** a row opens the project page on Substations. Status uses the
  same words as Checks (`Ready`, `2 errors`, `Library out of date`).
- **States:** first run (steps list, "Install a library…" primary, the project
  actions disabled with an explanation); no projects yet; opened from a file.

### Project
- **Layout:** breadcrumb (Projects), title, client and folder, tab list, one
  form or table per tab.
- **Overview:** name, client, logo, the device library the project was built with
  against the active one (with "Record 1.4.0 in this project"), and **Shared
  defaults** (power margin, spare ports, rack space kept free, spare DC and AC
  branches). A substation starts from these; the values it changes are marked
  in its own screens.
- **Substations:** a table (name and folder, panels, last changed, status) with
  Open and a row menu (Rename…, Create from this…, Delete…), and a primary "New substation…". Substations created
  from another say so under their name.
- **Documents:** the **register**, one per project, grouped by substation with a
  band row and an "Add" button for each. Columns: document, document number,
  revision, issue date, used by, state (assumed dates are flagged, with a Confirm button),
  and a remove button that is disabled while the document is used. All cells are editable.
- **Backup and share:** Export and Import actions, and a Backups table (file,
  saved, size, library, Restore…, Show in folder) with "Back up now".
- **Delete project:** a danger section at the foot of Overview; the project name must be typed.
- **States:** unsaved; invalid field; library older than active.

### Substation settings
Only what belongs to this substation: *General* (name, title line, and a
read-only "From the project" block with a link to the project page), *Documents*
(which register entry each calculation sheet prints; cabinet BOMs choose theirs on
each panel), *Output* (main document, file-name pattern with the resulting name,
calculation sheet names), *Design constants* (the ten spec constants with unit,
default, a "Changed from …" mark and a Reset per row, and "Reset all to defaults"; defaults
come from the project), *Loose
material* and *YAML* (`substation.yaml`). Project-wide values are not repeated
here.

### Network
- **Layout:** two columns. Left: **Field network** (IED count, Star or Ring, ring
  size when Ring), **Equipment** (device, role, A+B, L2 ports, height), and
  **Spares** (ports kept free, spare SFPs per L1, rack space kept free, spare DC
  and AC branches). Right: a read-only **Result** card from the engine
  (`NetworkPlan`): L1 and L2 switches, L2 ports used of usable, links, and the
  note for the chosen topology.
- **L1 switch model:** under Field network, a ranked table of the engine's
  `rank_l1_switches` result (rank, model, ports, switches per side, **usable
  ports**). The row in use is marked "Tool's pick" or, when `substation.yaml` pins
  a model, "Pinned" (the Result card says "(pinned)"); a top row that is not in
  use shows "Tool's pick" in muted text. The UI never ranks; it shows the
  engine's order. No ranking is shown until the IED count is set. In the built
  app the pin is made in `substation.yaml` (see *Departures in the built app*).
- **Behaviour:** the Result card shows a busy state and updates after each
  change. Equipment rows are checked against the library; an unknown part id
  shows an inline error with a suggestion. In a star, each L1 has one uplink to
  its L2 plus an A–B interlink. The equipment table sits here because the panels
  are generated from it (approved by A1).
- **New substation:** the **setup card** (see `components.md`) sits above Field network and lists
  the steps left: IEDs, equipment, panels. The IED count is marked required until entered.
- **Equipment rows:** part (with "Change part…"), role, A and B, quantity (L1 rows read "Sized"),
  L2 ports and remove, all editable; the Result card recalculates after each change.
- **States:** substation with no network yet (setup card, IED count marked
  required, empty equipment, empty result); IED count assumed; unknown device.

### Panels
- **Header actions:** Undo, Reset to automatic, Add hand-written panel….
- **Board tab:** one column per generated panel, grouped in pairs
  (**Pair 1: panels 1 and 2**). Column header: panel name, side badge, a U meter
  and "21 of 32 U used · 11 U free". The rack shows each device as a block whose
  height follows its size in U, a gap for each blank plate (plates are not BOM
  rows), the free space, and the space kept free for expansion. A switch,
  firewall or patch panel is one block with its 1 U cable manager (Q32 default:
  cable managers count against the 32 U), so its height reads "1 U + 1 U cable
  manager" and the meter counts both. DIN-rail parts
  are counted under the column and take no rack space. Common devices (GPS,
  RTAC, I/O) sit in the same panels as the A and B units; there is no common
  column.
- **Select, move, pin, delete:** selecting a device shows its tag and an action bar:
  "Move pair…", "Move this unit only…", **Pin here** or **Unpin**, "Delete pair". A device that has no
  partner shows "Move…" and "Delete". The partner of the selection is outlined.
  Dragging does the same as "Move pair…" and also sets the position; Alt+drag moves only the unit. A pair
  moves to panels (2n−1, 2n); a single A unit moves only to odd panels and a
  single B unit only to even ones. Pinned devices carry a pin icon, and
  "N pinned · M deleted" opens the list with Unpin and Restore. Full rules, the drag states and the
  keyboard are in [`editing.md`](editing.md) ("Panels board").
- **Not allowed:** while dragging, a column that cannot take the move shows a
  red border; on drop, a banner says why ("Panel 1 needs 34 U, only 32 U may be
  used. Nothing was changed."). A move never silently re-flows other devices.
  The move dialog lists every destination with the resulting U, and greys out
  the ones that do not fit with the reason.
- **Undo and reset:** every move or deletion is one undo step (toast Undo and
  Ctrl+Z). "Reset to automatic" asks for confirmation, states how many moves and
  deletions are removed, and can be undone.
- **Keyboard:** Tab to a device, Enter selects, then Tab to the action bar;
  "Move…" opens the destination list. Delete removes the focused device.
- **List tab:** the panels as a table (sheet, cabinet, name, written by, side,
  rack space, status), including the hand-written ones.
- **Boundary:** the board only writes `layout.overrides` and `removed` and shows
  the result of `layout_preview`; the placement rules live in the engine.
  Overrides refer to equipment ids and pairs, not tags.
- **States:** no panels yet (link to Network); errors in a panel; manual changes
  present.

### Panel editor
- **Header:** breadcrumb, cabinet name, cabinet number · kind · side, "Preview
  BOM" and Save.
- **Generated panel:** a banner says the layout writes the devices. Devices (with an Origin
  column that marks pinned devices) is read-only; Enclosure, Port plans, Options and Document are
  editable, with their scope stated (shared by all generated panels, or this panel only).
  The YAML tab is labelled Generated and read-only. The banner links to Network and the board.
- **Hand-written panel** (`manual_panels`, for example the WS console): the full
  editor, as in the first design. Devices: reorder handle, device, quantity,
  purpose, HWIO override, generated tag, remove; "Add device" opens the picker.
- **Tabs:** Enclosure (make,
  model, code, H × D × W, base frame, cable entry), Port plans (a small table per
  switch with an "Engine result" footer), Options (spares, ventilation, diodes,
  main MCB override, socket, terminals, smoke detector, busbars, terminal
  overrides, each override with a warning line), Document, `panels/<id>.yaml`.

### Library
- **Layout:** title with the library name, version and install date; header actions *Add device…* (primary),
  *Export…* and *Import…* (a menu: update package or CSV). Two tabs, *Devices* and *Catalogues*. A
  **pending bar** at the foot while there are unapplied edits (see [`editing.md`](editing.md), "Library
  editing").
- **Devices tab:** a toolbar (search, category, data quality, "Has alternatives", count); a table (part id,
  make and model, supply and rated power, data-quality badge) beside a 400 px detail pane.
- **Detail pane:** tabs *Overview*, *Datasheet*, *Alternatives* (the compact comparison list with *Use…* and
  *Compare in full*), and *Edit device* in the pane header.
- **Catalogues tab:** a segmented switch (MCBs, Aux contacts, Terminal blocks, Busbars, Housekeeping); brand
  tabs with a *Default* badge, *Make default*, *Add brand…*; an editable table with *Add row* and per-row
  remove. Housekeeping is a role table with *Change…*.
- **Behaviour:** selecting a row fills the pane; the arrow keys move the selection when the table has focus.
  Every edit becomes a pending entry. Nothing is written to the installed version.
- **States:** no library installed (banner with an "Import…" action); no match (empty row); no datasheet or
  alternatives recorded (sentence in the pane); pending set empty (no bar).

### Device editor
- **Route:** `#/library/device/<part id>`, or the same page for a new device. Breadcrumb Library › part id.
- **Layout:** title (part id), make and model, header actions *Copy as alternative…* and *Delete…*; an
  "in use" banner; tabs *Identity*, *Electrical*, *Ports and mounting*, *Parts it brings*, *Datasheet*,
  *Alternatives*. Field list in `editing.md`. It is a form: save bar "Save device", Ctrl+S, leave dialog.
- **Alternatives tab:** the alternative group key and the full comparison list (tier, part, make, power,
  inrush, ports, height, data quality, *Use…*) with delta chips; *Add alternative…*; empty state when none.
- **States:** new device (part id editable, "new device" subtitle), device in use, device not found,
  duplicate part id on creation (toast and the field marked).

### Review library changes
- **Route:** `#/library/review`. Counts (added, changed, removed), the diff list grouped by kind, the new
  version it creates and the one it replaces, a note, and *Apply and activate 1.4.0+local.1*. Empty state
  when nothing is pending. After applying: toast, the top bar and sidebar show the new version, and
  Installed versions lists it as a local version.

### Import a spreadsheet (CSV)
- **Route:** `#/library/csv`; steps choose, review, done as in `editing.md`. The review shows file facts,
  checks, rows with a problem (table, row, column, message), what changes, and a sticky action bar
  "Add N valid rows to pending changes" and "Choose a different file".

### Import update and installed versions
- **Tabs:** *Import package* and *Installed versions*.
- **Import flow:** (1) choose: drop zone and "Choose package…"; (2) review: the
  package facts (file, size, library, version against active, schema, needs app,
  built), release notes, a verification checklist (checksums, schema version,
  app version, signature status), and "What changes" (badges for added,
  changed, removed, catalogues, device-database files, then the diff list); a
  sticky action bar with "Import and activate x.y.z" and "Choose a different
  package"; (3) installing: progress bar; (4) done: success banner, "previous
  version kept", and an info banner about projects built with the old version.
- **Refusals** (each shows a red banner naming the problem and what to do, and
  the primary action is disabled): older than installed (can be forced with an
  explicit "Install anyway (downgrade)" checkbox); checksum mismatch (nothing
  installed, no override); needs a newer app or schema (no override); same
  version (offers "Reinstall anyway").
- **Installed versions:** table (version, released, notes, projects built with
  it, state) with "Make active" on non-active versions, which opens a confirm
  dialog. Making a version active never edits project files.

### Checks
Per substation. Problems in the project files (register, defaults) appear here
too and their "Go to field" opens the project page.
- **Layout:** a status banner (red with the count, or green with "Go to
  Build"); a Problems section with level filter chips and a table (level,
  `file:line` and field path, what is wrong and what to do, "Go to field");
  an Engine checks section (SFPs match the port plans, main MCB covers the feed
  current, airflow covers the heat load, digital inputs cover the hardwired
  points) with Pass / Flag / Not run.
- **Behaviour:** "Run checks again" shows a busy button then a toast. Engine
  checks are "Not run" while errors exist and say why.

### Preview
- **Layout:** title, a banner when the last load had errors, sheet tabs (one
  Sheet per panel, then Power Consumption, Heat Dissipation, Heat Calculations),
  then the sheet.
- **BOM sheet:** group chips A to H with counts, a row filter, a switch for the
  hidden HWIO column (the revised-cells switch was dropped, see *Departures in
  the built app*); the sheet title block (cabinet number,
  substation and cabinet name); the table with a preview-only Grp column, SR.NO,
  designation, description, quantity, make, model, ordering code. Parent tags
  span their child rows and the empty separator rows between groups E to H are
  shown, as in the workbook. A footer gives the row count and the panel HWIO
  total.
- **Calculation sheets:** Power: headline metrics and block tables with totals
  including the 25% margin. Heat Dissipation: per-device W and BTU/h. Heat
  Calculations: forced-ventilation table with line-up check, natural-convection
  metrics and the resulting recommendation.
- **Behaviour:** read-only. Filters change the view only.

### Build
- **Layout:** two columns. Left: file name (from the pattern), save folder,
  options (highlight changes since the previous issue with a file picker, open
  when written), the Build button and the result area. Right: what the
  workbook contains, library, project revision and warning count.
- **States:** blocked (errors: red banner, disabled button with a reason);
  ready; building (button busy, four named steps with a progress bar);
  success (path, size, sheet count, Open workbook primary, Show in folder, and
  a short check report); failed because the file is open in Excel (red banner,
  "Try again", "Save as new name"). An existing file with the same name asks
  for confirmation in a dialog before it is replaced.

## Departures in the built app

The app (M10) follows this design except where listed here. Each departure was
reviewed by the design owner and is the intended behaviour; the prototype in
`prototype/` is not changed to match.

- **Projects, substations and settings are read-only.** Creating and editing
  projects, substations and settings is not in the first release: the pages show
  the values in disabled fields, "New project…", "New substation…" and similar
  actions are disabled, and one line under the page subtitle says "Creating and
  editing … in the app is not available yet. Edit the YAML files, then open the
  project again." It is a single component (`note` in `pageHead`): one line, an
  info icon, ellipsis and a tooltip on overflow. Empty read-only fields read
  "Not set".
- **Network pin.** "Use this one" and "Unpin" are not offered; the pin is written
  in `substation.yaml`. The ranking table's last column is "Use".
- **Panels board.** The banner for hand-written panels is one line ("Hand-written
  panels. The board shows what `bomgen layout` would write; Build uses your panel
  files.") with a "Show N problem(s)" button; the expanded list starts with
  "Running it would report N problems:". The line under it is one sentence
  ("Select a device to see its part and size.") with a ? help icon whose tooltip
  explains blank plates and the cable manager. Both columns of a pair have the
  same width.
- **Import project.** When the project already exists the dialog offers
  "Replace my project" and "Keep both"; Keep both imports it under the suggested
  id. The decision banner sits at the top and says that Replace backs up the
  existing project first. Restoring a backup uses the same dialog with a
  "Restore" action.
- **Preview.** Sheet tabs use short labels (Sheet 1 to Sheet 4, Power, Heat
  dissipation, Heat calculations) so they fit one row; the cabinet name is the
  tooltip and the title block. The "Show revised cells" switch is removed. An
  ordering code equal to the model reads "Same as model" (muted).
- **Build.** The running state is an indeterminate bar (a pulsing full-width
  fill, no sliding stripe) with "This takes a few seconds." instead of four
  named steps. The file-name hint says only "From the pattern in Settings →
  Output."
- **Library.** "Partial" data quality uses the plain badge with an info icon;
  amber is kept for a problem.
- **Home.** With no projects the table is replaced by "No projects yet" with the
  workspace folder, and the library-update banner stays.

## Cross-cutting behaviour

- **Unsaved changes:** form pages show a save bar and the status bar says "Unsaved changes";
  leaving the page, switching project or substation, or closing the app opens a dialog with
  Keep editing, Discard changes and Save and leave. Details in [`editing.md`](editing.md).
- **Validation:** runs on save and on "Run checks again"; the counts in the
  navigation and status bar update after each run.
- **Library version:** opening a project whose recorded library differs from
  the active one adds a warning to Checks, never blocks.
- **Keyboard:** Ctrl+S saves, Ctrl+O opens a project, F6 moves between the
  navigation, content and status bar, Esc closes dialogs and popovers. Every
  action is reachable without a mouse.
- **Scaling:** designed at 100%, 125% and 150% Windows scaling; minimum window
  1280 × 720.

## What the app needs from the engine

The UI is built on a small Python API (milestone M10). From the design, it needs:

| Need | Used by |
| --- | --- |
| List the projects on this PC, with each one's substations, status and recorded library version | Home, Project |
| Open a project: parsed models, or located errors (`file:line`, field path, message) | Project, Substation, Checks |
| `layout_preview(substation, overrides) -> LayoutResult`: panels with devices, U used, blank plates, DIN-rail counts, and errors for a move that does not fit | Panels board, panel editor |
| `NetworkPlan` for a substation (read-only): L1 and L2 switches per side, ports used and usable, links | Network |
| `rank_l1_switches`: the library's L1 models best first (model, ports, switches per side, spare ports), the tool's pick, and a way to pin another model in `substation.yaml` | Network |
| Stable equipment ids, so overrides name a device or a pair and never a tag | Panels board |
| Project export (`.bomproj`), and `project_store.preview_project_import(package, workspace=None) -> ProjectImportPreview(checks, manifest, files, project_id, target_dir, exists, library_note, can_import)`: each `Check(id, label, status ok/warning/failed/skipped, detail, kind)`; a failed check skips the rest; a name clash is a warning | Project, Home |
| Backups: `list_backups(project_file) -> [BackupInfo(path, saved, size, project_id, library_name, library_version, file_count, problem)]` newest first, write a backup, `restore_backup(backup)` after the same dry-run | Backup and share |
| Whether the app was started from a `.bomproj` file | Home |
| The JSON Schemas for project and panels, plus a label and help override file | Forms |
| Validate and run engine checks: problem list and the four check results | Checks, status bar |
| Generated values per panel: tags, HWIO, engine port-plan results | Panel editor |
| Create a substation from another (copy rules above) and write `substation.yaml` | New substation |
| The installed library: devices with datasheet, alternatives, sources and data-quality level | Library, device picker |
| Library packages: `library_store.preview_library_import(package, force=False) -> LibraryImportPreview(checks, manifest, files, previous, diff, can_import)` (check ids: package, paths, size, manifest, files, checksums, library, validation, version, signature; signature is always skipped, there is no signing), import, list versions, roll back | Import and versions |
| Sheet models or computed rows for each workbook sheet | Preview |
| Build: stage events (load, engine, sheets, write) and the result path, or a typed error such as "file is open" | Build |

If any of these is missing, or shaped differently, the owning agent decides
whether the engine or the design changes. The UI does not work around it by
calculating rules itself.

### Open items found against the other work (to resolve, not resolved here)

Recorded from A1's review of this PR, checked against the code on `main` and the
open PRs at the time.

| Area | Mismatch | Design assumption to revisit |
| --- | --- | --- |
| Library packages (A5) | Resolved on the engine side: previews return a list of checks with a status each (see the engine list above). | The Import screen's verification checklist maps one row to each check; `skipped` renders as a muted row, and the signature row always reads "Not signed (not used)". |
| Library packages (A5) | "Projects built with it" has no data source until M1b records the library per project. `InstalledLibrary.problem` had no UI state. | The Versions table shows a project count. A library with a problem shows a red "Problem" badge in the state column, the problem text under it, and "Make active" disabled. |
| Device records (A3) | Data-quality level is `confirmed`, not `verified`. A tier's `verified` is a boolean. Alternatives are `make` plus `tiers{low,mid,high}` with `ordering_code`, `url`, `notes`. Datasheet `ratings`, `ordering_code_decoded` and `product_url` exist. `make` may be absent. | The prototype uses `confirmed`/`partial`/`unverified` per tier row and shows no URL, notes or ratings. Decide whether to show them. |
| Device records and library | Nobody owns the loader that joins device-database records to the library `part_id`s inside a `.bomlib`. | M10 dependency. The Library and the picker need it. |
| Project model (A2) | `Project.library` is a path with no recorded name or version yet. | The "Built with" line and the Older-than-active badge need a recorded name and version. |
| Panel model (A2) | Enclosure `base_frame` is `{h,d,w}`. `DeviceInstance.tag` and `lan` overrides, and `PortPlan.serial_ports`, are not in the Devices table. Constants are named `air_constant_m3k_per_wh` and `steel_coefficient_w_per_m2c`. | The prototype's field names are illustrative. The forms are generated from the JSON Schema, so labels come from the schema. |
| Labels and help | The shape of the label and help override file needs a short section in the A2 schema ADR. | Forms need labels and help text beyond what the schema carries. |


## Decisions from the critique pass

- Preview: groups are chosen from one named select (for example "B Network
  devices"), not eight lettered chips. Group letters are preview-only.
- Preview: while errors exist the primary action is on the warning banner
  (Open checks) and the header offers a secondary "Build (blocked)".
- Checks: while errors exist the engine checks collapse to one sentence; the
  table appears once they have run. The Where column leads with the panel and
  tab, with `file:line` and the field path underneath.
- Navigation rail: Project and Substation are separate groups, so it is always clear whether an item acts on the project or the substation.
- Navigation rail: Build shows an icon with "Blocked" or "Ready" so state is never
  colour only.
- Devices table: the drag handle is full-contrast. Keyboard reorder is
  Alt+Up/Alt+Down on the focused row. Removing a row marks the project unsaved
  and offers Undo (Ctrl+Z) until the next save. The prototype only hides the row.
- Generated panels (including B panels that mirror their A panel): Enclosure,
  Devices, Port plans and Options are read-only; only hand-written panels
  (`manual_panels`) keep the full editor. This replaces the Mirror dialog of the
  first design.
- Preview, Power and Heat show figures the engine supplies. The prototype holds
  them as literal values in `data.js`; no rule is computed in the UI.
- Still open for Ali: a read-only reviewer mode (hides Save, Add device and
  Remove for non-engineers). Not designed yet; it is a likely M10 follow-up.
