# Editing model (v0.2)

Design for the v0.2 editors (M16 library, M17 projects and panels, M18 loose material). Ali tested
v0.1.0 and found settings, panels and the library read as static examples. For v0.2, **every value the
app shows is real and editable, or says why it is not**. A control that cannot act is not drawn as
if it could: it is absent, or disabled with a reason beside it (backlog points 4, 7 and 9).
Business rules stay in the engine. The UI collects values, shows what the engine says about them and
writes through the engine's writers; it never sizes, places or validates by itself.

Files stay the source of truth, but nobody has to open one. YAML and `.bomproj` are for import, export and
backup. The YAML tabs stay as an advanced view (see "YAML tabs").

## Three kinds of write

| Kind | Where | How it behaves |
| --- | --- | --- |
| **Form** | Project, Substation settings, Network, hand-written panel | Edits are held until the person saves. A **save bar** appears at the foot of the page while there are unsaved changes. |
| **Direct action** | Create or delete a project, substation, panel or document; board moves, pins and deletes; remove a row | Writes at once, says what it did in a toast, and offers **Undo** or has a backup behind it. Never silent. |
| **Pending set** | Library device and catalogue edits | Edits collect in a *pending changes* list. "Review and apply…" shows the diff (the same review as importing a library update) and writes one new local library version. See "Library editing (v0.2)". |

Rule of thumb: a *value* is saved with the form; a *record* appears or disappears at once.

## Save bar

A strip fixed to the foot of the content area, shown only while the page has unsaved changes.

- Left: a dot and **"3 unsaved changes · saved to substation.yaml"**. It names the file that will be written.
- Right: **Discard** (secondary) and **Save changes** (primary, shows `Ctrl+S`).
- While any field is invalid the left text becomes a red **"1 field needs fixing before you can save."**
  with the error icon, Save is disabled, and clicking the text moves focus to the first invalid field.
- The status bar says "Unsaved changes" in warning colour while the bar shows.
- Discard restores the saved values and toasts "Changes discarded". Save writes, clears the bar and toasts
  "Saved 3 changes".
- The header has no Save button on form pages: one place to save, always in the same place.
- Not shown on the Substations and Backup tabs of a project, or on the Panels board, whose actions write at once.

**Leaving with unsaved changes** (a navigation link, a different project or substation, closing the app)
opens a dialog: *Keep editing* · *Discard changes* · *Save and leave*. Save and leave is disabled while
a field is invalid, and says why. Moving between tabs of the same page keeps the changes.

## Validation

- Each field is checked as it is edited, by the engine's model for that file, so the message is the
  engine's. Show the **problem and the fix**: "Enter the number of field IEDs, for example 40."
- A field is marked (red border, error icon, message under it) once it has been left or once it is
  invalid *and* was valid before; an empty required field in a new record is marked on first save attempt,
  not while the person is still typing in the first field.
- Number fields accept digits and one decimal point; anything else is invalid until fixed.
- Problems that need the whole file (a missing document, a part not in the library) come back on
  save, appear as errors on the field they name, and also appear in **Checks** as today.
- A save that the engine refuses shows a red banner at the top of the page naming the file and the
  reason; nothing is written and the edits stay in the form.

## When the file changes behind the app

Colleagues and Windows sync can change a file the app has open. When the window regains focus the app
compares the modified time of the open project and substation files.

- No unsaved changes: reload quietly and toast "substation.yaml changed on disk. Reloaded."
- Unsaved changes: a warning banner at the top of the page: **"substation.yaml changed on disk since you
  opened it."** with *Reload (lose my changes)* and *Keep mine (overwrite the file)*. Neither is the default
  action; the page stays editable meanwhile.

## Creating

| Record | Entry point | What the person enters | What the app fills in |
| --- | --- | --- | --- |
| Project | Home › **New project…** (dialog) | Name, client (optional), device library (default: the active one), whether to add a first substation and its name | The folder, named from the project (shown, with "Change where projects are kept"), shared defaults from the spec, an empty document register, the library version stamp |
| Substation | Project › Substations › **New substation…** (dialog), or **Create from this…** | Start from (blank or a copy), name, first cabinet number, tag prefix | Folder from the name, three calculation documents in the register with blank numbers, a cabinet document per panel when panels appear |
| Document | Project › Documents › **Add** (dialog) | Substation, name, number, revision, issue date | The register key |
| Equipment row | Network › **Add device** (picker) | The part; then role, A and B, quantity, L2 ports in the row | Defaults from the library entry |
| Hand-written panel | Panels › **Add hand-written panel…** | Name, cabinet number, kind | Tag prefix, empty devices |

A new substation opens on **Network** with a **setup card** that lists what is left, in order: the number of
field IEDs, the equipment, then "Look at the panels". Each step is done when its data exists.
Creating never needs a path, a file name or YAML. The folder name of a substation is fixed once it
exists; its **name** can change at any time (Rename), so file paths in a `.bomproj` do not move.

## Deleting and undoing

| Action | Confirmation | Safety net |
| --- | --- | --- |
| Remove a row (equipment, loose item, document row, panel device) | None | Toast with **Undo** for 8 s; also undone by Discard before save |
| Delete a document | None; disabled with the reason ("Used by Sheet 1. Pick another document there first.") when something uses it | Toast with Undo |
| Delete a substation | Dialog that states what goes (network, N panels, settings, its documents) and needs a tick box | A backup of the whole project is saved first and named in the toast |
| Delete a project | Dialog; the project name must be typed | A `.bomproj` is saved first in the app's Deleted folder; Home keeps "Restore deleted project" for 30 days |
| Board move, pin, delete | None | Undo (button, toast, Ctrl+Z) and "Reset to automatic" |

## Panels board: drag, drop, pin, delete

The board is a **direct-action** surface: every change writes `layout.overrides` or `layout.removed` at
once, shows the new layout, and offers Undo. The status bar reads "Substation saved just now"; there is
no save bar on the board. The engine places everything; the board only records what the person
decided and shows what the engine returns (`layout_preview`).

### Pins

A **pin** holds a unit (or a pair) at a panel, and optionally at a position, so it stays there when the
network or equipment changes. It is the user-facing word for a layout override.

- Dragging or moving a device **pins** it. The block shows a pin icon and the selection bar offers **Unpin**.
- **Pin here** pins a device where it already is, without moving it. A pin that equals the automatic place is
  kept (engine need below).
- **Unpin** hands the device back to the layout; it is placed again automatically.
- A pin holds. The layout still fills first and the overrides are applied after it (R7, A8's #100), so a pinned unit is where it was pinned and the layout does not move it.
- A pair is pinned and unpinned together; "Move this unit only…" pins one unit.
- The header link reads "2 pinned · 1 deleted" (or "Nothing pinned or deleted") and opens the list:
  each row says what is pinned ("L1 switch 2 (pair) to panels 3 and 4, position 2") with **Unpin**, and each
  deleted device with **Restore**.
- **Reset to automatic** releases every pin and deletion, after a confirmation that counts them. It can be undone.

### Drag and drop contract

The board never draws an affordance that does not act. The grip, the grab cursor and the drop targets exist
only when the board can write; otherwise the page shows one line: "Moving a device here is not available
yet. To move one, add it to layout.overrides in substation.yaml." and the blocks are plain.

| State | What the person sees |
| --- | --- |
| Idle | Block with a grip; cursor `grab` on hover |
| Dragging | The source block is dimmed (45%); cursor `grabbing`; the destination is evaluated live |
| Over a panel that can take it | The panel (both panels of a pair, when moving a pair) gets a green border and tint, and a blue **insertion line** with a dot shows the position between two blocks |
| Over a panel that cannot | Red border and tint, cursor `not-allowed`; no insertion line |
| Drop that fits | The layout runs again, the block shows the pin, a toast says "Pinned L2 switch (pair) to panels 3 and 4, position 2" with Undo |
| Drop that does not fit | Nothing changes; a red banner says why: "Panel 1 needs 34 U, only 32 U may be used. Nothing was changed." |
| Drop where it already is | Nothing happens, no toast |
| Esc while dragging | Cancels |

- Dragging a redundant unit moves the **pair**; hold **Alt** to move that unit only. Side rules hold: an A unit only
  goes to an odd panel, a B unit only to an even one.
- The position is the gap the pointer is in. Dropping into the same panel only changes the position.
- Moves never re-flow other devices silently. If a move does not fit, it is refused.

### Keyboard

Tab to a block; Enter or Space selects it; then:

- **Alt + ↑ / ↓** move it one position up or down in its panel.
- **Alt + ← / →** move it to the neighbouring panel (a pair moves to the neighbouring pair).
- **Move…** in the selection bar opens the destination list with the panel and a position (where the layout
  puts it, at the top, at the bottom), and greys out panels that do not fit with the reason.
- **Delete** removes the selected device (the pair, if it has a partner); **Ctrl+Z** undoes.

### Delete

Delete removes a device from the BOM (`layout.removed`). It is not a pin. The toast says so ("Deleted Gateway
(both units) from the BOM") with Undo, and the list offers Restore.

## Panel editor (v0.2)

- **Generated panels.** Devices stay read-only (they follow Network and the board; each row links to the board).
  **Enclosure** is editable and shared by all generated panels, with a note that says so. **Options** are
  editable with an **Apply to** switch: *All generated panels* or *This panel only*; a value set for one panel
  is marked **Own value** with a link to go back to the shared one. **Port plans** are editable; they belong
  to the equipment, so a change applies to the other panels with that device and to both sides, and the tab says so.
  **Document** is editable. The YAML tab is read-only.
- **Hand-written panels.** Everything is editable, as before, plus **Delete panel…** (confirmation, Undo).
  Created from Panels › **Add hand-written panel…**.

## Engine needs for the board (for A8 and A2)

- An override may carry a **position** (index among the panel's rack devices): `DeviceMove.position`,
  `PairMove.position`, optional.
- An override that equals the automatic place must be **kept**, not dropped, so that "Pin here" holds.
- Overrides are applied after the automatic fill (R7, #100). A pin holds the unit where it was pinned; a pin that cannot fit is a reported error, never a silent reflow.
- `layout_preview` keeps returning, per device, whether it is pinned and its position in the panel.
- The writers (A2) write `layout.overrides` and `layout.removed` for each action and return the new
  `layout_preview`.

## Back-end needs for the generated-panel editor (for A2 and A8, via A1)

What the panel editor writes, by model field. Most fields exist in the model; what is missing is the writer, and
for two of them a way to go back.

| Editor control | Model field | What is needed |
| --- | --- | --- |
| Enclosure (shared by all generated panels) | `generated_panels.enclosure` | Writer; per-field validation of the `Enclosure` fields. One value for all panels, so no per-panel enclosure is designed. |
| Options, *All generated panels* | `generated_panels.options` | Writer; validation by `PanelOptions` for each key. |
| Options, *This panel only* | `generated_panels.options_by_panel[n]` | Writer that sets one key for panel `n`, and one that **removes** the key again (the "Own value, use the shared one" link). The reader must report, per option, whether panel `n` has its own value, and the shared value it overrides. |
| Port plans | `equipment[].port_plan` (`uplinks_l3`, `uplinks`, `downlinks`, `serial_ports`) | Writer per equipment row. The plan is per unit and scaled by the row's `qty`, so a change reaches every panel that holds that device and both sides of a redundant pair; the tab says so. |
| Document | `generated_panels.document` | Writer; the document must be in the register. |
| Hand-written panel (all tabs) | `panels/<id>.yaml` | Write, create and delete the file, and keep `manual_panels` in the substation file in step. |

Each writer returns the new `layout_preview` and the problems it caused, as the board's writers do.

## Field inventory

What each form shows, so every field in the models is reachable. *Check* is who validates; *Default*
shows what a new record starts with. Labels are the user-facing words; model names are in the schema.

### New project dialog

| Field | Control | Notes |
| --- | --- | --- |
| Project name | Text, required | Becomes the folder name (shown) |
| Client | Text | Optional |
| Device library | Select of installed versions | Default is the active one |
| Add a first substation now | Checkbox, on | Shows its name field |

### Project › Overview

| Field | Control | Notes |
| --- | --- | --- |
| Project name | Text, required | Bold line at the top of every sheet header |
| Client | Text | Empty reads "Not set" when the field is read-only |
| Logo | File chooser (PNG) with a preview and **Remove** | The file is copied into the project; a missing logo shows the warning |
| Device library | Read-only facts, **Record 1.4.0 in this project** | Library version stamp; never edited by hand |
| Catalogue brands | One select each for MCBs, aux contacts and terminal blocks, listing the library's brands with the default marked | Starts as the library default; changes the ordering codes on the next build, not ratings or sizes. A substation can override it (Substation › Settings). See "Library editing" |
| Shared defaults | Number fields with units: power margin, spare ports, rack space kept free, spare DC branches per feed, spare AC branches | A substation starts from these |
| Delete project | Danger button | See "Deleting" |

### Project › Documents (the register)

| Field | Control | Notes |
| --- | --- | --- |
| Document no. | Text, mono | One per row |
| Rev | Text, mono | e.g. 02 |
| Issue date | Text, mono, ISO date | An assumed date shows **Assumed date** with a **Confirm** button |
| Name | Shown in the row; edited in the dialog | |
| Used by | Read-only | Sheet or panel that picks the document |
| Add / remove | **Add** per substation band; trash per row | Remove is disabled while *Used by* is set |

### Substation › Settings

| Tab | Fields |
| --- | --- |
| General | Substation name (editable), substation id (read-only: "Names the substation in the register and in tags"), title line, **Catalogue brands** (one select each for MCBs, aux contacts and terminal blocks; the first option is "Same as the project (ABB S200)"), the read-only **From the project** block with a link to the overview |
| Documents | One select per calculation sheet (Power, Heat dissipation, Heat calculations) from the register, with its number, revision and date shown |
| Output | Main document (select), file name pattern with the resulting name shown, the sheet names (Loose Material, Power, Heat dissipation, Heat calculations) |
| Design constants | The ten constants as number fields with unit and default; changed ones are marked **Changed from 125** with **Reset**; **Reset all to defaults** in the table foot |
| Loose material | Moved to its own page, **Loose material** in the sidebar (see "Loose material (v0.2)") |
| YAML | Advanced view of the file |

### Substation › Network

| Field | Control | Notes |
| --- | --- | --- |
| Field IEDs | Number, required | Never a BOM row; sizes the L1 switches. A new substation marks it required |
| Topology | Star or Ring (segmented) | Ring shows *Switches per ring* |
| L1 switch model | Ranked table, **Pin** per row, **Unpin** | The engine ranks; the UI pins only |
| Equipment rows | Part (picker; **Change part…**), role, A+B, quantity, L2 ports, remove | Quantity is replaced by "Sized" on an L1 row, because the sizing sets it. Height comes from the library |
| Spares | Ports kept free (%), spare SFPs per L1, rack space kept free (U), spare DC branches per feed, spare AC branches | Start from the project's defaults; changed ones are marked |
| Result | Read-only card | Updates as the fields change; shows a busy state |

### Panel (hand-written; generated panels keep their read-only tabs)

| Tab | Fields |
| --- | --- |
| Enclosure | Make, model, ordering code, height, depth, width, base frame height, cable entry, rack height |
| Devices | Reorder, part (picker), quantity, purpose, HWIO override, remove, **Add device** |
| Port plans | Per switch: use, ports, speed, media, spare; **Add allocation**; the engine's result under it |
| Options | Spare branches, ventilation, change-over diodes, main MCB override, socket, inter-panel terminals, smoke detector, grounding busbars, terminal overrides |
| Document | Register document (select), revised cells list with **Add** |

A **generated panel** shows the same tabs read-only under a banner that says what writes them and links to the
page that does (Network, Panels board). Those fields are not disabled inputs that look editable: they are
shown as plain values.

## Library editing (v0.2)

The library is edited by the person who owns it, so every value in it is editable and every edit is reversible
before it is applied. Library edits use the **pending set**: they do not touch the installed version. Projects
keep using the version they record until the person applies the set and a project records the result.

### The pending set

- **What goes in:** every saved device edit, every catalogue cell, brand or housekeeping change, every row
  accepted from a CSV file, and every device deletion. Each entry is one line: area, what, from, to.
- **Pending bar:** while the set is not empty, a bar at the foot of the Library page says "3 pending changes ·
  not applied yet. Projects keep using 1.4.0 until you apply them." with *Discard all* and *Review and
  apply…*. It looks like the save bar but is a different thing: it stays across pages and sessions of the
  Library and is never a leave-page warning.
- **Review and apply** (`#/library/review`): the same diff list as importing an update (added, changed,
  removed), the version it will create (`1.4.0+local.1`), a note, and *Apply and activate*. Applying writes a
  new **local version**, makes it active and keeps the previous version installed, so going back is *Make
  active* on Installed versions. A local version is marked "local" and builds from `+local.N` of the version it
  started from.
- **Discard all** asks first and offers Undo after.
- **Why not edit in place:** a project records its library version so a colleague can reproduce its workbook.
  An in-place edit would silently change old projects.

### Catalogues tab

The Library has two tabs, *Devices* and *Catalogues*. Catalogues has a segmented switch for the five
catalogues: **MCBs, Aux contacts, Terminal blocks, Busbars, Housekeeping**.

- **Brand per catalogue:** MCBs, aux contacts and terminal blocks each have one tab per brand (Schneider
  Acti9, ABB S200, Siemens 5SL6 for MCBs). One brand carries the *Default* badge. *Make X the default brand*
  changes it. *Add brand…* creates one, optionally as a copy of the current brand's rows so only the codes
  need typing. The project chooses its brands on Project › Overview ("Catalogue brands"); a new project starts
  with the library default. A substation may choose its own on Substation › Settings › General, where the
  first option is "Same as the project (ABB S200)"; the substation's choice wins.
- **Rows are cells:** each row is editable in place (rating and ordering code for MCBs; model and code for aux
  contacts; type and code for terminal blocks; description and tag for busbars). *Add rating* / *Add row* and a
  per-row remove. Edits are pending entries, never writes. A removed row is listed under *Removed* on review.
- **Housekeeping** is a table of roles (lamp, door switch, fan, vent filter, thermostat, IPR kit, change-over
  diodes, socket), each pointing to a library part, with *Change…* to pick another part.
- **Validation** is the engine's per field (an MCB rating is a whole number, a code is unique inside a
  brand). The inline message and the *Review* page show it; a pending entry with a problem cannot be applied.

### Device editor

A device opens in its own page, `#/library/device/<part id>`, from *Edit device* on the detail pane, and
*Add device…* opens the same page for a new one. It is a **form**: save bar ("Save device", Ctrl+S), validation
as you type, leave dialog. Saving adds one pending entry per changed field; it does not apply anything.

Tabs and fields, mapped to the model's `DeviceType`:

| Tab | Fields |
| --- | --- |
| Identity | Part ID (fixed once saved: projects refer to it), Category, Make, Model, Ordering code, Description in the BOM (with `{placeholders}`), Tag type, Purdue level |
| Electrical | Supply type, Voltage, Power supplies, Rated power (W), Inrush current (A), Load type, Minimum branch MCB (A), HWIO points, Digital inputs, Alarm on the branch MCB, Leave out of the power total |
| Ports and mounting | Height (U), Fibre cores, port groups (count, speed, media, kind, used for) with add and remove |
| Parts it brings | Child parts (part, qty), Terminals (strip, block, count, per), Loose items (part, qty, tag) |
| Datasheet | Supply range, Operating temperature, Typical and Maximum power, Ports, Dimensions, Weight, Certifications, Datasheet link, Data quality, Sources |
| Alternatives | Alternative group key and the comparison list below, *Add alternative…* |

- **In use:** a banner says how many equipment rows in the open substation use the device, and that an edit
  reaches a project only when it records the version you apply. *Delete…* names the rows that use it and
  warns that the substation will report an error until another part is picked.
- **Part ID is a record, not a value:** it cannot change once saved. To rename, copy and retire.
- **Add device** (dialog): start from a blank device or a copy of an existing one (a copy keeps electrical
  data, ports and parts), then Part ID (unique, checked), Category, Make, Model. *Create and edit* opens the
  editor on the new device, which exists only in the pending set until saved and applied.

### Alternatives: one comparison list per device

Alternatives are library parts, linked by one group key (`alt_group`), not a separate structure. The list shows
the device itself first and then each alternative:

| Column | Notes |
| --- | --- |
| Tier | Low, Mid, High |
| Part | Part ID and model |
| Make | |
| Power (W), Inrush (A) | each with a **delta chip** against this device, warning-tinted when higher and success-tinted when lower; the chip is plain text with a sign, never colour alone |
| Ports, Height | the first port group and the height, with a delta for height |
| Data | the data-quality badge |
| *Use…* | "use this instead" |

The library page's detail pane shows a compact version (part, power, inrush, *Use…*); *Compare in full* opens
the device editor on this tab.

**Use this instead** opens a dialog listing the equipment rows of the open substation that use the device
(each checked), says that only the part changes and the layout, MCB sizes and BOM are worked out again, and
that pins stay put. Confirming goes to Network with the change held as an unsaved edit on those rows, so the
person reviews it and saves it like any other Network edit. With no substation open, or no row using the
device, the dialog says so and the action is disabled. The Change-part picker on Network lists the current
part's alternatives first under "Alternatives to X".

### Export and import

- **Export…** (dialog): *Spreadsheet (CSV)* or *Backup package (.bomlib)*. CSV: choose tables (devices,
  alternatives, catalogues) and a folder; one file per table, written as UTF-8 with a byte-order mark so Excel
  shows accents and symbols. A note says to keep `part_id` and `alt_group` as they are: they link rows.
  Backup writes a complete package of the active version that can be kept or handed on as an update.
- **Import…** is a menu: *Update package (.bomlib)…* (the existing flow) and *Spreadsheet (CSV)…*.
- **CSV import** (`#/library/csv`) has a review step before anything is added: (1) choose or drop a file;
  (2) review: file facts (name, size, rows per table), **Checks** (required columns, unique part IDs, every
  alt group has two members), **Rows with a problem** (table, row, column, plain message with an example of a
  good value), and **What changes** (added, changed, removed with from → to); (3) *Add N valid rows to pending
  changes* adds them to the pending set (rows with problems are skipped and listed, and the sentence says how
  to include them); (4) done: banner with *Review and apply…*. A CSV import never writes the library directly.

### Engine needs for the library (for A5, A2 and A11)

- **A2:** per-field validation for every device and catalogue field (path and value in, message or nothing out).
- **A5 (ADR 0018):** write a local library version from a diff and the version it starts from, keeping the previous one.
- **A5 (ADR 0018):** CSV export (UTF-8 with BOM) and a CSV **dry run** that returns checks, row problems with table, row,
  column and message, and the added, changed and removed lists, without writing.
- **A2:** alternatives as parts with a group key, returning the comparison fields (tier, make, power, inrush, ports,
  height, data quality) for a device.
- **A2:** catalogue brand choice per project and per substation (M13, #97): the substation's choice wins, otherwise the project's, otherwise the library default.
- **A2:** list the equipment rows of a substation that use a part, for *Use this instead* and the delete warning.

## Loose material (v0.2)

Loose material is the substation's own list of items that are not mounted in any cabinet. Since ADR 0020 (Ali's
answer to Q36) it is printed on its **own sheet**, so it has its own page, its own tab in Preview and its own
sheet name; it is no longer a Settings tab and no longer sits under the WS console.

- **Page:** *Loose material* in the sidebar under Panels, with the item count. It is a **form** (save bar,
  Ctrl+S, leave dialog); adding and removing rows are edits held until saved. Discard brings the rows back.
- **Header actions:** *Add from library…* (primary) and *Add free text…*.
- **Table:** No., Part or description, Designation, Qty, Fed from, remove.
  - *Part or description:* a library part shows its part id with make and model and, when the part brings
    something with it, "comes with LPA37-696". A free-text item shows an editable description and a *Free text*
    badge; it never has "comes with" (ADR 0022).
  - *Designation:* the text printed in the Tag column. Library items start with make and model.
  - *Qty:* a whole number of at least 1, or `1 Lot`. Message: "Enter a whole number, or 1 Lot."
  - *Fed from:* Not fed, or a generated cabinet. An item that needs power names the cabinet that feeds it, and the
    engine adds the load there. A free-text item shows "—" with a screen-reader line "Not fed: a free-text item
    has no library part"; it is not a control, because the engine refuses `fed_from` without a part (ADR 0022).
- **Add from library (dialog):** search, a radio list of library parts with their data-quality badge, Quantity,
  Designation and Fed from. Parts the library brings with the item are added by the library, not typed.
- **Add free text (dialog):** Description (required), Quantity (required) and Designation; no Fed from. An info
  banner says a free-text item has no ordering code, make or model on the sheet and cannot be fed from a cabinet,
  and that an item that needs power, or needs those columns, must be added to the library first (ADR 0022).
- **Both dialogs** check the item with the engine before it joins the list, and show the engine's message by
  field label (Part, Fed from, Comes with), never by key.
- **Empty state:** "No loose material. With no items the workbook has no Loose Material sheet." with both add
  actions.
- **Below the table:** an *On the workbook* card (sheet name, position "after the cabinet sheets, before Power
  Consumption", "written only while there are items", a link to Preview) and an *Issued under* card: **Document
  of** (select of the panels), which is `loose_material.host_panel`. It names the document whose number, revision
  and date print in the sheet header; it no longer names the sheet the table is printed on.
- **Elsewhere:** Preview gets a *Loose Material (n)* tab between the cabinet sheets and Power Consumption, shown
  only when there are items, with an *Edit the list* link. Settings › Output gets a fourth sheet name, *Loose
  material* (`output.sheet_names.loose_material`). Build lists the sheet under "This workbook contains" only when
  it will be written.
- **Back-end needs (A2, A10, A11):**
  - Done by ADR 0022: an item has `part_id` *or* `description`; the page's Designation is `tag`; a free-text
    item has no `fed_from` or `children`.
  - Read and write `loose_material.items` (`part_id` or `description`, `qty` as a whole number or `1 Lot`, `tag`,
    and for library items `fed_from`) and `loose_material.host_panel`, with per-field validation; `fed_from`
    must name a generated panel.
  - The engine returns, per library item, what comes with it (children) so the page can show "comes with".
  - Preview needs the Loose Material sheet model (`SheetModel`) from the engine, like the other sheets.

## YAML tabs

Kept as an advanced view of the file, last in each tab list, labelled "Advanced". They show exactly what the
form will write, update as the form changes, and may be edited and applied back to the form as before.
Neither the form nor the YAML tab is required for any task. A generated panel's YAML is read-only.

## What the app needs from the engine (for A2 and A11)

The writers are the engine's; the UI calls them and shows what they return.

- Create a project (name, client, library version) and a substation (blank or from another), returning the
  new record and its first problems.
- Update, rename and delete a project or substation (delete saves a backup first and returns its file).
- Read and update every field in the inventory above, with **per-field validation**: a function that takes a
  field path and a value and returns the engine's message or nothing, so the form can mark it as the person
  types.
- Document register: add, update, remove, with the *used by* list so the UI can disable remove.
- Equipment rows and hand-written panel devices: add, update (part, role, redundancy, quantity, L2 ports,
  purpose, HWIO, port plan), remove, reorder.
- Report whether a file changed on disk since it was read (modified time or hash), for the focus check.
