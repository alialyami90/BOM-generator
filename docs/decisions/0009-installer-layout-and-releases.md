# 0009. Installer layout and releases

- Status: Accepted (Ali, 2026-10-28)
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
  they are unit-tested. `app_main` routes a single `.bomlib` argument to
  `bomgen.library_store.import_library` and shows the result (or the refusal's
  `kind` and message) in a message box, exiting 1 on a refusal. A `.bomproj`
  argument and a plain start both call `bomgen.app.window.run_window(project_file,
  notify)` (ADR 0015), which blocks until the window closes and returns the exit
  code. The double-click import installs straight away, as `bomgen library import`
  does; the window adds the preview and confirmation.
  `cli_main` answers `--version` itself (the CI smoke test relies on it) and
  hands every other argument to the typer app in `bomgen.cli` once M1 adds it.
  The spec collects every `bomgen` submodule, so new modules need no spec edits.
- **`src/bomgen/app/` is shared with M10.** `app/__init__.py` stays import-free
  (a unit test enforces it) so the launcher can start, answer `--self-test` and
  import libraries without loading pywebview. The launcher imports
  `bomgen.app.window` only when it opens the window, and `window.py` imports
  pywebview only inside `run_window`.
- **`--self-test` checks the bundle, not just the launcher.** A frozen app can
  only walk the modules PyInstaller kept, so a dropped module would pass
  unnoticed. The spec writes the source tree's module list into the bundle
  (`bomgen_modules.txt`) and `BOM Generator.exe --self-test` imports every entry,
  exiting 1 and naming the failures. CI runs it on the frozen build and again on
  the installed copy; it also runs `bomgen.exe --help`, which may exit 2 only
  while `bomgen.cli` is absent.
- **The UI ships inside the bundle.** The window loads
  `bomgen/app/ui/index.html` next to `window.py`, and PyInstaller doesn't copy
  data files by itself, so the spec bundles the whole `ui` folder with
  `collect_data_files("bomgen.app")` at the same package-relative path, and
  collects pywebview's backends as hidden imports (`pip install ".[app]"`).
  `--self-test` also fails when that start page, or any script, stylesheet or
  font it loads, is missing from the bundle, since the window would otherwise
  open blank or broken. On the Windows runner CI also starts the
  frozen app and waits for a window titled "BOM Generator"; `run_window` exits 1
  at once when the UI, WebView2 or pywebview is missing, so a broken bundle fails
  that step.
- **Per-user install:** `PrivilegesRequired=lowest`, no override dialog,
  installs to `%LOCALAPPDATA%\Programs\BOM Generator`, registers `.bomlib` and `.bomproj` under
  `HKCU\Software\Classes`, 64-bit Windows 10 21H2+ (Q20). Uninstall removes the
  app, shortcut and association but keeps `%LOCALAPPDATA%\bomgen\` (installed
  libraries, ADR 0008).
- **Unattended runs.** `BOMGEN_NO_DIALOGS=1` makes the windowed app print to stderr
  instead of showing a message box, so CI can open a `.bomlib` with the installed
  app and check the library with `bomgen.exe library list`.
- **WebView2** is checked at install time and fetched with Microsoft's
  bootstrapper when missing; failure warns but doesn't block, since the CLI
  doesn't need it.
- **Releases are cut by merging a version bump to main.** A push to main whose
  `bomgen.__version__` has no `v<version>` tag yet makes
  `.github/workflows/release.yml` freeze, smoke-test the frozen executables,
  compile the installer, install it silently, check files, shortcut and
  registry, uninstall and check cleanup, then create the tag on that commit and
  the GitHub Release with `bomgen-setup-<version>.exe` and `default.bomlib`.
  It all happens in one run with `GITHUB_TOKEN`, because a tag that token creates
  starts no other workflow; agent sessions can't push tags, so a tag-driven
  release needed Ali at a terminal (amended 2026-10-28, Ali's approval). The
  run creates nothing when the tag already exists, when the build fails, when
  `CHANGELOG.md` has no `## [<version>]` section (Ali: never release with a
  missing changelog), or when `pyproject.toml` and `__version__` disagree. A
  `v<version>` tag pushed by hand still releases that commit and must equal
  `__version__`. Release runs queue rather than cancel each other. PRs touching
  packaging run the same build without publishing. Unsigned for now (Q19).
- **The default device library ships inside the installer.** The workflow packs
  the shipped library `data/library/psa-devices.yaml` (plan Q38) plus `data/device-db` into
  `out/default.bomlib` (name and
  version are the project's `library:`), and `bomgen.iss` installs it to
  `{app}\library`. When the window starts and the library store holds no library,
  the launcher imports it through `library_store`; a store with any library is
  never touched, so a reinstall or upgrade changes nothing. A refusal or an
  unwritable folder is shown and never blocks the window. A double-clicked
  `.bomlib` skips this step.
- **Build tools stay out of `pyproject.toml`**: PyInstaller is pinned in
  `packaging/requirements.txt`, so packaging doesn't widen the dev install.

- **The example project is the smoke test.** The frozen and the installed
  `bomgen.exe` run `validate` and then `build` on `examples/project.yaml`, which
  loads every model, the YAML and the library from the bundle and writes the
  workbook, so a missing data file or module fails the job.

## Consequences

- M8b only has to teach the window what to do with a `.bomproj` file;
  both associations are registered, so the installer doesn't change again.
- The release workflow isn't in `ci-status`'s `needs` (ADR 0006); it runs only
  for packaging paths and tags, so it can't block ordinary PRs. **Never make
  `release.yml` a required check:** a path-filtered workflow reports no status on
  other PRs, so a required check would hang them.
- Every PR that changes the version is a release once merged, so a version bump
  goes in its own PR, with its changelog section, after A1 or Ali call the
  release (`packaging/README.md`).
- Each release smoke-tests the real installer on a clean per-user profile, but
  only on the runner's Windows version.
- Until signed, users see SmartScreen on first run (`docs/install.md`).
