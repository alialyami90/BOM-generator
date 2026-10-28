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
| **Pending set** | Library device and catalogue edits | Edits collect in a *pending changes* list. "Review and apply…" shows the diff (the same review as importing a library update) and writes one new local library version. Specified in the Library design. |

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
- Pinned units are placed first; the rest of the layout fills around them.
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
- Overrides are applied before the automatic fill: pinned units are placed first.
- `layout_preview` keeps returning, per device, whether it is pinned and its position in the panel.
- The writers (A2) write `layout.overrides` and `layout.removed` for each action and return the new
  `layout_preview`.

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
| General | Substation name (editable), substation id (read-only: "Names the substation in the register and in tags"), title line, the read-only **From the project** block with a link to the overview |
| Documents | One select per calculation sheet (Power, Heat dissipation, Heat calculations) from the register, with its number, revision and date shown |
| Output | Main document (select), file name pattern with the resulting name shown, the three calculation sheet names |
| Design constants | The ten constants as number fields with unit and default; changed ones are marked **Changed from 125** with **Reset**; **Reset all to defaults** in the table foot |
| Loose material | Moves to its own page (see the Loose material design) |
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
