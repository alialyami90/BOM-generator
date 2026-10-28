"""Import a `.bomproj` file into the workspace (ADR 0012)."""

from __future__ import annotations

import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from bomgen.bundle.container import MANIFEST_NAME, read_bundle, sha256
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.store import (
    LibraryRef,
    LibraryStore,
    default_library_home,
    library_mismatch,
)
from bomgen.project_store.backup import backup_directory
from bomgen.project_store.export import (
    BACKUPS_DIR,
    SKIPPED_DIRS,
    ProjectIdentity,
    parse_project_identity,
    read_project_identity,
)
from bomgen.project_store.manifest import (
    PROJECT_FILE,
    PROJECT_FORMAT_VERSION,
    ProjectManifest,
    is_valid_project_id,
)
from bomgen.project_store.rename import rewrite_project_id
from bomgen.project_store.workspace import default_workspace


@dataclass(frozen=True)
class ProjectImportResult:
    manifest: ProjectManifest
    project_dir: Path
    replaced: bool
    backup: Path | None
    library_note: str | None
    library_hint: str | None = None


def parse_project_manifest(raw: object) -> ProjectManifest:
    if isinstance(raw, dict) and "project_id" not in raw and "schema_version" in raw:
        raise LibraryPackageError(
            "this is a .bomlib library, not a .bomproj project",
            hint="use 'bomgen library import' to install it",
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


@dataclass(frozen=True)
class LibraryNote:
    """`text` says how the project's library differs; `hint` is the command-line remedy."""

    text: str
    hint: str


def library_note(manifest: ProjectManifest, store: LibraryStore) -> LibraryNote | None:
    """The note for a project built with a library other than the active one."""
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
        text = f"project was built with library {name} {version}, which is installed but not active"
        if active:
            text += f"; the active version is {active}"
        return LibraryNote(text, f"bomgen library rollback {name} --to {version}")
    return LibraryNote(problem, f"bomgen library import {name}-{version}.bomlib")


def import_project(
    package: Path,
    *,
    workspace: Path | None = None,
    force: bool = False,
    store: LibraryStore | None = None,
    now: datetime | None = None,
    rename_to: str | None = None,
) -> ProjectImportResult:
    """Verify a `.bomproj` and unpack it into `<workspace>/<project-id>/`.

    An existing project with the same id is refused unless `force`; a forced
    import saves it to its `Backups/` first, keeps its `Backups/` and `out/`
    folders, and restores it if the import fails.

    With `rename_to` the project is unpacked under that new id instead, with
    `project.id` rewritten in `project.yaml`; an id that is taken is always
    refused, so nothing is replaced and `force` does not apply.
    """
    if rename_to is not None and force:
        raise LibraryPackageError(
            "a new project id and force cannot be combined: a renamed import never replaces",
            RefusalKind.INVALID_PROJECT,
        )
    manifest, files = read_bundle(package, parse_project_manifest, ".bomproj project file")
    check_identity(manifest, files)
    refuse_build_output(files)
    note = library_note_or_none(manifest, store or LibraryStore(default_library_home()))
    if rename_to is not None:
        manifest, files = _renamed(manifest, files, rename_to)
    workspace = workspace or default_workspace()
    target = workspace / manifest.project_id
    exists = target.exists()
    if exists and rename_to is not None:
        raise LibraryPackageError(
            f"project {rename_to!r} already exists in {workspace}", RefusalKind.PROJECT_EXISTS
        )
    if exists and not force:
        raise LibraryPackageError(
            f"project {manifest.project_id!r} already exists in {workspace}",
            RefusalKind.PROJECT_EXISTS,
            hint=(
                "import with --force to replace it (it is backed up first), "
                "or with --rename-to <new id> to keep both"
            ),
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
        library_note=note.text if note else None,
        library_hint=note.hint if note else None,
    )


def _renamed(
    manifest: ProjectManifest, files: dict[str, bytes], new_id: str
) -> tuple[ProjectManifest, dict[str, bytes]]:
    """The package as it would read under `new_id`; the original bytes are not changed."""
    if not is_valid_project_id(new_id):
        raise LibraryPackageError(
            f"{new_id!r} is not a usable project id: 1-64 letters, digits, '.', '_' or '-', "
            "starting with a letter or digit",
            RefusalKind.INVALID_PROJECT,
        )
    text = files[PROJECT_FILE].decode("utf-8")
    rewritten = rewrite_project_id(text, new_id).encode("utf-8")
    renamed = manifest.model_copy(
        update={
            "project_id": new_id,
            "files": {**manifest.files, PROJECT_FILE: sha256(rewritten)},
        }
    )
    return renamed, {**files, PROJECT_FILE: rewritten}


def check_identity(manifest: ProjectManifest, files: dict[str, bytes]) -> None:
    """The manifest and the packed `project.yaml` must name the same project."""
    identity = parse_project_identity(files[PROJECT_FILE].decode("utf-8", "replace"))
    if identity.id != manifest.project_id:
        raise LibraryPackageError(
            f"the manifest names project {manifest.project_id!r} "
            f"but {PROJECT_FILE} names {identity.id!r}"
        )


def refuse_build_output(files: dict[str, bytes]) -> None:
    """A `.bomproj` never holds `out/`, `.git/`, caches or the top-level `Backups/`."""
    for name in files:
        parts = name.split("/")
        if SKIPPED_DIRS.intersection(parts[:-1]) or parts[0] == BACKUPS_DIR or name in SKIPPED_DIRS:
            raise LibraryPackageError(
                f"package contains {name!r}, build output a .bomproj never holds"
            )


def library_note_or_none(manifest: ProjectManifest, store: LibraryStore) -> LibraryNote | None:
    """The note is advice; a locked library folder must not turn a good import into an error."""
    try:
        return library_note(manifest, store)
    except (LibraryPackageError, OSError):
        return None


def _backup_existing(project_dir: Path, project_id: str, now: datetime | None) -> Path:
    try:
        try:
            identity = read_project_identity(project_dir / PROJECT_FILE)
            if identity.id != project_id:
                identity = ProjectIdentity(
                    project_id, identity.library_name, identity.library_version
                )
        except LibraryPackageError:
            identity = ProjectIdentity(project_id, None, None)
        return backup_directory(project_dir, identity, now=now)
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
            keep = name in SKIPPED_DIRS or (relative == Path() and name == BACKUPS_DIR)
            if keep:
                dirs.remove(name)
                shutil.copytree(
                    here / name, new / relative / name, symlinks=True, dirs_exist_ok=True
                )
