"""The installed-library store: one per user, no admin rights (ADR 0008).

Layout under the store root::

    <name>/<version>/manifest.json, library.yaml, extra files
    <name>/active          text file holding the active version

`active` is a plain file rather than a symlink because symlinks need admin
rights on Windows. Every version stays installed so it can be rolled back to.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bomgen.library_store.diff import LibraryDiff, diff_libraries, parse_library
from bomgen.library_store.errors import LibraryPackageError
from bomgen.library_store.manifest import LIBRARY_FILE, MANIFEST_NAME, Manifest
from bomgen.library_store.package import PackageContents, read_package
from bomgen.library_store.versions import Version

HOME_ENV = "BOMGEN_LIBRARY_HOME"
ACTIVE_FILE = "active"

Validator = Callable[[Path], None]


def default_library_home(env: Mapping[str, str] = os.environ, platform: str = sys.platform) -> Path:
    """`%LOCALAPPDATA%\\bomgen\\libraries` on Windows, the XDG data dir elsewhere."""
    if override := env.get(HOME_ENV):
        return Path(override)
    if platform == "win32":
        base = (
            Path(env["LOCALAPPDATA"])
            if env.get("LOCALAPPDATA")
            else Path.home() / "AppData" / "Local"
        )
    else:
        base = (
            Path(env["XDG_DATA_HOME"])
            if env.get("XDG_DATA_HOME")
            else Path.home() / ".local" / "share"
        )
    return base / "bomgen" / "libraries"


@dataclass(frozen=True)
class LibraryRef:
    name: str
    version: str


def library_mismatch(recorded: LibraryRef, active: LibraryRef | None) -> str | None:
    """Warning for a project rebuilt against a library other than the one it recorded."""
    if active is None:
        return (
            f"project was built with library {recorded.name} {recorded.version}, "
            "which is not installed"
        )
    if active != recorded:
        return (
            f"project was built with library {recorded.name} {recorded.version}; "
            f"the active version is {active.version}"
        )
    return None


@dataclass(frozen=True)
class InstalledLibrary:
    name: str
    active: str | None
    versions: list[str]
    problem: str | None = None


@dataclass(frozen=True)
class ImportResult:
    manifest: Manifest
    previous: str | None
    diff: LibraryDiff


def _write_text_atomic(path: Path, text: str) -> None:
    partial = path.with_name(f".{path.name}.{uuid.uuid4().hex}")
    try:
        partial.write_text(text, encoding="utf-8")
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


class LibraryStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    # -- reading -----------------------------------------------------------------

    def versions(self, name: str) -> list[str]:
        """Installed versions of `name`, oldest first."""
        directory = self.root / name
        if not directory.is_dir():
            return []
        found: list[Version] = []
        for child in directory.iterdir():
            if not (child / MANIFEST_NAME).is_file():
                continue
            try:
                found.append(Version.parse(child.name))
            except ValueError:
                continue
        return [str(v) for v in sorted(found)]

    def active_version(self, name: str) -> str | None:
        pointer = self.root / name / ACTIVE_FILE
        if not pointer.is_file():
            return None
        version = pointer.read_text(encoding="utf-8").strip()
        if version not in self.versions(name):
            raise LibraryPackageError(
                f"library {name}: the active version {version!r} is not installed; "
                "import a package or run rollback --to <version>"
            )
        return version

    def list(self) -> list[InstalledLibrary]:
        if not self.root.is_dir():
            return []
        libraries: list[InstalledLibrary] = []
        for directory in sorted(p for p in self.root.iterdir() if p.is_dir()):
            versions = self.versions(directory.name)
            if not versions:
                continue
            try:
                active, problem = self.active_version(directory.name), None
            except LibraryPackageError as exc:
                active, problem = None, str(exc)
            libraries.append(InstalledLibrary(directory.name, active, versions, problem))
        return libraries

    def library_file(self, name: str, version: str | None = None) -> Path:
        """Path of the installed `library.yaml` (the active version by default)."""
        version = version or self.active_version(name)
        if version is None or version not in self.versions(name):
            raise LibraryPackageError(f"library {name} {version or ''} is not installed".strip())
        return self.root / name / version / LIBRARY_FILE

    def manifest(self, name: str, version: str) -> Manifest:
        path = self.root / name / version / MANIFEST_NAME
        return Manifest.model_validate_json(path.read_bytes())

    # -- changing ----------------------------------------------------------------

    def preview_import(self, path: Path, *, force: bool = False) -> ImportResult:
        """Everything `import_package` checks and reports, without installing."""
        _, result = self._plan_import(path, force)
        return result

    def import_package(
        self, path: Path, *, force: bool = False, validate: Validator | None = None
    ) -> ImportResult:
        """Verify, install and activate a package.

        `validate` gets the extracted `library.yaml` before anything is committed;
        if it raises, the store is left exactly as it was.
        """
        contents, result = self._plan_import(path, force)
        name, version = contents.manifest.name, contents.manifest.version
        library_dir = self.root / name
        library_dir.mkdir(parents=True, exist_ok=True)
        incoming = library_dir / f".incoming-{uuid.uuid4().hex}"
        replaced = library_dir / f".replaced-{uuid.uuid4().hex}"
        target = library_dir / version
        try:
            self._extract(contents, incoming)
            if validate is not None:
                validate(incoming / LIBRARY_FILE)
            if target.exists():
                os.replace(target, replaced)
            try:
                os.replace(incoming, target)
            except OSError:
                if replaced.exists():
                    os.replace(replaced, target)
                raise
            _write_text_atomic(library_dir / ACTIVE_FILE, version)
        finally:
            shutil.rmtree(incoming, ignore_errors=True)
            shutil.rmtree(replaced, ignore_errors=True)
        return result

    def rollback(self, name: str, to: str | None = None) -> str:
        """Activate `to`, or the newest installed version older than the active one."""
        versions = self.versions(name)
        if not versions:
            raise LibraryPackageError(f"library {name} is not installed")
        if to is not None:
            if to not in versions:
                raise LibraryPackageError(
                    f"library {name} {to} is not installed (installed: {', '.join(versions)})"
                )
            target = to
        else:
            active = self.active_version(name)
            if active is None:
                raise LibraryPackageError(f"library {name} has no active version; use --to")
            older = [v for v in versions if Version.parse(v) < Version.parse(active)]
            if not older:
                raise LibraryPackageError(f"library {name} has no older version than {active}")
            target = older[-1]
        _write_text_atomic(self.root / name / ACTIVE_FILE, target)
        return target

    # -- helpers -----------------------------------------------------------------

    def _plan_import(self, path: Path, force: bool) -> tuple[PackageContents, ImportResult]:
        contents = read_package(path)
        manifest = contents.manifest
        try:
            active = self.active_version(manifest.name)
        except LibraryPackageError:
            active = None  # a broken pointer is repaired by the import
        if manifest.version in self.versions(manifest.name) and not force:
            hint = (
                ""
                if manifest.version == active
                else f"; run rollback --to {manifest.version} to activate it"
            )
            raise LibraryPackageError(
                f"library {manifest.name} {manifest.version} is already installed{hint}"
            )
        if active is not None and manifest.parsed_version < Version.parse(active) and not force:
            raise LibraryPackageError(
                f"library {manifest.name} {manifest.version} is older than the active "
                f"{active}; use force to downgrade"
            )
        old_library: dict[str, Any] | None = None
        old_files: dict[str, str] = {}
        if active is not None:
            old_library = parse_library(self.library_file(manifest.name, active).read_bytes())
            old_files = self.manifest(manifest.name, active).files
        diff = diff_libraries(old_library, contents.library, old_files, manifest.files)
        return contents, ImportResult(manifest, active, diff)

    @staticmethod
    def _extract(contents: PackageContents, directory: Path) -> None:
        directory.mkdir()
        for member, data in contents.files.items():
            target = directory / member
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        manifest_json = json.dumps(contents.manifest.model_dump(mode="json"), indent=2)
        (directory / MANIFEST_NAME).write_text(manifest_json, encoding="utf-8")
