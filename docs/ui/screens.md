# Screens, flows and states

Layouts and behaviour for every screen in the desktop app, in the prototype's
route form (`prototype/index.html#/…`). Components are in
[`components.md`](components.md); the approved scope is in [`brief.md`](brief.md).

## Map

```
Home ─┬─ Open / New project ──▶ Project ─ Panels ─ Library ─ Checks ─ Preview ─ Build
      └─ Install a library ──▶ Library (Import update)
```

| Route | Screen | Purpose |
| --- | --- | --- |
| `#/home` | Home | Recent projects; first-run guidance when no library is installed |
| `#/project/<tab>` | Project | Project settings in six tabs, one of them YAML |
| `#/panels` | Panels | The cabinets of the project |
| `#/panels/<id>/<tab>` | Panel editor | One cabinet: enclosure, devices, port plans, options, document, YAML |
| `#/library` | Library | Browse the installed devices, datasheets and alternatives (read-only) |
| `#/library/import` | Import and versions | Review and install a `.bomlib`; installed versions and rollback |
| `#/checks` | Checks | Problems in the files, then the engine's checks |
| `#/preview/<sheet>` | Preview | The seven workbook sheets as the engine computes them |
| `#/build` | Build | Choose the name and folder, write the workbook |

The left navigation follows the workflow. Home and Library are always
reachable; the other items are disabled until a project is open.

## Primary flows

**1. First run.** Home shows three numbered steps. "Install a library…" opens
Library → Import update. After a successful import the navigation unlocks and
Home becomes the recent-projects list.

**2. Open, fix, build.** Open project → Project opens on General → Checks shows
the problem list → "Go to field" opens the right panel tab with the field
highlighted → fix → "Run checks again" → Preview → Build → "Open workbook".
Build is disabled while errors exist and says why.

**3. Update the device library.** Library → Import update… → choose the
package → review verification and changes → "Import and activate x.y.z". The
previous version stays installed. Projects built with the previous version
show a warning in Checks until rebuilt.

**4. Mirror a panel.** Panels → Mirror a panel… → pick the original, enter the
panel id, cabinet number, cabinet name, sheet name, tag prefix and LAN → the new
panel opens with a banner that says it follows the original. A mirror is a small
file (`mirror_of`, identity fields, its own `options` and `document`). Its
Enclosure, Devices and Port plans tabs show the original's content read-only with
an "Open PSA1" button. Options (only the filled fields are written), Document and
YAML are editable. An error in the original's devices is reported on the original.

**5. Edit as YAML.** Any record with a YAML tab (Project, Panel) offers the
file's source. Errors show on the line. "Apply to form" is available only when
the YAML is valid.

## Screens

### Home
- **Layout:** title and two actions (Open project primary, New project
  secondary); a table of recent projects (name and path, document number,
  panels, library used, last opened, status); an info banner about importing a
  library update.
- **Behaviour:** a row opens the project. Status uses the same words as Checks
  (`Ready`, `2 errors`, `Library out of date`).
- **States:** first run (library missing): steps list, "Install a library…"
  primary, "Open project…" disabled with an explanation. Empty recent list
  (library installed): heading "No projects yet" and the two actions.

### Project
- **Layout:** title, Save (enabled only when changed), tab list, one form per
  tab (720–840 px column).
- **Tabs:** *General* (name, substation, document number, revision, logo, and a
  read-only block for the library the project was built with and the active
  one); *Documents* (a table for the three calculation sheets: document number,
  revision, issue date, scope); *Output* (file-name pattern with the resulting
  name shown, sheet names); *Design constants* (a table of the ten spec
  constants with unit, default and a "Changed from …" badge when different);
  *Loose material* (items not in any cabinet, with the cabinet that feeds them);
  *YAML* (`project.yaml`).
- **States:** unsaved (status bar shows "Unsaved changes", Save enabled);
  invalid field (inline error); library older than active (badge and a
  "Record 1.4.0 in this project" action).

### Panels (list)
- **Layout:** table (sheet, cabinet number, name, kind, LAN, device count,
  mirror of, status), actions "Mirror a panel…" and "Add panel".
- **Behaviour:** order is sheet order. Mirror and Add open dialogs. Status shows
  the panel's error count.

### Panel editor
- **Header:** breadcrumb, cabinet name, cabinet number · kind · LAN · mirror,
  "Preview BOM" and Save. A mirrored panel shows an info banner above the tabs and read-only Enclosure, Devices and Port plans.
- **Enclosure:** make, model, ordering code, H × D × W with unit suffixes, base
  frame height, cable entry.
- **Devices:** the main table. Columns: reorder handle, device (id and model),
  quantity, purpose, HWIO override, generated tag, remove. "Add device" opens
  the device picker. Order sets BOM order and breaker numbering. An unknown part
  id shows an inline error with a suggestion.
- **Port plans:** one section per switch with a small table (use, ports, speed,
  media, spare) and an "Engine result" footer.
- **Options:** spare branches, ventilation, change-over diodes, main MCB
  override, auxiliary socket, inter-panel terminals, smoke detector, grounding
  busbars, terminal overrides. Overrides carry a warning help line.
- **Document:** document number, revision, issue date, revised-cell list.
- **YAML:** `panels/<id>.yaml`.
- **States:** tab error badges; invalid field; mirrored panel; unsaved.

### Library
- **Layout:** title with the library name, version and install date, "Import
  update…" secondary; a toolbar (search, category, data quality, "Has
  alternatives", count); a table (part id, make and model, category, supply
  and rated power, data-quality badge) beside a 420 px detail pane.
- **Detail pane:** tabs *Overview* (library fields), *Datasheet* (supply range,
  typical and maximum power, ports, dimensions, weight, operating temperature,
  certifications, datasheet link, sources), *Alternatives* (two brands, each
  with Low, Mid and High models and a data-quality badge, copy buttons, and a
  note that swapping is not available yet).
- **Behaviour:** read-only. Selecting a row fills the pane; the arrow keys move
  the selection when the table has focus.
- **States:** no library installed (banner with an "Import…" action); no match
  (empty row); no datasheet or alternatives recorded (sentence in the pane).

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
- **Layout:** a status banner (red with the count, or green with "Go to
  Build"); a Problems section with level filter chips and a table (level,
  `file:line` and field path, what is wrong and what to do, "Go to field");
  an Engine checks section (SFPs match the port plans, main MCB covers the feed
  current, airflow covers the heat load, digital inputs cover the hardwired
  points) with Pass / Flag / Not run.
- **Behaviour:** "Run checks again" shows a busy button then a toast. Engine
  checks are "Not run" while errors exist and say why.

### Preview
- **Layout:** title, a banner when the last load had errors, sheet tabs (Sheet 1
  to 4, Power Consumption, Heat Dissipation, Heat Calculations), then the sheet.
- **BOM sheet:** group chips A to H with counts, a row filter, switches for the
  hidden HWIO column and revised cells; the sheet title block (cabinet number,
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

## Cross-cutting behaviour

- **Unsaved changes:** the status bar shows the state; leaving the project or
  closing the app with unsaved changes opens a dialog with Save, Discard and
  Cancel.
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
| Open a project: parsed models, or located errors (`file:line`, field path, message) | Project, Panels, Checks |
| The JSON Schemas for project and panels, plus a label and help override file | Forms |
| Validate and run engine checks: problem list and the four check results | Checks, status bar |
| Generated values per panel: tags, HWIO, engine port-plan results | Panel editor |
| The installed library: devices with datasheet, alternatives, sources and data-quality level | Library, device picker |
| Library packages: verify and preview (the dry-run result), import, list versions, roll back | Import and versions |
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
| Library packages (A5) | `preview_import` raises `LibraryPackageError(str)` for downgrade, same version, schema, minimum app version and checksum. There is no signature concept. | The Import screen assumes structured refusals and a per-check verification list. Needs typed refusals or a result object that lists each check. |
| Library packages (A5) | "Projects built with it" has no data source. `InstalledLibrary.problem` has no UI state. | The Versions table shows a project count; a library with a problem needs a state and wording. |
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
- Navigation rail: Build shows an icon with "Blocked" or "Ready" so state is never
  colour only.
- Devices table: the drag handle is full-contrast. Keyboard reorder is
  Alt+Up/Alt+Down on the focused row. Removing a row marks the project unsaved
  and offers Undo (Ctrl+Z) until the next save. The prototype only hides the row.
- Mirrored panels: Enclosure, Devices and Port plans are read-only and follow the
  original, matching A2's `PanelMirror`. The sample error moved to the original.
- Preview, Power and Heat show figures the engine supplies. The prototype holds
  them as literal values in `data.js`; no rule is computed in the UI.
- Still open for Ali: a read-only reviewer mode (hides Save, Add device and
  Remove for non-engineers). Not designed yet; it is a likely M10 follow-up.
