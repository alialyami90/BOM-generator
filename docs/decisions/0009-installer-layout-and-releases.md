# 0009. Installer layout and tag-driven releases

- Status: Proposed
- Date: 2026-10-28
- Spec sections: — (packaging is outside the spec; plan M11, Q19–Q20, ADR 0007, ADR 0008)

## Context

ADR 0007 picks PyInstaller (one folder) and an Inno Setup per-user installer,
published from CI on GitHub Releases. M11 is being built before the CLI (M1),
the library store (M8) and the window (M10) exist, so the pipeline has to work
end to end now and let those milestones plug in without touching packaging.

## Decision

- **Two executables, one folder.** `BOM Generator.exe` is windowed (no console
  flash) and is what the Start-menu shortcut and the `.bomlib` association
  open. `bomgen.exe` is the console CLI in the same folder, sharing one Python
  runtime. A windowed PyInstaller build has no stdout, so a single executable
  can't serve both.
- **Entry points live in `bomgen.app.launcher`**, not in packaging scripts, so
  they are unit-tested. `app_main` routes a single `.bomlib` argument to library
  import (M8 placeholder) and everything else to the window (M10 placeholder).
  `cli_main` answers `--version` itself (the CI smoke test relies on it) and
  hands every other argument to the typer app in `bomgen.cli` once M1 adds it.
  The spec collects every `bomgen` submodule, so new modules need no spec edits.
- **Per-user install:** `PrivilegesRequired=lowest`, no override dialog,
  installs to `%LOCALAPPDATA%\Programs\BOM Generator`, registers `.bomlib` under
  `HKCU\Software\Classes`, 64-bit Windows 10 21H2+ (Q20). Uninstall removes the
  app, shortcut and association but keeps `%LOCALAPPDATA%\bomgen\` (installed
  libraries, ADR 0008).
- **WebView2** is checked at install time and fetched with Microsoft's
  bootstrapper when missing; failure warns but doesn't block, since the CLI
  doesn't need it.
- **Releases are cut by pushing a tag `v<version>`** that must equal
  `bomgen.__version__`. `.github/workflows/release.yml` freezes, smoke-tests the
  frozen executables, compiles the installer, installs it silently, checks
  files, shortcut and registry, uninstalls and checks cleanup, then creates the
  GitHub Release with `bomgen-setup-<version>.exe` (and `default.bomlib` once M8
  produces `out/default.bomlib`). PRs touching packaging run the same build
  without publishing. Unsigned for now (Q19).
- **Build tools stay out of `pyproject.toml`**: PyInstaller is pinned in
  `packaging/requirements.txt`, so packaging doesn't widen the dev install.

## Consequences

- M1, M8 and M10 replace placeholders in `bomgen.app.launcher` only.
- The release workflow isn't in `ci-status`'s `needs` (ADR 0006); it runs only
  for packaging paths and tags, so it can't block ordinary PRs.
- Each release smoke-tests the real installer on a clean per-user profile, but
  only on the runner's Windows version.
- Until signed, users see SmartScreen on first run (`docs/install.md`).
