"""Packing and verifying `.bomlib` packages (ADR 0008, plan M8 tests)."""

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bomgen.bundle import container
from bomgen.library_store.errors import LibraryPackageError
from bomgen.library_store.package import pack, read_package

LIBRARY = b"devices:\n  - part_id: RST2228-L1-24MM\n    unit_power_w: 77\ncatalogues: {}\n"
CREATED = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)


@pytest.fixture
def library_file(tmp_path: Path) -> Path:
    path = tmp_path / "src" / "library.yaml"
    path.parent.mkdir()
    path.write_bytes(LIBRARY)
    return path


@pytest.fixture
def package_file(tmp_path: Path, library_file: Path) -> Path:
    out = tmp_path / "psa-devices-1.0.0.bomlib"
    pack(library_file, out, name="psa-devices", version="1.0.0", created=CREATED)
    return out


def _rewrite(source: Path, target: Path, members: dict[str, bytes | None]) -> Path:
    """Copy a package, replacing (bytes) or dropping (None) the named members."""
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w") as new:
        for name in old.namelist():
            if name not in members:
                new.writestr(name, old.read(name))
        for name, data in members.items():
            if data is not None:
                new.writestr(name, data)
    return target


def _with_manifest(source: Path, target: Path, **changes: object) -> Path:
    with zipfile.ZipFile(source) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    manifest.update(changes)
    return _rewrite(source, target, {"manifest.json": json.dumps(manifest).encode()})


def test_pack_then_read_round_trips(package_file: Path) -> None:
    contents = read_package(package_file)

    assert contents.manifest.name == "psa-devices"
    assert contents.manifest.version == "1.0.0"
    assert contents.manifest.created == CREATED
    assert contents.files == {"library.yaml": LIBRARY}
    assert contents.library["devices"][0]["part_id"] == "RST2228-L1-24MM"


def test_pack_is_deterministic(tmp_path: Path, library_file: Path, package_file: Path) -> None:
    again = tmp_path / "again.bomlib"
    pack(library_file, again, name="psa-devices", version="1.0.0", created=CREATED)

    assert again.read_bytes() == package_file.read_bytes()


def test_pack_carries_only_yaml_files_from_extra_directories(
    tmp_path: Path, library_file: Path
) -> None:
    device_db = tmp_path / "device-db"
    (device_db / "sub").mkdir(parents=True)
    (device_db / "network.yaml").write_text("a: 1\n")
    (device_db / "sub" / "more.yml").write_text("x\n")
    (device_db / "FINDINGS.md").write_text("notes\n")
    out = tmp_path / "with-db.bomlib"

    manifest = pack(library_file, out, name="psa-devices", version="1.1.0", extra_dirs=[device_db])

    assert sorted(manifest.files) == [
        "device-db/network.yaml",
        "device-db/sub/more.yml",
        "library.yaml",
    ]
    assert read_package(out).files["device-db/network.yaml"] == b"a: 1\n"


def test_pack_refuses_extra_directory_named_like_a_reserved_file(
    tmp_path: Path, library_file: Path
) -> None:
    reserved = tmp_path / "library.yaml.d" / "library.yaml"
    reserved.mkdir(parents=True)
    (reserved / "x.yaml").write_text("a: 1\n")

    with pytest.raises(LibraryPackageError, match="reserved"):
        pack(library_file, tmp_path / "x.bomlib", name="a", version="1.0.0", extra_dirs=[reserved])


def test_pack_refuses_invalid_library(tmp_path: Path) -> None:
    bad = tmp_path / "library.yaml"
    bad.write_text("devices: 3\n")

    with pytest.raises(LibraryPackageError, match="devices"):
        pack(bad, tmp_path / "x.bomlib", name="a", version="1.0.0")
    assert not (tmp_path / "x.bomlib").exists()


def test_tampered_file_is_rejected(tmp_path: Path, package_file: Path) -> None:
    tampered = _rewrite(package_file, tmp_path / "t.bomlib", {"library.yaml": LIBRARY + b"#\n"})

    with pytest.raises(LibraryPackageError, match=r"checksum mismatch: library\.yaml"):
        read_package(tampered)


def test_unlisted_file_is_rejected(tmp_path: Path, package_file: Path) -> None:
    extra = _rewrite(package_file, tmp_path / "e.bomlib", {"extra.yaml": b"a: 1\n"})

    with pytest.raises(LibraryPackageError, match=r"not listed in the manifest: extra\.yaml"):
        read_package(extra)


def test_missing_listed_file_is_rejected(tmp_path: Path, package_file: Path) -> None:
    missing = _rewrite(package_file, tmp_path / "m.bomlib", {"library.yaml": None})

    with pytest.raises(LibraryPackageError, match=r"missing from the package: library\.yaml"):
        read_package(missing)


def test_missing_manifest_is_rejected(tmp_path: Path, package_file: Path) -> None:
    bare = _rewrite(package_file, tmp_path / "b.bomlib", {"manifest.json": None})

    with pytest.raises(LibraryPackageError, match=r"no manifest\.json"):
        read_package(bare)


def test_invalid_manifest_is_rejected(tmp_path: Path, package_file: Path) -> None:
    bad = _rewrite(package_file, tmp_path / "b.bomlib", {"manifest.json": b"{not json"})

    with pytest.raises(LibraryPackageError, match=r"manifest\.json is invalid"):
        read_package(bad)


def test_manifest_without_library_file_is_rejected(tmp_path: Path, package_file: Path) -> None:
    no_lib = _with_manifest(package_file, tmp_path / "n.bomlib", files={})
    no_lib = _rewrite(no_lib, tmp_path / "n2.bomlib", {"library.yaml": None})

    with pytest.raises(LibraryPackageError, match=r"has no library\.yaml"):
        read_package(no_lib)


@pytest.mark.parametrize("member", ["../evil.yaml", "/abs.yaml", "dir/../../x", "a\\b.yaml"])
def test_unsafe_member_is_rejected(tmp_path: Path, package_file: Path, member: str) -> None:
    unsafe = _rewrite(package_file, tmp_path / "u.bomlib", {member: b"x"})

    with pytest.raises(LibraryPackageError, match="unsafe path"):
        read_package(unsafe)


def test_schema_version_mismatch_is_rejected(tmp_path: Path, package_file: Path) -> None:
    newer = _with_manifest(package_file, tmp_path / "s.bomlib", schema_version=2)

    with pytest.raises(LibraryPackageError, match="schema version 2"):
        read_package(newer)


def test_newer_min_app_version_is_rejected(tmp_path: Path, package_file: Path) -> None:
    newer = _with_manifest(package_file, tmp_path / "a.bomlib", min_app_version="9.0.0")

    with pytest.raises(LibraryPackageError, match=r"needs bomgen 9\.0\.0 or later"):
        read_package(newer, app_version="1.0.0")


def test_not_a_zip_is_rejected(tmp_path: Path) -> None:
    junk = tmp_path / "junk.bomlib"
    junk.write_text("hello")

    with pytest.raises(LibraryPackageError, match=r"not a \.bomlib package"):
        read_package(junk)


def test_missing_package_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(LibraryPackageError, match="cannot open"):
        read_package(tmp_path / "nope.bomlib")


def test_oversized_package_is_rejected(monkeypatch: pytest.MonkeyPatch, package_file: Path) -> None:
    monkeypatch.setattr(container, "MAX_UNCOMPRESSED_BYTES", 10)

    with pytest.raises(LibraryPackageError, match="too large"):
        read_package(package_file)


def test_future_format_version_asks_for_a_newer_bomgen(tmp_path: Path, package_file: Path) -> None:
    future = _with_manifest(package_file, tmp_path / "f.bomlib", format_version=2)

    with pytest.raises(LibraryPackageError, match="newer bomgen"):
        read_package(future)


def test_corrupt_compressed_data_is_rejected(tmp_path: Path, package_file: Path) -> None:
    data = bytearray(package_file.read_bytes())
    # Damage the deflate stream of the first stored member (manifest.json).
    start = 30 + len(b"manifest.json") + 4
    data[start : start + 8] = b"\xff" * 8
    broken = tmp_path / "broken.bomlib"
    broken.write_bytes(bytes(data))

    with pytest.raises(LibraryPackageError):
        read_package(broken)


def test_directory_entries_from_other_zip_tools_are_ignored(
    tmp_path: Path, package_file: Path
) -> None:
    with zipfile.ZipFile(package_file) as old, zipfile.ZipFile(tmp_path / "d.bomlib", "w") as new:
        new.writestr("assets/", b"")
        for name in old.namelist():
            new.writestr(name, old.read(name))

    assert read_package(tmp_path / "d.bomlib").files == {"library.yaml": LIBRARY}


def test_members_that_differ_only_by_case_are_rejected_when_packing(
    tmp_path: Path, library_file: Path
) -> None:
    extra = tmp_path / "db"
    (extra / "A").mkdir(parents=True)
    (extra / "a").mkdir()
    (extra / "A" / "x.yaml").write_text("1\n")
    (extra / "a" / "x.yaml").write_text("2\n")
    if len({p.name for p in extra.iterdir()}) < 2:  # case-insensitive file system
        pytest.skip("file system folds case")

    with pytest.raises(LibraryPackageError, match="differ only by case"):
        pack(library_file, tmp_path / "c.bomlib", name="a", version="1.0.0", extra_dirs=[extra])


def test_a_bomproj_given_to_library_import_is_explained(tmp_path: Path) -> None:
    project = tmp_path / "p.bomproj"
    manifest = {"format_version": 1, "project_id": "jfgp2", "files": {}}
    with zipfile.ZipFile(project, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))

    with pytest.raises(LibraryPackageError, match=r"\.bomproj project.*bomgen project import"):
        read_package(project)
