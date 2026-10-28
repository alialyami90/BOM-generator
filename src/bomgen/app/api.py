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
import functools
import os
import traceback
from collections.abc import Callable, Mapping
from datetime import date
from enum import Enum
from pathlib import Path, PurePath
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from bomgen import __version__
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.io.errors import InputError
from bomgen.io.loader import load_library
from bomgen.library_store.device_db import DeviceRecord, load_device_records
from bomgen.library_store.manifest import Manifest
from bomgen.library_store.preview import preview_library_import
from bomgen.library_store.service import import_library
from bomgen.library_store.store import InstalledLibrary, LibraryStore, default_library_home
from bomgen.library_store.versions import Version
from bomgen.project_store.workspace import default_workspace

APP_TITLE = "BOM Generator"
OPEN_DIALOG = 10  # webview.FileDialog.OPEN, kept here so pywebview is imported only by window.py
FILE_TYPES = {
    "bomlib": "Library packages (*.bomlib)",
    "bomproj": "Project files (*.bomproj)",
}


class FileDialogWindow(Protocol):
    """The part of ``webview.Window`` the API uses."""

    def create_file_dialog(
        self, dialog_type: int = ..., *, file_types: tuple[str, ...] = ...
    ) -> Any: ...


class AppError(Exception):
    """A refusal the API itself makes; ``kind`` reaches the page like a ``RefusalKind``."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


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

    def _set_window(self, window: FileDialogWindow) -> None:
        """Called by ``run_window`` once the window exists (it owns the file dialogs)."""
        self._window = window

    def _library_store(self) -> LibraryStore:
        return LibraryStore(default_library_home(self._env))

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
        file_type = FILE_TYPES.get(kind)
        if file_type is None:
            raise AppError("unknown_file_kind", f"Unknown kind of file: {kind}")
        if self._window is None:
            return None
        chosen = self._window.create_file_dialog(OPEN_DIALOG, file_types=(file_type,))
        return str(chosen[0]) if chosen else None

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
