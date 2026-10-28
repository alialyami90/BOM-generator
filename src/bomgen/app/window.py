"""The desktop app's window: the M9 UI in pywebview (plan M10, ADR 0007, ADR 0015).

``bomgen.app.launcher.app_main`` calls :func:`run_window`. pywebview is imported
inside it, never at module level, so the frozen app's ``--self-test`` can import
this module where pywebview is not installed (ADR 0009).
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from bomgen.app.api import APP_TITLE, Api

UI_DIR = Path(__file__).resolve().parent / "ui"
INDEX = UI_DIR / "index.html"
WINDOW_SIZE = (1440, 900)
MIN_SIZE = (1280, 720)  # docs/ui/screens.md, "Scaling"
DEBUG_ENV = "BOMGEN_DEBUG"  # set to open the WebView2 developer tools

NO_RUNTIME = (
    "The app window could not open.\n\n{error}\n\n"
    "BOM Generator needs the Microsoft Edge WebView2 Runtime, which is part of "
    "Windows 10 and 11. If it was removed, install it from Microsoft, then start "
    "the app again. bomgen.exe in the install folder works without it."
)


def run_window(
    project_file: Path | None,
    notify: Callable[[str], None],
    webview_module: ModuleType | None = None,
) -> int:
    """Open the window and block until it closes; return the process exit code.

    ``project_file`` is the ``.bomproj`` the app was started with, if any.
    """
    try:
        webview = webview_module or importlib.import_module("webview")
    except ModuleNotFoundError as exc:
        if exc.name != "webview":
            raise
        notify(NO_RUNTIME.format(error="pywebview is not installed (pip install bomgen[app])."))
        return 1
    webview.create_window(
        APP_TITLE,
        url=INDEX.as_uri(),  # a file:// URL: a bare path would start a local HTTP server
        js_api=Api(project_file),
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=MIN_SIZE,
        text_select=True,
    )
    try:
        webview.start(debug=bool(os.environ.get(DEBUG_ENV)))
    except webview.errors.WebViewException as exc:
        notify(NO_RUNTIME.format(error=exc))
        return 1
    return 0
