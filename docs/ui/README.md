# UI design (M9)

Design for the Windows desktop app (ADR 0007, library updates per ADR 0008).
Design only: the app itself is M10. Status: ready for Ali's review.

## Read in this order

| File | What it holds |
|---|---|
| `brief.md` | Approved brief: audience, direction, scope, open decisions |
| `design-language.md` | Principles, the readiness rail, colour, type, layout, motion, voice |
| `tokens.json` | Design tokens (W3C format): colour light/dark, type, space, size, radius, motion |
| `components.md` | Every component with sizes, states and accessibility notes |
| `screens.md` | Screen map, flows, per-screen layout and states, what the app needs from the engine |
| `prototype/` | Clickable prototype (vanilla HTML/CSS/JS) |
| `fonts/` | Hanken Grotesk and JetBrains Mono (variable, SIL OFL 1.1, licences included) |
| `../decisions/0011-ui-design-language.md` | The ADR |

## Open the prototype

Double-click `prototype/index.html` in Edge or Chrome. No server or install.
The "Prototype states" button in the status bar jumps between states (empty
library, errors, clean, import outcomes, build outcomes). It is not part of the app.
All data is illustrative.

## Regenerate tokens

`prototype/tokens.css` is generated from `tokens.json`:

```
node docs/ui/tools/build-tokens.mjs          # write
node docs/ui/tools/build-tokens.mjs --check  # fail if out of date
```

## Specified but not in the prototype

Ctrl+S, Ctrl+O and F6, the unsaved-changes dialog, overwrite confirmation, the empty
recent-projects state, Home/End in tab lists, the "Open a project first" nav
tooltip, sortable table headers, Undo after removing a device row, keyboard
reorder.

In the prototype: deep links (`#/panels/<id>/<tab>`, `#/project/<tab>`) and the
device picker keys (↑ ↓ Enter Esc). They are in `components.md` and `screens.md` and belong to M10.

## Depends on other work

- Alternatives are browse-only. Swapping a part needs a schema change (A2) and data (A3).
- `verified` levels are confirmed/partial/unverified; `same_as` means a tier reuses a lower tier's part number and is shown as one spanning row (confirmed by A1).
- Located errors (`file:line: path: message`) come from ADR 0010; the Checks screen
  assumes the engine returns them as data.

## Critique pass

Method: the impeccable detector (`impeccable detect --json docs/ui/prototype`)
returns no findings. A separate design review (a sub-agent that was given only the
screenshots and the brief, not this conversation) scored Nielsen's heuristics 29/40
and raised the points below. One round of fixes was applied; a second review was
not run.

Fixed: Build/Preview primary action when blocked, icon on Blocked/Ready in the rail,
Preview control overload (group select), Checks page (collapsed engine checks,
panel-first Where column), device-table drag handle and removal feedback, wrapped
dates in Versions, cabinet names in the heat table, "Saved" wording.

Fixed after A1's review: Preview, Power and Heat render literal engine figures only; library table fits 1280 px; mirrored panels follow A2's model (read-only tabs, full Mirror dialog, sample error moved to the original); deep links and picker keys; form labels now linked to their fields; hard-coded colours moved to tokens.

Not done, and why: read-only reviewer mode (needs Ali's call, see `screens.md`);
inputs only on the focused device row (kept always-editable for speed, to review
on the prototype); jump from a BOM row to its source device (needs engine
provenance data); contrast values of 12 px muted text were not measured, so M10
should run an automated contrast check.
