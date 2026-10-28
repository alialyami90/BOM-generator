"""Import a `.bomproj` file into the workspace (ADR 0012)."""

from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from bomgen.bundle.container import MANIFEST_NAME, read_bundle
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.store import (
    LibraryRef,
    LibraryStore,
    default_library_home,
    library_mismatch,
)
from bomgen.project_store.backup import backup_directory
from bomgen.project_store.export import BACKUPS_DIR, ProjectIdentity, parse_project_identity
from bomgen.project_store.manifest import PROJECT_FILE, PROJECT_FORMAT_VERSION, ProjectManifest
from bomgen.project_store.workspace import default_workspace


@dataclass(frozen=True)
class ProjectImportResult:
    manifest: ProjectManifest
    project_dir: Path
    replaced: bool
    backup: Path | None
    library_note: str | None


def _parse_manifest(raw: object) -> ProjectManifest:
    if isinstance(raw, dict) and "project_id" not in raw and "schema_version" in raw:
        raise LibraryPackageError(
            "this is a .bomlib library, not a .bomproj project; "
            "use 'bomgen library import' to install it"
        )
    version = raw.get("format_version") if isinstance(raw, dict) else None
    if isinstance(version, int) and version > PROJECT_FORMAT_VERSION:
        raise LibraryPackageError(
            f"project file format version {version} needs a newer bomgen "
            f"(this one reads version {PROJECT_FORMAT_VERSION})",
            RefusalKind.INCOMPATIBLE,
        )
    try:
        manifest = ProjectManifest.model_validate(raw)
    except ValidationError as exc:
        raise LibraryPackageError(f"{MANIFEST_NAME} is invalid: {exc}") from exc
    if PROJECT_FILE not in manifest.files:
        raise LibraryPackageError(f"package has no {PROJECT_FILE}")
    return manifest


def library_note(manifest: ProjectManifest, store: LibraryStore) -> str | None:
    """What to do when the project was built with a library other than the active one."""
    name, version = manifest.library_name, manifest.library_version
    if name is None or version is None:
        return None
    try:
        active = store.active_version(name)
    except LibraryPackageError:
        active = None
    recorded = LibraryRef(name, version)
    problem = library_mismatch(recorded, LibraryRef(name, active) if active else None)
    if problem is None:
        return None
    if version in store.versions(name):
        return f"{problem}; it is installed, so run: bomgen library rollback {name} --to {version}"
    return f"{problem}; install it with: bomgen library import {name}-{version}.bomlib"


def import_project(
    package: Path,
    *,
    workspace: Path | None = None,
    force: bool = False,
    store: LibraryStore | None = None,
    now: datetime | None = None,
) -> ProjectImportResult:
    """Verify a `.bomproj` and unpack it into `<workspace>/<project-id>/`.

    An existing project with the same id is refused unless `force`; a forced
    import saves it to its `Backups/` first, keeps its `Backups/` and `out/`
    folders, and restores it if the import fails.
    """
    manifest, files = read_bundle(package, _parse_manifest, ".bomproj project file")
    identity = parse_project_identity(files[PROJECT_FILE].decode("utf-8", "replace"))
    if identity.id != manifest.project_id:
        raise LibraryPackageError(
            f"the manifest names project {manifest.project_id!r} "
            f"but {PROJECT_FILE} names {identity.id!r}"
        )
    workspace = workspace or default_workspace()
    target = workspace / manifest.project_id
    exists = target.exists()
    if exists and not force:
        raise LibraryPackageError(
            f"project {manifest.project_id!r} already exists in {workspace}; "
            "import with --force to replace it (it is backed up first)",
            RefusalKind.PROJECT_EXISTS,
        )

    workspace.mkdir(parents=True, exist_ok=True)
    incoming = workspace / f".incoming-{uuid.uuid4().hex}"
    replaced = workspace / f".replaced-{uuid.uuid4().hex}"
    backup: Path | None = None
    committed = False
    try:
        for name, data in files.items():
            path = incoming / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if exists:
            backup = _backup_existing(target, manifest.project_id, now)
            _carry_over(target, incoming)
            os.replace(target, replaced)
            try:
                os.replace(incoming, target)
            except BaseException:
                os.replace(replaced, target)
                raise
        else:
            os.replace(incoming, target)
        committed = True
    finally:
        shutil.rmtree(incoming, ignore_errors=True)
        if committed:
            shutil.rmtree(replaced, ignore_errors=True)

    return ProjectImportResult(
        manifest,
        target,
        replaced=exists,
        backup=target / BACKUPS_DIR / backup.name if backup else None,
        library_note=library_note(manifest, store or LibraryStore(default_library_home())),
    )


def _backup_existing(project_dir: Path, project_id: str, now: datetime | None) -> Path:
    try:
        return backup_directory(project_dir, ProjectIdentity(project_id, None, None), now=now)
    except (LibraryPackageError, OSError) as exc:
        raise LibraryPackageError(
            f"cannot back up the existing project, so it was not replaced: {exc}",
            RefusalKind.INVALID_PROJECT,
        ) from exc


def _carry_over(old: Path, new: Path) -> None:
    """Copy what a package never holds (`Backups/` and every `out/`) into the new tree."""
    for root, dirs, _files in os.walk(old):
        here = Path(root)
        relative = here.relative_to(old)
        for name in list(dirs):
            keep = name == "out" or (relative == Path() and name == BACKUPS_DIR)
            if keep:
                dirs.remove(name)
                shutil.copytree(
                    here / name, new / relative / name, symlinks=True, dirs_exist_ok=True
                )
