# LESSONS: role 11, Desktop app (append-only)

## Decisions (too small for an ADR)
- **Bridge replies for edits.**
  - Decision: they are `{written, issues, page}`, where `page` is the refreshed screen (`editing.edit_reply`, whose `page` argument defaults to the board).
  - Why: one round trip per edit.
  - Rejected: re-fetching the page separately.
- **Layout moves are pre-checked.**
  - Decision: the bridge compares `layout_preview` errors before and after (`editing.layout_check`).
  - Why: `io/edit` writers accept a move the layout cannot take, because the files still load.
- **The board is read-only on hand-written panels.**
  - Why: Build ignores layout pins and deletes there (A4's #126 review). The contract is "never draw an affordance that does not act".
- **Pin here passes the unit's current position.**
  - Why: a pin without a position lets the layout move the unit within the panel (A4's review).
- **The loose page saves a draft through the writers in a fixed order: removes (descending), then sets, then adds, then host.**
  - Each written step moves the draft onto the file, so a refusal leaves the rest to save again.
  - Rejected: an ops log, because a failed op blocks replays.
- **Loose qty 1 is not written.** It is the model default, so this avoids noise in the YAML.
- **Loose fed-from on a free-text row shows "—".** ADR 0022 refuses fed_from without a part.
- **The in-cell qty message is "Enter a number, or 1 Lot."** The model accepts only an integer or "1 Lot", and A4's full sentence did not fit the cell.

## Failed approaches and what they taught
- **Dynamic bridge calls broke the guard test.** `Bridge.call(name, …)` fails `test_every_endpoint_the_screens_call_exists`, which parses literal names. Always write `Bridge.call('literal', …)`.
- **A `//` comment broke a one-line handler.** Inserted into a one-line handler, it caused "Unexpected end of input". Use `/* */` inside one-liners, and run `node --check` on every UI file.
- **A refused drop with `dropEffect = 'none'` never fires `drop`.** Keep it `'move'` and explain the refusal in the banner.
- **E2E on the example needs generated panels.** Edit `fed_from: psa3` to `psa1` first, or the layout fails with "names panel 'psa3', which the layout does not write".
- **The `pytest` and `mypy` binaries fail in this container.** Use `python -m …`.

## B11 (2026-10-28)
- **Drift at takeover:** origin/main had moved from `aad6094` to `502f564` (handoff docs only); the gate was green on main (2414 passed). The reported `check_layout` failures were an old editable install, not main: run `pip install -e ".[dev]"` in a fresh container, then `python -m pytest`.
- **A successor cannot push to its predecessor's branch.** Each session may push only to its own designated branch. Carry the open PR's commits onto your branch, add the fixes, open a replacement PR that says so, and comment on the old PR (#131 → #146).
- **Ctrl+S on a form must commit the focused field.** keydown fires before `change`, so the save ran without the typed value. Blur `document.activeElement` first.
- **Never call `App.render()` synchronously from a `change` handler.** A blur during `innerHTML` (the focused input being removed) fires `change`, and a nested render throws "Failed to set the 'innerHTML' property". Queue it with `queueMicrotask(App.render)`.
- **E2E without the window:** pack `examples/library.yaml` with `bomgen library pack … --name psa-devices --version 1.0.0` and import it into `BOMGEN_LIBRARY_HOME`, or Home shows the first-run page. The bridge stub: `page.exposeFunction('__py', …)` plus an init script setting `window.pywebview = { api: new Proxy({}, { get: (_, n) => (...a) => window.__py(n, a) }) }`, backed by a line-based Python process over `Api(env=…)`.
