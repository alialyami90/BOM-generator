"""Frozen-app entry points (plan M11; the window itself arrives in M10)."""

import ast
import importlib
import sys
import types
from pathlib import Path

import pytest

import bomgen
from bomgen.app import launcher
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


def test_app_window_shows_placeholder_until_m10() -> None:
    shown: list[str] = []

    assert launcher.app_main([], notify=shown.append) == 0
    assert len(shown) == 1
    assert "desktop app" in shown[0]


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


def test_bomproj_argument_opens_project() -> None:
    assert launcher.parse_args(["site.BOMPROJ"]) == launcher.Launch(
        "open_project", Path("site.BOMPROJ")
    )


def test_app_bomproj_shows_placeholder_until_project_export() -> None:
    shown: list[str] = []

    assert launcher.app_main(["site.bomproj"], notify=shown.append) == 0
    assert "site.bomproj" in shown[0]
    assert "after M8b" in shown[0]


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
    monkeypatch.setitem(sys.modules, "bomgen.cli", fake_cli)

    assert launcher.cli_main(["validate", "--project", "p.yaml"]) == 3
    assert calls == [(["validate", "--project", "p.yaml"], "bomgen")]


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


def test_app_self_test_fails_when_a_module_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(launcher, "self_test", lambda: ["bomgen.engine.power"])

    assert launcher.app_main(["--self-test"], notify=lambda _: None) == 1
    assert "bomgen.engine.power" in capsys.readouterr().err


def test_cli_prints_a_string_exit_code_and_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_app(*, args: list[str], prog_name: str) -> None:
        raise SystemExit("bad project file")

    fake_cli = types.ModuleType("bomgen.cli")
    fake_cli.app = fake_app  # type: ignore[attr-defined]
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
        "bomgen\nbomgen.app.launcher\nbomgen.engine.power\n", encoding="utf-8"
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert launcher.self_test() == ["bomgen.engine.power"]


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
