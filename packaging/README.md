# Packaging

Builds the per-user Windows installer (plan M11, ADR 0007, ADR 0009).

| File | What |
| --- | --- |
| `bomgen.spec` | PyInstaller spec: one folder with `BOM Generator.exe` (windowed) and `bomgen.exe` (console); records the module list `--self-test` checks |
| `entry_app.py`, `entry_cli.py` | entry scripts; the logic is in `bomgen.app.launcher` |
| `bomgen.iss` | Inno Setup script: per-user install, Start menu, `.bomlib` association, WebView2 check |
| `requirements.txt` | pinned build tools |
| `release-notes.md` | text placed at the top of each GitHub Release |
| `icons/bomgen.ico` | optional; used when present (comes with the M9 design) |

## Release

Bump `__version__` in `src/bomgen/__init__.py` and `version` in
`pyproject.toml`, merge, then push a matching tag:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

Don't cut a release tag before M1 and M10 land: until then the installed app
and CLI only show placeholder messages. `.github/workflows/release.yml` builds,
smoke-tests the install and uninstall,
and publishes the GitHub Release. Run it by hand (Actions → Release → Run
workflow) to get the installer as an artifact without releasing.

## Local build (Windows, Python 3.12, Inno Setup 6.4+)

```powershell
pip install . -r packaging/requirements.txt
pyinstaller packaging/bomgen.spec --noconfirm --clean
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=0.0.1 packaging\bomgen.iss
```

Output: `out\installer\bomgen-setup-0.0.1.exe` (`out/`, `build/` and `dist/`
are git-ignored). PyInstaller also runs on Linux and macOS for checking the
spec, but the installer is Windows-only.
