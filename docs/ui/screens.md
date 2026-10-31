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
                               └─ Substation ─ Settings · Parts · Device preview · Panels (board, list, panel editor) · Loose material
Library (import, versions)         └─ Checks ─ Preview ─ Build        (each per substation)
```

A **project** holds the document register, the project information, shared
defaults and the substations. A **substation** has one system: its network,
panels, checks and workbook. The first substation can be copied to start the next.

| Route | Screen | Purpose |
| --- | --- | --- |
| `#/home` | Home | All projects on this PC; first-run guidance when no library is installed |
| `#/project/<tab>` | Project | `info`, `substations`, `documents`, `share` |
| `#/settings/<tab>` | Substation settings | Substation-only settings (general, documents used, output, constants, YAML) |
| `#/parts` | Parts | IED count and topology, network fine tuning, one row per device type with its library part, part number and overrides, the catalogue brands (M22; `#/network` redirects here) |
| `#/device-preview` | Device preview | Each device with its panel, rack position and MCBs, and a front view of each panel, before the workbook is built (M22) |
| `#/panels` | Panels | The Board and List views of the generated panels |
| `#/panels/<id>/<tab>` | Panel editor | One cabinet; generated panels have editable enclosure, port plans, options and document, hand-written ones are fully editable |
| `#/loose` | Loose material | The substation's own list of items not mounted in a cabinet, printed on its own sheet |
| `#/library`, `#/library/import` | Library, Import and versions | Browse the installed devices; review and install a `.bomlib` |
| `#/checks`, `#/preview/<sheet>`, `#/build` | Verify and issue | For the open substation |

The rail has three groups. Top: Home and Library, always reachable. **Project**:
one item that opens the project page, with its status. **Substation**: a
switcher (a select that lists the project's substations) over Settings, Parts, Device preview,
Panels and Loose material, then **Verify and issue** (Checks, Preview, Build). The substation
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

**4. Pick the parts, check the placement, adjust the panels.** Parts sets the IED count, topology, one
library part per device type with this design's part number and overrides, and the network fine tuning;
the layout engine places the devices in panels. **Generate preview** opens Device preview: each device's
panel, rack position and MCBs, and a front view of each panel. The Panels board shows
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
  substation's Parts page.
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
Only what belongs to this substation: *General* (name, which is also the BOM title line, and a
read-only "From the project" block with a link to the project page), *Documents*
(which register entry each calculation sheet prints; cabinet BOMs choose theirs on
each panel), *Output* (main document, file-name pattern with the resulting name,
sheet names, including Loose Material), *Design constants* (the ten spec constants with unit,
default, a "Changed from …" mark and a Reset per row, and "Reset all to defaults"; defaults
come from the project) and *YAML* (`substation.yaml`). *General* also holds **Catalogue brands**: the
substation uses the project's choice unless it sets its own. Loose material has its own page. Project-wide values are not repeated
here.

### Loose material
- **Layout:** title and lede; header actions *Add free text…* and *Add from library…* (primary). The
  table (No., Part or description, Designation, Qty, Fed from, remove) across the page, with a foot that counts
  the items and says what a quantity may be. Below it, two cards side by side: *On the workbook* (sheet name,
  position, "written only while there are items", link to Preview) and *Issued under* (the document the sheet
  header takes).
- **Behaviour:** a form; every cell is editable in place; add and remove are held until saved (Undo toast on
  remove, Discard restores). A free-text item shows a *Free text* badge and "—" for Fed from (ADR 0022). Details, field rules and back-end
  needs are in [`editing.md`](editing.md), "Loose material (v0.2)".
- **States:** empty (explains that no sheet is written, offers both add actions); a library part that is not
  in the active library is shown as "Library part" without make and model; invalid quantity marks the cell ("Enter a whole number, or 1 Lot.").

### Parts (M22, replaces Network)

Part picking design (`docs/superpowers/specs/2026-10-31-part-picking-design.md` §3). One page answers
"what is in this substation, and which part is each thing": the network inputs at the top, then one
row per device type in the order the layout fills panels, then the catalogue brands. It is a form page
with the save bar; everything on it is saved together.

- **Layout:** the two columns of the old Network page. Left, top to bottom:
  1. **Field network:** Field IEDs (required on a new substation) and Topology (Star or Ring), as before.
  2. **Network fine tuning**, a disclosure under them, closed once the substation is set up. Closed, it
     is one muted summary line ("Star · 1 uplink per L1 · A–B interlink · 20% ports kept free · 4 U kept
     free"); open, it holds switches per ring (Ring only), L1 uplinks per switch, A–B interlink, L3
     uplinks per L2 and the spares (ports kept free, DC branches per feed, AC branches, rack U kept free).
     A changed value is marked and the disclosure's summary names how many differ from the project's
     defaults.
  3. **Devices:** the part rows (`components.md` "Part row"), in this default order: Time server clock,
     L2 switch, L1 switch, Operator workstation, Engineering workstation, DA server, KVM, Console,
     Annunciator, then any rows added with **Add a device**. The order is the order the layout fills
     panels in; **Move up** and **Move down** in each row's menu change it.
  4. **Catalogue brands:** MCB make and series (AC and DC, one select each, as in Settings) and Terminal
     blocks. No part number, no overrides.

  Right: the **Result** card as before (L1 and L2 switches per side, ports used, links), plus
  **Generate preview** (primary). The L1 ranking table is gone: the L1 switch is picked in its row.
- **Behaviour:** picking a part fills the row's details strip from the library. A value clicked in the
  strip becomes an input; a value that differs from the library is an **override**, marked, with a reset.
  The Result card recalculates after each change, as before. Rows with no part number get a warning on
  Checks ("printed with the library model").
- **Sized switches:** the L1 and L2 rows show "Sized" for quantity. With no part picked, the sizing picks
  one and the row says so ("The sizing picks the switch"); the strip then reads "Pick the switch to
  change its data." and offers no overrides.
- **Generate preview** opens Device preview. With unsaved changes it is disabled, and its hint says
  "Save your changes first".
- **States:** new substation (setup card; IED count required; only the rows of the default order, each
  with no part); set up and clean; overrides present; an override that is invalid (inline error and the
  save bar's sentence); a row whose part is not in the active library (the id in error, "Pick another
  part", an empty strip); 20 or more rows (strips collapse to a one-line summary per row; the save bar
  never covers the last row).

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
- **States:** no panels yet (link to Parts); errors in a panel; manual changes
  present.

### Panel editor
- **Header:** breadcrumb, cabinet name, cabinet number · kind · side, "Preview
  BOM" and Save.
- **Generated panel:** a banner says the layout writes the devices. Devices (with an Origin
  column that marks pinned devices) is read-only; Enclosure, Port plans, Options and Document are
  editable, with their scope stated (shared by all generated panels, or this panel only).
  The YAML tab is labelled Generated and read-only. The banner links to Parts and the board.
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
  Sheet per panel, then **Loose Material (n)** when the substation has loose material, then **Nameplates (n)** when some panel has plates, then Power Consumption, Heat Dissipation, Heat Calculations),
  then the sheet.
- **BOM sheet:** group chips A to H with counts, a row filter, a switch for the
  hidden HWIO column (the revised-cells switch was dropped, see *Departures in
  the built app*); the sheet title block (cabinet number,
  substation and cabinet name); the table with a preview-only Grp column, SR.NO,
  designation, description, quantity, make, model, ordering code. Parent tags
  span their child rows and the empty separator rows between groups E to H are
  shown, as in the workbook. A footer gives the row count and the panel HWIO
  total.
- **Loose Material sheet:** the panel BOM layout without group chips: the grey title block, then SR.NO, tag,
  description, quantity, make, model and ordering code; an item's children follow it. A line says which
  document the header comes from, with *Edit the list*.
- **Nameplates sheet (ADR 0026):** S.No, panel (cabinet number), plate text in mono and device, one row per
  plate in each panel's row order, with the plate count under the table.
- **Calculation sheets:** Power: headline metrics and block tables with totals
  including the 25% margin. Heat Dissipation: per-device W and BTU/h. Heat
  Calculations: forced-ventilation table with line-up check, natural-convection
  metrics and the resulting recommendation.
- **Behaviour:** read-only. Filters change the view only.

### Device preview (M22)

Part picking design §6. "Will this build the way I expect?" answered before the workbook is
written. Reached from Parts (**Generate preview**) and the rail. Read-only except for dragging on the
front view. The workbook's sheet preview (above) is unchanged.

- **Layout:** title and lede, the check report's errors and then its warnings for this substation
  (banners above the front views; warnings have **Go to the row**, which opens the Parts row), then a
  **panel strip**: one front view per panel (`components.md` "Rack
  elevation"), side by side and scrolling sideways when they do not fit. Under it, the **device table**,
  one row per unit: device, part, BOM part number, panel, U position, watts, supply, PS1 MCB (tag and
  rating), PS2 MCB (tag and rating), terminal strip. Overridden values carry the override marker.
- **Linked selection:** clicking a unit on a front view selects its table row and scrolls it into view;
  clicking a row selects the unit. Clicking a panel's header filters the table to that panel; the
  filter chips above the table (All panels, then one per panel) do the same.
- **Dragging** on a front view follows the board's contract (`editing.md` "Drag and drop contract"):
  to another panel or another U; Alt moves one unit of a pair; the target is checked live; a drop
  writes a pin. A KVM or console dropped away from waist height is allowed and marked "Pinned away
  from waist height".
- **Flags** (design §7.3): a unit whose MCB is at the 2 A minimum, or whose watts are 0, shows a
  warning marker in its row with the reason in the tooltip and the accessible name. A one-line legend
  above the table says what the warning marker and the override dot mean. A pinned unit's U cell
  reads "Pinned" in words.
- **Keyboard:** the selected unit bar (`components.md` "Rack elevation") moves a unit up or down 1 U
  and unpins it; Arrow Up and Down on the selected unit do the same.
- **States:** clean; warnings; a panel that overflows (an error banner above the front views with the
  check report's sentence and the fix, and the panel's count in red, "35 of 32 U used"; units are
  never drawn outside the rack); a KVM that cannot sit at waist height (the same banner, the KVM drawn
  where it landed); an engine error (no front views or table, one banner naming the row and the
  library version, with **Go to the row**); unsaved changes on Parts (a banner says the preview shows
  the saved parts; the header's **Back to Parts** is the only way back).

### Build
- **Layout:** two columns. Left: file name (from the pattern), save folder,
  options (highlight changes since the previous issue with a file picker, open
  when written), the Build button and the result area. Right: what the
  workbook contains (the Loose Material sheet only when it will be written), library, project revision and warning count.
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

- **Editing (v0.2, M16–M18).** Projects, substations, panels, loose material and the
  library are edited in the app through the save bar in `editing.md`; the v0.1
  read-only note under page titles is gone. Empty read-only fields (such as the
  substation id) still read "Not set".
- **Changed marker, not revision yellow (v0.2.1, #205).** An unsaved edit shows the
  Changed marker (a warning dot before the label or at the start of the cell, with
  a hidden "changed" for screen readers). The revision yellow is used only in
  Preview, for cells revised since the previous issue.
- **Panels board of hand-written panels (v0.2).** When the substation's panels are
  hand-written files the board is read-only: no grips, no pins, no delete, and a
  one-line banner says why ("Hand-written panels. The board shows what `bomgen
  layout` would write; Build uses your panel files."). See `editing.md`, "Panels
  board: drag, drop, pin, delete".
- **Move… dialog (v0.2, #129).** Position is a choice of "Where the layout puts
  it", "At the top" or "At the bottom", not a numbered select; the destination
  panels are listed under it with what each move would do.
- **Network › Equipment (v0.2.1, #199, #207).** Each row keeps its part id on one
  line in mono with Change… after it; when the column is narrow Change… wraps
  under the id. A changed part shows the new id with the Changed marker and
  "Was X". The Role column shows whole names. Parts replaced this screen in M23.
- **Parts (M23).** The app differs from the M22 prototype in these ways:
  - A long part name is cut at the edge of the part select (or the Device picker's
    button), and the full name is its tooltip. The picker lists the row's current part
    first and says how many matches it hides ("Showing 8 of 20").
  - *Add a device* opens a dialog that picks the part. The model takes no equipment
    row without one, so a row cannot be added empty.
  - A category the library has no parts for (KVM, console) shows "The library has no
    KVM parts yet." on its row instead of a select, and is disabled in the *Add a
    device* menu with the same sentence.
  - SFP sub-rows show the media and speed without the engine's count, and the first
    option reads "Automatic: same make first".
  - Time accessories write at once, not through the save bar. *Add accessory* needs
    the loose material's host panel; without one the row points to Loose material.
  - At 20 or more rows a row's strip stays open while one of its values is being edited
    or refused, and an opened row stays open until the page is left.
  - The annunciator's "Mount in panel" switch is not built (Q51).
- **Device preview (M24).** The app differs from the M22 prototype in these ways:
  - The Strip column shows a unit's own terminal strips as the engine gives them, not
    the X1/X2 feed strips the prototype shows, and only when some unit has strips.
  - An AC unit's own AC branch MCB (ADR 0025) shows as its PS1, and its PS2 is "—".
  - With hand-written panels the page shows what the layout would place, with a banner
    pointing to Panels, and nothing can be dragged or pinned: pins reach only
    generated panels.
  - Up 1 U and Down 1 U appear once the bridge has checked that the move fits.
  - "Go to the row" lands on Parts with that row's part select focused.
  - There is no "Parts has unsaved changes" banner: Parts asks to save or discard
    before you leave it, so the preview always shows the saved parts.
- **Settings › General (v0.2.1, #207).** The catalogue brands sit in a two-column
  form; the first option of each select names the resolved brand, "Same as the
  project (Schneider Acti9 2P)", and for the DC MCB set "Same as AC branches".
- **Settings › Documents.** The register select shows the document key only; the
  number, revision and date of the chosen document appear in the row's cells.
- **Settings › Design constants.** The Default column reads a muted "Default" on
  unchanged rows and "Changed from X" on rows that differ from the project.
- **Project › Documents (v0.2, #192).** Register rows are editable in place; an
  assumed issue date gets an "Assumed date" badge with a Confirm action on the
  same line, and Used by lists the panels and sheets without repeating the
  substation prefix inside its group.
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

If any of these is missing, or shaped differently, the engine owner decides
whether the engine or the design changes. The UI does not work around it by
calculating rules itself.

### Open items found against the other work (to resolve, not resolved here)

Recorded from the review of this PR, checked against the code on `main` and the
open PRs at the time.

| Area | Mismatch | Design assumption to revisit |
| --- | --- | --- |
| Library packages | Resolved on the engine side: previews return a list of checks with a status each (see the engine list above). | The Import screen's verification checklist maps one row to each check; `skipped` renders as a muted row, and the signature row always reads "Not signed (not used)". |
| Library packages | "Projects built with it" has no data source until M1b records the library per project. `InstalledLibrary.problem` had no UI state. | The Versions table shows a project count. A library with a problem shows a red "Problem" badge in the state column, the problem text under it, and "Make active" disabled. |
| Device records | Data-quality level is `confirmed`, not `verified`. A tier's `verified` is a boolean. Alternatives are `make` plus `tiers{low,mid,high}` with `ordering_code`, `url`, `notes`. Datasheet `ratings`, `ordering_code_decoded` and `product_url` exist. `make` may be absent. | The prototype uses `confirmed`/`partial`/`unverified` per tier row and shows no URL, notes or ratings. Decide whether to show them. |
| Device records and library | Nobody owns the loader that joins device-database records to the library `part_id`s inside a `.bomlib`. | M10 dependency. The Library and the picker need it. |
| Project model | `Project.library` is a path with no recorded name or version yet. | The "Built with" line and the Older-than-active badge need a recorded name and version. |
| Panel model | Enclosure `base_frame` is `{h,d,w}`. `DeviceInstance.tag` and `lan` overrides, and `PortPlan.serial_ports`, are not in the Devices table. Constants are named `air_constant_m3k_per_wh` and `steel_coefficient_w_per_m2c`. | The prototype's field names are illustrative. The forms are generated from the JSON Schema, so labels come from the schema. |
| Labels and help | The shape of the label and help override file needs a short section in the input schema ADR. | Forms need labels and help text beyond what the schema carries. |


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
- Parts and Device preview (M22): every U number comes from one source. A switch with a cable
  manager reads "1 U + CM" on the front view, matching the 1 U on Parts; an overflowing panel counts
  what could not be drawn ("35 of 32 U used"); the waist error names the U above the line.
- Parts (M22): the rail shows "Not set up" on a new substation and "1 error" when a row is invalid or
  its part is missing from the library, like Checks. The setup card ticks a step only when its field
  is filled. Device preview is disabled in the rail until Parts is set up.
- Device preview (M22): errors sit in a banner above the front views, not under the base frame, so
  they are seen at 800 px tall. Each panel keeps a second meta line while any panel has an error, so
  the frames stay aligned.
- Device preview (M22): a selected unit gets a bar with Up 1 U, Down 1 U and Unpin, plus Arrow Up and
  Down, so pinning does not need a mouse. Moving to another panel stays drag-only for now: the only
  other panel in the example is on the other side, where every move is refused anyway.
- Device preview (M22): a drop or a move writes the pin straight away with a toast and Undo, as the
  Panels board does (`editing.md` "Drag and drop contract"). It does not go through the save bar. A
  KVM pinned away from waist height is added to the warnings banner in words.
- Kept as they are after the M22 critique: the green drop colour (the board uses it, and the ghost
  says "U 9" in words); amber Changed and cobalt Override dots side by side (the existing components;
  Changed sits before the label, Override before the value); a second "Firewall" row added from Add a
  device shows the same label (its part and tags tell them apart in the built app, which is M23's
  call); below 1280 px the page does not reflow (1280 is the minimum width, `design-language.md`).
- Still open for Ali: a read-only reviewer mode (hides Save, Add device and
  Remove for non-engineers). Not designed yet; it is a likely M10 follow-up.
