# M32 The panel editor (design brief)

- Status: Draft for A1 (no code yet)
- Date: 2026-10-31
- Audit findings:
  - APP-3: the panel editor is a stub.
  - APP-4: Panels header actions.
  - APP-7: an engine error leads to the row to fix.
  - DOC-1, DOC-2: the generated-panel and hand-written writers are not wired in.
- Design authority:
  - [`docs/ui/screens.md`](../../ui/screens.md): "Panels board and list", "Panel editor".
  - [`docs/ui/editing.md`](../../ui/editing.md): "Panels board", "Panel editor (v0.2)", "Back-end needs for the generated-panel editor", "Panel (hand-written…)".
  - The approved prototype, `docs/ui/prototype` (`screens-project.js` `panelEditor`, `screens-layout.js` header actions).
- Mode: Operate. This is a refinement of the shipped visual system (tokens, components, save bar, banners); no new visual world.

## Job and outcome

Ali has laid out a substation (automatic since M27). He opens one cabinet to set what the layout
cannot know: enclosure, options, the ports each switch uses, and the document. He then checks the
BOM for that cabinet. The odd cabinet that the layout doesn't make, such as a WS console, he writes
by hand in the same editor.

He has succeeded when every value on a cabinet sheet that is not derived from Parts can be set
from that cabinet's page, and Preview shows it, without opening a YAML file. Today every tab is
a stub (`screens-panels.js:73`) while all the writers exist and are tested.

## What stays as approved

Build the prototype's panel editor as designed:

- **Header:** breadcrumb, cabinet name, then "cabinet number · kind · Side A, pair 1 (panels 1 and 2)". **Preview BOM** opens Preview on this cabinet's sheet.
- **Banner:** what writes this panel.
- **Tabs:** Enclosure, Devices, Port plans, Options, Document, YAML.
- **Generated panels:**
  - Devices is read-only.
  - Enclosure is shared by all generated panels, and a banner says so.
  - Options has the **Apply to** switch (*All generated panels* · *This panel only*), with **Own value** marks and "Use the shared value".
  - Port plans says that it changes every panel with that device, on both sides.
  - Document is editable.
  - YAML is read-only, labelled Generated.
- **Hand-written panels:** every tab is editable.
  - Devices has reorder, picker, quantity, purpose, HWIO override and remove.
  - The header has **Delete panel…**.
- **Panels header:** **Undo**, **Reset to automatic** (disabled with nothing to reset) and **Add hand-written panel…**.
- **Writes:** form tabs use the shared save bar (`draftForm`), so M29's leave dialog and the "Unsaved changes" status come for free. Board actions stay direct writes with Undo.

## What changes from the v0.2 design, and why

1. **The generated banner points at Parts and Device preview, not Network.** Network became Parts (M23), and Device preview is where a unit is moved or pinned (M24). The banner reads: "**Written by the layout.** Its devices come from Parts and where you place them on Device preview or the board. Enclosure, port plans, options and the document are yours to set." It has two actions: **Open Parts** and **Open Device preview**.
2. **Devices on a generated panel lists each unit with Origin** (Layout, Pinned, Pinned away from waist height). Each row has **Show on Device preview**, which selects that unit there, so a move is one click away. The tab has no editable cells; values are plain text (editing.md "shown as plain values").
3. **Port plans own `port_plan`; Parts owns the L2 link (M31).**
   - The M31 note puts "L2 links, speed/media, COM ports used" on the Parts row.
   - To keep one home per field, Port plans edits `port_plan` only: uplinks to L3, uplinks, downlinks and serial ports.
   - Each table shows the engine result under it.
   - Each device's L2 link (`l2_ports`, `l2_speed`, `l2_media`) appears as a read-only line, "Linked to the L2 switch: 1 × 1G MM", with **Change on Parts**.
   - If M31 lands later, this tab still works; the line just reads "Not set".
4. **Undo on Panels covers board writes only.** These are pins, moves, deletes, Reset to automatic and Lay out panels. Form tabs have Discard instead, as on every form page. The history is per substation and is cleared when it changes, as the board's `history` already is.
5. **Add hand-written panel…** asks for name, cabinet number and kind (Console, Network cabinet). It creates `panels/<id>.yaml` with an empty device list (`create_panel`) and opens the new panel on Devices. The id is made from the name, as substations are. The panel is listed last, after the generated panels, as `manual_panels` puts it.
6. **Delete panel…** names what still uses the panel. The writer refuses while a mirror or loose material names it, and the dialog then lists what to change first instead of a disabled button with no reason. A delete that goes through toasts with Undo, which recreates the file from the copy kept in memory.

## Engine errors lead to the fix (APP-7)

Every located problem gets one action that opens the place to fix it. The action's label says where it goes. Today the only action is "Show the line", which opens the read-only YAML tab.

| Problem location | Action | Goes to |
| --- | --- | --- |
| `equipment[n]…` | Go to the row | Parts, row n focused and its strip opened |
| `network.*`, `spares.*`, `catalogue_choice.*` | Go to the field | Parts, that field focused |
| `generated_panels.enclosure.*` / `.options.*` / `.options_by_panel[n].*` / `.document` | Open the panel | Panel editor of panel n (or the first generated panel), on that tab, field focused |
| `panels/<id>.yaml` (any key) | Open the panel | That hand-written panel, on the tab that holds the key |
| `layout.overrides[i]` / `layout.removed[i]` | Open the board | Panels board with the changes list open on that pin |
| `loose_material.*` | Open loose material | Loose material, row focused |
| substation fields (`output`, `calculations`, `document`, constants) | Go to the field | Settings, that tab, field focused |
| anything else | Show the line | Settings › YAML (as today) |

The problem text also stops blaming "library.yaml" when the installed library is in use. It names the library by name and version, for example "SEL-2730M is not in psa-devices 1.9.0".

The routing is one function in the UI, `whereToFix(problem) → {label, hash, focus}`, and it is unit-tested through the asset tests. Checks, Device preview's error banner and Panels' "No layout" state all use it.

## States

- **The panel can't be read** (the substation has errors): the editor shows the problems banner with the actions above. Tabs are not shown.
- **No generated panels yet:** Panels shows M27's state. The editor is unreachable.
- **Options for one panel:** the reader is `panel_options(n)`. An own value shows **Own value · shared 3**, with **Use the shared value**.
- **Saving refused:** the model's message goes under the field (editing.md "Validation"), and nothing is written.
- **Hand-written panel with no devices:** the empty state reads "No devices yet. Add the first one; the BOM lists them in this order." with **Add device**.
- **Range:** 1–12 panels. Devices per panel run 1–30, with up to about 6 port-plan rows per switch.

## Back end

Most of this exists and is tested. New endpoints are in bold.

| Need | Exists | New |
| --- | --- | --- |
| Generated: enclosure, document, options (all or one, remove), port plan | `set_enclosure`, `set_generated_document`, `panel_options`, `set_panel_option`, `remove_panel_option`, `set_port_plan` | none |
| One page per panel: header facts, devices with origin, tabs' values, problems located in it | no | **`panel_page(project, sub, panel_id)`**, built from `layout_page` and the loaded panel |
| Hand-written: create, write, delete | `io/panel_edit.py` `create_panel`, `write_panel`, `delete_panel` | **`create_panel`, `set_panel_field` (path into the file, with `check_panel_field`), `delete_panel`** on `Api` |
| Where to fix a problem | problems carry `file`, `location`, `line` | none; the UI maps them (table above) |

Each writer returns the new panel page, as the board's writers return the layout.

## Scope and order

One milestone, in two PRs so that each stays reviewable:

- **M32a:** the generated-panel editor (all six tabs), Panels header actions, and APP-7 routing.
- **M32b:** hand-written panels: Add, the editable Devices, Enclosure and Options tabs, and Delete.

Not in M32:

- ENG-10 (a control cabinet type, a later milestone).
- Paired moves on the board (ALI-17, A1's card).
- The Settings YAML "Apply to form" (APP-21).

## Open decisions

1. **Ali (card posted):** on a generated panel, is a device added only through Parts? The recommended answer is yes: Devices stays read-only and links to Parts.
2. **A1, A3:** split port fields as in point 3 above, port plans here and the L2 link on Parts (M31)?
3. **A1:** two PRs, M32a then M32b, or one?
