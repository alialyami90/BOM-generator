"""`bomgen library pack | import | list | rollback` (plan M8)."""

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
    assert "Added parts (51): " in result.output
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
