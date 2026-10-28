"""The library commands inside the root `bomgen` app, validating with M1's loader."""

import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bomgen.cli import app
from bomgen.library_store.package import pack

EXAMPLE_LIBRARY = Path(__file__).parents[3] / "examples" / "library.yaml"
SCHEMA_INVALID = "devices:\n  - part_id: X\n    bogus: 1\n"


@pytest.fixture
def runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    monkeypatch.setenv("BOMGEN_LIBRARY_HOME", str(tmp_path / "home"))
    return CliRunner()


def _pack_unchecked(tmp_path: Path, library: Path) -> Path:
    """A package around a library `pack` would refuse, as an old or foreign tool might make."""
    out = tmp_path / "unchecked.bomlib"
    pack(library, out, name="psa", version="1.0.0")
    return out


def _pack(runner: CliRunner, tmp_path: Path, library: Path, version: str = "1.0.0") -> Path:
    out = tmp_path / f"psa-{version}.bomlib"
    result = runner.invoke(
        app,
        ["library", "pack", str(library), "--name", "psa", "--version", version, "--out", str(out)],
    )
    assert result.exit_code == 0, result.output
    return out


def test_library_group_is_part_of_the_bomgen_app(runner: CliRunner) -> None:
    result = runner.invoke(app, ["library", "--help"])

    assert result.exit_code == 0
    for command in ("pack", "import", "list", "rollback"):
        assert command in result.output


def test_importing_the_example_library_installs_it(runner: CliRunner, tmp_path: Path) -> None:
    package = _pack(runner, tmp_path, EXAMPLE_LIBRARY)

    result = runner.invoke(app, ["library", "import", str(package)])

    assert result.exit_code == 0, result.output
    assert "Installed and activated psa 1.0.0." in result.output
    assert "psa  1.0.0 (active)" in runner.invoke(app, ["library", "list"]).output


def test_import_refuses_a_library_that_fails_schema_validation(
    runner: CliRunner, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(SCHEMA_INVALID)
    package = _pack_unchecked(tmp_path, bad)

    result = runner.invoke(app, ["library", "import", str(package)])

    assert result.exit_code == 1
    assert "error: library.yaml fails validation" in result.output
    assert "library.yaml:3: devices[0].bogus: unknown key" in result.output
    assert ".incoming" not in result.output
    assert not (tmp_path / "home").exists() or not list((tmp_path / "home").rglob("*.yaml"))


def test_dry_run_also_reports_schema_problems(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(SCHEMA_INVALID)
    package = _pack_unchecked(tmp_path, bad)

    result = runner.invoke(app, ["library", "import", str(package), "--dry-run"])

    assert result.exit_code == 1
    assert "fails validation" in result.output


def test_pack_only_carries_yaml_files_from_extra_directories(
    runner: CliRunner, tmp_path: Path
) -> None:
    device_db = tmp_path / "device-db"
    device_db.mkdir()
    (device_db / "network.yaml").write_text("a: 1\n")
    (device_db / "FINDINGS.md").write_text("notes\n")
    (device_db / "scratch.tmp").write_text("x\n")
    out = tmp_path / "db.bomlib"

    args = ["library", "pack", str(EXAMPLE_LIBRARY), "--name", "psa", "--version", "1.0.0"]
    args += ["--add", str(device_db), "--out", str(out)]

    result = runner.invoke(app, args)

    assert result.exit_code == 0, result.output
    with zipfile.ZipFile(out) as zf:
        assert sorted(zf.namelist()) == [
            "device-db/network.yaml",
            "library.yaml",
            "manifest.json",
        ]
