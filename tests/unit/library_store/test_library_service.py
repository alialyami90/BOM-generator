"""The public entry points the CLI, the launcher and the desktop app share."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bomgen.cli import app
from bomgen.library_store import LibraryPackageError, RefusalKind, import_library, validate_library
from bomgen.library_store.package import pack
from bomgen.library_store.store import LibraryStore

EXAMPLE_LIBRARY = Path(__file__).parents[3] / "examples" / "library.yaml"
SCHEMA_INVALID = "devices:\n  - part_id: X\n    bogus: 1\n"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("BOMGEN_LIBRARY_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@pytest.fixture
def example_package(tmp_path: Path) -> Path:
    out = tmp_path / "psa-1.0.0.bomlib"
    pack(EXAMPLE_LIBRARY, out, name="psa", version="1.0.0")
    return out


def test_validate_library_accepts_the_example_library() -> None:
    validate_library(EXAMPLE_LIBRARY)


def test_validate_library_reports_located_problems(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(SCHEMA_INVALID)

    with pytest.raises(LibraryPackageError) as caught:
        validate_library(bad)

    assert caught.value.kind is RefusalKind.VALIDATION_FAILED
    assert "library.yaml:3: devices[0].bogus: unknown key" in str(caught.value)
    assert str(tmp_path) not in str(caught.value)


def test_import_library_installs_into_the_default_store(home: Path, example_package: Path) -> None:
    result = import_library(example_package)

    assert result.manifest.version == "1.0.0"
    assert LibraryStore(home).active_version("psa") == "1.0.0"


def test_import_library_dry_run_installs_nothing(home: Path, example_package: Path) -> None:
    result = import_library(example_package, dry_run=True)

    assert result.diff.added
    assert not home.exists()


def test_import_library_refuses_with_a_kind(home: Path, example_package: Path) -> None:
    import_library(example_package)

    with pytest.raises(LibraryPackageError) as caught:
        import_library(example_package)
    assert caught.value.kind is RefusalKind.ALREADY_INSTALLED

    assert import_library(example_package, force=True).diff.is_empty


def test_import_library_rejects_a_schema_invalid_library(home: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(SCHEMA_INVALID)
    package = tmp_path / "bad.bomlib"
    pack(bad, package, name="psa", version="1.0.0")

    with pytest.raises(LibraryPackageError) as caught:
        import_library(package)

    assert caught.value.kind is RefusalKind.VALIDATION_FAILED
    assert not home.exists() or list(home.iterdir()) == []


def test_pack_command_refuses_a_schema_invalid_source(home: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(SCHEMA_INVALID)
    out = tmp_path / "bad.bomlib"

    result = CliRunner().invoke(
        app, ["library", "pack", str(bad), "--name", "psa", "--version", "1.0.0", "--out", str(out)]
    )

    assert result.exit_code == 1
    assert "library.yaml fails validation" in result.output
    assert not out.exists()
