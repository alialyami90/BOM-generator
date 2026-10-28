"""The desktop app's window: the M9 UI in pywebview (plan M10, ADR 0007, ADR 0015).

``bomgen.app.launcher.app_main`` calls :func:`run_window`. pywebview is imported
inside it, never at module level, so the frozen app's ``--self-test`` can import
this module where pywebview is not installed (ADR 0009).
"""

from __future__ import annotations

import importlib
import os
import platform as platform_module
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from bomgen.app.api import APP_TITLE, Api

UI_DIR = Path(__file__).resolve().parent / "ui"
INDEX = UI_DIR / "index.html"
WINDOW_SIZE = (1440, 900)  # when restored from maximized
MIN_SIZE = (1280, 720)  # docs/ui/screens.md, "Scaling"
DEBUG_ENV = "BOMGEN_DEBUG"  # set to open the WebView2 developer tools

NO_WINDOW = (
    "The app window could not open.\n\n{error}\n\n"
    "bomgen.exe in the install folder works without the window."
)
NO_WEBVIEW2 = (
    "The Microsoft Edge WebView2 Runtime was not found. BOM Generator shows its "
    "window with it; it is part of Windows 10 and 11 and is installed with the app. "
    'Install it from Microsoft (search for "WebView2 Runtime"), then start the app '
    "again."
)
NO_UI = "The app's screens are missing from this installation ({path}). Reinstall BOM Generator."

# The registry keys pywebview reads to choose Edge WebView2 over Internet Explorer
# (webview/platforms/winforms.py, _is_chromium). Without one it falls back silently.
WEBVIEW2_CLIENTS = (
    "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",  # runtime
    "{2CD8A007-E189-409D-A2C8-9AF4EF3C72AA}",  # beta
    "{0D50BFEC-CD6A-4F9A-964C-C7416E3ACB10}",  # dev
    "{65C35B14-6C1D-4122-AC46-7148CC9D6497}",  # canary
)
MIN_WEBVIEW2 = (86, 0, 622, 0)

RegistryRead = Callable[[str, str], str | None]
"""Read the ``pv`` value of a key: ``(hive name, path under it) -> value or None``."""


def read_registry_pv(hive: str, path: str) -> str | None:
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(getattr(winreg, hive), path) as key:
            value, _ = winreg.QueryValueEx(key, "pv")
    except OSError:
        return None
    return str(value)


def _version(text: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in text.split("."))
    except ValueError:
        return None


def webview2_version(
    read: RegistryRead = read_registry_pv, machine: str | None = None
) -> str | None:
    """The installed Edge WebView2 version pywebview would use, or None."""
    machine = machine or platform_module.machine()
    for client in WEBVIEW2_CLIENTS:
        for hive in ("HKEY_CURRENT_USER", "HKEY_LOCAL_MACHINE"):
            wow = "" if machine == "x86" or hive == "HKEY_CURRENT_USER" else "WOW6432Node\\"
            pv = read(hive, f"SOFTWARE\\{wow}Microsoft\\EdgeUpdate\\Clients\\{client}")
            version = _version(pv) if pv else None
            if version and version >= MIN_WEBVIEW2:
                return pv
    return None


def run_window(
    project_file: Path | None,
    notify: Callable[[str], None],
    webview_module: ModuleType | None = None,
    platform: str = sys.platform,
    find_webview2: Callable[[], str | None] = webview2_version,
) -> int:
    """Open the window and block until it closes; return the process exit code.

    ``project_file`` is the ``.bomproj`` the app was started with, if any.
    """
    if not INDEX.is_file():
        notify(NO_UI.format(path=INDEX))
        return 1
    if platform == "win32" and find_webview2() is None:
        notify(NO_WEBVIEW2)
        return 1
    try:
        webview = webview_module or importlib.import_module("webview")
    except ModuleNotFoundError as exc:
        if exc.name != "webview":
            raise
        notify(NO_WINDOW.format(error="pywebview is not installed (pip install bomgen[app])."))
        return 1
    api = Api(project_file)
    window = webview.create_window(
        APP_TITLE,
        url=INDEX.as_uri(),  # a file:// URL: a bare path would start a local HTTP server
        js_api=api,
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=MIN_SIZE,
        maximized=True,
        text_select=True,
    )
    api._set_window(window)
    try:
        webview.start(debug=bool(os.environ.get(DEBUG_ENV)))
    except webview.errors.WebViewException as exc:
        notify(NO_WINDOW.format(error=exc))
        return 1
    return 0
