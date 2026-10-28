"""Export a project folder as a `.bomproj` file (ADR 0012)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import yaml
from pydantic import ValidationError

import bomgen
from bomgen.bundle.container import collect_tree, sha256, write_bundle
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.versions import Version
from bomgen.project_store.manifest import (
    PROJECT_FORMAT_VERSION,
    PROJECT_SUFFIX,
    ProjectManifest,
    is_valid_project_id,
)

_SKIPPED_DIRS = frozenset({"out", ".git", "__pycache__"})
BACKUPS_DIR = "Backups"


@dataclass(frozen=True)
class ProjectIdentity:
    id: str
    library_name: str | None
    library_version: str | None


@dataclass(frozen=True)
class ProjectExport:
    path: Path
    manifest: ProjectManifest


def _invalid(message: str) -> LibraryPackageError:
    return LibraryPackageError(message, RefusalKind.INVALID_PROJECT)


def read_project_identity(project_file: Path) -> ProjectIdentity:
    """Read the project id and the library it was built with from `project.yaml`.

    Reads plain YAML so exporting does not depend on the input models.
    """
    try:
        document = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise _invalid(f"cannot read {project_file}: {exc}") from exc
    project = document.get("project") if isinstance(document, dict) else None
    project_id = project.get("id") if isinstance(project, dict) else None
    if not is_valid_project_id(project_id):
        raise _invalid(
            f"{project_file.name}: project.id must be 1-64 letters, digits, '.', '_' or '-' "
            f"(got {project_id!r})"
        )
    library = document.get("library")
    if library is None:
        return ProjectIdentity(project_id, None, None)
    name = library.get("name") if isinstance(library, dict) else None
    version = library.get("version") if isinstance(library, dict) else None
    try:
        if not isinstance(name, str) or not name or not isinstance(version, str):
            raise ValueError("library needs a name and a version")
        Version.parse(version)
    except ValueError as exc:
        raise _invalid(f"{project_file.name}: library: {exc}") from exc
    return ProjectIdentity(project_id, name, version)


def project_files(project_dir: Path) -> dict[str, bytes]:
    """The files a `.bomproj` carries: everything except build outputs and backups."""

    def include(relative: PurePosixPath, is_dir: bool) -> bool:
        if is_dir:
            return relative.name not in _SKIPPED_DIRS and relative != PurePosixPath(BACKUPS_DIR)
        return relative.suffix != PROJECT_SUFFIX and not relative.name.endswith(".partial")

    return collect_tree(project_dir, include=include)


def export_project(
    project_file: Path, out: Path | None = None, *, created: datetime | None = None
) -> ProjectExport:
    """Write the project folder holding `project_file` as one `.bomproj` file."""
    identity = read_project_identity(project_file)
    files = project_files(project_file.parent)
    manifest = _manifest(identity, files, created)
    out = out or Path.cwd() / f"{identity.id}{PROJECT_SUFFIX}"
    write_bundle(out, manifest, files)
    return ProjectExport(out, manifest)


def _manifest(
    identity: ProjectIdentity, files: dict[str, bytes], created: datetime | None
) -> ProjectManifest:
    try:
        return ProjectManifest(
            format_version=PROJECT_FORMAT_VERSION,
            project_id=identity.id,
            library_name=identity.library_name,
            library_version=identity.library_version,
            app_version=bomgen.__version__,
            created=created or datetime.now(UTC).replace(microsecond=0),
            files={name: sha256(data) for name, data in sorted(files.items())},
        )
    except ValidationError as exc:
        raise _invalid(f"invalid project details: {exc}") from exc
