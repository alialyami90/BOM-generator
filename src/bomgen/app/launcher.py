"""Entry points of the frozen Windows app (plan M11, ADR 0009).

The installer ships two executables built from this module:

* ``BOM Generator.exe`` (windowed) runs :func:`app_main`. The Start-menu
  shortcut opens the window with no arguments, double-clicking a ``.bomlib`` file
  imports that library (ADR 0008), and a ``.bomproj`` file opens the window on that
  project. Starting the window on a store with no library installs the default
  library the installer shipped.
* ``bomgen.exe`` (console) runs :func:`cli_main`, the typer CLI.

The window itself is ``bomgen.app.window`` (M10), imported only when it is needed.
"""

import importlib
import os
import pkgutil
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Literal

from bomgen import __version__
from bomgen.library_store import LibraryPackageError, import_library
from bomgen.library_store.store import LibraryStore, default_library_home

APP_TITLE = "BOM Generator"
LIBRARY_SUFFIX = ".bomlib"
PROJECT_SUFFIX = ".bomproj"
MAX_SUMMARY_LINES = 20
UI_ENTRY = "bomgen/app/ui/index.html"  # the window's start page; see bomgen.app.window
NO_DIALOGS_ENV = "BOMGEN_NO_DIALOGS"  # set by unattended CI: print instead of a message box
SELF_TEST_FLAG = "--self-test"
MODULE_MANIFEST = "bomgen_modules.txt"  # written by packaging/bomgen.spec
BUNDLED_LIBRARY = Path("library") / "default.bomlib"  # beside the exe; see packaging/bomgen.iss

Action = Literal["window", "import_library", "open_project", "self_test"]


@dataclass(frozen=True)
class Launch:
    action: Action
    path: Path | None = None


def parse_args(argv: Sequence[str]) -> Launch:
    if list(argv) == [SELF_TEST_FLAG]:
        return Launch("self_test")
    if len(argv) == 1:
        suffix = PureWindowsPath(argv[0]).suffix.lower()
        if suffix == LIBRARY_SUFFIX:
            return Launch("import_library", Path(argv[0]))
        if suffix == PROJECT_SUFFIX:
            return Launch("open_project", Path(argv[0]))
    return Launch("window")


def show_message(text: str) -> None:
    if sys.platform == "win32" and not os.environ.get(NO_DIALOGS_ENV):
        import ctypes

        mb_iconinformation = 0x40
        ctypes.windll.user32.MessageBoxW(None, text, APP_TITLE, mb_iconinformation)
    else:
        print(text, file=sys.stderr)


def module_names() -> list[str]:
    """Every ``bomgen`` module that must be importable.

    From source this walks the package. Frozen, the walk would only see modules
    PyInstaller kept, so it reads the list ``bomgen.spec`` recorded at build time.
    """
    if getattr(sys, "frozen", False):
        manifest = Path(getattr(sys, "_MEIPASS", ".")) / MODULE_MANIFEST
        return manifest.read_text(encoding="utf-8").split()
    package = importlib.import_module("bomgen")
    return ["bomgen"] + [
        info.name for info in pkgutil.walk_packages(package.__path__, prefix="bomgen.")
    ]


def ui_entry_missing() -> str | None:
    """The UI start page's bundle path when the window would find nothing to show."""
    try:
        window = importlib.import_module("bomgen.app.window")
    except Exception:
        return None  # self_test reports the failed import itself
    return None if window.INDEX.is_file() else UI_ENTRY


def self_test(
    import_module: Callable[[str], object] = importlib.import_module,
) -> list[str]:
    """Import every ``bomgen`` module and check the UI is bundled; return what failed.

    Run from the frozen app (``--self-test``), this proves the bundle is complete;
    a green build otherwise says nothing about modules or UI files added later.
    """
    try:
        names = module_names()
    except OSError:
        return [MODULE_MANIFEST]
    failed: list[str] = []
    for name in names:
        try:
            import_module(name)
        except Exception:  # a broken module must be reported, not abort the test
            failed.append(name)
    if (missing := ui_entry_missing()) is not None:
        failed.append(missing)
    return sorted(set(failed))


def import_library_message(package: Path) -> tuple[str, bool]:
    """Import a double-clicked ``.bomlib``; return the message to show and whether it worked."""
    try:
        result = import_library(package)
    except LibraryPackageError as error:
        return f"Could not import {package.name}.\n\n{error}\n\n({error.kind.value})", False
    except OSError as error:  # e.g. the library folder isn't writable
        return f"Could not import {package.name}.\n\n{error}", False
    manifest = result.manifest
    heading = f"Imported library {manifest.name} {manifest.version}"
    if result.previous:
        heading += f" (was {result.previous})"
    lines = result.diff.summary_lines()
    if len(lines) > MAX_SUMMARY_LINES:
        lines = [*lines[:MAX_SUMMARY_LINES], f"... and {len(lines) - MAX_SUMMARY_LINES} more lines"]
    return "\n".join([f"{heading}.", "", *lines]), True


def install_bundled_library() -> str | None:
    """Install the installer's default library when the store has none; say why if it fails.

    A store that already holds any library is left alone, so a reinstall or an upgrade
    never replaces or downgrades what the user has.
    """
    package = Path(sys.executable).parent / BUNDLED_LIBRARY
    if not package.is_file():
        return None
    try:
        store = LibraryStore(default_library_home())
        if store.list():
            return None
        import_library(package, store=store)
    except LibraryPackageError as error:
        return f"Could not install the default device library.\n\n{error}\n\n({error.kind.value})"
    except OSError as error:  # e.g. the library folder isn't writable
        return f"Could not install the default device library.\n\n{error}"
    return None


def app_main(
    argv: Sequence[str] | None = None, notify: Callable[[str], None] = show_message
) -> int:
    launch = parse_args(sys.argv[1:] if argv is None else argv)
    if launch.action == "self_test":
        failed = self_test()
        for name in failed:
            print(f"self-test: missing or not importable: {name}", file=sys.stderr)
        return 1 if failed else 0
    if launch.action == "import_library":
        assert launch.path is not None
        message, imported = import_library_message(launch.path)
        notify(message)
        return 0 if imported else 1
    if problem := install_bundled_library():
        notify(problem)
    window = importlib.import_module("bomgen.app.window")
    return int(window.run_window(launch.path, notify))


def cli_main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--version"]:
        print(f"bomgen {__version__}")
        return 0
    try:
        cli = importlib.import_module("bomgen.cli")
    except ModuleNotFoundError as exc:
        if exc.name != "bomgen.cli":
            raise
        print("bomgen: the command line is not available in this build (plan M1).", file=sys.stderr)
        return 2
    cli.utf8_console()  # the frozen exe's console is cp1252; cli.main() isn't used here
    try:
        cli.app(args=args, prog_name="bomgen")
    except SystemExit as exc:
        if exc.code is None or isinstance(exc.code, int):
            return exc.code or 0
        print(exc.code, file=sys.stderr)
        return 1
    return 0
