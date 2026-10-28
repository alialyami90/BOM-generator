"""Entry points of the frozen Windows app (plan M11, ADR 0009).

The installer ships two executables built from this module:

* ``BOM Generator.exe`` (windowed) runs :func:`app_main`. The Start-menu
  shortcut opens it with no arguments, and double-clicking a ``.bomlib`` file
  opens it with that file (ADR 0008).
* ``bomgen.exe`` (console) runs :func:`cli_main`, the typer CLI.

The window (M10) and library import (M8) are placeholders until those
milestones land; only their hand-off points live here.
"""

import importlib
import pkgutil
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Literal

from bomgen import __version__

APP_TITLE = "BOM Generator"
LIBRARY_SUFFIX = ".bomlib"
SELF_TEST_FLAG = "--self-test"
MODULE_MANIFEST = "bomgen_modules.txt"  # written by packaging/bomgen.spec

Action = Literal["window", "import_library", "self_test"]


@dataclass(frozen=True)
class Launch:
    action: Action
    path: Path | None = None


def parse_args(argv: Sequence[str]) -> Launch:
    if list(argv) == [SELF_TEST_FLAG]:
        return Launch("self_test")
    if len(argv) == 1 and PureWindowsPath(argv[0]).suffix.lower() == LIBRARY_SUFFIX:
        return Launch("import_library", Path(argv[0]))
    return Launch("window")


def show_message(text: str) -> None:
    if sys.platform == "win32":
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


def self_test(
    import_module: Callable[[str], object] = importlib.import_module,
) -> list[str]:
    """Import every ``bomgen`` module and return the names that failed.

    Run from the frozen app (``--self-test``), this proves the bundle is complete;
    a green build otherwise says nothing about modules added by later milestones.
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
    return sorted(set(failed))


def app_main(
    argv: Sequence[str] | None = None, notify: Callable[[str], None] = show_message
) -> int:
    launch = parse_args(sys.argv[1:] if argv is None else argv)
    if launch.action == "self_test":
        failed = self_test()
        for name in failed:
            print(f"self-test: cannot import {name}", file=sys.stderr)
        return 1 if failed else 0
    if launch.action == "import_library":
        assert launch.path is not None
        notify(f"Importing library packages is not available yet (plan M8).\n\n{launch.path.name}")
        return 0
    notify(
        f"{APP_TITLE} {__version__}\n\n"
        "The desktop app is not available yet (plan M10). "
        "Use bomgen.exe in the install folder from a terminal."
    )
    return 0


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
    try:
        cli.app(args=args, prog_name="bomgen")
    except SystemExit as exc:
        if exc.code is None or isinstance(exc.code, int):
            return exc.code or 0
        print(exc.code, file=sys.stderr)
        return 1
    return 0
