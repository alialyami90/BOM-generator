# Design language

The look and feel of the bomgen desktop app. Values live in
[`tokens.json`](tokens.json); this file says how to use them. The approved
brief is [`brief.md`](brief.md).

## Principles

1. **A working tool first.** Engineers scan tables all day and non-engineers
   check results. Standard controls, an aligned grid, nothing decorative. The
   brand shows in colour, type, density and one signature move, never in
   layout or custom controls.
2. **Dense tables, calm chrome.** Table rows are 28 px so a whole cabinet BOM
   fits on one screen. Around them: generous space, plain sentences, few
   colours.
3. **Say what is wrong and what to do.** Every error names the file, the field,
   the problem and the recovery. No codes without words.
4. **Values come from the engine.** The UI never calculates a rule. It shows
   what the engine returned and where it came from (generated tags, engine
   results beside inputs).
5. **Readiness is always visible.** The user should know at any moment whether
   the project can be built, and what blocks it.

## Signature move: the readiness rail

The left navigation is the workflow (Prepare → Verify and issue), and each step
carries its own status at the right edge: a tick on Project, a count on
Panels, the active library version, `2 errors` in red on Checks, `Blocked` or
`Ready` on Build. The status bar repeats the error and warning counts and
jumps to Checks. This is the one place the world of configurators and
relay-setting tools lends something specific: a visible "selections to
complete" counter that follows you everywhere.

## Colour

Inspired by the palette of an industrial power-systems vendor's site and
software (sampled from screenshots Ali supplied): a deep navy bar, cobalt
actions, cool off-white ground, red only for problems. Inspiration only: the app
carries no vendor logo, name or trademark and must not read as that vendor's
product.

| Role | Light | Dark | Use |
| --- | --- | --- | --- |
| `bar` | navy `#003B5D` | `#05273F` | Top bar only. Never a page background. |
| `ground` | `#F2F5FA` | `#0E1B29` | Window background behind content. |
| `surface` | `#FFFFFF` | `#14263A` | Tables, forms, panels. |
| `action` | cobalt `#1A3FD8` | `#3D5CF0` | Primary buttons, switches, active selection fills. |
| `actionText` | `#1A3FD8` | `#8FA8FF` | Links, outlined buttons, focus. Lighter in dark for contrast. |
| `heading` | navy `#003B5D` | `#E6ECF4` | Headings. |
| `danger` / `warning` / `success` | red / amber / green | lighter variants | State only, always with an icon and words. |

- One saturated colour carries action (cobalt). Red, amber and green never
  decorate; they appear only on states and are always paired with an icon and
  text, so colour is never the only signal.
- Text contrast is at least 4.5:1 and control borders at least 3:1 in both
  themes (checked against the token values).
- The yellow `#FFFF00` exists only to show which cells the workbook will
  highlight as revised; it is not a UI colour.
- **Theme.** Light first. Dark uses the same roles from the `semantic.dark`
  set and follows the Windows setting unless the user picks one.

## Typography

- **Hanken Grotesk** (variable, SIL OFL 1.1), bundled. A light-to-medium
  neo-grotesque with the airy feel of the reference: light weight for screen
  titles (28 px, 300), regular body (14 px), semibold for group headings and
  column labels.
- **JetBrains Mono** (variable, SIL OFL 1.1), bundled. Only for things that are
  code or data: part ids, ordering codes, tags, quantities in inputs, YAML,
  file paths. Never as decoration.
- Numerals in tables are tabular so columns align. Numbers align right in
  tables and left in forms (right next to a unit suffix).
- Uppercase is only for table column labels, navigation group labels and
  status labels. Headings are never preceded by a small label.
- Body measure stays under about 70 characters; form columns are 720 px at most.

## Layout

- **Shell:** 48 px navy bar, 216 px navigation rail, content, 28 px status bar.
  Minimum window 1280 × 720. The content scrolls; the bar, rail and status bar
  never do.
- **Content:** left-aligned, up to 1280 px wide, 32 px side padding. Pages are
  built from sections separated by space and hairlines, not from nested cards.
  Lists of records are tables.
- **Spacing:** 4 px unit; 8, 12, 16 inside groups, 24 to 32 between groups.
- **Shape:** near-square (2 px) controls, tables and badges; 4 px dialogs and
  popovers. Round only for status dots.
- **Depth:** hairline borders carry structure. Shadows (offset and blur) appear
  only on popovers and dialogs.
- **Iconography:** one drawn set, 24 px grid, 1.5 px stroke, round caps, shown at
  16 px. No emoji or glyph characters as icons. Icon-only buttons have an
  accessible name and a tooltip.

## Motion

One authored moment: panels and dialogs rise 8 px and fade in over 240 ms with
an exponential ease-out; progress fills ease over the same time. Everything else
changes state instantly or in 100 to 160 ms. With "reduce motion" on, nothing
animates and the state change itself is the feedback.

## Voice

Plain, specific and short. Buttons name the action ("Import and activate
1.5.0", not "OK"). Errors say what is wrong and what to do next. Engineers' terms
(MCB, HWIO, SFP, BOM) are used as they appear in the spec, and the first
appearance on a screen that non-engineers see carries a short explanation in
help text or a tooltip.

## What not to do

- No vendor logo, name, product imagery or trademarked wording.
- No coloured side stripes on alerts or rows; alerts are tinted boxes with a
  full hairline border and an icon.
- No cards of equal size as a page structure, and no card inside a card.
- No gradient text, glass, decorative blur or hard offset shadows.
- No custom scrollbars, selects or checkboxes that behave differently from the
  platform; they are styled from the tokens but work the same.
- No hiding of disabled actions: show them disabled and say why.
