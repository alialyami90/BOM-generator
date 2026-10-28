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
project (name and `document no. · Rev`), spacer, library chip, theme button,
help button. The library chip is a link to the Library screen: a status dot
(green installed, red none) plus `name version`. The theme button cycles light,
dark and system, announces the new theme, and has the current mode in its
accessible name.

| State | Behaviour |
| --- | --- |
| No project open | Project block hidden. |
| No library installed | Chip reads "No library installed", dot red. |

### Navigation rail
216 px, `color.surface`. A flat list of links in workflow order with group
labels ("Prepare", "Verify and issue"). Each item: icon, label, optional tail
status at the right edge.

| State | Appearance |
| --- | --- |
| Default | Text colour, no fill. |
| Hover | `surfaceSunken` fill. |
| Current | `actionSoft` fill, semibold heading colour, cobalt icon; `aria-current="page"`. |
| Disabled (no project) | 45% opacity, not focusable, tooltip "Open a project first". |

Tail status types: tick (complete), count (neutral), version (neutral), error
count (red with icon), `Blocked` (red), `Ready` (green). The status is text, so
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
Joined buttons, 30 px, one pressed (`action` fill). For mutually exclusive view
choices (not used on the main screens; the prototype's controls use selects).

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
move and select, Home/End jump. A tab can carry a small error badge when its
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
| Revised cell | `#FFFF00` fill with dark text, only when "Show revised cells" is on. |
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

Data-quality badges map the device-database `verified` level: Verified (ok),
Partly verified (warn), Unverified (plain). The exact levels come from the
device-database records and must be checked with that work before the UI is
built.

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
project.yaml"). Not used for errors or anything the user must act on. Announced
politely in a live region.

### Dialog
Modal, 520 px wide, 4 px radius, scrim over the window. Used only when the task
needs protected focus: opening or creating a project, mirroring or adding a
panel, confirming a rollback or an overwrite. Anatomy: title, body, footer with
a secondary "Cancel" and a primary action named for what it does. Focus moves
to the first button on open, is trapped inside, Esc cancels, focus returns to
the trigger. A dialog never holds a form longer than five fields; use a screen
for more.

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
