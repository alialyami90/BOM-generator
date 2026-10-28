"""The library import dry-run: every check listed, nothing written (design: Import update)."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import bomgen
from bomgen.bundle.checks import Check, CheckStatus
from bomgen.bundle.container import inspect_bundle
from bomgen.library_store.diff import LibraryDiff, parse_library
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.manifest import LIBRARY_FILE, Manifest
from bomgen.library_store.package import PackageContents, parse_manifest
from bomgen.library_store.service import validate_library
from bomgen.library_store.store import LibraryStore, default_library_home

_SKIPPED_LABELS = {
    "library": "Library file is readable",
    "validation": "Library passes the schema",
    "version": "Version is newer than the active one",
}


@dataclass(frozen=True)
class PackageFile:
    name: str
    size: int


@dataclass(frozen=True)
class LibraryImportPreview:
    """What importing a `.bomlib` would do. `can_import` is False when a check failed.

    `files` is empty when a check failed, and `diff` is None unless the library and
    version checks passed. `previous` is the active version the diff is against.
    """

    checks: list[Check]
    manifest: Manifest | None
    files: list[PackageFile]
    previous: str | None
    diff: LibraryDiff | None

    @property
    def can_import(self) -> bool:
        return all(check.status is not CheckStatus.FAILED for check in self.checks)


def preview_library_import(
    package: Path, *, force: bool = False, store: LibraryStore | None = None
) -> LibraryImportPreview:
    """Verify a `.bomlib` and report each check; the store is untouched.

    With `force`, a downgrade or a reinstall is a warning instead of a failure.
    """
    store = store or LibraryStore(default_library_home())
    inspection = inspect_bundle(
        package, lambda raw: parse_manifest(raw, bomgen.__version__), ".bomlib package"
    )
    checks = list(inspection.checks)
    manifest, files = inspection.manifest, inspection.files
    contents: PackageContents | None = None
    previous: str | None = None
    diff: LibraryDiff | None = None

    if manifest is not None and files is not None:
        checks.append(Check("library", _SKIPPED_LABELS["library"], CheckStatus.OK))
        try:
            contents = PackageContents(manifest, files, parse_library(files[LIBRARY_FILE]))
        except LibraryPackageError as exc:
            checks[-1] = Check("library", _SKIPPED_LABELS["library"], *_failed(exc))
    else:
        checks.append(Check("library", _SKIPPED_LABELS["library"], CheckStatus.SKIPPED))

    checks.append(_validation(contents))
    if contents is None or checks[-1].status is CheckStatus.FAILED:
        checks.append(Check("version", _SKIPPED_LABELS["version"], CheckStatus.SKIPPED))
    else:
        version_check, previous, diff = _version(store, contents, force)
        checks.append(version_check)
    checks.append(
        Check(
            "signature",
            "Package is signed",
            CheckStatus.SKIPPED,
            "packages carry checksums only; they are not signed",
        )
    )
    can_show = files is not None and all(c.status is not CheckStatus.FAILED for c in checks)
    shown = (
        [PackageFile(name, len(data)) for name, data in sorted(files.items())]
        if files is not None and can_show
        else []
    )
    return LibraryImportPreview(checks, manifest, shown, previous, diff)


def _failed(exc: LibraryPackageError) -> tuple[CheckStatus, str, RefusalKind]:
    return CheckStatus.FAILED, str(exc), exc.kind


def _validation(contents: PackageContents | None) -> Check:
    label = _SKIPPED_LABELS["validation"]
    if contents is None:
        return Check("validation", label, CheckStatus.SKIPPED)
    with tempfile.TemporaryDirectory(prefix="bomlib-preview-") as scratch:
        library_file = Path(scratch) / LIBRARY_FILE
        library_file.write_bytes(contents.files[LIBRARY_FILE])
        try:
            validate_library(library_file)
        except LibraryPackageError as exc:
            return Check("validation", label, *_failed(exc))
    return Check("validation", label, CheckStatus.OK)


def _version(
    store: LibraryStore, contents: PackageContents, force: bool
) -> tuple[Check, str | None, LibraryDiff | None]:
    manifest = contents.manifest
    label = _SKIPPED_LABELS["version"]
    warning: str | None = None
    try:
        try:
            plan = store.plan_import(contents)
        except LibraryPackageError as exc:
            if not force or exc.kind not in (RefusalKind.DOWNGRADE, RefusalKind.ALREADY_INSTALLED):
                raise
            warning = str(exc)
            plan = store.plan_import(contents, force=True)
    except (LibraryPackageError, OSError) as exc:
        kind = exc.kind if isinstance(exc, LibraryPackageError) else RefusalKind.STORE_DAMAGED
        return Check("version", label, CheckStatus.FAILED, str(exc), kind), None, None
    if warning is not None:
        return Check("version", label, CheckStatus.WARNING, warning), plan.previous, plan.diff
    if plan.previous is None:
        detail = f"{manifest.name} {manifest.version} is the first version installed"
    else:
        detail = f"{manifest.version} is newer than the active {plan.previous}"
    return Check("version", label, CheckStatus.OK, detail), plan.previous, plan.diff
