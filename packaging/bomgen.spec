# PyInstaller spec for the Windows app (plan M11, ADR 0009).
#
# One folder, two executables sharing it:
#   BOM Generator.exe  windowed app (Start menu, .bomlib double-click)
#   bomgen.exe         console CLI
#
# Build from the repository root after `pip install . -r packaging/requirements.txt`:
#   pyinstaller packaging/bomgen.spec --noconfirm --clean
# Output: dist/bomgen/

from pathlib import Path

from PyInstaller.config import CONF
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

APP_EXE_NAME = "BOM Generator"

HERE = Path(SPECPATH)  # noqa: F821 (injected by PyInstaller)
ICON = HERE / "icons" / "bomgen.ico"
icon = [str(ICON)] if ICON.exists() else None

# bomgen.cli and later modules are imported lazily, so collect every submodule.
bomgen_modules = ["bomgen", *collect_submodules("bomgen")]
# pywebview picks its platform backend at run time (plus the hook from
# pyinstaller-hooks-contrib); install it with `pip install ".[app]"`.
webview_modules = collect_submodules("webview")
hiddenimports = bomgen_modules + webview_modules
excludes = ["tkinter"]

# The window loads bomgen/app/ui/index.html next to bomgen/app/window.py, and
# collect_submodules doesn't pick up data files, so bundle the whole ui folder
# (html, js, css, fonts) at the same package-relative path.
datas = collect_data_files("bomgen.app", includes=["ui/**/*"])

# `BOM Generator.exe --self-test` imports every bomgen module listed here (see
# bomgen.app.launcher.module_names) and every UI file the start page loads, so a module or
# UI file missing from the bundle fails the release job instead of passing unnoticed.
# pywebview's modules are not listed: its backends only import on their own platform.
manifest = Path(CONF["workpath"]) / "bomgen_modules.txt"
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text("\n".join(bomgen_modules), encoding="utf-8")
datas.append((str(manifest), "."))

app_analysis = Analysis(  # noqa: F821
    [str(HERE / "entry_app.py")], datas=datas, hiddenimports=hiddenimports, excludes=excludes
)
cli_analysis = Analysis(  # noqa: F821
    [str(HERE / "entry_cli.py")], datas=datas, hiddenimports=hiddenimports, excludes=excludes
)

app_exe = EXE(  # noqa: F821
    PYZ(app_analysis.pure),  # noqa: F821
    app_analysis.scripts,
    [],
    exclude_binaries=True,
    name=APP_EXE_NAME,
    console=False,
    icon=icon,
)
cli_exe = EXE(  # noqa: F821
    PYZ(cli_analysis.pure),  # noqa: F821
    cli_analysis.scripts,
    [],
    exclude_binaries=True,
    name="bomgen",
    console=True,
    icon=icon,
)

COLLECT(  # noqa: F821
    app_exe,
    app_analysis.binaries,
    app_analysis.datas,
    cli_exe,
    cli_analysis.binaries,
    cli_analysis.datas,
    name="bomgen",
)
