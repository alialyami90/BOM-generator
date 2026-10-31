"""`bomgen library pack | import | list | export | rollback` (plan M8)."""

import zipfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from bomgen.library_store.cli import library_app

EXAMPLE = Path(__file__).parents[3] / "examples" / "library.yaml"


def _library(extra_part: str, spool_make: str = "Hubbell") -> str:
    """The example library plus one extra component, with the spool's make adjustable."""
    library = yaml.safe_load(EXAMPLE.read_text())
    for device in library["devices"]:
        if device["part_id"] == "FOPP-SPOOL":
            device["make"] = spool_make
    library["devices"].append(
        {"part_id": extra_part, "category": "component", "description_template": extra_part}
    )
    return yaml.safe_dump(library, sort_keys=False)


V1 = _library("PART-OLD")
V2 = _library("PART-NEW", spool_make="Panduit")


@pytest.fixture
def runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.setenv("BOMGEN_LIBRARY_HOME", str(tmp_path / "home"))
    return CliRunner()


def _pack(runner: CliRunner, tmp_path: Path, version: str, library: str, *extra: str) -> Path:
    source = tmp_path / f"library-{version}.yaml"
    source.write_text(library)
    out = tmp_path / f"psa-devices-{version}.bomlib"
    args = ["pack", str(source), "--name", "psa-devices", "--version", version, "--out", str(out)]
    result = runner.invoke(library_app, [*args, *extra])
    assert result.exit_code == 0, result.output
    return out


def test_cli_pack_import_list_rollback(runner: CliRunner, tmp_path: Path) -> None:
    v1 = _pack(runner, tmp_path, "1.0.0", V1)
    v2 = _pack(runner, tmp_path, "1.1.0", V2, "--notes", "SW power corrected")

    assert runner.invoke(library_app, ["import", str(v1)]).exit_code == 0
    imported = runner.invoke(library_app, ["import", str(v2)])
    assert imported.exit_code == 0, imported.output
    assert "psa-devices 1.1.0 (active was 1.0.0)" in imported.output
    assert "SW power corrected" in imported.output
    assert "Added parts (1): PART-NEW" in imported.output
    assert "Removed parts (1): PART-OLD" in imported.output
    assert "FOPP-SPOOL: make" in imported.output

    listed = runner.invoke(library_app, ["list"])
    assert listed.exit_code == 0
    assert "psa-devices  1.1.0 (active)  installed: 1.0.0, 1.1.0" in listed.output

    rolled = runner.invoke(library_app, ["rollback", "psa-devices"])
    assert rolled.exit_code == 0
    assert "psa-devices 1.0.0 is now active" in rolled.output


def test_cli_pack_defaults_output_name(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "library.yaml").write_text(V1)

    result = runner.invoke(
        library_app, ["pack", "library.yaml", "--name", "psa-devices", "--version", "2.0.0"]
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "psa-devices-2.0.0.bomlib").is_file()


def test_cli_pack_adds_extra_directories(runner: CliRunner, tmp_path: Path) -> None:
    extras = tmp_path / "extras"
    extras.mkdir()
    (extras / "network.yaml").write_text("a: 1\n")

    package = _pack(runner, tmp_path, "1.0.0", V1, "--add", str(extras))

    with zipfile.ZipFile(package) as zf:
        assert "extras/network.yaml" in zf.namelist()


def test_cli_import_dry_run_installs_nothing(runner: CliRunner, tmp_path: Path) -> None:
    package = _pack(runner, tmp_path, "1.0.0", V1)

    result = runner.invoke(library_app, ["import", str(package), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "Added parts (331): " in result.output
    assert "Dry run: nothing was installed." in result.output
    assert not (tmp_path / "home").exists()


def test_cli_rejects_tampered_package_with_exit_1(runner: CliRunner, tmp_path: Path) -> None:
    package = _pack(runner, tmp_path, "1.0.0", V1)
    tampered = tmp_path / "tampered.bomlib"
    with zipfile.ZipFile(package) as old, zipfile.ZipFile(tampered, "w") as new:
        for name in old.namelist():
            data = old.read(name)
            new.writestr(name, data + b"#\n" if name == "library.yaml" else data)

    result = runner.invoke(library_app, ["import", str(tampered)])

    assert result.exit_code == 1
    assert "error: checksum mismatch: library.yaml" in result.output


def test_cli_downgrade_needs_force(runner: CliRunner, tmp_path: Path) -> None:
    newer = _pack(runner, tmp_path, "2.0.0", V2)
    older = _pack(runner, tmp_path, "1.0.0", V1)
    runner.invoke(library_app, ["import", str(newer)])

    refused = runner.invoke(library_app, ["import", str(older)])
    forced = runner.invoke(library_app, ["import", str(older), "--force"])

    assert refused.exit_code == 1
    assert "older than the active 2.0.0" in refused.output
    assert forced.exit_code == 0, forced.output


def test_cli_list_of_empty_store(runner: CliRunner) -> None:
    result = runner.invoke(library_app, ["list"])

    assert result.exit_code == 0
    assert "No libraries installed." in result.output


def test_cli_prints_the_remedy_for_an_inactive_reinstall(runner: CliRunner, tmp_path: Path) -> None:
    v1 = _pack(runner, tmp_path, "1.0.0", V1)
    v2 = _pack(runner, tmp_path, "1.1.0", V2)
    runner.invoke(library_app, ["import", str(v1)])
    runner.invoke(library_app, ["import", str(v2)])

    result = runner.invoke(library_app, ["import", str(v1)])

    assert result.exit_code == 1
    assert "error: library psa-devices 1.0.0 is installed but not active" in result.output
    assert "hint: run: bomgen library rollback psa-devices --to 1.0.0" in result.output


def test_cli_export_writes_a_backup_of_the_active_version(
    runner: CliRunner, tmp_path: Path
) -> None:
    runner.invoke(library_app, ["import", str(_pack(runner, tmp_path, "1.0.0", V1))])
    out = tmp_path / "backup.bomlib"

    result = runner.invoke(library_app, ["export", "psa-devices", "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert "psa-devices 1.0.0" in result.output
    assert out.is_file()
    again = runner.invoke(library_app, ["import", str(out), "--dry-run", "--force"])
    assert again.exit_code == 0, again.output


def test_cli_export_defaults_the_file_name_and_names_a_missing_version(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner.invoke(library_app, ["import", str(_pack(runner, tmp_path, "1.0.0", V1))])
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(library_app, ["export", "psa-devices"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "psa-devices-1.0.0.bomlib").is_file()
    missing = runner.invoke(library_app, ["export", "psa-devices", "--version", "9.9.9"])
    assert missing.exit_code == 1
    assert "9.9.9 is not installed" in missing.output


def test_cli_export_csv_writes_the_tables_as_a_zip_or_a_folder(
    runner: CliRunner, tmp_path: Path
) -> None:
    runner.invoke(library_app, ["import", str(_pack(runner, tmp_path, "1.0.0", V1))])
    zipped = tmp_path / "tables.zip"
    folder = tmp_path / "tables"

    first = runner.invoke(library_app, ["export-csv", "psa-devices", "--out", str(zipped)])
    second = runner.invoke(
        library_app,
        ["export-csv", "psa-devices", "--out", str(folder), "--tables", "catalogues"],
    )

    assert first.exit_code == 0, first.output
    with zipfile.ZipFile(zipped) as archive:
        assert "devices.csv" in archive.namelist()
    assert second.exit_code == 0, second.output
    assert (folder / "mcb.csv").is_file()
    assert not (folder / "devices.csv").exists()


def test_cli_export_csv_names_a_bad_table_group(runner: CliRunner, tmp_path: Path) -> None:
    runner.invoke(library_app, ["import", str(_pack(runner, tmp_path, "1.0.0", V1))])

    result = runner.invoke(
        library_app,
        ["export-csv", "psa-devices", "--out", str(tmp_path / "x"), "--tables", "nonsense"],
    )

    assert result.exit_code == 1
    assert "unknown table group nonsense" in result.output


def _csv_tables(runner: CliRunner, tmp_path: Path) -> Path:
    runner.invoke(library_app, ["import", str(_pack(runner, tmp_path, "1.0.0", V1))])
    folder = tmp_path / "tables"
    result = runner.invoke(library_app, ["export-csv", "psa-devices", "--out", str(folder)])
    assert result.exit_code == 0, result.output
    return folder


def test_cli_import_csv_saves_the_edited_rows_as_a_local_version(
    runner: CliRunner, tmp_path: Path
) -> None:
    folder = _csv_tables(runner, tmp_path)
    devices = folder / "devices.csv"
    devices.write_text(
        devices.read_text("utf-8-sig").replace("Panduit", "Acme").replace("Hubbell", "Acme"),
        "utf-8-sig",
    )

    dry = runner.invoke(library_app, ["import-csv", "psa-devices", str(folder), "--dry-run"])
    done = runner.invoke(
        library_app, ["import-csv", "psa-devices", str(folder), "--notes", "from Excel"]
    )

    assert dry.exit_code == 0, dry.output
    assert "[ok] Files are readable tables" in dry.output
    assert "Dry run: nothing was saved." in dry.output
    assert done.exit_code == 0, done.output
    assert "Saved and activated psa-devices 1.0.0+local.1 (from 1.0.0)." in done.output
    listing = runner.invoke(library_app, ["list"])
    assert "1.0.0+local.1 (active)" in listing.output


def test_cli_import_csv_refuses_rows_with_problems_unless_told_to_skip_them(
    runner: CliRunner, tmp_path: Path
) -> None:
    folder = _csv_tables(runner, tmp_path)
    devices = folder / "devices.csv"
    lines = devices.read_text("utf-8-sig").splitlines()
    header = lines[0].split(",")
    cells = lines[2].split(",")
    cells[header.index("voltage_v")] = "abc"
    lines[2] = ",".join(cells)
    lines[3] = lines[3].replace("Hubbell", "Acme").replace("Panduit", "Acme")
    devices.write_text("\r\n".join(lines) + "\r\n", "utf-8-sig")

    refused = runner.invoke(library_app, ["import-csv", "psa-devices", str(folder)])
    dry = runner.invoke(library_app, ["import-csv", "psa-devices", str(folder), "--dry-run"])

    assert refused.exit_code == 1
    assert "devices.csv row 3, voltage_v" in refused.output
    assert dry.exit_code == 1
    assert "[failed] Every row reads cleanly" in dry.output


def test_cli_import_csv_with_nothing_to_change_says_so(runner: CliRunner, tmp_path: Path) -> None:
    folder = _csv_tables(runner, tmp_path)

    result = runner.invoke(library_app, ["import-csv", "psa-devices", str(folder)])

    assert result.exit_code == 1
    assert "nothing differs from 1.0.0" in result.output


def test_cli_pack_creates_the_folder_of_the_package_file(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "backups" / "2026" / "psa.bomlib"

    _pack(runner, tmp_path, "1.0.0", V1, "--out", str(out))

    assert out.is_file()


def test_cli_pack_into_an_unusable_folder_is_a_clean_error(
    runner: CliRunner, tmp_path: Path
) -> None:
    source = tmp_path / "library.yaml"
    source.write_text(V1)
    blocker = tmp_path / "taken"
    blocker.write_text("a file, not a folder")
    args = ["pack", str(source), "--name", "psa-devices", "--version", "1.0.0"]

    result = runner.invoke(library_app, [*args, "--out", str(blocker / "psa.bomlib")])

    assert result.exit_code == 1
    assert "error: cannot write" in result.output
    assert "Traceback" not in result.output
    assert "Errno" not in result.output
