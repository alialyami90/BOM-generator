"""Backups: an export into the project's own `Backups/` folder (ADR 0012)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bomgen.bundle.errors import LibraryPackageError
from bomgen.project_store.export import (
    BACKUPS_DIR,
    ProjectIdentity,
    export_directory,
    read_project_identity,
)
from bomgen.project_store.manifest import PROJECT_SUFFIX


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
            return export_directory(project_dir, identity, target).path
    raise LibraryPackageError(f"too many backups in {backups} for {stamp}")
