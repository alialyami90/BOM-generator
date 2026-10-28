"""Build and verify `.bomlib` packages (ADR 0008).

A package is a zip with `manifest.json`, `library.yaml` and optional extra files
(for example the device database). Verification checks everything before any
file is written to disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

import bomgen
from bomgen.library_store.diff import parse_library
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.manifest import (
    FORMAT_VERSION,
    LIBRARY_FILE,
    LIBRARY_SCHEMA_VERSION,
    MANIFEST_NAME,
    Manifest,
    is_safe_member,
)
from bomgen.library_store.versions import Version

PACKAGE_SUFFIX = ".bomlib"
MAX_UNCOMPRESSED_BYTES = 64 * 1024**2
_EXTRA_SUFFIXES = (".yaml", ".yml")
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class PackageContents:
    manifest: Manifest
    files: dict[str, bytes]
    library: dict[str, Any]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _collect_extra(extra_dirs: Sequence[Path], files: dict[str, bytes]) -> None:
    for directory in extra_dirs:
        if not directory.is_dir():
            raise LibraryPackageError(f"not a directory: {directory}")
        if directory.name in (LIBRARY_FILE, MANIFEST_NAME):
            raise LibraryPackageError(f"{directory.name!r} is a reserved name in a package")
        if any(name.startswith(f"{directory.name}/") for name in files):
            raise LibraryPackageError(f"two extra directories are named {directory.name!r}")
        for path in sorted(
            p for p in directory.rglob("*") if p.is_file() and p.suffix in _EXTRA_SUFFIXES
        ):
            member = f"{directory.name}/{path.relative_to(directory).as_posix()}"
            if not is_safe_member(member):
                raise LibraryPackageError(f"cannot package unsafe path {member!r}")
            files[member] = path.read_bytes()
    _check_case_collisions(files)


def _check_case_collisions(members: Sequence[str] | dict[str, bytes]) -> None:
    seen: dict[str, str] = {}
    for member in members:
        other = seen.setdefault(member.casefold(), member)
        if other != member:
            raise LibraryPackageError(
                f"{other!r} and {member!r} differ only by case; Windows would merge them"
            )


def pack(
    library: Path,
    out: Path,
    *,
    name: str,
    version: str,
    release_notes: str = "",
    extra_dirs: Sequence[Path] = (),
    min_app_version: str = bomgen.__version__,
    created: datetime | None = None,
) -> Manifest:
    """Write a package holding `library` (stored as `library.yaml`) and each extra directory."""
    files = {LIBRARY_FILE: library.read_bytes()}
    parse_library(files[LIBRARY_FILE])
    _collect_extra(extra_dirs, files)
    try:
        manifest = Manifest(
            format_version=FORMAT_VERSION,
            name=name,
            version=version,
            schema_version=LIBRARY_SCHEMA_VERSION,
            min_app_version=min_app_version,
            release_notes=release_notes,
            created=created or datetime.now(UTC).replace(microsecond=0),
            files={member: _sha256(data) for member, data in sorted(files.items())},
        )
    except ValidationError as exc:
        raise LibraryPackageError(f"invalid package details: {exc}") from exc

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
    return manifest


def _read_manifest(zf: zipfile.ZipFile) -> Manifest:
    try:
        raw = json.loads(_read_member(zf, MANIFEST_NAME))
    except ValueError as exc:
        raise LibraryPackageError(f"{MANIFEST_NAME} is invalid: {exc}") from exc
    format_version = raw.get("format_version") if isinstance(raw, dict) else None
    if isinstance(format_version, int) and format_version > FORMAT_VERSION:
        raise LibraryPackageError(
            f"package format version {format_version} needs a newer bomgen "
            f"(this one reads version {FORMAT_VERSION})",
            RefusalKind.INCOMPATIBLE,
        )
    try:
        return Manifest.model_validate(raw)
    except ValidationError as exc:
        raise LibraryPackageError(f"{MANIFEST_NAME} is invalid: {exc}") from exc


def _read_member(zf: zipfile.ZipFile, member: str) -> bytes:
    try:
        return zf.read(member)
    except (zipfile.BadZipFile, zlib.error, OSError, RuntimeError, NotImplementedError) as exc:
        raise LibraryPackageError(f"cannot read {member} from the package: {exc}") from exc


def _check_compatible(manifest: Manifest, app_version: str) -> None:
    if manifest.schema_version != LIBRARY_SCHEMA_VERSION:
        raise LibraryPackageError(
            f"package uses library schema version {manifest.schema_version}; "
            f"this bomgen reads version {LIBRARY_SCHEMA_VERSION}",
            RefusalKind.INCOMPATIBLE,
        )
    if Version.parse(manifest.min_app_version) > Version.parse(app_version):
        raise LibraryPackageError(
            f"package needs bomgen {manifest.min_app_version} or later (this is {app_version})",
            RefusalKind.INCOMPATIBLE,
        )


def read_package(path: Path, *, app_version: str = bomgen.__version__) -> PackageContents:
    """Open and fully verify a package; raise `LibraryPackageError` on any problem."""
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise LibraryPackageError(f"{path.name} is not a .bomlib package (not a zip file)") from exc
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
        _check_case_collisions(names)
        if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
            raise LibraryPackageError("package is too large")
        if MANIFEST_NAME not in names:
            raise LibraryPackageError(f"package has no {MANIFEST_NAME}")

        manifest = _read_manifest(zf)
        _check_compatible(manifest, app_version)
        if LIBRARY_FILE not in manifest.files:
            raise LibraryPackageError(f"package has no {LIBRARY_FILE}")
        members = set(names) - {MANIFEST_NAME}
        if unlisted := sorted(members - manifest.files.keys()):
            raise LibraryPackageError(f"files not listed in the manifest: {', '.join(unlisted)}")
        if missing := sorted(manifest.files.keys() - members):
            raise LibraryPackageError(f"files missing from the package: {', '.join(missing)}")

        files: dict[str, bytes] = {}
        for member in sorted(members):
            data = _read_member(zf, member)
            if _sha256(data) != manifest.files[member]:
                raise LibraryPackageError(f"checksum mismatch: {member} has been changed")
            files[member] = data

    return PackageContents(manifest, files, parse_library(files[LIBRARY_FILE]))
