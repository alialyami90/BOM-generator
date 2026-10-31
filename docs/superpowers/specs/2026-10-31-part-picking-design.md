# Part picking, panel priority and the device preview — design

Status: draft for Ali's review (2026-10-31). Source: Ali's request in the project thread
"Replace network section with part picking" and his answers on the decision cards there.

## 1. Goal

Setting up a substation becomes "pick a part for each device type, adjust what this design
needs, look at the result". Success means:

- The Network page is replaced by a **Parts** page: one row per device type, each with a
  dropdown of library parts of that type, the library data shown next to the pick and
  overridable, and a part number box whose text is printed on the BOM. A plus button adds rows.
- The overrides drive everything downstream: the panel layout, MCB sizing, the power and heat
  sheets.
- Inside each panel, devices stack in a fixed priority, and KVM and console screens sit at
  waist height.
- A **Preview** shows each device with its panel, its place in the panel and its MCBs, plus a
  front view of each panel, before the workbook is built.

## 2. What Ali decided (2026-10-31)

| # | Question | Answer |
| --- | --- | --- |
| a | What sets a device's data? | The dropdown pick: height, power, supply and the rest come from the library and are shown next to it. Any of them can be overridden for this design. |
| b | What is the part number box? | Free text printed as the ordering code on the BOM. The library has the model but not the project's part number. |
| c | Network fine tuning | Today's network settings (ring size, uplinks, interlink, L3 uplinks, spares) in a subsection under the IED count and topology. The L1 ranking table goes; the L1 switch is picked in its row. |
| d | KVM and console height | A project setting, height in mm from the floor. |
| e | Where the lowest rack U sits | A project setting in mm above the floor, base frame included. |
| f | Does priority choose the panel? | No. Devices go to panels as today (equipment order, ADR 0013); priority only orders the stack inside each panel. |
| g | Preview content | A per-device table and a front view (elevation) of each panel. |
| h | SFP selection | One SFP model per media and speed the switch needs; the sizing still computes the counts. |
| i | Drag and drop in the panel views | Both: the Panels board's dragging does not work in the installed app and must be fixed, and the Preview's panel elevation gets dragging too. |

## 3. The Parts page

Replaces the Network page (`#/network` becomes `#/parts`; the old route redirects).

**Top:** Field IEDs (count) and Topology, as today.

**Network fine tuning** (collapsible, closed by default once the substation is set up): switches
per ring (ring only), L1 uplinks per switch, A–B interlink, L3 uplinks per L2, and the spares
(port fraction, DC branches per feed, AC branches, rack U reserved). Same fields, same checks
as today's page.

**Device rows**, in this order by default:

| Row | Dropdown lists library parts of category | Sub-rows |
| --- | --- | --- |
| Time server clock | `gps_clock` | Time accessories (see below) |
| L2 switch | `network_switch` usable as L2 | SFP per media/speed |
| L1 switch | `network_switch` usable as L1 | SFP per media/speed |
| Operator workstation | `workstation` | |
| Engineering workstation | `workstation` | |
| DA server | `workstation` | |
| KVM | `kvm` (new) | |
| Console | `console` (new) | |
| Annunciator | `annunciator` | |
| MCB make and series | the AC and DC MCB brands (catalogue choice, ADR 0023) | |
| TB make and series | the terminal block brands (catalogue choice) | |

Each device row has: the dropdown, the part number box, quantity, "A and B" (redundant), and a
details strip showing the library values (height U, watts, supply, voltage, power supplies,
inrush A, load type). Clicking a value turns it into an input; an overridden value is marked
and has a reset. The IED row has no part (it is the count at the top); L1 and L2 quantities stay
computed from the sizing, as today.

The MCB and TB rows set the existing catalogue choices; they have no part number box or
overrides.

**Time accessories** are extra library parts (antenna kit, cable, surge arrester) with a
quantity each. They go to loose material, as the GPS antenna kit does today.

**Plus row** at the end: pick a category, then it behaves like any other device row (FOPP,
firewall, EXT switch, gateway, RTAC, I/O and so on). Rows can be removed and reordered; the order
is the equipment order the layout fills panels in (decision f).

Everything on the page is saved together with the existing Save/Discard bar.

## 4. Data model (ADR 0024)

`Equipment` (substation file) gains:

- `ordering_code: str | None` — printed in the BOM's ORDERING CODE column instead of the
  library's `ordering_code`/`model`.
- `overrides: PartOverrides | None` — any of `height_u`, `unit_power_w`, `supply_type`,
  `voltage_v`, `power_supplies`, `inrush_a`, `load_type`. Each is checked as the library field.
- `sfp: list[SfpChoice]` — `{speed, media, part_id}`, L1 and L2 switches only; a missing entry
  keeps today's automatic pick (first matching SFP, same make first).
- `role` gains `time_server`, `operator_ws`, `engineering_ws`, `da_server`, `kvm`, `console`,
  `annunciator`, `time_accessory`. These label the Parts page rows and choose the panel priority;
  sizing treats them as `other`.

`Category` gains `kvm` and `console`. `Project.defaults.layout` (new) holds
`waist_height_mm` (default 1000, ASSUMED) and `rack_start_mm` (default 200, ASSUMED).

**How overrides reach the engine (recommended approach).** The loader turns each equipment entry
that has an `ordering_code` or `overrides` into a **derived part**: a copy of the library part
with those fields replaced, under the id `<part_id>+<equipment id>` (`~` is not a valid `PartId` character; `+` is), added to that substation's
resolved library only. The layout and every engine step then use that part id unchanged. The
library files are never written.

Rejected: threading override fields through every engine step (touches the 15 pipeline steps
and the sheets); saving overrides as new parts in a local library version (one design's
change would leak into every project using that library).

Hand-written panels keep working: a `DeviceInstance` names a library part as today.

## 5. Panel priority and waist height (amends ADR 0013, R5–R7)

Fill is unchanged: devices go to panels in equipment order (decision f). Then, inside each
panel, rack units stack top to bottom by:

1. Time server (`gps_clock`)
2. Network (`network_switch`, `patch_panel`, `firewall`, `gateway`)
3. Servers and workstations (`workstation`)
4. Others

Ties keep equipment order. DIN-rail parts (0 U) are not in the stack.

**Exception:** a KVM or console unit is placed so its bottom edge is at the U nearest to
`waist_height_mm`: `u = round((waist_height_mm − rack_start_mm) / 44.45)` counted from the
bottom of the rack space. Priority devices fill from the top down to it; anything that does not
fit above goes below it. If the panel's capacity cannot hold the KVM there, the check report
gives an error naming the panel. A pinned position (`layout.overrides` with `position`) still
wins over the priority, as today.

The rack now has absolute positions: each unit gets a top U, and blank space is reported, still
with no BOM row (Q25).

## 6. Preview

A **Preview** step after Parts, reachable from the Parts page's "Generate preview" button and
the nav. It runs the engine without writing the workbook.

- **Device table**, one row per unit: device, part, BOM part number, panel, U position, watts,
  supply, PS1 MCB (tag and rating), PS2 MCB (tag and rating), terminal strip. Overridden values
  are marked. Filter by panel.
- **Panel elevation**, one per panel: a scaled front view of the rack with each unit's tag and
  height, blank space, and the waist-height line.
- Check report issues appear above both, with "Go to" links to the row on the Parts page.

- **Dragging on the elevation** works as on the Panels board (editing.md, "Drag and drop
  contract"): drag a unit to another panel or U, Alt moves one unit of a pair, the target is
  checked live, and a drop saves a pin in `layout.overrides`. Dropping a KVM or console away from
  waist height is allowed (the pin wins) and the preview marks it. The same pointer-based drag
  code as the board fix (section 6a) is used, so both views behave the same.

The existing workbook sheet preview stays where it is.

## 6a. Panels board drag and drop fix

The board has HTML5 drag-and-drop code since M17 (`screens-panels.js`, `dragstart`/`drop`), and
the Linux Playwright test passes, but Ali reports dragging does not work in the installed Windows
app (WebView2). Plan:

1. Reproduce on the Windows CI runner (the "Build Windows installer" job can drive the frozen app
   with a Playwright/WebView2 script) to find the cause: WebView2 or pywebview blocking HTML5
   drag events is the most likely one.
2. Replace HTML5 drag-and-drop with pointer events (`pointerdown`/`pointermove`/`pointerup` with
   pointer capture), which WebView2 handles like any click. Same states, same bridge check,
   same Esc-cancels and Alt-moves-one rules; the keyboard "Move…" path is unchanged.
3. A test drives a drag with pointer events in Playwright and asserts the pin is saved.

## 7. Improvements added (Ali asked for these "as you see fit")

1. A row with no part number warns on the check report ("printed with the library model").
2. The details strip shows which values are overridden, with one reset per value and a "Reset
   all".
3. The preview flags devices whose MCB is at the minimum or whose watts are 0.

## 8. Milestones (one PR each)

| Milestone | Content |
| --- | --- |
| M19 | Panels board drag fix (section 6a): pointer-event drag, Windows reproduction, test. Ships first; it is independent. |
| M20 | ADR 0024; `Equipment.ordering_code`, `overrides`, `sfp`, new roles and categories, `defaults.layout`; derived parts in the loader; schemas; spec update. TDD, golden test unchanged. |
| M21 | Panel priority and waist-height placement in `engine/layout.py`; ADR 0013 amendment; layout preview gives top U per unit. |
| M22 | Parts page and device preview design in `docs/ui/` with the impeccable skill (CLAUDE.md "UI work"); the new step is named "Device preview". |
| M23 | Parts page in the app, replacing Network; writers for the new fields. |
| M24 | Preview page (engine API for per-unit MCBs and positions, table, elevation with dragging). |

## 9. Testing

- Unit tests named after each rule, e.g.
  `test_override_height_moves_the_layout`, `test_part_number_box_is_the_bom_ordering_code`,
  `test_time_server_stacks_above_network_in_a_panel`,
  `test_kvm_bottom_sits_at_waist_height`, `test_sfp_choice_replaces_the_automatic_pick`.
- The golden test from `examples/` must still reproduce the spec values; the example has no
  overrides, no KVM and its panels already follow the priority, so no golden value should move.
  If one does, it gets an ADR before the change.
- App: `node --check` and Playwright screenshots of the Parts and Preview pages.

## 10. Assumptions to confirm

- Waist height 1000 mm and rack start 200 mm are placeholders, marked ASSUMED.
- Gateway and firewall count as "Network"; RTAC and I/O as "Others".
- Time accessories and the annunciator go to loose material by default; the annunciator row has
  a "Mount in panel" switch for a panel annunciator.
