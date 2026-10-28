"""Frozen-app entry points (plan M11); the window itself lives in bomgen.app.window (M10)."""

import ast
import importlib
import io
import sys
import types
from pathlib import Path

import pytest

import bomgen
from bomgen.app import launcher, window
from bomgen.library_store.diff import LibraryDiff
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

EXAMPLE_LIBRARY = Path(__file__).parents[2] / "examples" / "library.yaml"


def pack_example(directory: Path, version: str) -> Path:
    out = directory / f"psa-{version}.bomlib"
    pack(EXAMPLE_LIBRARY, out, name="psa", version=version)
    return out


@pytest.fixture
def library_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("BOMGEN_LIBRARY_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@pytest.fixture
def package(tmp_path: Path) -> Path:
    return pack_example(tmp_path, "1.0.0")


def test_no_arguments_opens_window() -> None:
    assert launcher.parse_args([]) == launcher.Launch("window")


def test_bomlib_argument_imports_library() -> None:
    assert launcher.parse_args([r"C:\Users\ali\Downloads\devices-1.2.bomlib"]) == (
        launcher.Launch("import_library", Path(r"C:\Users\ali\Downloads\devices-1.2.bomlib"))
    )


def test_bomlib_suffix_is_case_insensitive() -> None:
    assert launcher.parse_args(["DEVICES.BOMLIB"]).action == "import_library"


def test_other_file_argument_opens_window() -> None:
    assert launcher.parse_args(["notes.txt"]) == launcher.Launch("window")


def test_self_test_flag_runs_self_test() -> None:
    assert launcher.parse_args(["--self-test"]) == launcher.Launch("self_test")


def fake_window(
    monkeypatch: pytest.MonkeyPatch, exit_code: int = 0
) -> list[tuple[Path | None, object]]:
    calls: list[tuple[Path | None, object]] = []

    def run_window(project_file: Path | None, notify: object) -> int:
        calls.append((project_file, notify))
        return exit_code

    module = types.ModuleType("bomgen.app.window")
    module.run_window = run_window  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bomgen.app.window", module)
    return calls


def test_app_without_arguments_opens_the_window(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_window(monkeypatch)
    notify = print

    assert launcher.app_main([], notify=notify) == 0
    assert calls == [(None, notify)]


def test_app_returns_the_exit_code_of_the_window(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_window(monkeypatch, exit_code=1)

    assert launcher.app_main([], notify=print) == 1


def test_app_bomlib_imports_into_the_library_store(library_home: Path, package: Path) -> None:
    shown: list[str] = []

    assert launcher.app_main([str(package)], notify=shown.append) == 0
    assert LibraryStore(library_home).active_version("psa") == "1.0.0"
    assert len(shown) == 1
    assert "psa 1.0.0" in shown[0]
    assert "Added parts" in shown[0]


def test_app_bomlib_reimport_of_the_same_version_is_refused(
    library_home: Path, package: Path
) -> None:
    shown: list[str] = []
    assert launcher.app_main([str(package)], notify=lambda _: None) == 0

    assert launcher.app_main([str(package)], notify=shown.append) == 1
    assert "already_installed" in shown[0]


def test_app_bomlib_refusal_shows_the_kind_and_message(library_home: Path, tmp_path: Path) -> None:
    shown: list[str] = []
    broken = tmp_path / "broken.bomlib"
    broken.write_text("not a zip")

    assert launcher.app_main([str(broken)], notify=shown.append) == 1
    assert "broken.bomlib" in shown[0]
    assert "invalid_package" in shown[0]
    assert "not a zip file" in shown[0]
    assert not library_home.exists()


def test_app_bomlib_reports_a_library_folder_that_cannot_be_written(
    monkeypatch: pytest.MonkeyPatch, package: Path
) -> None:
    shown: list[str] = []

    def denied(_: Path) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr(launcher, "import_library", denied)

    assert launcher.app_main([str(package)], notify=shown.append) == 1
    assert "access denied" in shown[0]


def test_app_bomlib_refuses_a_downgrade(library_home: Path, tmp_path: Path) -> None:
    shown: list[str] = []
    newer = pack_example(tmp_path, "2.0.0")
    older = pack_example(tmp_path, "1.0.0")
    assert launcher.app_main([str(newer)], notify=lambda _: None) == 0

    assert launcher.app_main([str(older)], notify=shown.append) == 1
    assert "downgrade" in shown[0]
    assert LibraryStore(library_home).active_version("psa") == "2.0.0"


def test_app_bomlib_message_caps_a_long_change_list(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, package: Path
) -> None:
    shown: list[str] = []
    many = ["Changed parts (30):", *(f"  P{n}: unit_power_w" for n in range(30))]
    monkeypatch.setattr(LibraryDiff, "summary_lines", lambda self: many)

    launcher.app_main([str(package)], notify=shown.append)

    assert "P0: unit_power_w" in shown[0]
    assert "P29" not in shown[0]
    assert "more lines" in shown[0]


@pytest.fixture
def bundled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The default library as the installer lays it out, beside the (frozen) executable."""
    app_dir = tmp_path / "app"
    (app_dir / "library").mkdir(parents=True)
    default = pack_example(app_dir / "library", "1.0.0")
    default.rename(app_dir / "library" / "default.bomlib")
    monkeypatch.setattr(sys, "executable", str(app_dir / "BOM Generator.exe"))
    return app_dir / "library" / "default.bomlib"


def test_first_start_installs_the_bundled_default_library(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, bundled: Path
) -> None:
    fake_window(monkeypatch)
    shown: list[str] = []

    assert launcher.app_main([], notify=shown.append) == 0

    assert LibraryStore(library_home).active_version("psa") == "1.0.0"
    assert shown == []


def test_start_with_a_project_file_installs_the_bundled_library_too(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, bundled: Path, tmp_path: Path
) -> None:
    fake_window(monkeypatch)

    assert launcher.app_main([str(tmp_path / "plant.bomproj")], notify=print) == 0

    assert LibraryStore(library_home).active_version("psa") == "1.0.0"


def test_second_start_leaves_the_installed_library_unchanged(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, bundled: Path
) -> None:
    fake_window(monkeypatch)
    shown: list[str] = []
    launcher.app_main([], notify=shown.append)
    installed = LibraryStore(library_home).library_file("psa", "1.0.0")
    stamp = installed.stat().st_mtime_ns

    assert launcher.app_main([], notify=shown.append) == 0

    assert shown == []
    assert LibraryStore(library_home).versions("psa") == ["1.0.0"]
    assert installed.stat().st_mtime_ns == stamp


def test_start_never_replaces_a_library_the_user_already_has(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, bundled: Path, tmp_path: Path
) -> None:
    fake_window(monkeypatch)
    newer = tmp_path / "newer"
    newer.mkdir()
    LibraryStore(library_home).import_package(pack_example(newer, "2.0.0"))

    assert launcher.app_main([], notify=print) == 0

    store = LibraryStore(library_home)
    assert store.versions("psa") == ["2.0.0"]
    assert store.active_version("psa") == "2.0.0"


def test_start_with_another_library_installed_adds_no_default(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, bundled: Path, tmp_path: Path
) -> None:
    fake_window(monkeypatch)
    other = tmp_path / "other.bomlib"
    pack(EXAMPLE_LIBRARY, other, name="plant-devices", version="3.1.0")
    LibraryStore(library_home).import_package(other)

    launcher.app_main([], notify=print)

    assert [lib.name for lib in LibraryStore(library_home).list()] == ["plant-devices"]


def test_start_without_a_bundled_library_changes_nothing(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, tmp_path: Path
) -> None:
    fake_window(monkeypatch)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app" / "BOM Generator.exe"))
    shown: list[str] = []

    assert launcher.app_main([], notify=shown.append) == 0

    assert shown == []
    assert not library_home.exists()


def test_start_reports_a_bundled_library_that_cannot_be_installed(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, bundled: Path
) -> None:
    calls = fake_window(monkeypatch)
    bundled.write_text("not a zip")
    shown: list[str] = []

    assert launcher.app_main([], notify=shown.append) == 0

    assert len(calls) == 1  # a broken package must not stop the window
    assert "default device library" in shown[0]
    assert "invalid_package" in shown[0]
    assert not library_home.exists()


def test_start_reports_a_library_folder_that_cannot_be_written(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, bundled: Path
) -> None:
    fake_window(monkeypatch)

    def denied(*_: object, **__: object) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr(launcher, "import_library", denied)
    shown: list[str] = []

    assert launcher.app_main([], notify=shown.append) == 0
    assert "access denied" in shown[0]


def test_bomlib_double_click_does_not_install_the_bundled_library_first(
    library_home: Path, bundled: Path, tmp_path: Path
) -> None:
    mine = tmp_path / "mine"
    mine.mkdir()

    assert launcher.app_main([str(pack_example(mine, "1.0.0"))], notify=lambda _: None) == 0

    assert LibraryStore(library_home).versions("psa") == ["1.0.0"]


def test_bomproj_argument_opens_project() -> None:
    assert launcher.parse_args(["site.BOMPROJ"]) == launcher.Launch(
        "open_project", Path("site.BOMPROJ")
    )


def test_app_bomproj_opens_the_window_with_the_project_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = fake_window(monkeypatch)
    notify = print

    assert launcher.app_main(["site.bomproj"], notify=notify) == 0
    assert calls == [(Path("site.bomproj"), notify)]


def test_app_bomlib_does_not_open_the_window(
    monkeypatch: pytest.MonkeyPatch, library_home: Path, package: Path
) -> None:
    calls = fake_window(monkeypatch)

    launcher.app_main([str(package)], notify=lambda _: None)

    assert calls == []


def test_app_self_test_exits_cleanly_without_ui() -> None:
    shown: list[str] = []

    assert launcher.app_main(["--self-test"], notify=shown.append) == 0
    assert shown == []


def test_cli_version_prints_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert launcher.cli_main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"bomgen {bomgen.__version__}"


def test_cli_delegates_to_typer_app_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], str]] = []

    def fake_app(*, args: list[str], prog_name: str) -> None:
        calls.append((args, prog_name))
        raise SystemExit(3)

    fake_cli = types.ModuleType("bomgen.cli")
    fake_cli.app = fake_app  # type: ignore[attr-defined]
    fake_cli.utf8_console = lambda: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bomgen.cli", fake_cli)

    assert launcher.cli_main(["validate", "--project", "p.yaml"]) == 3
    assert calls == [(["validate", "--project", "p.yaml"], "bomgen")]


def test_cli_writes_utf8_to_a_cp1252_console(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The frozen bomgen.exe gets a cp1252 console on Windows and goes through cli_main,
    # not bomgen.cli.main(), so the launcher must switch the streams itself.
    streams = {}
    for name in ("stdout", "stderr"):
        raw = io.BytesIO()
        streams[name] = raw
        monkeypatch.setattr(sys, name, io.TextIOWrapper(raw, encoding="cp1252"))
    project = Path(__file__).resolve().parents[2] / "examples" / "project.yaml"

    code = launcher.cli_main(["build", str(project), "-o", str(tmp_path)])

    sys.stdout.flush()
    sys.stderr.flush()
    written = (streams["stdout"].getvalue() + streams["stderr"].getvalue()).decode("utf-8")
    assert code == 0
    assert "\u03a3Q" in written


def test_cli_without_cli_module_reports_it_is_pending(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setitem(sys.modules, "bomgen.cli", None)

    assert launcher.cli_main(["validate"]) == 2
    assert "not available" in capsys.readouterr().err


def test_self_test_imports_every_bomgen_submodule() -> None:
    imported: list[str] = []

    def record(name: str) -> object:
        imported.append(name)
        return importlib.import_module(name)

    assert launcher.self_test(import_module=record) == []
    assert "bomgen.app.launcher" in imported
    assert len(imported) == len(set(imported))


def test_self_test_reports_modules_that_fail_to_import() -> None:
    def fail_on_launcher(name: str) -> object:
        if name == "bomgen.app.launcher":
            raise ImportError("dropped from the bundle")
        return importlib.import_module(name)

    assert launcher.self_test(import_module=fail_on_launcher) == ["bomgen.app.launcher"]


def test_self_test_fails_when_the_ui_entry_file_is_not_in_the_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Without app/ui the window would open blank, so the bundle check names the file.
    monkeypatch.setattr(window, "INDEX", tmp_path / "ui" / "index.html")

    assert launcher.self_test() == [launcher.UI_ENTRY]


def test_self_test_passes_with_the_ui_entry_file_present() -> None:
    assert window.INDEX.is_file()
    assert launcher.UI_ENTRY == "bomgen/app/ui/index.html"
    assert launcher.self_test() == []


def test_app_self_test_fails_when_a_module_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(launcher, "self_test", lambda: ["bomgen.not_a_module"])

    assert launcher.app_main(["--self-test"], notify=lambda _: None) == 1
    assert "bomgen.not_a_module" in capsys.readouterr().err


def test_cli_prints_a_string_exit_code_and_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_app(*, args: list[str], prog_name: str) -> None:
        raise SystemExit("bad project file")

    fake_cli = types.ModuleType("bomgen.cli")
    fake_cli.app = fake_app  # type: ignore[attr-defined]
    fake_cli.utf8_console = lambda: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bomgen.cli", fake_cli)

    assert launcher.cli_main(["validate"]) == 1
    assert "bad project file" in capsys.readouterr().err


def test_app_package_init_stays_import_free() -> None:
    # M10 owns the rest of bomgen/app/; importing the package must not pull in
    # the window or its dependencies (ADR 0009).
    init = Path(launcher.__file__).with_name("__init__.py")
    tree = ast.parse(init.read_text(encoding="utf-8"))

    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]


def test_frozen_self_test_checks_the_build_time_module_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A frozen app can only walk the modules PyInstaller kept, so a dropped module
    # would never be noticed; the spec records the source tree's modules instead.
    (tmp_path / launcher.MODULE_MANIFEST).write_text(
        "bomgen\nbomgen.app.launcher\nbomgen.not_a_module\n", encoding="utf-8"
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert launcher.self_test() == ["bomgen.not_a_module"]


def test_frozen_self_test_fails_without_the_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert launcher.self_test() == [launcher.MODULE_MANIFEST]


def test_show_message_prints_instead_of_a_dialog_when_dialogs_are_disabled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # CI runs the installed app unattended; a message box would wait for a click forever.
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("BOMGEN_NO_DIALOGS", "1")

    launcher.show_message("hello")

    assert capsys.readouterr().err.strip() == "hello"
