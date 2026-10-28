"""The zip container behind `.bomlib` and `.bomproj` packages.

A bundle is a zip with `manifest.json` plus the files the manifest lists with a
SHA-256 each. Reading checks everything (paths, sizes, checksums) before any
file reaches the disk.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import zipfile
import zlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from pydantic import BaseModel

from bomgen.bundle.checks import Check, CheckStatus
from bomgen.bundle.errors import LibraryPackageError
from bomgen.bundle.paths import check_case_collisions, is_safe_member

MANIFEST_NAME = "manifest.json"
MAX_UNCOMPRESSED_BYTES = 64 * 1024**2
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
_SHA256 = re.compile(r"[0-9a-f]{64}")


class _HasFiles(Protocol):
    @property
    def files(self) -> dict[str, str]: ...


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_file_table(files: dict[str, str]) -> dict[str, str]:
    """Validate a manifest's `files` (path to SHA-256): safe paths, well-formed digests."""
    for path, digest in files.items():
        if not is_safe_member(path) or path == MANIFEST_NAME:
            raise ValueError(f"unsafe file path {path!r}")
        if not _SHA256.fullmatch(digest):
            raise ValueError(f"{path}: checksum must be 64 lowercase hex digits")
    return files


def write_bundle(out: Path, manifest: BaseModel, files: Mapping[str, bytes]) -> None:
    """Write `manifest.json` and `files`; equal inputs give equal bytes.

    Missing folders on the way to `out` are created. A folder or file that cannot be written is
    a `LibraryPackageError` naming `out`.
    """
    manifest_bytes = json.dumps(manifest.model_dump(mode="json"), indent=2).encode()
    partial = out.with_name(f".{out.name}.partial")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(partial, "w") as zf:
            for member, data in [(MANIFEST_NAME, manifest_bytes), *sorted(files.items())]:
                info = zipfile.ZipInfo(member, date_time=_ZIP_EPOCH)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zf.writestr(info, data)
        os.replace(partial, out)
    except OSError as exc:
        raise LibraryPackageError(f"cannot write {out}: {exc.strerror or exc}") from exc
    finally:
        with contextlib.suppress(OSError):
            partial.unlink(missing_ok=True)


@dataclass(frozen=True)
class BundleInspection[M: _HasFiles]:
    """What opening a bundle found, check by check.

    `files` is set only when every check passed; `manifest` is set once the
    manifest check passed. `sizes` are the declared uncompressed sizes.
    """

    checks: list[Check]
    manifest: M | None
    files: dict[str, bytes] | None
    sizes: dict[str, int]
    error: LibraryPackageError | None


class _Reader[M: _HasFiles]:
    """The verification steps of `inspect_bundle`, run in order on one zip file."""

    def __init__(self, path: Path, parse_manifest: Callable[[object], M], what: str) -> None:
        self.path, self.parse_manifest, self.what = path, parse_manifest, what
        self.zf: zipfile.ZipFile | None = None
        self.infos: list[zipfile.ZipInfo] = []
        self.manifest: M | None = None
        self.files: dict[str, bytes] = {}

    @property
    def names(self) -> list[str]:
        return [info.filename for info in self.infos]

    @property
    def sizes(self) -> dict[str, int]:
        return {i.filename: i.file_size for i in self.infos if i.filename != MANIFEST_NAME}

    def package(self) -> str:
        try:
            self.zf = zipfile.ZipFile(self.path)
        except zipfile.BadZipFile as exc:
            raise LibraryPackageError(
                f"{self.path.name} is not a {self.what} (not a zip file)"
            ) from exc
        except OSError as exc:
            raise LibraryPackageError(f"cannot open {self.path}: {exc.strerror or exc}") from exc
        self.infos = [info for info in self.zf.infolist() if not info.is_dir()]
        return f"{self.path.name}, {self.path.stat().st_size} bytes"

    def paths(self) -> str:
        for member in self.names:
            if not is_safe_member(member):
                raise LibraryPackageError(f"package contains an unsafe path {member!r}")
        if len(set(self.names)) != len(self.names):
            raise LibraryPackageError("package contains duplicate entries")
        check_case_collisions(self.names)
        return _count(len(self.names), "entry", "entries")

    def size(self) -> str:
        total = sum(info.file_size for info in self.infos)
        if total > MAX_UNCOMPRESSED_BYTES:
            raise LibraryPackageError("package is too large")
        return f"{total} bytes unpacked"

    def manifest_step(self) -> str:
        assert self.zf is not None
        if MANIFEST_NAME not in self.names:
            raise LibraryPackageError(f"package has no {MANIFEST_NAME}")
        try:
            raw = json.loads(_read_member(self.zf, MANIFEST_NAME))
        except ValueError as exc:
            raise LibraryPackageError(f"{MANIFEST_NAME} is invalid: {exc}") from exc
        self.manifest = self.parse_manifest(raw)
        return ""

    def files_step(self) -> str:
        assert self.manifest is not None
        members = set(self.names) - {MANIFEST_NAME}
        if unlisted := sorted(members - self.manifest.files.keys()):
            raise LibraryPackageError(f"files not listed in the manifest: {', '.join(unlisted)}")
        if missing := sorted(self.manifest.files.keys() - members):
            raise LibraryPackageError(f"files missing from the package: {', '.join(missing)}")
        return _count(len(members), "file", "files")

    def checksums(self) -> str:
        assert self.zf is not None
        assert self.manifest is not None
        for member in sorted(self.manifest.files):
            data = _read_member(self.zf, member)
            if sha256(data) != self.manifest.files[member]:
                raise LibraryPackageError(f"checksum mismatch: {member} has been changed")
            self.files[member] = data
        return "the file matches" if len(self.files) == 1 else f"all {len(self.files)} files match"


def _count(number: int, singular: str, plural: str) -> str:
    return f"{number} {singular if number == 1 else plural}"


_STAGES = (
    ("package", "Package is a readable file"),
    ("paths", "File paths are safe"),
    ("size", "Size is within the limit"),
    ("manifest", "Manifest is valid and supported"),
    ("files", "Files match the manifest"),
    ("checksums", "Checksums match"),
)


def inspect_bundle[M: _HasFiles](
    path: Path, parse_manifest: Callable[[object], M], what: str
) -> BundleInspection[M]:
    """Run every verification step and report each one; a bad bundle does not raise.

    A failed step skips the steps after it. `parse_manifest` and `what` are as in
    `read_bundle`.
    """
    reader = _Reader(path, parse_manifest, what)
    steps = (
        reader.package,
        reader.paths,
        reader.size,
        reader.manifest_step,
        reader.files_step,
        reader.checksums,
    )
    checks: list[Check] = []
    error: LibraryPackageError | None = None
    try:
        for (check_id, label), step in zip(_STAGES, steps, strict=True):
            if error is not None:
                checks.append(Check(check_id, label, CheckStatus.SKIPPED))
                continue
            try:
                detail = step()
            except LibraryPackageError as exc:
                error = exc
                checks.append(Check(check_id, label, CheckStatus.FAILED, str(exc), exc.kind))
            else:
                checks.append(Check(check_id, label, CheckStatus.OK, detail))
    finally:
        if reader.zf is not None:
            reader.zf.close()
    return BundleInspection(
        checks,
        reader.manifest,
        reader.files if error is None else None,
        reader.sizes,
        error,
    )


def read_bundle[M: _HasFiles](
    path: Path, parse_manifest: Callable[[object], M], what: str
) -> tuple[M, dict[str, bytes]]:
    """Open and fully verify a bundle; raise `LibraryPackageError` on any problem.

    `parse_manifest` turns the decoded `manifest.json` into the caller's manifest
    model and applies the caller's own compatibility rules. `what` names the file
    type in messages, for example ".bomlib package".
    """
    inspection = inspect_bundle(path, parse_manifest, what)
    if inspection.error is not None:
        raise inspection.error
    assert inspection.manifest is not None
    assert inspection.files is not None
    return inspection.manifest, inspection.files


def _read_member(zf: zipfile.ZipFile, member: str) -> bytes:
    try:
        return zf.read(member)
    except (zipfile.BadZipFile, zlib.error, OSError, RuntimeError, NotImplementedError) as exc:
        raise LibraryPackageError(f"cannot read {member} from the package: {exc}") from exc


def collect_tree(
    root: Path,
    *,
    prefix: str = "",
    include: Callable[[PurePosixPath, bool], bool] | None = None,
) -> dict[str, bytes]:
    """Read the files under `root` as posix-named bytes, skipping symlinks.

    `include(relative_path, is_dir)` can drop directories (and everything below
    them) or single files. Names Windows cannot extract, or that differ only by
    case, are refused.
    """
    files: dict[str, bytes] = {}

    def walk(directory: Path, relative: PurePosixPath) -> None:
        with os.scandir(directory) as scanner:
            entries = sorted(scanner, key=lambda entry: entry.name)
        for entry in entries:
            if entry.is_symlink():
                continue
            rel = relative / entry.name
            is_dir = entry.is_dir(follow_symlinks=False)
            if not is_dir and not entry.is_file(follow_symlinks=False):
                continue
            if include is not None and not include(rel, is_dir):
                continue
            member = f"{prefix}/{rel.as_posix()}" if prefix else rel.as_posix()
            if not is_safe_member(member):
                raise LibraryPackageError(f"cannot package unsafe path {member!r}")
            if is_dir:
                walk(Path(entry.path), rel)
            else:
                try:
                    files[member] = Path(entry.path).read_bytes()
                except OSError as exc:
                    raise LibraryPackageError(f"cannot read {entry.path}: {exc.strerror}") from exc

    walk(root, PurePosixPath())
    check_case_collisions(files)
    return files
