"""Build and verify `.bomlib` packages (ADR 0008).

A package is a bundle (see `bomgen.bundle`) holding `library.yaml` and optional
extra files, for example the device database.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

import bomgen
from bomgen.bundle.container import MANIFEST_NAME, collect_tree, read_bundle, sha256, write_bundle
from bomgen.bundle.paths import check_case_collisions
from bomgen.library_store.device_db import parse_device_records
from bomgen.library_store.diff import parse_library
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.manifest import (
    FORMAT_VERSION,
    LIBRARY_FILE,
    LIBRARY_SCHEMA_VERSION,
    Manifest,
)
from bomgen.library_store.versions import Version

PACKAGE_SUFFIX = ".bomlib"
_EXTRA_SUFFIXES = (".yaml", ".yml")


@dataclass(frozen=True)
class PackageContents:
    manifest: Manifest
    files: dict[str, bytes]
    library: dict[str, Any]


def _only_yaml(relative: PurePosixPath, is_dir: bool) -> bool:
    return is_dir or relative.suffix in _EXTRA_SUFFIXES


def _collect_extra(extra_dirs: Sequence[Path], files: dict[str, bytes]) -> None:
    for directory in extra_dirs:
        if not directory.is_dir():
            raise LibraryPackageError(f"not a directory: {directory}")
        if directory.name in (LIBRARY_FILE, MANIFEST_NAME):
            raise LibraryPackageError(f"{directory.name!r} is a reserved name in a package")
        if any(name.startswith(f"{directory.name}/") for name in files):
            raise LibraryPackageError(f"two extra directories are named {directory.name!r}")
        files.update(collect_tree(directory, prefix=directory.name, include=_only_yaml))
    check_case_collisions(files)


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
    parse_device_records(files)
    try:
        manifest = Manifest(
            format_version=FORMAT_VERSION,
            name=name,
            version=version,
            schema_version=LIBRARY_SCHEMA_VERSION,
            min_app_version=min_app_version,
            release_notes=release_notes,
            created=created or datetime.now(UTC).replace(microsecond=0),
            files={member: sha256(data) for member, data in sorted(files.items())},
        )
    except ValidationError as exc:
        raise LibraryPackageError(f"invalid package details: {exc}") from exc
    write_bundle(out, manifest, files)
    return manifest


def parse_manifest(raw: object, app_version: str) -> Manifest:
    if isinstance(raw, dict) and "project_id" in raw:
        raise LibraryPackageError(
            "this is a .bomproj project, not a .bomlib library; "
            "use 'bomgen project import' to open it"
        )
    format_version = raw.get("format_version") if isinstance(raw, dict) else None
    if isinstance(format_version, int) and format_version > FORMAT_VERSION:
        raise LibraryPackageError(
            f"package format version {format_version} needs a newer bomgen "
            f"(this one reads version {FORMAT_VERSION})",
            RefusalKind.INCOMPATIBLE,
        )
    try:
        manifest = Manifest.model_validate(raw)
    except ValidationError as exc:
        raise LibraryPackageError(f"{MANIFEST_NAME} is invalid: {exc}") from exc
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
    if LIBRARY_FILE not in manifest.files:
        raise LibraryPackageError(f"package has no {LIBRARY_FILE}")
    return manifest


def read_package(path: Path, *, app_version: str = bomgen.__version__) -> PackageContents:
    """Open and fully verify a package; raise `LibraryPackageError` on any problem."""
    manifest, files = read_bundle(
        path, lambda raw: parse_manifest(raw, app_version), ".bomlib package"
    )
    return PackageContents(manifest, files, parse_library(files[LIBRARY_FILE]))
