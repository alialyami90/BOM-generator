# 0015. Desktop app: how the UI calls the engine

- Status: Proposed
- Date: 2026-10-28
- Spec sections: — (the app is outside the spec; ADR 0007, `docs/ui/screens.md` "What the app needs from the engine")

## Context

ADR 0007 puts the M9 design in a pywebview window that calls `bomgen` in-process.
pywebview exposes every public attribute of the `js_api` object to the page and
returns results as JSON promises. An exception inside a call reaches the page as a
rejected promise with whatever text pywebview gives it, and pywebview runs each call
on its own thread. The design (`docs/ui/`) is owned by A4 and keeps evolving; the
app must not drift from it.

## Decision

- **One API class.** `bomgen.app.api.Api` is the `js_api`. Each public method is an
  endpoint; state is in private attributes. A test fails if a public attribute is
  not an endpoint.
- **Envelopes, not exceptions.** Every endpoint returns `{"ok": true, "data": …}` or
  `{"ok": false, "error": {"kind": …, "message": …}}`. `kind` is the
  `RefusalKind` value for store refusals (`already_installed`, `downgrade`,
  `project_exists`, …), `io` for file errors (such as a workbook open in Excel), and
  `internal` for anything unexpected, which is also printed to stderr. Results are
  converted to JSON (paths to strings, dataclasses and pydantic models to objects).
- **No rule in the bridge.** Endpoints call engine and store functions and reshape
  their results; anything missing goes to the owning agent, not into `app/`.
- **One JS entry.** `ui/bridge.js` is the only script that touches
  `window.pywebview.api`. `Bridge.call(name, ...args)` resolves with `data` or
  rejects with `{kind, message}`. Opened in a plain browser it rejects with
  `no_backend`, so the UI still renders for design review.
- **No server.** The window loads `ui/index.html` by `file://` URL; a bare path would
  make pywebview start a local HTTP server.
- **The UI ships inside the package** (`src/bomgen/app/ui/`, with the fonts), copied
  from `docs/ui/prototype/`. Tests require `tokens.css` and the fonts to stay
  byte-identical to `docs/ui/`, every script to be loaded, and nothing to be loaded
  from the network. Screens move from the prototype's illustrative `data.js` to
  endpoints one PR at a time (plan M10b–M10d); `data.js` and `engine-stub.js` go
  when the last screen is connected.
- **pywebview is optional.** It is the `app` extra; `bomgen.app` imports it only
  inside `run_window`, so the CLI and the frozen app's `--self-test` never need it.
  Without it, or without WebView2, `run_window` shows a message and returns 1.

## Consequences

- The UI handles every failure the same way: a banner or toast with the message,
  chosen by `kind`.
- Long calls (build, layout) block only their own pywebview thread; progress for
  Build needs a push channel (`window.evaluate_js`), decided when M10d starts.
- Design changes in `docs/ui/` reach the app by copying files; the token and font
  tests catch the shared files, screen changes are reviewed by A4.
