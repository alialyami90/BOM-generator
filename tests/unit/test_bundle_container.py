"""The zip container shared by .bomlib and .bomproj packages."""

import os
import zipfile
from pathlib import Path, PurePosixPath

import pytest
from pydantic import BaseModel, ConfigDict

from bomgen.bundle import container
from bomgen.bundle.checks import CheckStatus
from bomgen.bundle.container import (
    collect_tree,
    inspect_bundle,
    read_bundle,
    sha256,
    write_bundle,
)
from bomgen.bundle.errors import LibraryPackageError, RefusalKind


class _Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    files: dict[str, str]


def _parse(raw: object) -> _Manifest:
    return _Manifest.model_validate(raw)


def _write(tmp_path: Path, files: dict[str, bytes]) -> Path:
    out = tmp_path / "x.bundle"
    manifest = _Manifest(files={name: sha256(data) for name, data in files.items()})
    write_bundle(out, manifest, files)
    return out


def _tree(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def test_bundle_round_trips_and_is_deterministic(tmp_path: Path) -> None:
    files = {"a.yaml": b"a: 1\n", "sub/b.bin": b"\x00\x01"}
    first = _write(tmp_path, files)
    second = tmp_path / "again.bundle"
    write_bundle(second, _Manifest(files={n: sha256(d) for n, d in files.items()}), files)

    manifest, contents = read_bundle(first, _parse, "test bundle")

    assert contents == files
    assert manifest.files["a.yaml"] == sha256(b"a: 1\n")
    assert first.read_bytes() == second.read_bytes()


def test_read_bundle_names_what_it_expected(tmp_path: Path) -> None:
    junk = tmp_path / "junk"
    junk.write_text("no")

    with pytest.raises(LibraryPackageError, match="not a test bundle"):
        read_bundle(junk, _parse, "test bundle")


def test_read_bundle_rejects_a_changed_file(tmp_path: Path) -> None:
    good = _write(tmp_path, {"a.yaml": b"a: 1\n"})
    bad = tmp_path / "bad.bundle"
    with zipfile.ZipFile(good) as old, zipfile.ZipFile(bad, "w") as new:
        for name in old.namelist():
            new.writestr(name, b"changed" if name == "a.yaml" else old.read(name))

    with pytest.raises(LibraryPackageError, match=r"checksum mismatch: a\.yaml"):
        read_bundle(bad, _parse, "test bundle")


def test_read_bundle_enforces_the_size_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write(tmp_path, {"a.yaml": b"a: 1\n"})
    monkeypatch.setattr(container, "MAX_UNCOMPRESSED_BYTES", 3)

    with pytest.raises(LibraryPackageError, match="too large"):
        read_bundle(path, _parse, "test bundle")


def test_collect_tree_reads_files_with_posix_names(tmp_path: Path) -> None:
    root = _tree(tmp_path / "p", {"project.yaml": "a", "substations/s1/substation.yaml": "b"})

    assert collect_tree(root) == {
        "project.yaml": b"a",
        "substations/s1/substation.yaml": b"b",
    }


def test_collect_tree_applies_the_include_filter_to_directories_and_files(
    tmp_path: Path,
) -> None:
    root = _tree(
        tmp_path / "p",
        {
            "project.yaml": "a",
            "out/x.xlsx": "x",
            "s/out/y.xlsx": "y",
            "Backups/old": "z",
            "k.bomproj": "k",
        },
    )

    def include(rel: PurePosixPath, is_dir: bool) -> bool:
        if is_dir:
            return rel.name != "out" and rel != PurePosixPath("Backups")
        return rel.suffix != ".bomproj"

    assert sorted(collect_tree(root, include=include)) == ["project.yaml"]


def test_collect_tree_prefixes_names(tmp_path: Path) -> None:
    root = _tree(tmp_path / "device-db", {"net.yaml": "a"})

    assert list(collect_tree(root, prefix="device-db")) == ["device-db/net.yaml"]


def test_collect_tree_skips_symlinks(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.yaml").write_text("secret")
    root = _tree(tmp_path / "p", {"project.yaml": "a"})
    try:
        os.symlink(outside, root / "linked-dir", target_is_directory=True)
        os.symlink(outside / "secret.yaml", root / "linked.yaml")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")

    assert list(collect_tree(root)) == ["project.yaml"]


def test_collect_tree_refuses_windows_unsafe_names(tmp_path: Path) -> None:
    root = _tree(tmp_path / "p", {"nul.yaml": "a"})

    with pytest.raises(LibraryPackageError, match=r"unsafe path 'nul\.yaml'"):
        collect_tree(root)


def test_collect_tree_refuses_names_that_differ_only_by_case(tmp_path: Path) -> None:
    root = tmp_path / "p"
    _tree(root, {"A/x.yaml": "1", "a/x.yaml": "2"})
    if len({entry.name for entry in root.iterdir()}) < 2:
        pytest.skip("file system folds case")

    with pytest.raises(LibraryPackageError, match="differ only by case"):
        collect_tree(root)


def _statuses(inspection: object) -> dict[str, str]:
    return {c.id: c.status.value for c in inspection.checks}  # type: ignore[attr-defined]


def test_inspect_lists_every_check_for_a_good_bundle(tmp_path: Path) -> None:
    path = _write(tmp_path, {"a.yaml": b"a: 1\n", "b/c.yaml": b"c: 2\n"})

    inspection = inspect_bundle(path, _parse, "test bundle")

    assert [c.id for c in inspection.checks] == [
        "package",
        "paths",
        "size",
        "manifest",
        "files",
        "checksums",
    ]
    assert all(c.status is CheckStatus.OK for c in inspection.checks)
    assert inspection.error is None
    assert inspection.files == {"a.yaml": b"a: 1\n", "b/c.yaml": b"c: 2\n"}
    assert inspection.sizes == {"a.yaml": 5, "b/c.yaml": 5}
    assert "2 files" in next(c for c in inspection.checks if c.id == "checksums").detail


def test_inspect_reports_a_changed_file_and_skips_nothing_before_it(tmp_path: Path) -> None:
    good = _write(tmp_path, {"a.yaml": b"a: 1\n"})
    bad = tmp_path / "bad.bundle"
    with zipfile.ZipFile(good) as old, zipfile.ZipFile(bad, "w") as new:
        for name in old.namelist():
            new.writestr(name, b"changed" if name == "a.yaml" else old.read(name))

    inspection = inspect_bundle(bad, _parse, "test bundle")

    assert _statuses(inspection) == {
        "package": "ok",
        "paths": "ok",
        "size": "ok",
        "manifest": "ok",
        "files": "ok",
        "checksums": "failed",
    }
    failed = next(c for c in inspection.checks if c.status is CheckStatus.FAILED)
    assert "checksum mismatch: a.yaml" in failed.detail
    assert failed.kind is RefusalKind.INVALID_PACKAGE
    assert inspection.files is None
    assert isinstance(inspection.error, LibraryPackageError)


def test_inspect_skips_the_checks_after_a_failure(tmp_path: Path) -> None:
    junk = tmp_path / "junk"
    junk.write_text("no")

    inspection = inspect_bundle(junk, _parse, "test bundle")

    assert _statuses(inspection) == {
        "package": "failed",
        "paths": "skipped",
        "size": "skipped",
        "manifest": "skipped",
        "files": "skipped",
        "checksums": "skipped",
    }
    assert inspection.manifest is None


def test_inspect_flags_unsafe_paths_without_reading_the_files(tmp_path: Path) -> None:
    path = tmp_path / "evil.bundle"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("../evil.yaml", b"x")
        zf.writestr("manifest.json", b"{}")

    inspection = inspect_bundle(path, _parse, "test bundle")

    assert _statuses(inspection)["paths"] == "failed"
    assert _statuses(inspection)["checksums"] == "skipped"


def test_inspect_surfaces_an_incompatible_manifest(tmp_path: Path) -> None:
    path = _write(tmp_path, {"a.yaml": b"a: 1\n"})

    def refuse(raw: object) -> _Manifest:
        raise LibraryPackageError("needs a newer bomgen", RefusalKind.INCOMPATIBLE)

    inspection = inspect_bundle(path, refuse, "test bundle")

    manifest_check = next(c for c in inspection.checks if c.id == "manifest")
    assert manifest_check.status is CheckStatus.FAILED
    assert manifest_check.kind is RefusalKind.INCOMPATIBLE
    assert manifest_check.detail == "needs a newer bomgen"


def test_read_bundle_still_raises_the_first_failure(tmp_path: Path) -> None:
    junk = tmp_path / "junk"
    junk.write_text("no")

    with pytest.raises(LibraryPackageError, match="not a test bundle"):
        read_bundle(junk, _parse, "test bundle")


def test_inspect_details_use_the_singular_for_one_file(tmp_path: Path) -> None:
    inspection = inspect_bundle(_write(tmp_path, {"a.yaml": b"a: 1\n"}), _parse, "test bundle")

    details = {c.id: c.detail for c in inspection.checks}

    assert details["paths"] == "2 entries"
    assert details["files"] == "1 file"
    assert details["checksums"] == "the file matches"


def test_write_bundle_creates_the_missing_folders(tmp_path: Path) -> None:
    out = tmp_path / "backups" / "2026" / "x.bundle"
    manifest = _Manifest(files={})

    write_bundle(out, manifest, {})

    assert out.is_file()


def test_write_bundle_refuses_cleanly_when_the_folder_cannot_be_made(tmp_path: Path) -> None:
    blocker = tmp_path / "taken"
    blocker.write_text("a file, not a folder")

    with pytest.raises(LibraryPackageError, match="cannot write") as raised:
        write_bundle(blocker / "x.bundle", _Manifest(files={}), {})

    assert str(blocker) in str(raised.value)
