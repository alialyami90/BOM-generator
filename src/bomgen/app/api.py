"""The Python API the desktop app's UI calls through pywebview (plan M10, ADR 0015).

pywebview exposes every public attribute of the object given as ``js_api`` to the
page, so each public method of :class:`Api` is an endpoint and everything else is
private. An endpoint returns an envelope, ``{"ok": true, "data": ...}`` or
``{"ok": false, "error": {"kind": ..., "message": ...}}``, so the UI always gets
text it can show. Endpoints call the engine and the stores and reshape their
results for JSON; they hold no business rule.
"""

from __future__ import annotations

import dataclasses
import errno
import functools
import os
import subprocess
import sys
import threading
import traceback
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path, PurePath
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from bomgen import __version__
from bomgen.app.projects import RecentProjects, project_files, summarize
from bomgen.app.substations import (
    ProjectInvalidError,
    SubstationNotFoundError,
    substation_page,
)
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.io.errors import InputError
from bomgen.io.loader import PROJECT_FILE, load_library
from bomgen.library_store.device_db import DeviceRecord, load_device_records
from bomgen.library_store.manifest import Manifest
from bomgen.library_store.preview import preview_library_import
from bomgen.library_store.service import import_library
from bomgen.library_store.store import InstalledLibrary, LibraryStore, default_library_home
from bomgen.library_store.versions import Version
from bomgen.project_store import (
    backup_project,
    export_project,
    import_project,
    list_backups,
    preview_backup_restore,
    preview_project_import,
    restore_backup,
)
from bomgen.project_store.manifest import PROJECT_SUFFIX
from bomgen.project_store.workspace import default_workspace

APP_TITLE = "BOM Generator"
# webview.FileDialog values, kept here so pywebview is imported only by window.py
OPEN_DIALOG, FOLDER_DIALOG, SAVE_DIALOG = 10, 20, 30
FILE_TYPES = {
    "bomlib": "Library packages (*.bomlib)",
    "bomproj": "Project files (*.bomproj)",
}


class FileDialogWindow(Protocol):
    """The part of ``webview.Window`` the API uses."""

    def create_file_dialog(
        self, dialog_type: int = ..., *, file_types: tuple[str, ...] = ..., save_filename: str = ...
    ) -> Any: ...


class AppError(Exception):
    """A refusal the API itself makes; ``kind`` reaches the page like a ``RefusalKind``."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def _first(chosen: object) -> str | None:
    """The path a file dialog returned: a tuple of paths, one path, or None."""
    if isinstance(chosen, str | PurePath):
        return str(chosen) or None
    if isinstance(chosen, Sequence) and chosen:
        return str(chosen[0])
    return None


APP_HOME_ENV = "BOMGEN_APP_HOME"


def default_app_home(env: Mapping[str, str] = os.environ, platform: str = sys.platform) -> Path:
    """Where the app keeps its own files: ``%LOCALAPPDATA%\\bomgen\\app`` on Windows."""
    if override := env.get(APP_HOME_ENV, "").strip():
        return Path(override)
    if platform == "win32":
        local = env.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
    else:
        data = env.get("XDG_DATA_HOME")
        base = Path(data) if data else Path.home() / ".local" / "share"
    return base / "bomgen" / "app"


def _spawn(args: list[str]) -> None:
    """Start a program and reap it in the background, so no zombie is left behind."""
    child = subprocess.Popen(args)
    threading.Thread(target=child.wait, daemon=True).start()


def reveal(
    path: Path, platform: str = sys.platform, run: Callable[[list[str]], object] = _spawn
) -> None:
    """Show ``path`` in the file manager: selected in Explorer, its folder elsewhere."""
    if platform == "win32":
        run(["explorer", f"/select,{path}"])
    else:
        run(["open" if platform == "darwin" else "xdg-open", str(path.parent)])


Envelope = dict[str, object]


def to_json(value: object) -> object:
    """Paths, dates, enums, dataclasses and pydantic models as plain JSON values."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_json(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [to_json(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, PurePath):
        return str(value)
    if isinstance(value, date):  # datetime too
        return value.isoformat()
    return value


def error(kind: str, message: str) -> Envelope:
    return {"ok": False, "error": {"kind": kind, "message": message}}


def endpoint[**P](method: Callable[P, object]) -> Callable[P, Envelope]:
    """Wrap a method so it returns an envelope and never raises into the page."""

    @functools.wraps(method)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Envelope:
        try:
            return {"ok": True, "data": to_json(method(*args, **kwargs))}
        except AppError as exc:
            return error(exc.kind, str(exc))
        except LibraryPackageError as exc:
            return error(exc.kind.value, str(exc))
        except OSError as exc:
            return error("io", str(exc))
        except Exception as exc:  # the page must get text it can show, not a dead promise
            traceback.print_exc()
            return error("internal", f"{type(exc).__name__}: {exc}")

    return wrapper


class Api:
    """Endpoints for the UI. One instance per window."""

    def __init__(self, project_file: Path | None = None, env: Mapping[str, str] = os.environ):
        self._project_file = project_file
        self._env = env
        self._window: FileDialogWindow | None = None
        self._reveal: Callable[[Path], object] = reveal
        self._listed: set[Path] = set()  # files the page was given; show_in_folder opens only these

    def _set_window(self, window: FileDialogWindow) -> None:
        """Called by ``run_window`` once the window exists (it owns the file dialogs)."""
        self._window = window

    def _library_store(self) -> LibraryStore:
        return LibraryStore(default_library_home(self._env))

    def _workspace(self) -> Path:
        return default_workspace(self._env)

    def _recent(self) -> RecentProjects:
        return RecentProjects(default_app_home(self._env))

    def _list(self, *paths: Path) -> None:
        self._listed.update(Path(os.path.abspath(p)) for p in paths)

    def _dialog(self, dialog_type: int, kind: str, save_filename: str = "") -> str | None:
        if kind not in FILE_TYPES:
            raise AppError("unknown_file_kind", f"Unknown kind of file: {kind}")
        if self._window is None:
            return None
        options: dict[str, Any] = {"file_types": (FILE_TYPES[kind],)}
        if save_filename:
            options["save_filename"] = save_filename
        return _first(self._window.create_file_dialog(dialog_type, **options))

    def _active_library(self) -> InstalledLibrary | None:
        """The library the app shows: the first installed one with an active version.

        Without one, the first installed library, so its versions can be made active.
        """
        installed = self._library_store().list()
        return next((lib for lib in installed if lib.active), installed[0] if installed else None)

    def _manifest(self, name: str, version: str) -> tuple[Manifest | None, str | None]:
        """An installed version's manifest, or why it cannot be read."""
        try:
            return self._library_store().manifest(name, version), None
        except ValidationError:
            return None, f"{name} {version}: its manifest.json is damaged"
        except OSError as exc:
            return None, f"{name} {version}: its manifest.json cannot be read ({exc.strerror})"

    @endpoint
    def app_info(self) -> dict[str, Any]:
        """Version, how the app was started, the workspace and the installed libraries."""
        return {
            "title": APP_TITLE,
            "version": __version__,
            "project_file": self._project_file,
            "workspace": default_workspace(self._env),
            "libraries": self._library_store().list(),
        }

    @endpoint
    def choose_file(self, kind: str) -> str | None:
        """Ask for a ``.bomlib`` or ``.bomproj`` file; None when the user cancels."""
        return self._dialog(OPEN_DIALOG, kind)

    # -- Library (docs/ui/screens.md: Library, Import update and installed versions) --

    @endpoint
    def library_overview(self) -> dict[str, Any]:
        """The active library's facts, its devices in file order, and their device records."""
        installed = self._active_library()
        if installed is None or installed.active is None:
            return {"library": None, "devices": [], "records": {}, "records_problem": None}
        store = self._library_store()
        manifest, problem = self._manifest(installed.name, installed.active)
        try:
            library = load_library(store.library_file(installed.name, installed.active))
        except InputError as exc:
            raise LibraryPackageError(
                f"library {installed.name} {installed.active} is damaged: {exc}",
                RefusalKind.STORE_DAMAGED,
            ) from exc
        records: dict[str, DeviceRecord] = {}
        records_problem: str | None = None
        try:
            records = load_device_records(store, installed.name, installed.active)
        except LibraryPackageError as exc:  # datasheets are extra; the library still shows
            records_problem = str(exc)
        return {
            "library": {
                "name": installed.name,
                "version": installed.active,
                "created": manifest.created if manifest else None,
                "notes": manifest.release_notes if manifest else None,
                "problem": problem,
            },
            "devices": [device.model_dump(mode="json") for device in library.devices],
            "records": records,
            "records_problem": records_problem,
        }

    @endpoint
    def library_versions(self) -> dict[str, Any]:
        """Installed versions of the active library, newest first."""
        installed = self._active_library()
        if installed is None:
            return {"name": None, "versions": []}
        rows = []
        for version in sorted(installed.versions, key=Version.parse, reverse=True):
            manifest, problem = self._manifest(installed.name, version)
            rows.append(
                {
                    "version": version,
                    "released": manifest.created if manifest else None,
                    "notes": manifest.release_notes if manifest else None,
                    "active": version == installed.active,
                    "problem": problem,
                }
            )
        return {"name": installed.name, "versions": rows}

    @endpoint
    def preview_library_import(self, path: str, force: bool = False) -> dict[str, Any]:
        """The import review of a ``.bomlib``: every check, the facts and the changes."""
        package = Path(path)
        preview = preview_library_import(package, force=force, store=self._library_store())
        return {
            **{f.name: getattr(preview, f.name) for f in dataclasses.fields(preview)},
            "can_import": preview.can_import,
            "file_name": package.name,
            "package_size": package.stat().st_size if package.is_file() else None,
        }

    @endpoint
    def import_library(self, path: str, force: bool = False) -> dict[str, Any]:
        """Install and activate a ``.bomlib``; the previous version stays installed."""
        result = import_library(Path(path), force=force, store=self._library_store())
        return {"manifest": result.manifest, "previous": result.previous, "diff": result.diff}

    @endpoint
    def activate_library_version(self, name: str, version: str) -> str:
        """Make an installed version active again. Project files are not touched."""
        return self._library_store().rollback(name, to=version)

    # -- Projects (docs/ui/screens.md: Home, Project, Back up and share) --

    @endpoint
    def list_projects(self) -> list[dict[str, Any]]:
        """The workspace's projects and the ones opened from elsewhere, newest change first."""
        store = self._library_store()
        rows = [summarize(f, store) for f in project_files(self._workspace(), self._recent())]
        self._list(*(r["file"] for r in rows))
        return sorted(
            rows, key=lambda r: r["changed"] or datetime.min.replace(tzinfo=UTC), reverse=True
        )

    @endpoint
    def open_project(self, project_file: str) -> dict[str, Any]:
        """The Project page: the summary plus info, defaults, register and located problems."""
        file = Path(project_file)
        if not file.is_file():
            raise FileNotFoundError(errno.ENOENT, "No project file here", str(file))
        page = summarize(file, self._library_store(), details=True)
        self._list(file)
        workspace = self._workspace().resolve()
        if workspace not in file.resolve().parents:
            self._recent().add(file)
        return page

    @endpoint
    def choose_project_folder(self) -> str | None:
        """Ask for a folder holding ``project.yaml``; its path, or None when cancelled."""
        if self._window is None:
            return None
        folder = _first(self._window.create_file_dialog(FOLDER_DIALOG))
        if folder is None:
            return None
        project_file = Path(folder) / PROJECT_FILE
        if not project_file.is_file():
            raise AppError(
                "not_a_project", f"{folder} has no {PROJECT_FILE}. Choose the project's folder."
            )
        return str(project_file)

    @endpoint
    def export_project(self, project_file: str) -> dict[str, Any] | None:
        """Ask where to save, then write the project as one ``.bomproj``; None when cancelled."""
        file = Path(project_file)
        name = f"{file.parent.name}-{datetime.now():%Y-%m-%d}{PROJECT_SUFFIX}"
        target = self._dialog(SAVE_DIALOG, "bomproj", save_filename=name)
        if target is None:
            return None
        out = Path(target)
        exported = export_project(
            file, out if out.suffix == PROJECT_SUFFIX else out.with_suffix(PROJECT_SUFFIX)
        )
        self._list(exported.path)
        return {"path": exported.path, "size": exported.path.stat().st_size}

    @endpoint
    def backup_project(self, project_file: str) -> dict[str, Any]:
        """Save a backup in the project's ``Backups`` folder."""
        path = backup_project(Path(project_file))
        self._list(path)
        return {"path": path, "size": path.stat().st_size}

    @endpoint
    def list_backups(self, project_file: str) -> list[Any]:
        """The project's backups, newest first."""
        backups = list_backups(Path(project_file))
        self._list(*(b.path for b in backups))
        return backups

    @endpoint
    def show_in_folder(self, path: str) -> None:
        """Open the file manager on a backup, an export or a project file the page was given."""
        target = Path(path)
        if Path(os.path.abspath(target)) not in self._listed:
            raise AppError("not_listed", "Only files the app has listed can be shown")
        if not target.exists():
            raise FileNotFoundError(errno.ENOENT, "This file is no longer there", path)
        self._reveal(target)

    # -- Substation (docs/ui/screens.md: Substation settings, Network) --

    @endpoint
    def open_substation(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """Settings and Network inputs of one substation, with its located problems."""
        try:
            return substation_page(Path(project_file), substation_id, self._library_store())
        except ProjectInvalidError as exc:
            raise AppError("project_invalid", f"The project cannot be read: {exc}") from None
        except SubstationNotFoundError:
            raise AppError(
                "not_found", f"The project has no substation {substation_id!r}"
            ) from None

    @endpoint
    def preview_project_import(self, path: str) -> dict[str, Any]:
        """The import review of a ``.bomproj``; nothing is written."""
        package = Path(path)
        preview = preview_project_import(
            package, workspace=self._workspace(), store=self._library_store()
        )
        return self._preview(package, preview)

    @endpoint
    def import_project(
        self, path: str, replace: bool = False, rename_to: str | None = None
    ) -> dict[str, Any]:
        """Import a ``.bomproj`` into the workspace.

        On a clash, ``replace`` backs up and replaces the project; ``rename_to`` keeps both
        by importing under that new id (the preview's ``suggested_id``).
        """
        result = import_project(
            Path(path),
            workspace=self._workspace(),
            force=replace,
            store=self._library_store(),
            rename_to=rename_to or None,
        )
        return self._imported(result)

    @endpoint
    def preview_backup_restore(self, backup: str) -> dict[str, Any]:
        """The review before a restore: its refusals, then the import dry-run."""
        package = Path(backup)
        return self._preview(package, preview_backup_restore(package, store=self._library_store()))

    @endpoint
    def restore_backup(self, backup: str) -> dict[str, Any]:
        """Put a backup back as its project; the current state is backed up first."""
        return self._imported(restore_backup(Path(backup), store=self._library_store()))

    @staticmethod
    def _preview(package: Path, preview: Any) -> dict[str, Any]:
        return {
            **{f.name: getattr(preview, f.name) for f in dataclasses.fields(preview)},
            "can_import": preview.can_import,
            "file_name": package.name,
            "package_size": package.stat().st_size if package.is_file() else None,
        }

    @staticmethod
    def _imported(result: Any) -> dict[str, Any]:
        return {
            "project_file": result.project_dir / PROJECT_FILE,
            "replaced": result.replaced,
            "backup": result.backup,
            "library_note": result.library_note,
            "manifest": result.manifest,
        }
