# UI design (M9)

Design for the Windows desktop app (ADR 0007, library updates per ADR 0008).
Status: the design is accepted and built. The first prototype was accepted (#8), reworked
for projects and substations (Home lists projects; a project holds substations and the document
register; `.bomproj` export, import and backups) with the Network screen and the Panels board
from the substations and auto-layout design
(`docs/superpowers/specs/2026-10-28-substations-and-auto-layout-design.md`), and extended for
v0.2 editing (`editing.md`). The app (M10, M16–M18, v0.2.1) implements it; where the built app
differs, `screens.md` "Departures in the built app" says so, and the prototype is not changed
to match.

## Read in this order

| File | What it holds |
|---|---|
| `brief.md` | Approved brief: audience, direction, scope, open decisions |
| `design-language.md` | Principles, the readiness rail, the panels board, colour, type, layout, motion, voice |
| `tokens.json` | Design tokens (W3C format): colour light/dark, type, space, size, radius, motion |
| `components.md` | Every component with sizes, states and accessibility notes |
| `editing.md` | v0.2 editing model: save bar, validation, create and delete rules, every editable field, library editing, loose material, back-end needs |
| `screens.md` | Screen map, flows, per-screen layout and states, what the app needs from the engine |
| `prototype/` | Clickable prototype (vanilla HTML/CSS/JS) |
| `fonts/` | Hanken Grotesk and JetBrains Mono (variable, SIL OFL 1.1, licences included) |
| `../decisions/0011-ui-design-language.md` | The ADR |

## Open the prototype

Double-click `prototype/index.html` in Edge or Chrome on a PC. No server or install.
It loads its CSS, scripts and fonts from beside it, so it shows a blank page when
opened alone from a phone or a file manager. For that, build one self-contained file:
`node docs/ui/tools/build-standalone.mjs` writes `out/ui-prototype.html` (git-ignored).
The "Prototype states" button in the status bar jumps between states (first run,
started from a `.bomproj` file, errors, clean, import outcomes, build outcomes). It is not
part of the app. All data is illustrative. Try: Home → open the project → Substations →
open GIS Substation 01 → Panels (select a device, drag it, "Move pair…", Undo, Reset to
automatic); switch to Control Building 03 in the rail for a substation with no network.
`prototype/engine-stub.js` stands in for the layout engine so the board can be tried; it is
not UI code: it applies the sizes in the layout design (32 U usable, one blank plate between neighbours, A in odd panels, B in even) just well enough to demonstrate, and the layout engine is authoritative.

## Regenerate tokens

`prototype/tokens.css` is generated from `tokens.json`:

```
node docs/ui/tools/build-tokens.mjs          # write
node docs/ui/tools/build-tokens.mjs --check  # fail if out of date
```

## Specified but not in the prototype

Ctrl+S, Ctrl+O and F6 (Ctrl+Z works on the Panels board only), the unsaved-changes dialog, overwrite confirmation, the empty
recent-projects state, Home/End in tab lists, the "Open a project first" nav
tooltip, sortable table headers, Undo after removing a device row, keyboard
reorder.

In the prototype: deep links (`#/panels/<id>/<tab>`, `#/project/<tab>`) and the
device picker keys (↑ ↓ Enter Esc). They are in `components.md` and `screens.md` and belong to M10.

## Depends on other work

- The engine contract for the board: `layout_preview(substation, overrides) -> LayoutResult`,
  a read-only `NetworkPlan`, stable equipment ids, a project import dry-run, a backups
  listing and an "opened from a .bomproj file" state (see `screens.md`, "What the app needs
  from the engine").

- Alternatives are library parts since M13 (ADR 0017); "Use this instead" on the Alternatives
  tab puts one on an equipment row (#194).
- `verified` levels are confirmed/partial/unverified; `same_as` means a tier reuses a lower tier's part number and is shown as one spanning row.
- Located errors (`file:line: path: message`) come from ADR 0010; the Checks screen
  assumes the engine returns them as data.

## Critique pass

Method: the impeccable detector (`impeccable detect --json docs/ui/prototype`)
returns no findings. A separate design review (given only the
screenshots and the brief, not this conversation) scored Nielsen's heuristics 29/40
and raised the points below. One round of fixes was applied; a second review was
not run.

Fixed: Build/Preview primary action when blocked, icon on Blocked/Ready in the rail,
Preview control overload (group select), Checks page (collapsed engine checks,
panel-first Where column), device-table drag handle and removal feedback, wrapped
dates in Versions, cabinet names in the heat table, "Saved" wording.

Fixed after review: Preview, Power and Heat render literal engine figures only; library table fits 1280 px; mirrored panels follow the input model (read-only tabs, full Mirror dialog, sample error moved to the original); deep links and picker keys; form labels now linked to their fields; hard-coded colours moved to tokens.

Not done, and why: read-only reviewer mode (needs Ali's call, see `screens.md`);
inputs only on the focused device row (kept always-editable for speed, to review
on the prototype); jump from a BOM row to its source device (needs engine
provenance data); contrast values of 12 px muted text were not measured, so M10
should run an automated contrast check.
