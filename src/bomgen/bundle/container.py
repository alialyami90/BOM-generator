"""The zip container behind `.bomlib` and `.bomproj` packages.

A bundle is a zip with `manifest.json` plus the files the manifest lists with a
SHA-256 each. Reading checks everything (paths, sizes, checksums) before any
file reaches the disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
import zlib
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Protocol

from pydantic import BaseModel

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
    """Write `manifest.json` and `files`; equal inputs give equal bytes."""
    manifest_bytes = json.dumps(manifest.model_dump(mode="json"), indent=2).encode()
    partial = out.with_name(f".{out.name}.partial")
    try:
        with zipfile.ZipFile(partial, "w") as zf:
            for member, data in [(MANIFEST_NAME, manifest_bytes), *sorted(files.items())]:
                info = zipfile.ZipInfo(member, date_time=_ZIP_EPOCH)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zf.writestr(info, data)
        os.replace(partial, out)
    finally:
        partial.unlink(missing_ok=True)


def read_bundle[M: _HasFiles](
    path: Path, parse_manifest: Callable[[object], M], what: str
) -> tuple[M, dict[str, bytes]]:
    """Open and fully verify a bundle; raise `LibraryPackageError` on any problem.

    `parse_manifest` turns the decoded `manifest.json` into the caller's manifest
    model and applies the caller's own compatibility rules. `what` names the file
    type in messages, for example ".bomlib package".
    """
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise LibraryPackageError(f"{path.name} is not a {what} (not a zip file)") from exc
    except OSError as exc:
        raise LibraryPackageError(f"cannot open {path}: {exc.strerror or exc}") from exc
    with zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        names = [info.filename for info in infos]
        for member in names:
            if not is_safe_member(member):
                raise LibraryPackageError(f"package contains an unsafe path {member!r}")
        if len(set(names)) != len(names):
            raise LibraryPackageError("package contains duplicate entries")
        check_case_collisions(names)
        if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
            raise LibraryPackageError("package is too large")
        if MANIFEST_NAME not in names:
            raise LibraryPackageError(f"package has no {MANIFEST_NAME}")

        try:
            raw = json.loads(_read_member(zf, MANIFEST_NAME))
        except ValueError as exc:
            raise LibraryPackageError(f"{MANIFEST_NAME} is invalid: {exc}") from exc
        manifest = parse_manifest(raw)

        members = set(names) - {MANIFEST_NAME}
        if unlisted := sorted(members - manifest.files.keys()):
            raise LibraryPackageError(f"files not listed in the manifest: {', '.join(unlisted)}")
        if missing := sorted(manifest.files.keys() - members):
            raise LibraryPackageError(f"files missing from the package: {', '.join(missing)}")

        files: dict[str, bytes] = {}
        for member in sorted(members):
            data = _read_member(zf, member)
            if sha256(data) != manifest.files[member]:
                raise LibraryPackageError(f"checksum mismatch: {member} has been changed")
            files[member] = data
    return manifest, files


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
