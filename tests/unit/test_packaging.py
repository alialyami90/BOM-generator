"""Installer configuration invariants (plan M11, Q20; ADR 0007, 0008, 0009).

The installer itself is built and smoke-tested on the Windows runner
(``.github/workflows/release.yml``); these tests pin the settings that must
not drift.
"""

import re
from pathlib import Path

PACKAGING = Path(__file__).resolve().parents[2] / "packaging"
ISS = (PACKAGING / "bomgen.iss").read_text(encoding="utf-8")
SPEC = (PACKAGING / "bomgen.spec").read_text(encoding="utf-8")


def setup_value(key: str) -> str:
    match = re.search(rf"^{key}=(.*)$", ISS, flags=re.MULTILINE)
    assert match, f"[Setup] has no {key}"
    return match.group(1).strip()


def test_installer_is_per_user_without_admin_rights() -> None:
    assert setup_value("PrivilegesRequired") == "lowest"
    assert "PrivilegesRequiredOverridesAllowed" not in ISS
    assert setup_value("DefaultDirName").startswith("{autopf}")


def test_installer_targets_64_bit_windows_10_21h2_and_later() -> None:
    assert setup_value("ArchitecturesAllowed") == "x64compatible"
    assert setup_value("ArchitecturesInstallIn64BitMode") == "x64compatible"
    assert setup_value("MinVersion") == "10.0.19044"


def test_installer_registers_bomlib_association_for_current_user() -> None:
    assert setup_value("ChangesAssociations") == "yes"
    association = [line for line in ISS.splitlines() if "Software\\Classes" in line]
    assert any(".bomlib" in line for line in association)
    assert all(line.startswith("Root: HKA;") for line in association)
    assert all("uninsdelete" in line for line in association)
    assert '"{app}\\{#AppExeName}"" ""%1"""' in ISS


def test_installer_registers_bomproj_association_for_current_user() -> None:
    lines = [line for line in ISS.splitlines() if "Software\\Classes" in line]
    project = [line for line in lines if ".bomproj" in line or "ProjectProgId" in line]
    assert any('Subkey: "Software\\Classes\\.bomproj"' in line for line in project)
    assert any(r"Software\Classes\{#ProjectProgId}\shell\open\command" in line for line in project)
    assert all(line.startswith("Root: HKA;") for line in project)
    assert all("uninsdelete" in line for line in project)
    assert re.search(r"#define ProjectProgId \"bomgen\.project\"", ISS)


def test_each_association_opens_its_file_with_the_app() -> None:
    commands = [line for line in ISS.splitlines() if "shell\\open\\command" in line]
    assert len(commands) == 2
    assert all('"{app}\\{#AppExeName}"" ""%1"""' in line for line in commands)


def test_installer_output_name_carries_the_version() -> None:
    assert setup_value("OutputBaseFilename") == "bomgen-setup-{#AppVersion}"


def test_installer_keeps_user_libraries_on_uninstall() -> None:
    assert "[UninstallDelete]" not in ISS
    assert "{localappdata}\\bomgen" not in ISS


def test_spec_builds_windowed_app_and_console_cli_from_existing_entry_scripts() -> None:
    for script in ("entry_app.py", "entry_cli.py"):
        assert script in SPEC
        assert (PACKAGING / script).is_file()
    assert re.search(r"name=APP_EXE_NAME,.*?console=False", SPEC, flags=re.DOTALL)
    assert re.search(r'name="bomgen",.*?console=True', SPEC, flags=re.DOTALL)


def test_spec_bundles_the_ui_where_the_window_looks_for_it() -> None:
    # window.INDEX is <bomgen package>/app/ui/index.html; frozen, that is
    # <bundle>/bomgen/app/ui, which collect_data_files("bomgen.app") reproduces.
    from bomgen.app import window

    assert window.INDEX.relative_to(Path(window.__file__).parents[2]).as_posix() == (
        "bomgen/app/ui/index.html"
    )
    assert 'collect_data_files("bomgen.app"' in SPEC
    assert '"ui/' in SPEC


def test_spec_collects_pywebview_without_listing_it_in_the_self_test_manifest() -> None:
    # The manifest is imported by --self-test, which must not need pywebview's backends.
    assert 'collect_submodules("webview")' in SPEC
    assert re.search(r"hiddenimports\s*=\s*bomgen_modules\s*\+\s*webview_modules", SPEC)
    assert re.search(r"write_text\([^)]*bomgen_modules", SPEC)


def test_release_workflow_installs_the_app_extra() -> None:
    workflow = (PACKAGING.parent / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    assert 'pip install ".[app]"' in workflow


def test_release_workflow_builds_the_example_project_with_the_frozen_and_installed_cli() -> None:
    # Building loads and runs everything (models, YAML, library, engine, writer) from the
    # bundle, so a missing data file or module fails the job; validate stays as the cheap check.
    workflow = (PACKAGING.parent / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    assert (PACKAGING.parent / "examples" / "project.yaml").is_file()
    assert workflow.count("validate examples\\project.yaml") == 2
    assert workflow.count("build examples\\project.yaml --out") == 2


def test_release_workflow_has_no_variable_followed_by_a_colon() -> None:
    # PowerShell reads "$name:" as a scope prefix and the step fails to parse; write ${name}:.
    workflow = (PACKAGING.parent / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    scoped = re.findall(r"\$(?!(?:env|global|script|local):)\w+:", workflow)
    assert scoped == []
