"""The import dry-run: every check listed, nothing written (design: Back up and share)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bomgen.bundle.checks import Check, CheckStatus
from bomgen.bundle.container import inspect_bundle
from bomgen.bundle.errors import LibraryPackageError
from bomgen.library_store.store import LibraryStore, default_library_home
from bomgen.project_store.importer import (
    LibraryNote,
    check_identity,
    library_note,
    parse_project_manifest,
    refuse_build_output,
)
from bomgen.project_store.manifest import ProjectManifest
from bomgen.project_store.rename import suggest_project_id
from bomgen.project_store.workspace import default_workspace


@dataclass(frozen=True)
class PackageFile:
    name: str
    size: int


@dataclass(frozen=True)
class ProjectImportPreview:
    """What importing a `.bomproj` would do. `can_import` is False when a check failed.

    An existing project with the same id is a warning, not a failure: the import
    replaces it after a backup. `files` is empty when a check failed.
    """

    checks: list[Check]
    manifest: ProjectManifest | None
    files: list[PackageFile]
    project_id: str | None
    target_dir: Path | None
    exists: bool
    library_note: str | None
    library_hint: str | None = None
    suggested_id: str | None = None  # a free id for "keep both", set when the project exists

    @property
    def can_import(self) -> bool:
        return all(check.status is not CheckStatus.FAILED for check in self.checks)


def preview_project_import(
    package: Path, *, workspace: Path | None = None, store: LibraryStore | None = None
) -> ProjectImportPreview:
    """Verify a `.bomproj` and report each check; the workspace and library store are untouched."""
    inspection = inspect_bundle(package, parse_project_manifest, ".bomproj project file")
    manifest = inspection.manifest
    checks = list(inspection.checks)
    workspace = workspace or default_workspace()
    target = workspace / manifest.project_id if manifest else None
    exists = bool(target and target.exists())
    note: LibraryNote | None = None

    verified = inspection.files
    ready = verified is not None and manifest is not None and target is not None
    for check_id, label, verify in (
        ("identity", "Project id matches project.yaml", check_identity),
        ("contents", "Package holds no build output", lambda _m, files: refuse_build_output(files)),
    ):
        check = _run(check_id, label, verify, manifest, verified) if ready else None
        checks.append(check or Check(check_id, label, CheckStatus.SKIPPED))
        ready = ready and checks[-1].status is not CheckStatus.FAILED
    if ready and manifest is not None:
        checks.append(_name_check(manifest.project_id, workspace, exists))
        library_check, note = _library_check(manifest, store)
        checks.append(library_check)
    else:
        checks.append(Check("name", "Project id in the workspace", CheckStatus.SKIPPED))
        checks.append(Check("library", "Built with the active library", CheckStatus.SKIPPED))

    files = (
        [PackageFile(name, size) for name, size in sorted(inspection.sizes.items())]
        if ready
        else []
    )
    return ProjectImportPreview(
        checks,
        manifest,
        files,
        manifest.project_id if manifest else None,
        target,
        exists,
        note.text if note else None,
        note.hint if note else None,
        suggest_project_id(manifest.project_id, workspace) if manifest and exists else None,
    )


def _run(
    check_id: str,
    label: str,
    verify: Callable[[ProjectManifest, dict[str, bytes]], None],
    manifest: ProjectManifest | None,
    files: dict[str, bytes] | None,
) -> Check:
    if manifest is None or files is None:
        return Check(check_id, label, CheckStatus.SKIPPED)
    try:
        verify(manifest, files)
    except LibraryPackageError as exc:
        return Check(check_id, label, CheckStatus.FAILED, str(exc), exc.kind)
    return Check(check_id, label, CheckStatus.OK)


def _name_check(project_id: str, workspace: Path, exists: bool) -> Check:
    label = "Project id in the workspace"
    if not exists:
        return Check("name", label, CheckStatus.OK, f"no project {project_id!r} in {workspace}")
    return Check(
        "name",
        label,
        CheckStatus.WARNING,
        f"project {project_id!r} already exists in {workspace}; "
        "importing replaces it, and it is backed up first",
    )


def _library_check(
    manifest: ProjectManifest, store: LibraryStore | None
) -> tuple[Check, LibraryNote | None]:
    label = "Built with the active library"
    if manifest.library_name is None:
        return Check("library", label, CheckStatus.OK, "the project records no library"), None
    try:
        note = library_note(manifest, store or LibraryStore(default_library_home()))
    except (LibraryPackageError, OSError) as exc:
        return Check(
            "library", label, CheckStatus.WARNING, f"cannot read the library store: {exc}"
        ), None
    if note is None:
        detail = f"{manifest.library_name} {manifest.library_version} is active"
        return Check("library", label, CheckStatus.OK, detail), None
    return Check("library", label, CheckStatus.WARNING, note.text), note
