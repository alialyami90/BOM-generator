# Component specs

Every component in the prototype, with its sizes, states, behaviour and
accessibility notes. Colours and sizes are token names from
[`tokens.json`](tokens.json); the prototype's `styles.css` is the reference
implementation. General rules for all components:

- **Focus:** a 2 px ring in `color.focus`, offset 1 px, on every interactive
  element and always visible from the keyboard. On the navy bar the ring is
  `color.onBar`.
- **Targets:** at least 24 × 24 px (`size.targetMin`); default controls are 32 px
  high, compact in-table controls 26 px.
- **Disabled** never hides an action. It is shown disabled and the reason is
  stated next to it ("Unavailable until the 2 errors are fixed").
- **Reduced motion:** all transitions drop to zero.
- **Text:** at least 4.5:1 against its background, in both themes.

## Shell

### Top bar
Navy (`color.bar`), 48 px. Left to right: app mark and name, divider, current
project (name, with the open substation's name under it), spacer, library chip, theme button,
help button. The library chip is a link to the Library screen: a status dot
(green installed, red none) plus `name version`. The theme button cycles light,
dark and system, announces the new theme, and has the current mode in its
accessible name.

| State | Behaviour |
| --- | --- |
| No project open | Project block hidden. |
| Project open, no substation | Second line reads "No substation open". |
| No library installed | Chip reads "No library installed", dot red. |

### Navigation rail
216 px, `color.surface`. Home and Library, then group labels **Project**,
**Substation** and **Verify and issue**. Each item: icon, label (one line,
ellipsis when long), optional tail status at the right edge. Under the Substation
label sits the **substation switcher**, a full-width select listing the project's
substations; choosing one keeps the current screen when it exists for every
substation, otherwise opens Panels.

| State | Appearance |
| --- | --- |
| Default | Text colour, no fill. |
| Hover | `surfaceSunken` fill. |
| Current | `actionSoft` fill, semibold heading colour, cobalt icon; `aria-current="page"`. |
| Disabled (no project, or no substation) | 45% opacity, not focusable, tooltip "Open a project first" or "Open a substation first". |

Tail status types: tick (complete), count (neutral), version (neutral), error
count (red with icon), `Not set up` (amber with icon), `Blocked` (red), `Ready` (green). The status is text, so
it does not rely on colour.

### Status bar
28 px, `surfaceSunken`. Left: save state ("Saved 10:02" or "Unsaved changes" in
amber) and the project path in mono. Right: one button with the error and
warning counts that opens Checks. In the prototype a "Prototype states" control
also sits here; it is not part of the app.

## Actions

### Button
Heights 32 px (default) and 26 px (`sm`), 2 px radius, label 13.5 px medium.
Icon + label, or icon-only (square, needs `aria-label` and tooltip).

| Variant | Use | Appearance |
| --- | --- | --- |
| Primary | The one main action on a screen | `action` fill, white label |
| Secondary | Other actions | Surface fill, `actionText` outline and label |
| Ghost | Low-emphasis, in-table actions | No fill, `actionText` label |
| Danger | Destructive actions that need care | Surface fill, red outline and label |

| State | Behaviour |
| --- | --- |
| Hover | Primary darkens to `actionHover`; others get `actionFaint` fill. |
| Focus | Focus ring. |
| Disabled | `surfaceSunken` fill, muted text, `not-allowed` cursor, `disabled`. |
| Busy | A 14 px spinner replaces the icon, label changes to the progressive form ("Building…"), `aria-busy="true"`, click ignored. |

One primary button per screen area. A destructive action is never primary.

### Link and link-button
`actionText`, underlined, 2 px offset. Used for in-sentence navigation. A
button that looks like a link (`link-btn`) is for actions inside a sentence.

### Chip (filter toggle)
26 px, outlined; pressed state has `actionSoft` fill, cobalt border and medium
weight; `aria-pressed`. Shows an optional muted count. Used for the BOM group
and problem-level filters.

### Segmented control
Joined options, 30 px, one selected (`action` fill). Built on radio inputs, so
the arrow keys move the choice and a screen reader hears a radio group with a
label. Used for Star or Ring on the Network screen.

## Inputs

### Field
Label above (13 px medium), control, then help text (12 px muted) and, when
invalid, an error line with an icon below it. The error replaces nothing: help
and error can both show. Labels are real `<label>` elements. Required-ness is
stated in words ("Optional" in the placeholder), not with asterisks.

### Text input
32 px, 1 px `borderControl` (3:1), 2 px radius, 13.5 px text.

| State | Appearance |
| --- | --- |
| Default | Surface fill. |
| Hover | Border darkens to muted text colour. |
| Focus | 2 px focus ring, border `focus`. |
| Read-only | `surfaceSunken` fill, muted text. Selectable. |
| Invalid | `dangerSoft` fill, red border, `aria-invalid="true"`, error text linked by `aria-describedby`. |
| Disabled | `surfaceSunken`, not focusable. |

Variants: mono (codes, paths), numeric (tabular figures; right-aligned in tables
and next to a unit, left-aligned elsewhere), with a unit suffix (an attached
`affix` box on the right: "mm", "A").

### Select
Native `<select>` styled like the text input with a chevron; same states. Used
for short fixed lists. Long or searchable lists use the device picker.

### Checkbox, radio
16 px, 1 px `borderControl`, checked = `action` fill with a white tick (radio:
dot). Label is part of the target. Group labels use a `label` element above.

### Switch
34 × 18 px track, 14 px thumb. For settings that apply immediately or are
simple on/off options. Always has a text label to its right; `role` is checkbox.

### Device picker (combobox)
Opens from "Add device" and from a device cell. A popover with a search input
(`role="combobox"`), a listbox of up to 8 matches, and a hint line. Each option:
part id (mono), make · model · supply · rated power, and the data-quality badge.
Keyboard: type to filter, ↑ ↓ to move, Enter to add, Esc to close and return
focus. Source is always the active library version, shown in the listbox's
label. No match: "No device matches. Check the spelling, or install a library
that has it."

### File picker field
A mono text field showing the path, plus a "Browse…" secondary button that
opens the native Windows picker. Paths are never typed blind: invalid paths show
an error on blur.

### Drop zone
Dashed 1 px border, centred icon, title, helper text and a primary "Choose
package…" button (the click path is always available; drag and drop is a
shortcut). Drag-over: `actionFaint` fill and cobalt border. Keyboard: focusable,
Enter or Space opens the picker.

## Navigation

### Tabs
Horizontal text tabs with a 1 px rule under the list. Selected: semibold heading
colour with a 2 px cobalt underline. `role="tablist"`, roving tabindex, ← →
move and select, Home/End jump (Home/End are not in the prototype). A tab can carry a small error badge when its
panel has a problem. Tab panels are labelled by their tab. Used for sections of
a record (Panel: Enclosure, Devices, Port plans, Options, Document, YAML) and
for workbook sheets in Preview.

### Breadcrumbs
`Panels › PSA Cabinet - 001`, 13 px, muted; the parent is a link. Only on
screens that are one level inside another.

## Data display

### Table
The core component. Sticky header row (`surfaceSunken`, 12 px uppercase labels,
tracking 0.04 em), 28 px body rows (36 px in comfortable density), 1 px row
rules, 13 px text, tabular numerals, 10 px cell padding.

| Feature | Behaviour |
| --- | --- |
| Row hover | `actionFaint` fill. |
| Clickable row | Whole row opens its record; `tabindex="0"`, Enter or Space activates, cursor pointer. |
| Selected row | `actionSoft` fill, `aria-selected`. |
| Inline controls | Compact 26 px inputs and selects in cells. |
| Two-line cell | Primary text, then a 12 px muted sub-line (mono for ids). |
| Group separator | An empty bordered row (spec: groups E–H) or a `surfaceBand` row. |
| Merged cell | `rowspan` for a parent tag over its child rows; the issued sheet merges them too. |
| Revised cell | `#FFFF00` fill with dark text, in the Preview, on cells the engine marks as revised (there is no switch for it). |
| Empty | One row with a sentence that says what to do ("Clear the filter to see all 71 rows."). |
| Footer | 12 px strip with row counts or notes. |

Columns: numbers right-aligned, text left, status last. Headers are real `th`
with `scope`. Tables never wrap ids; descriptions wrap only where marked.
Horizontal overflow scrolls inside the table, the page never scrolls sideways.
Sortable columns (library, projects) show a sort button in the header with
`aria-sort`; not all prototype tables implement sorting.

### Badge
20 px, 12 px medium text, 2 px radius, soft fill, optional 12 px icon. Kinds:
ok, warn, bad, info, plain. Always text, never a bare coloured dot.

Data-quality badges map the device-database `verified` level (confirmed by A1):
Confirmed (ok), Partial (warn), Unverified (plain).

In the Alternatives table, `same_as` means a tier reuses the part number of a
named lower tier. Show it as one row spanning those tiers (for example
"Low, Mid"), not as duplicate rows. The prototype data has no such case yet.

### Key-value list
Two columns, 180 px label (muted) and value (wraps anywhere for long codes).
Used for device and package details.

### Metric row
A single bordered strip of three figures, 24 px light weight over a small label.
Used on the Power and Heat Calculations tabs for the headline results. Figures
are tabular and carry units.

### Code view (YAML)
Mono 12.5 px with a line-number gutter, scrolls inside a bordered box. Syntax
colours use tokens (key = `actionText`, string = success, number = warning,
comment = muted). An error line gets `dangerSoft` background, a wavy underline,
a red line number, and an error message under the editor ("Line 17: …").
"Apply to form" is disabled while any error remains; "Revert" restores the
saved file.

### Diff list
For the library import preview. A disclosure per group (Added, Changed, Removed,
Catalogues, Device-database files) with a count badge. Changed parts list the
field names that differ. Added and changed groups open by default only when
small. Mirrors the dry-run output of the library package work.

## Feedback

### Banner
A tinted box with a full 1 px border, an icon, a title in semibold and a
sentence, and an optional action on the right. Kinds: info, ok, warn, bad. Bad
uses `role="alert"`, the rest `role="status"`. One banner per message; never
inside a card.

### Toast
Bottom right, navy, 3.6 s, for confirmations of a completed action ("Saved
project.yaml", "Deleted GIS Substation 02. Backup saved."). Not used for errors or anything the user must act on. Announced
politely in a live region. A toast for an undoable action carries an **Undo** link
button and stays 8 s ("Pinned Gateway (pair) to panels 3 and 4").

### Dialog
Modal, 520 px wide, 4 px radius, scrim over the window. Used only when the task
needs protected focus: creating a project or substation, importing or exporting
a project file, adding a hand-written panel, choosing a move destination,
confirming a reset, a rollback or an overwrite. Anatomy: title, body, footer with
a secondary "Cancel" and a primary action named for what it does. Focus moves
to the first button on open, is trapped inside, Esc cancels, focus returns to
the trigger. A dialog never holds a form longer than five fields; use a screen
for more.

### Save bar
Fixed to the foot of the content area while a form page has unsaved changes; it has a
1 px top rule and a soft upward shadow, and spans the content width. Left: a
warning dot and "3 unsaved changes · saved to substation.yaml". Right: Discard
(secondary) and Save changes (primary, with `Ctrl+S` as a keycap). While a field is
invalid the text turns red with the error icon ("1 field needs fixing before you
can save."), Save is disabled and the text moves focus to the first invalid field.
The whole sentence is one control; "needs fixing" and "before you can save" are never
split apart. `role="region"`, labelled "Unsaved changes". Rules in [`editing.md`](editing.md).

### Changed marker (v0.2)
Marks a value that differs from the saved file until it is saved or discarded. It is a
6 px dot in `warning`, placed before the field label, or at the start of a table cell
for an edited cell, with "changed" for screen readers (`<span class="sr-only">`).
A new table row gets the dot in its first cell only. A list edited as a whole (port
groups, child parts) keeps the *Changed* badge on its heading. The control itself
keeps its normal fill and border, so an error state still reads.
- **Never the yellow.** `highlight.yellow` means "the workbook will highlight this cell
  as revised" (Preview and the sheets only, design-language "Colour"). An unsaved edit
  painted yellow would read as a revision.

### Pending bar
Like the save bar (same height, rule and shadow) with a warning dot, "3 pending changes · not applied yet.
Projects keep using 1.4.0 until you apply them.", *Discard all* (secondary) and *Review and apply…*
(primary link). Shown at the foot of the Library page while the pending set is not empty; it is a different
object from the save bar because it outlives a page and is never a leave-page warning.
`role="region"`, labelled "Pending library changes".

### Comparison list (alternatives)
A table of one device and its alternatives. The device's own row is first, tinted with the faint action
colour and labelled "This device". Numbers right-aligned in mono; each number that differs carries a **delta
chip** after it (`+5`, `−16`): a small mono chip with a sign, warning-tinted for higher and success-tinted for
lower, always with the sign so colour is never the only cue, and a `title` naming the comparison. The row
action is *Use…* with an `aria-label` that names both parts. The compact form (library pane) drops make,
ports, height and data quality, puts tier and make under the part id, and moves the chip under the number.

### Brand tabs
A tab list with one tab per brand and a *Default* badge on the default brand; beside it, a muted detail line
for the brand, *Make X the default brand* (secondary, hidden on the default) and *Add brand…* (ghost).

### Row menu
A "⋯" icon button at the end of a table row (`aria-haspopup="menu"`,
`aria-expanded`) opens a 200 px menu: Rename…, Create from this…, a rule, then
Delete… in danger colour. `role="menu"` with `menuitem` buttons; ↑ ↓ move, Enter
activates, Esc closes and returns focus to the button. The row's main action (Open)
stays visible beside it; the menu holds the rest.

### Setup card
A bordered box on a new substation's Network page: "Set up GIS Substation 01" and a list
of steps. Each step has a status icon (done: green tick, current: cobalt info,
waiting: muted), a title, one muted sentence and an action when there is one. A step
is done when its data exists; the card disappears when all are done.

### Progress
Determinate bar (6 px) with `role="progressbar"` and a step list beneath: done
(green tick), running (spinner, medium weight), waiting (muted). The step names
are the engine's stages, so the list reads as the real work.

### Empty state
A dashed box with a short heading, one or two sentences and one or two actions.
Used for first run and for lists with nothing to show, never for errors.

## Domain patterns

### Problem list row
Level badge, location (`file:line` and the field path in mono), message with the
recovery in muted text, and a "Go to field" action that opens the right screen,
tab and field. Errors sort before warnings.

### Engine result beside input
Under an input table (port plans), a footer strip reads "Engine result" with
the engine's output in mono (`=24+3 × 1000BASE-SX MM`). The UI does not compute
it; it updates after each validation run.

### Generated value
Values the engine produces (tags, derived HWIO) show in muted mono, read-only,
in the column headed "Generated …", so engineers can tell typed from derived.

### Override marker
Any input that overrides an engine rule (main MCB, HWIO points, terminal
quantities) shows a warning-coloured help line saying what it overrides and how
to return to the rule, and appears as a warning in Checks.

### Panel column (board)
232 px wide, one per generated panel, `color.surface` with a hairline border and
4 px radius; two columns of a pair sit 8 px apart, pairs 20 px apart under a
"Pair n · panels 2n−1 and 2n" label. Header: panel name (links to the panel
editor) and a side badge. Under it, the **U meter**: a 6 px bar, `action` fill,
`warning` fill when fewer than 3 U remain, with the text "21 of 32 U used · 11 U
free" (the text carries the meaning; the bar is decoration with an accessible
name). Then the **rack**: a sunken well in which 1 U is 18 px. Footer: "38 DIN-rail
parts · no rack space".

| State | Appearance |
| --- | --- |
| Drop allowed | Green border and `successSoft` fill on both columns of the target pair (or the single column for a unit). |
| Drop refused | Red border and `dangerSoft` fill; the drop still lands and the error banner gives the reason. |

### Device block
A bordered tile as tall as the device (1 U = 18 px), grip icon, name, tag in mono
when 2 U or taller (shorter tiles keep the tag in the tooltip and the accessible
name), height in U at the right. A button with `aria-pressed`: Enter or Space
selects. Draggable.

| State | Appearance |
| --- | --- |
| Default | `surface` fill, control border. |
| Selected | `actionSoft` fill, cobalt border and a 2 px ring. |
| Partner of the selection | Dashed cobalt border, `actionFaint` fill. |
| Pinned | Cobalt border and a small pin icon before the height; "pinned" in the accessible name. |
| Dragging | 45% opacity; cursor `grabbing` (`grab` when idle). |
| Drop target that fits | Panel border `success` and `successSoft` tint, plus a 3 px cobalt **insertion line** with a dot at the position the pointer is in. |
| Drop target that does not fit | Panel border `danger` and `dangerSoft` tint, cursor `not-allowed`, no insertion line. |

A device with a cable manager (switch, firewall, patch panel) is one block: the
device row on top and a 17 px "Cable manager 1 U" strip under a dashed rule, inside
the same border. It selects, drags and moves as one, and its height is the sum.

### Blank plate, free space, reserve
A blank plate is a 1 U gap with a thin rule, drawn between neighbouring devices.
It is not a BOM row. Free space is a dashed box labelled "11 U free"; the
**reserve** is a dotted box labelled "10 U kept free for expansion" at the
bottom, never available for devices.

### Selection bar
Above the board when a device is selected: name, tag, side, height; actions
"Move pair…", "Move this unit only…", "Delete pair", or "Move…" and "Delete" for a
device without a partner; a close button. When nothing is selected the line shows
a hint and the "N manual changes" disclosure, which lists each override with
Revert (or Restore for a deletion).

### Move dialog
A list of radio rows, one per destination ("Panels 3 and 4", or a single panel).
Each row shows the result ("After: 27 U and 27 U of 32 U"), or, greyed and not
selectable, the reason it does not fit. The current location is marked "(now)".
The text above says what moves: both units, or one unit and why it stays on its
side.
