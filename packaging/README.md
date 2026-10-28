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

Bump `__version__` in `src/bomgen/__init__.py` and `version` in
`pyproject.toml`, merge, then push a matching tag:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

Don't cut a release tag until M10 is finished and A1 or Ali say so: the window
works but the screens are still being wired to the engine. `.github/workflows/release.yml`
builds, smoke-tests the install, uninstall and window start,
and publishes the GitHub Release. Run it by hand (Actions → Release → Run
workflow) to get the installer as an artifact without releasing.

## Local build (Windows, Python 3.12, Inno Setup 6.4+)

```powershell
pip install ".[app]" -r packaging/requirements.txt
pyinstaller packaging/bomgen.spec --noconfirm --clean
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=0.1.0 packaging\bomgen.iss
```

Output: `out\installer\bomgen-setup-0.1.0.exe` (`out/`, `build/` and `dist/`
are git-ignored). PyInstaller also runs on Linux and macOS for checking the
spec, but the installer is Windows-only.
