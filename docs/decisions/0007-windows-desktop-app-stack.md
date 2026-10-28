# 0007. Windows desktop app: pywebview + PyInstaller + Inno Setup

- Status: Accepted (Ali, 2026-10-28)
- Date: 2026-10-28
- Spec sections: — (the app is outside the spec; requested by Ali in the project thread)

## Context

Ali wants the tool as a Windows package that can be installed and easily
shared, with its UI designed using the `impeccable` skill. The generator is a
Python package (ADR 0002). impeccable designs in web terms (HTML/CSS).

## Options

1. **pywebview + PyInstaller + Inno Setup** (recommended). The UI is HTML/CSS/JS
   shown in a native window through Microsoft Edge WebView2 (built into
   Windows 10/11). JavaScript calls Python functions in the same process; no
   server, no open port, works offline. The impeccable prototype becomes the
   real UI. One language for the engine and the app host.
2. PySide6 (Qt) + PyInstaller. Native widgets and mature tooling, but the
   impeccable design has to be re-expressed as Qt widgets and stylesheets, and
   Qt adds ~60–100 MB and LGPL obligations.
3. Tauri or Electron shell + Python sidecar process. Polished shells, but two
   toolchains (Rust or Node plus Python), inter-process plumbing, and a larger
   build. Electron alone adds ~100 MB.
4. Local web app opened in the browser. Simplest to build, but it isn't an
   installable app in the sense Ali asked for.

## Decision (proposed)

Option 1. Freeze with PyInstaller (one-folder mode starts faster and is less
often flagged by antivirus than one-file), and wrap in an Inno Setup per-user
installer with Start-menu shortcut, uninstaller and `.bomlib` file association.
CI builds the installer on `windows-latest` and publishes it on GitHub Releases.

## Consequences

- The UI is web tech, so impeccable's output is used directly and the same UI
  could later be served in a browser if a shared hosted version is ever wanted.
- WebView2 is present on current Windows; the installer bootstraps it when
  missing (rare on Windows 10 21H2+ and 11).
- Unsigned installers show a SmartScreen warning until we sign them (plan Q19).
