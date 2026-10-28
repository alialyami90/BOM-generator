"""The desktop app's window (plan M10, ADR 0007, ADR 0015)."""

import ast
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from bomgen.app import window
from bomgen.app.api import Api

APP_PACKAGE = Path(window.__file__).parent


class WebViewException(Exception):  # noqa: N818 (pywebview's name)
    pass


class FakeWebview(types.ModuleType):
    def __init__(self, start_error: Exception | None = None) -> None:
        super().__init__("webview")
        self.windows: list[dict[str, Any]] = []
        self.created: list[object] = []
        self.started: dict[str, Any] | None = None
        self.start_error = start_error
        self.errors = types.SimpleNamespace(WebViewException=WebViewException)

    def create_window(self, title: str, **options: Any) -> object:
        self.windows.append({"title": title, **options})
        self.created.append(object())
        return self.created[-1]

    def start(self, **options: Any) -> None:
        if self.start_error:
            raise self.start_error
        self.started = options


def run(
    fake: FakeWebview,
    project_file: Path | None = None,
    platform: str = "linux",
    webview2: str | None = "131.0.2903.70",
) -> tuple[int, list[str]]:
    shown: list[str] = []
    code = window.run_window(
        project_file,
        shown.append,
        webview_module=fake,
        platform=platform,
        find_webview2=lambda: webview2,
    )
    return code, shown


def test_window_opens_the_bundled_ui_from_disk_without_a_server() -> None:
    fake = FakeWebview()

    assert run(fake) == (0, [])
    (created,) = fake.windows
    assert created["title"] == "BOM Generator"
    assert created["url"] == (APP_PACKAGE / "ui" / "index.html").as_uri()
    assert created["url"].startswith("file://")  # a plain path makes pywebview start a server
    assert fake.started is not None
    assert fake.started.get("http_server", False) is False


def test_window_minimum_size_is_1280_by_720_and_it_opens_maximized() -> None:
    fake = FakeWebview()

    run(fake)

    assert fake.windows[0]["min_size"] == (1280, 720)
    assert fake.windows[0]["maximized"] is True


def test_missing_ui_files_notify_instead_of_opening_a_blank_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(window, "INDEX", tmp_path / "ui" / "index.html")
    fake = FakeWebview()

    code, shown = run(fake)

    assert code == 1
    assert fake.windows == []
    assert "Reinstall" in shown[0]


def test_windows_without_webview2_notifies_instead_of_falling_back_to_internet_explorer() -> None:
    fake = FakeWebview()

    code, shown = run(fake, platform="win32", webview2=None)

    assert code == 1
    assert fake.windows == []
    assert "WebView2" in shown[0]


def test_windows_with_webview2_opens_the_window() -> None:
    fake = FakeWebview()

    assert run(fake, platform="win32") == (0, [])
    assert len(fake.windows) == 1


def test_webview2_is_only_probed_on_windows() -> None:
    fake = FakeWebview()

    assert run(fake, platform="linux", webview2=None) == (0, [])


def test_window_gives_the_page_an_api_that_knows_the_opened_project_file(tmp_path: Path) -> None:
    fake = FakeWebview()
    opened = tmp_path / "eastern-province.bomproj"

    run(fake, opened)

    api = fake.windows[0]["js_api"]
    assert isinstance(api, Api)
    assert api.app_info()["data"]["project_file"] == str(opened)  # type: ignore[index]


def test_window_gives_the_api_the_window_for_file_dialogs() -> None:
    fake = FakeWebview()

    run(fake)

    assert fake.windows[0]["js_api"]._window is fake.created[0]


def test_gui_backend_failure_notifies_and_returns_1() -> None:
    # e.g. pythonnet cannot load on Windows, or no GTK/Qt elsewhere
    fake = FakeWebview(WebViewException("You must have either QT or GTK installed"))

    code, shown = run(fake)

    assert code == 1
    (message,) = shown
    assert "QT or GTK" in message


def test_missing_pywebview_notifies_and_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "webview", None)  # makes `import webview` fail
    shown: list[str] = []

    assert window.run_window(None, shown.append, platform="linux") == 1
    assert "pywebview" in shown[0]


def test_ui_entry_file_exists() -> None:
    assert window.INDEX == APP_PACKAGE / "ui" / "index.html"
    assert window.INDEX.is_file()


@pytest.mark.parametrize("module", ["__init__.py", "window.py", "api.py"])
def test_app_modules_never_import_webview_at_import_time(module: str) -> None:
    # The frozen app's --self-test imports every module, also where pywebview is absent.
    tree = ast.parse((APP_PACKAGE / module).read_text(encoding="utf-8"))
    top_level = [node for node in tree.body if isinstance(node, ast.Import | ast.ImportFrom)]
    names = [
        alias.name if isinstance(node, ast.Import) else node.module or ""
        for node in top_level
        for alias in node.names
    ]
    assert not [name for name in names if name.split(".")[0] == "webview"]


def test_app_package_init_stays_import_free() -> None:
    tree = ast.parse((APP_PACKAGE / "__init__.py").read_text(encoding="utf-8"))
    assert not [node for node in tree.body if isinstance(node, ast.Import | ast.ImportFrom)]


RUNTIME = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def registry(values: dict[tuple[str, str], str]) -> window.RegistryRead:
    return lambda hive, path: values.get((hive, path))


def test_webview2_found_in_the_machine_wide_install_on_64_bit_windows() -> None:
    path = rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{RUNTIME}"
    read = registry({("HKEY_LOCAL_MACHINE", path): "131.0.2903.70"})

    assert window.webview2_version(read, machine="AMD64") == "131.0.2903.70"


def test_webview2_found_in_the_per_user_install() -> None:
    path = rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{RUNTIME}"
    read = registry({("HKEY_CURRENT_USER", path): "130.0.2849.80"})

    assert window.webview2_version(read, machine="AMD64") == "130.0.2849.80"


@pytest.mark.parametrize("pv", [None, "0.0.0.0", "86.0.600.0", "not a version"])
def test_webview2_missing_uninstalled_or_too_old_is_not_found(pv: str | None) -> None:
    path = rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{RUNTIME}"
    read = registry({} if pv is None else {("HKEY_LOCAL_MACHINE", path): pv})

    assert window.webview2_version(read, machine="AMD64") is None
