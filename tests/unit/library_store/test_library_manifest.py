"""Package manifest and version rules (ADR 0008, plan M8)."""

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from bomgen.library_store.manifest import Manifest, is_safe_member
from bomgen.library_store.versions import Version


def _manifest(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "format_version": 1,
        "name": "psa-devices",
        "version": "1.0.0",
        "schema_version": 1,
        "min_app_version": "0.0.1",
        "release_notes": "",
        "created": datetime(2026, 10, 28, tzinfo=UTC),
        "files": {"library.yaml": "0" * 64},
    }
    data.update(overrides)
    return data


def test_versions_compare_numerically() -> None:
    assert Version.parse("1.10.0") > Version.parse("1.9.0")
    assert Version.parse("2.0.0") > Version.parse("1.99.99")
    assert Version.parse("1.2.3") == Version.parse("1.2.3")
    assert str(Version.parse("1.10.0")) == "1.10.0"


@pytest.mark.parametrize("text", ["1.2", "v1.2.3", "1.2.3-beta", "", "1.2.x", "01.2.3"])
def test_version_rejects_non_semver(text: str) -> None:
    with pytest.raises(ValueError, match="version"):
        Version.parse(text)


@pytest.mark.parametrize("path", ["../x", "/x", "C:/x", "a\\b", "a/../b", "", "a//b", "./a", "a/"])
def test_unsafe_member_paths_rejected(path: str) -> None:
    assert not is_safe_member(path)


@pytest.mark.parametrize("path", ["library.yaml", "device-db/network.yaml", "assets/a b.png"])
def test_safe_member_paths_accepted(path: str) -> None:
    assert is_safe_member(path)


def test_manifest_accepts_valid_data() -> None:
    manifest = Manifest.model_validate(_manifest())
    assert manifest.parsed_version == Version.parse("1.0.0")


def test_manifest_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(_manifest(signature="abc"))


@pytest.mark.parametrize("name", ["../evil", "My Lib", "", ".hidden", "a/b"])
def test_manifest_rejects_unsafe_library_name(name: str) -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(_manifest(name=name))


def test_manifest_rejects_bad_version() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(_manifest(version="1.0"))


def test_manifest_rejects_unsafe_file_path() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(_manifest(files={"library.yaml": "0" * 64, "../x": "0" * 64}))


def test_manifest_rejects_malformed_checksum() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate(_manifest(files={"library.yaml": "abc"}))
