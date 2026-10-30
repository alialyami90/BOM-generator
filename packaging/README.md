# Packaging

Builds the per-user Windows installer (plan M11, ADR 0007, ADR 0009).

| File | What |
| --- | --- |
| `bomgen.spec` | PyInstaller spec: one folder with `BOM Generator.exe` (windowed) and `bomgen.exe` (console); bundles the UI and pywebview, and records the module list `--self-test` checks |
| `entry_app.py`, `entry_cli.py` | entry scripts; the logic is in `bomgen.app.launcher` |
| `bomgen.iss` | Inno Setup script: per-user install, Start menu, `.bomlib` and `.bomproj` associations, WebView2 check |
| `requirements.txt` | pinned build tools |
| `release-notes.md` | text placed at the top of each GitHub Release |
| `icons/bomgen.ico` | optional; used when present (comes with the M9 design) |

## Release

A release is two ordinary PRs; nobody pushes a tag (ADR 0009; the steps in
detail are in `docs/handoff/STATE.md`, "How a release happens").

1. A docs PR moves the `[Unreleased]` entries in `CHANGELOG.md` under
   `## [<version>] - <date>` and updates the compare links.
2. After it merges, a bump PR sets the new version in `__version__`
   (`src/bomgen/__init__.py`), `version` in `pyproject.toml` and
   `tests/test_package.py`, and nothing else. Merging it publishes.
3. On that push to main, `.github/workflows/release.yml` sees that
   `v<version>` doesn't exist yet. It builds and smoke-tests the installer
   (install, window start, first-start library, build of the example,
   uninstall), then creates the tag on the tested commit and the GitHub Release
   with `bomgen-setup-<version>.exe` and `default.bomlib`.

The run refuses to release, and creates nothing, when `CHANGELOG.md` has no
section for the version or `pyproject.toml` and `__version__` disagree; a
failed build creates nothing either. Pushes to main that keep the version end
after the first job. A version with a letter (`0.2.0rc1`) is published as a
pre-release.

Pushing a `v<version>` tag by hand, or publishing a release in the GitHub UI,
still works: the same run builds that commit and attaches the installer. Run
the workflow by hand (Actions → Release → Run workflow) to get the installer as
an artifact without releasing.

## Local build (Windows, Python 3.12, Inno Setup 6.4+)

```powershell
pip install ".[app]" -r packaging/requirements.txt
pyinstaller packaging/bomgen.spec --noconfirm --clean
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=<version> packaging\bomgen.iss
```

Output: `out\installer\bomgen-setup-<version>.exe` (`out/`, `build/` and `dist/`
are git-ignored). PyInstaller also runs on Linux and macOS for checking the
spec, but the installer is Windows-only.
