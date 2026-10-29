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

## B11 (2026-10-29)
- **One shared draft form, not one per screen.** `App.draftForm(o)` in `ui.js` owns the draft, the checks, the save bar, Ctrl+S and the reset on route change.
  - A screen supplies `spec(key) -> [path, kind]`, `saved`, `check`, `write` and `done`.
  - Overview, Settings, Network and the register use it. Loose material and the device editor keep their own bars because their saves are multi-step.
- **Re-render on a check reply only when the error state changes.** A render while the user types elsewhere drops their keystrokes. This caused a lost `power_margin` draft.
- **Percentages are shown as % and written as fractions rounded to 0.1%.** Use `toModel` kind `pct`.
- **An empty field means null, which removes the key.** The project or library value then applies again.
- **The model refuses equipment without its redundant L1 and L2 switches** (Substation validator). The first equipment is therefore written in one go by `start_equipment` ("Add the core switches…").
- **`git rebase origin/main` after a squash merge replays the whole branch history and conflicts.** Use the restart recipe in NEXT.md (`checkout -B`, `merge -s ours`, `cherry-pick`).
- **A grep for " passed" also matches ruff's "All checks passed!".** Wait on `" in [0-9.]*s"` when tailing pytest output.
- **`icon` is a global in the UI scripts, not an `App` member.** Destructuring it from `App` makes it undefined.
- **ISO date strings must be converted to dates before `set_field`** (`_dated()` in `api.py`). Otherwise YAML writes them as quoted text.
- **Device records (data quality) exist only for an installed library.** A project whose `library.file` points to a folder copy has none, so the UI shows no badge rather than a wrong one.

## B11 (2026-10-29, polish pass and retirement)
- **Changed vs revision.** An unsaved edit gets the orange dot (`.chg`, via `App.changedField(html)` for a form field and `App.changedCell(on)` for a table cell). The yellow `td.changed` fill means "differs from the last issued revision" and is used on Preview only. Do not mix them (polish-v02 item 1).
- **Two class attributes on one element silently drop the second.** The Network qty and L2 cells were never marked until `ch(f, cls)` merged the cell's own class with `is-changed`. Build one `class="…"` string.
- **Model error text goes through `library_edit.in_words(key, message)`** before the UI shows it. Pydantic's "Input should be a valid integer" means nothing to an engineer; add a mapping there, not in JS.
- **A list row with an empty cell is "unfinished" and is not checked until save** (`unfinished` in `screens-libedit.js`), so a half-typed row does not show errors while the user is still filling it.
- **Async click → navigation race.** A button that awaits the bridge and then opens a dialog must set `aria-busy`/`disabled` and, after the await, return if `App.route()` or the substation changed (`eq-part-change`). The hashchange handler also calls `closeDialog()` before `render()`.
- **Grid overflow.** A `minmax(0, 1fr)` track does not stop a nested grid with an implicit `auto` column from growing to its widest table. Give the nested grid `grid-template-columns: minmax(0, 1fr)` and the item `min-width: 0` (`.net-grid`), so a wide table scrolls inside its `.table-wrap`.
- **Save bar at the window bottom.** A page with a save bar is a flex column with `min-height: 100%` and the bar has `margin-top: auto`. Flex items do not collapse margins: a child's `margin-top` now adds to the previous sibling's `margin-bottom` (the device editor tab panel moved 16px; fixed by dropping its own margin). Check spacing on every page after a layout-mode change.
- **Ids never break.** Part ids and row ids are `white-space: nowrap` (`.part-line .mono`, `.table .cell-sub .mono`); a long id lets `Change…` wrap under it instead.
- **Ruff RUF001** rejects ambiguous characters such as `›` in Python strings; write `›`.
- **E2E: a dirty page opens the leave dialog** on navigation. Discard first (or answer the dialog) before `location.hash = …`, or the script times out.
- **Reviews arrive from two agents at once** (role 1 and role 4 often send the same findings). Treat them as one list, fix once, answer both in one message to role 1.
- **Measure, then claim.** Role 4 checks clipping and gaps by eye on screenshots. Before saying "fixed", measure in Playwright: a select's text width vs `clientWidth - 34`, a table's right edge vs the next column's left, `getClientRects().length > 1` for a broken id, the gap between `.savebar` and `#main`'s bottom.
