"""Backups: an export into the project's own `Backups/` folder (ADR 0012)."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from bomgen.bundle.container import MANIFEST_NAME
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.store import LibraryStore
from bomgen.project_store.export import (
    BACKUPS_DIR,
    ProjectIdentity,
    export_directory,
    read_project_identity,
)
from bomgen.project_store.manifest import PROJECT_SUFFIX, ProjectManifest


def backup_project(project_file: Path, *, now: datetime | None = None) -> Path:
    """Save the project next to itself as `Backups/<id>-<timestamp>.bomproj`."""
    identity = read_project_identity(project_file)
    return backup_directory(project_file.parent, identity, now=now)


def backup_directory(
    project_dir: Path, identity: ProjectIdentity, *, now: datetime | None = None
) -> Path:
    """Back up `project_dir`, never overwriting an earlier backup."""
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    backups = project_dir / BACKUPS_DIR
    try:
        backups.mkdir(exist_ok=True)
    except OSError as exc:
        raise LibraryPackageError(f"cannot create {backups}: {exc.strerror}") from exc
    for attempt in range(1, 1000):
        suffix = "" if attempt == 1 else f"-{attempt}"
        target = backups / f"{identity.id}-{stamp}{suffix}{PROJECT_SUFFIX}"
        if not target.exists():
            created = (now or datetime.now()).astimezone(UTC).replace(microsecond=0)
            return export_directory(project_dir, identity, target, created=created).path
    raise LibraryPackageError(f"too many backups in {backups} for {stamp}")


if TYPE_CHECKING:
    from bomgen.project_store.importer import ProjectImportResult


@dataclass(frozen=True)
class BackupInfo:
    """One row of the Backups table; `problem` is set when the file cannot be read."""

    path: Path
    saved: datetime
    size: int
    project_id: str | None
    library_name: str | None
    library_version: str | None
    file_count: int | None
    problem: str | None


def list_backups(project_file: Path) -> list[BackupInfo]:
    """The project's backups, newest first. Reads manifests only; nothing is unpacked."""
    backups = project_file.parent / BACKUPS_DIR
    if not backups.is_dir():
        return []
    found = [_describe(path) for path in backups.glob(f"*{PROJECT_SUFFIX}") if path.is_file()]
    return sorted(found, key=lambda info: (info.saved, info.path.name), reverse=True)


def _describe(path: Path) -> BackupInfo:
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, UTC)
    try:
        with zipfile.ZipFile(path) as zf:
            manifest = ProjectManifest.model_validate(json.loads(zf.read(MANIFEST_NAME)))
    except (zipfile.BadZipFile, KeyError, ValueError, ValidationError, OSError) as exc:
        return BackupInfo(
            path, modified, stat.st_size, None, None, None, None, f"unreadable: {exc}"
        )
    saved = manifest.created if manifest.created.tzinfo else manifest.created.astimezone(UTC)
    return BackupInfo(
        path,
        saved,
        stat.st_size,
        manifest.project_id,
        manifest.library_name,
        manifest.library_version,
        len(manifest.files),
        None,
    )


def restore_backup(
    backup: Path, *, store: LibraryStore | None = None, now: datetime | None = None
) -> ProjectImportResult:
    """Put a backup back as its project, backing the current state up first.

    The backup must sit in `<project>/Backups/` of the project it was made from.
    For the review dialog use `preview_project_import(backup, workspace=<project>.parent)`.
    """
    # imported here: the importer itself takes a safety backup through this module
    from bomgen.project_store.importer import import_project
    from bomgen.project_store.preview import preview_project_import

    project_dir = backup.parent.parent
    if backup.parent.name != BACKUPS_DIR:
        raise LibraryPackageError(
            f"{backup.name} is not in a project's {BACKUPS_DIR} folder; "
            "import it with 'bomgen project import' instead",
            RefusalKind.INVALID_PROJECT,
        )
    preview = preview_project_import(backup, workspace=project_dir.parent, store=store)
    if preview.project_id is not None and preview.project_id != project_dir.name:
        raise LibraryPackageError(
            f"{backup.name} belongs to project {preview.project_id!r}, "
            f"not to the folder {project_dir.name!r}",
            RefusalKind.INVALID_PROJECT,
        )
    return import_project(backup, workspace=project_dir.parent, force=True, store=store, now=now)
