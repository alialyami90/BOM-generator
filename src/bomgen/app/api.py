"""The Python API the desktop app's UI calls through pywebview (plan M10, ADR 0015).

pywebview exposes every public attribute of the object given as ``js_api`` to the
page, so each public method of :class:`Api` is an endpoint and everything else is
private. An endpoint returns an envelope, ``{"ok": true, "data": ...}`` or
``{"ok": false, "error": {"kind": ..., "message": ...}}``, so the UI always gets
text it can show. Endpoints call the engine and the stores and reshape their
results for JSON; they hold no business rule.
"""

from __future__ import annotations

import contextlib
import dataclasses
import errno
import functools
import json
import os
import subprocess
import sys
import threading
import traceback
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path, PurePath
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from bomgen import __version__
from bomgen.app import library_csv
from bomgen.app.catalogues import catalogues_page
from bomgen.app.device_preview import device_preview_page
from bomgen.app.editing import (
    Page,
    edit_reply,
    layout_check,
    layout_issues,
    panel_options_page,
)
from bomgen.app.library_edit import EditRefusedError, LibraryEditor, PendingEdits
from bomgen.app.loose import loose_page
from bomgen.app.network import layout_page
from bomgen.app.output import OutputRefusedError, build_file, build_target, checks_page
from bomgen.app.parts import parts_page
from bomgen.app.preview import preview_page
from bomgen.app.projects import RecentProjects, free_id, project_files, summarize
from bomgen.app.substations import (
    ProjectInvalidError,
    SubstationNotFoundError,
    resolve,
    substation_page,
)
from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import write_generated_panels
from bomgen.io import edit, lifecycle, loose_edit, parts_edit
from bomgen.io.edit import EditError, EditResult
from bomgen.io.errors import InputError
from bomgen.io.fields import (
    PartUse,
    confirm_field,
    insert_item,
    move_item,
    part_users,
    remove_field,
    remove_item,
    set_field,
    validate_field,
)
from bomgen.io.loader import PROJECT_FILE, load_library
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.csv_export import GROUPS as CSV_GROUPS
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
    "xlsx": "Excel workbooks (*.xlsx)",
    "csv": "Spreadsheet tables (*.csv;*.zip)",
    "png": "PNG pictures (*.png)",
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


def open_with_default_app(
    path: Path,
    platform: str = sys.platform,
    run: Callable[[list[str]], object] = _spawn,
    start: Callable[[str], object] | None = None,
) -> None:
    """Open ``path`` in the program the system uses for it, such as Excel for a workbook."""
    if platform == "win32":
        # no command line, so no comma parsing; startfile exists on Windows only
        (start or getattr(os, "startfile"))(str(path))  # noqa: B009
    else:
        run(["open" if platform == "darwin" else "xdg-open", str(path)])


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


@contextlib.contextmanager
def _edit_refusals() -> Iterator[None]:
    """An edit that names something the file does not have changes nothing."""
    try:
        yield
    except EditError as exc:
        raise AppError("edit_refused", str(exc)) from None


DELETED_DIR = "deleted-projects"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _dated(path: Sequence[str | int], value: Any) -> Any:
    """An ISO date typed for an ``issue_date`` (alone or in a row) as a date, so the file
    keeps a YAML date rather than quoted text."""
    if isinstance(value, dict):
        return {k: _dated([k], v) for k, v in value.items()}
    if path and path[-1] == "issue_date" and isinstance(value, str):
        with contextlib.suppress(ValueError):
            return date.fromisoformat(value)
    return value


def _written(result: EditResult) -> None:
    """A writer that wrote nothing refuses with the problems the edit would cause."""
    if not result.written:
        listed = "; ".join(
            f"{i.location}: {i.message}" if i.location else i.message for i in result.issues
        )
        raise AppError("invalid_edit", listed or "The change was not written.")


class Api:
    """Endpoints for the UI. One instance per window."""

    def __init__(self, project_file: Path | None = None, env: Mapping[str, str] = os.environ):
        self._project_file = project_file
        self._env = env
        self._window: FileDialogWindow | None = None
        self._reveal: Callable[[Path], object] = reveal
        self._open: Callable[[Path], object] = open_with_default_app
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
        """The active library's facts, its devices in file order, their device records and
        the commodity catalogues."""
        installed = self._active_library()
        if installed is None or installed.active is None:
            return {
                "library": None,
                "devices": [],
                "records": {},
                "records_problem": None,
                "catalogues": None,
            }
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
            "catalogues": catalogues_page(library.catalogues, set(library.part_ids()), records),
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

    # -- Library editing (docs/ui/editing.md "Library editing (v0.2)", M16) --

    def _editor(self) -> LibraryEditor:
        installed = self._active_library()
        if installed is None:
            raise AppError("not_installed", "No library is installed.")
        return LibraryEditor(
            self._library_store(), PendingEdits(default_app_home(self._env)), installed.name
        )

    @endpoint
    def library_pending(self) -> dict[str, Any]:
        """The pending library changes: one entry per changed field, and the version they make."""
        return self._editor().page()

    @endpoint
    def library_device(self, part_id: str) -> dict[str, Any]:
        """One device with the pending edits applied, and its saved values."""
        try:
            return self._editor().device(part_id)
        except KeyError as exc:
            raise AppError("not_found", f"There is no part {part_id} in the library.") from exc

    @endpoint
    def check_library_field(self, part_id: str, field: str, value: object) -> str | None:
        """The model's message for setting a device field to `value`, or None when it fits."""
        return self._editor().check(part_id, field, value)

    @endpoint
    def add_library_edits(
        self, edits: list[dict[str, Any]], record_edits: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Add edits to the pending set; all are refused when one leaves the library invalid.
        `record_edits` brings back discarded datasheet edits (Undo)."""
        try:
            return self._editor().add(edits, record_edits or ())
        except (EditRefusedError, ValidationError) as exc:
            raise AppError("invalid_edit", f"The library cannot take this change: {exc}") from exc

    @endpoint
    def library_alternatives(self, part_id: str) -> dict[str, Any]:
        """The device and its alternatives (same `alt_group`) with the figures they differ in."""
        try:
            return self._editor().alternatives(part_id)
        except KeyError as exc:
            raise AppError("not_found", f"There is no part {part_id} in the library.") from exc

    @endpoint
    def check_library_record(self, part_id: str, path: str, value: object) -> str | None:
        """The model's message for setting a datasheet record field (a dotted path)."""
        try:
            return self._editor().check_record(part_id, path, value)
        except KeyError as exc:
            raise AppError("not_found", f"Part {part_id} has no datasheet record.") from exc

    @endpoint
    def set_library_record_fields(self, part_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Set datasheet record fields (dotted paths; null empties one) in the pending set."""
        try:
            return self._editor().set_record_fields(part_id, fields)
        except KeyError as exc:
            raise AppError("not_found", f"Part {part_id} has no datasheet record.") from exc
        except (EditRefusedError, ValidationError) as exc:
            raise AppError("invalid_edit", f"The record cannot take this change: {exc}") from exc

    @endpoint
    def add_library_device(
        self,
        part_id: str,
        category: str,
        make: str,
        model: str,
        copy_of: str | None = None,
        alt_group: str | None = None,
    ) -> dict[str, Any]:
        """Add a new device to the pending set, blank or as a copy of another part."""
        try:
            return self._editor().add_device(part_id, category, make, model, copy_of, alt_group)
        except KeyError as exc:
            raise AppError("not_found", f"There is no part {copy_of} in the library.") from exc
        except (EditRefusedError, ValidationError) as exc:
            raise AppError("invalid_edit", f"The library cannot take this change: {exc}") from exc

    @endpoint
    def library_part_users(
        self, part_id: str, project_file: str, substation_id: str
    ) -> dict[str, Any]:
        """The rows of the open substation, and of its library, that use ``part_id``; ``uses`` is
        None when the substation cannot be read (its problems are on Checks)."""
        with self._substation(substation_id):
            found = resolve(Path(project_file), substation_id, self._library_store())
        if found.loaded is None:
            return {"substation": substation_id, "uses": None}
        uses = part_users(found.loaded, part_id)
        panels = {file: panel for panel, file in found.loaded.panel_files.items()}

        def use(u: PartUse) -> dict[str, Any]:
            # an equipment row's index, for Use this instead (docs/ui/editing.md, Alternatives)
            index = u.path[1] if u.where == "equipment" else None
            if u.where != "panel":
                return {"where": u.where, "name": u.name, "panel": None, "index": index}
            panel = panels[u.file] if u.file is not None else None
            # part_users names a panel row "<panel>: <tag>"
            name = u.name.split(": ", 1)[-1]
            return {"where": u.where, "name": name, "panel": panel, "index": None}

        return {
            "substation": found.loaded.substation.substation.name or substation_id,
            "uses": [use(u) for u in uses],
        }

    # -- Library export and CSV import (docs/ui/editing.md: Export and import) --

    @endpoint
    def export_library_csv(
        self, include: list[str], folder: str | None = None
    ) -> dict[str, Any] | None:
        """Write the active version's tables (devices, catalogues) as CSV files in a new folder
        inside `folder`, asked for when not given; None when the person cancels."""
        unknown = [group for group in include if group not in CSV_GROUPS]
        if unknown or not include:
            raise AppError("invalid_request", f"Choose tables from {', '.join(CSV_GROUPS)}.")
        editor = self._editor()
        chosen = folder or (
            _first(self._window.create_file_dialog(FOLDER_DIALOG)) if self._window else None
        )
        if chosen is None:
            return None
        return library_csv.export_tables(editor.store, editor.name, Path(chosen), include)

    @endpoint
    def export_library_package(self, file: str | None = None) -> dict[str, Any] | None:
        """Write the active version as a `.bomlib` backup; None when the person cancels."""
        editor = self._editor()
        version = editor.store.active_version(editor.name)
        assert version is not None
        target = file or self._dialog(
            SAVE_DIALOG, "bomlib", save_filename=f"{editor.name}-{version}.bomlib"
        )
        if target is None:
            return None
        editor.store.export_package(editor.name, version, Path(target))
        return {"file": target, "version": version}

    @endpoint
    def preview_library_csv(self, path: str) -> dict[str, Any]:
        """The dry run of a CSV import: nothing is written or added."""
        try:
            return library_csv.preview(self._editor(), Path(path))
        except FileNotFoundError as exc:
            raise AppError("not_found", f"{path} is no longer there.") from exc

    @endpoint
    def add_library_csv(self, path: str) -> dict[str, Any]:
        """Add the valid rows of a CSV import to the pending set."""
        try:
            return library_csv.add_to_pending(self._editor(), Path(path))
        except FileNotFoundError as exc:
            raise AppError("not_found", f"{path} is no longer there.") from exc
        except (ValueError, EditRefusedError) as exc:
            raise AppError("invalid_edit", f"The rows cannot be added: {exc}") from exc

    @endpoint
    def discard_library_edits(self) -> dict[str, Any]:
        """Drop every pending change; returns them so the page can undo."""
        return self._editor().discard()

    @endpoint
    def apply_library_edits(self, note: str = "") -> dict[str, Any]:
        """Write the pending changes as a new local version and make it active."""
        return self._editor().apply(note)

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

    # -- Create, rename and delete (docs/ui/editing.md: Creating, Deleting; plan M17d) --

    @endpoint
    def new_project_form(self, name: str = "") -> dict[str, Any]:
        """What the New project dialog shows: the folder the name gives and the library."""
        installed = self._active_library()
        if installed is None or installed.active is None:
            raise AppError("not_installed", "Install a library before creating a project.")
        workspace = self._workspace()
        return {
            "folder": workspace / free_id(name, workspace) if name.strip() else None,
            "workspace": workspace,
            "library": {"name": installed.name, "version": installed.active},
            "versions": installed.versions,
        }

    @endpoint
    def create_project(
        self, name: str, client: str | None, library_version: str, substation: str | None
    ) -> dict[str, Any]:
        """Write a new project in the workspace, and its first substation when named."""
        installed = self._active_library()
        if installed is None:
            raise AppError("not_installed", "Install a library before creating a project.")
        if not name.strip():
            raise AppError("invalid_edit", "A project needs a name.")
        store = self._library_store()
        with _edit_refusals():
            made = lifecycle.create_project(
                self._workspace(),
                name,
                library_name=installed.name,
                library_version=library_version,
                client=(client or "").strip() or None,
                store=store,
            )
        self._list(made.project_file)
        reply: dict[str, Any] = {"project_file": made.project_file, "substation": None}
        if substation and substation.strip():
            reply["substation"] = self._new_substation(made.project_file, substation, None)
        return reply

    def _new_substation(self, project_file: Path, name: str, copy_from: str | None) -> str:
        if not name.strip():
            raise AppError("invalid_edit", "A substation needs a name.")
        substation_id = free_id(name, project_file.parent / lifecycle.SUBSTATIONS)
        with _edit_refusals():
            result = lifecycle.create_substation(
                project_file,
                substation_id,
                name.strip(),
                copy_from=copy_from,
                store=self._library_store(),
            )
        _written(result)
        return substation_id

    @endpoint
    def create_substation(
        self, project_file: str, name: str, copy_from: str | None = None
    ) -> dict[str, Any]:
        """Add a substation, blank or a copy of ``copy_from``; its folder comes from the name."""
        return {"id": self._new_substation(Path(project_file), name, copy_from)}

    @endpoint
    def rename_project(self, project_file: str, name: str) -> dict[str, Any]:
        """Change the project's name; its folder and id stay."""
        return self._rename(Path(project_file), ("project", "name"), name, None)

    @endpoint
    def rename_substation(self, project_file: str, substation_id: str, name: str) -> dict[str, Any]:
        """Change a substation's name; its folder and id stay."""
        return self._rename(Path(project_file), ("substation", "name"), name, substation_id)

    def _rename(
        self, project_file: Path, path: tuple[str, str], name: str, substation_id: str | None
    ) -> dict[str, Any]:
        if not name.strip():
            raise AppError("invalid_edit", "A name cannot be empty.")
        with _edit_refusals():
            result = set_field(
                project_file,
                path,
                name.strip(),
                substation=substation_id,
                store=self._library_store(),
            )
        _written(result)
        return {"name": name.strip()}

    @endpoint
    def delete_substation(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """Back the project up, then remove the substation and its register documents."""
        with self._substation(substation_id), _edit_refusals():
            deleted = lifecycle.delete_substation(
                Path(project_file), substation_id, store=self._library_store()
            )
        _written(deleted.result)
        if deleted.backup is not None:
            self._list(deleted.backup)
        return {"backup": deleted.backup}

    @endpoint
    def delete_project(self, project_file: str) -> dict[str, Any]:
        """Save the project as a ``.bomproj`` in the app's deleted-projects folder, then
        remove its folder; importing that file brings it back."""
        file = Path(project_file)
        if not file.is_file():
            raise FileNotFoundError(errno.ENOENT, "No project file here", str(file))
        with _edit_refusals():  # a .git folder, the home folder or a drive root
            saved = lifecycle.delete_project(file, default_app_home(self._env) / DELETED_DIR)
        self._recent().remove(file)
        self._list(saved)
        return {"saved": saved}

    # -- The Project page's own fields (docs/ui/editing.md, Project > Overview; M17c) --

    @endpoint
    def set_project_field(
        self, project_file: str, path: Sequence[str | int], value: Any
    ) -> dict[str, Any]:
        """Write one field of project.yaml (None or "" removes it, so the default applies);
        refused with the model's message when the project would not load. Returns the page."""
        return self._set_project_field(Path(project_file), path, value)

    def _set_project_field(
        self, file: Path, path: Sequence[str | int], value: Any
    ) -> dict[str, Any]:
        store = self._library_store()
        with _edit_refusals():
            if value is None or value == "":
                result = remove_field(file, tuple(path), store=store)
            else:
                result = set_field(file, tuple(path), _dated(path, value), store=store)
        _written(result)
        return summarize(file, store, details=True)

    @endpoint
    def check_project_field(
        self, project_file: str, path: Sequence[str | int], value: Any
    ) -> str | None:
        """The model's message for setting a project field to ``value``, or None."""
        with _edit_refusals():
            return validate_field(
                Path(project_file), tuple(path), value, store=self._library_store()
            )

    @endpoint
    def confirm_project_field(self, project_file: str, path: Sequence[str | int]) -> dict[str, Any]:
        """Drop the ``ASSUMED`` mark from a project.yaml value; returns the page."""
        file, store = Path(project_file), self._library_store()
        with _edit_refusals():
            result = confirm_field(file, tuple(path), store=store)
        _written(result)
        return summarize(file, store, details=True)

    @endpoint
    def add_document(self, project_file: str, substation_id: str, title: str) -> dict[str, Any]:
        """Add a register document for a substation, keyed from its title, with a blank
        number, revision 00 and today's date; returns the page."""
        file, store = Path(project_file), self._library_store()
        name = title.strip()
        if not name:
            raise AppError("invalid_edit", "Give the document a name.")
        taken = {str(d.get("key")) for d in read_yaml(file).data.get("documents") or []}
        base = lifecycle.project_id_for(f"{substation_id} {name}")
        key, number = base, 2
        while key in taken:
            key, number = f"{base}-{number}", number + 1
        row = {
            "key": key,
            "substation": substation_id,
            "title": name,
            "doc_no": "TBD",
            "rev": "00",
            "issue_date": date.today(),
        }
        with _edit_refusals():
            result = insert_item(file, ("documents",), None, row, store=store)
        _written(result)
        return summarize(file, store, details=True)

    @endpoint
    def remove_document(self, project_file: str, index: int) -> dict[str, Any]:
        """Remove a register document nothing uses; refused with its users otherwise. Returns
        the page and the row as written, for Undo."""
        file, store = Path(project_file), self._library_store()
        rows = summarize(file, store, details=True)["register"]
        if not 0 <= index < len(rows):
            raise AppError("edit_refused", f"There is no document {index + 1} in the register.")
        users = rows[index]["used_by"]
        if users is None:
            raise AppError(
                "edit_refused",
                "Fix the project's problems first: what uses this document is not known.",
            )
        if users:
            raise AppError(
                "edit_refused",
                f"{rows[index]['key']} is used by {', '.join(users)}. "
                "Pick another document there first.",
            )
        row = json.loads(json.dumps(read_yaml(file).data["documents"][index], default=str))
        with _edit_refusals():
            result = remove_item(file, ("documents",), index, store=store)
        _written(result)
        return {"page": summarize(file, store, details=True), "row": row}

    @endpoint
    def restore_document(
        self, project_file: str, row: dict[str, Any], index: int
    ) -> dict[str, Any]:
        """Put a removed register document back at its place (Undo); returns the page."""
        file, store = Path(project_file), self._library_store()
        with _edit_refusals():
            result = insert_item(file, ("documents",), index, _dated([], row), store=store)
        _written(result)
        return summarize(file, store, details=True)

    @endpoint
    def set_project_logo(
        self, project_file: str, source: str | None = None
    ) -> dict[str, Any] | None:
        """Copy a PNG (asked for when not given) into the project's ``assets`` folder and
        point ``project.logo`` at it; None when the person cancels."""
        chosen = source or self._dialog(OPEN_DIALOG, "png")
        if chosen is None:
            return None
        picture = Path(chosen)
        data = picture.read_bytes()
        if not data.startswith(PNG_SIGNATURE):
            raise AppError("invalid_edit", f"{picture.name} is not a PNG picture.")
        file = Path(project_file)
        stem = lifecycle.project_id_for(picture.stem)
        target, number = file.parent / "assets" / f"{stem}.png", 2
        while target.exists() and target.read_bytes() != data:  # never overwrite another logo
            target, number = target.with_name(f"{stem}-{number}.png"), number + 1
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        logo = target.relative_to(file.parent).as_posix()
        return self._set_project_field(file, ["project", "logo"], logo)

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

    def _given(self, path: str) -> Path:
        """A file the page was given by the app, and that is still there."""
        target = Path(path)
        if Path(os.path.abspath(target)) not in self._listed:
            raise AppError("not_listed", "Only files the app has listed can be opened or shown")
        if not target.exists():
            raise FileNotFoundError(errno.ENOENT, "This file is no longer there", path)
        return target

    @endpoint
    def show_in_folder(self, path: str) -> None:
        """Open the file manager on a file the page was given: a backup, an export, a workbook."""
        self._reveal(self._given(path))

    @endpoint
    def open_file(self, path: str) -> None:
        """Open a workbook the app wrote in the program the system uses for it."""
        self._open(self._given(path))

    # -- Substation (docs/ui/screens.md: Substation settings, Network) --

    @endpoint
    def open_substation(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """Settings and Network inputs of one substation, with its located problems."""
        with self._substation(substation_id):
            return substation_page(Path(project_file), substation_id, self._library_store())

    @endpoint
    def set_substation_field(
        self, project_file: str, substation_id: str, path: Sequence[str | int], value: Any
    ) -> dict[str, Any]:
        """Write one field of a substation.yaml (None or "" removes it, so the project's
        default applies); refused with the model's message. Returns the substation page."""
        store = self._library_store()
        with self._substation(substation_id), _edit_refusals():
            if value is None or value == "":
                result = remove_field(
                    Path(project_file), tuple(path), substation=substation_id, store=store
                )
            else:
                result = set_field(
                    Path(project_file), tuple(path), value, substation=substation_id, store=store
                )
        _written(result)
        return substation_page(Path(project_file), substation_id, store)

    @endpoint
    def check_substation_field(
        self, project_file: str, substation_id: str, path: Sequence[str | int], value: Any
    ) -> str | None:
        """The model's message for setting a substation field to ``value``, or None."""
        with self._substation(substation_id), _edit_refusals():
            return validate_field(
                Path(project_file),
                tuple(path),
                value,
                substation=substation_id,
                store=self._library_store(),
            )

    @endpoint
    def add_equipment(
        self, project_file: str, substation_id: str, row: dict[str, Any], index: int | None
    ) -> dict[str, Any]:
        """Insert an equipment row (at the end when ``index`` is None); refused with the
        model's message, e.g. for an id the substation already has. Returns the page."""
        store = self._library_store()
        with self._substation(substation_id), _edit_refusals():
            result = insert_item(
                Path(project_file),
                ("equipment",),
                index,
                row,
                substation=substation_id,
                store=store,
            )
        _written(result)
        return substation_page(Path(project_file), substation_id, store)

    @endpoint
    def remove_equipment(self, project_file: str, substation_id: str, index: int) -> dict[str, Any]:
        """Remove an equipment row; returns the page and the row as written, for Undo."""
        store = self._library_store()
        project = Path(project_file)
        with self._substation(substation_id):
            file = resolve(project, substation_id, store).file
        rows = read_yaml(file).data.get("equipment") or []
        if not 0 <= index < len(rows):
            raise AppError("edit_refused", f"There is no equipment row {index + 1}.")
        row = json.loads(json.dumps(rows[index], default=str))
        with self._substation(substation_id), _edit_refusals():
            result = remove_item(
                project, ("equipment",), index, substation=substation_id, store=store
            )
        _written(result)
        return {"page": substation_page(project, substation_id, store), "row": row}

    # -- Parts (plan M23; docs/ui/screens.md, Parts) --

    @endpoint
    def parts_page(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """The substation page with its Parts rows, part options and default rows."""
        with self._substation(substation_id):
            return parts_page(Path(project_file), substation_id, self._library_store())

    def _parts_write(
        self, project_file: str, substation_id: str, write: Callable[..., EditResult]
    ) -> dict[str, Any]:
        store = self._library_store()
        with self._substation(substation_id), _edit_refusals():
            result = write(Path(project_file), substation_id, store=store)
        _written(result)
        return parts_page(Path(project_file), substation_id, store)

    @endpoint
    def set_part_override(
        self, project_file: str, substation_id: str, index: int, field: str, value: Any
    ) -> dict[str, Any]:
        """Override one library value of equipment row ``index``; ``None`` or the library's
        own value removes the override. Returns the Parts page."""
        return self._parts_write(
            project_file,
            substation_id,
            functools.partial(parts_edit.set_override, index=index, field=field, value=value),
        )

    @endpoint
    def set_sfp_choice(
        self,
        project_file: str,
        substation_id: str,
        index: int,
        speed: str,
        media: str,
        part_id: str | None,
    ) -> dict[str, Any]:
        """Choose the SFP for one speed and media of a switch row; ``None`` is automatic."""
        return self._parts_write(
            project_file,
            substation_id,
            functools.partial(
                parts_edit.set_sfp_choice, index=index, speed=speed, media=media, part_id=part_id
            ),
        )

    @endpoint
    def set_cable_manager(
        self, project_file: str, substation_id: str, index: int, on: bool
    ) -> dict[str, Any]:
        """A network row has a cable manager or not; returns the refreshed Parts page."""
        return self._parts_write(
            project_file,
            substation_id,
            functools.partial(parts_edit.set_cable_manager, index=index, on=on),
        )

    @endpoint
    def set_equipment_part(
        self, project_file: str, substation_id: str, index: int, part_id: str
    ) -> dict[str, Any]:
        """Give equipment row ``index`` another part; ``cleared`` names what described the
        old part and went with it (overrides, sfp, ordering_code)."""
        store = self._library_store()
        with self._substation(substation_id), _edit_refusals():
            result, cleared = parts_edit.set_equipment_part(
                Path(project_file), substation_id, index, part_id, store=store
            )
        if not result.written and result.issues:
            _written(result)
        return {
            "page": parts_page(Path(project_file), substation_id, store),
            "cleared": list(cleared) if result.written else [],
        }

    @endpoint
    def move_equipment(
        self, project_file: str, substation_id: str, index: int, to: int
    ) -> dict[str, Any]:
        """Move equipment row ``index`` to ``to``: the order panels are filled in."""
        return self._parts_write(
            project_file,
            substation_id,
            lambda project, sub, store: move_item(
                project, ("equipment",), index, to, substation=sub, store=store
            ),
        )

    @endpoint
    def start_parts(
        self, project_file: str, substation_id: str, rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """A new substation's first rows, written with its sized L1 switch; a substation
        with no panels yet then gets them laid out from those rows."""
        store = self._library_store()
        project = Path(project_file)
        with self._substation(substation_id), _edit_refusals():
            result = parts_edit.start_parts(project, substation_id, rows, store=store)
        _written(result)
        found = resolve(project, substation_id, store)
        if found.loaded is not None and not found.loaded.panels:
            # the rows are saved either way; Panels shows why they cannot be laid out
            with contextlib.suppress(InputError, EngineError):
                write_generated_panels(
                    found.file, replace_hand_written=False, backup=False, store=store
                )
        return parts_page(project, substation_id, store)

    # -- Checks and Build (docs/ui/screens.md: Checks, Build) --

    @endpoint
    def run_checks(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """The substation's located problems, then the engine checks when the files load."""
        with self._substation(substation_id):
            return checks_page(Path(project_file), substation_id, self._library_store())

    @endpoint
    def build_target(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """The workbook's file name and default folder, and the problems that block a build."""
        with self._substation(substation_id):
            return build_target(Path(project_file), substation_id, self._library_store())

    @endpoint
    def substation_layout(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """The engine's network sizing, L1 ranking and panel layout, for Network and Panels."""
        with self._substation(substation_id):
            return layout_page(Path(project_file), substation_id, self._library_store())

    @endpoint
    def device_preview(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """Every generated unit with its panel, top U, MCBs and strips, for Device preview."""
        with self._substation(substation_id):
            return device_preview_page(Path(project_file), substation_id, self._library_store())

    # -- Editing (docs/ui/editing.md; writers in bomgen.io.edit, ADR 0021) --

    def _edit(
        self,
        project_file: str,
        substation_id: str,
        write: Callable[..., EditResult],
        *args: Any,
        page: Page = layout_page,
        **kwargs: Any,
    ) -> dict[str, Any]:
        store = self._library_store()
        project = Path(project_file)
        with self._substation(substation_id), _edit_refusals():
            result = write(project, substation_id, *args, store=store, **kwargs)
            return edit_reply(result, project, substation_id, store, page)

    @endpoint
    def set_layout_overrides(
        self, project_file: str, substation_id: str, overrides: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Write the board's pins and moves (``layout.overrides``), in order; a move the
        layout cannot take is refused and nothing is written."""
        return self._layout_edit(project_file, substation_id, overrides=overrides)

    @endpoint
    def set_layout_removed(
        self, project_file: str, substation_id: str, removed: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Write the units left out of the layout (``layout.removed``)."""
        return self._layout_edit(project_file, substation_id, removed=removed)

    def _layout_edit(
        self,
        project_file: str,
        substation_id: str,
        *,
        overrides: list[dict[str, Any]] | None = None,
        removed: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        store = self._library_store()
        with self._substation(substation_id):
            issues = layout_issues(
                Path(project_file), substation_id, store, overrides=overrides, removed=removed
            )
        if issues:
            return {"written": False, "issues": issues, "page": None}
        if overrides is not None:
            return self._edit(project_file, substation_id, edit.set_layout_overrides, overrides)
        return self._edit(project_file, substation_id, edit.set_layout_removed, removed)

    @endpoint
    def check_layout(
        self,
        project_file: str,
        substation_id: str,
        overrides: list[dict[str, Any]],
        removed: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Whether the layout can take these overrides and removed units, and the rack space
        each panel would then use, as the board asks while a device is moved; nothing is
        written."""
        with self._substation(substation_id):
            check = layout_check(
                Path(project_file),
                substation_id,
                self._library_store(),
                overrides=overrides,
                removed=removed,
            )
        return {"fits": not check["issues"], **check}

    @endpoint
    def generate_panels(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """Lay out the substation's panels from its equipment and write them, replacing
        hand-written panel files after copying them to ``panels/hand-written-<time>/``; the
        Panels board is then editable. Returns the files written, that folder, the layout's
        problems and the refreshed board."""
        store = self._library_store()
        project = Path(project_file)
        with self._substation(substation_id):
            file = resolve(project, substation_id, store).file
        try:
            written = write_generated_panels(
                file, replace_hand_written=True, backup=True, store=store
            )
        except (InputError, EngineError) as exc:
            raise AppError("edit_refused", f"The panels cannot be laid out: {exc}") from None
        return {
            "written": [str(path) for path in written.written],
            "backup": str(written.backup_dir) if written.backup_dir else None,
            "issues": [
                {
                    "level": "error" if issue.is_error else "warning",
                    "subject": issue.subject,
                    "message": issue.message,
                }
                for issue in written.report.issues
            ],
            "page": layout_page(project, substation_id, store),
        }

    @endpoint
    def set_enclosure(
        self, project_file: str, substation_id: str, enclosure: dict[str, Any]
    ) -> dict[str, Any]:
        """Write the enclosure every generated panel uses."""
        return self._edit(project_file, substation_id, edit.set_enclosure, enclosure)

    @endpoint
    def set_generated_document(
        self, project_file: str, substation_id: str, document: str
    ) -> dict[str, Any]:
        """Write the register key of the generated panels' document."""
        return self._edit(project_file, substation_id, edit.set_generated_document, document)

    @endpoint
    def panel_options(self, project_file: str, substation_id: str, panel: int) -> Any:
        """Generated panel ``panel``'s options, each with the shared value and whether the
        panel has its own."""
        with self._substation(substation_id), _edit_refusals():
            return panel_options_page(
                Path(project_file), substation_id, panel, self._library_store()
            )

    @endpoint
    def set_panel_option(
        self, project_file: str, substation_id: str, key: str, value: Any, panel: int | None
    ) -> dict[str, Any]:
        """Write an option for every generated panel, or for ``panel`` only."""

        def write(project: Path, sub: str, *, store: LibraryStore) -> EditResult:
            return edit.set_option(project, sub, key, value, panel=panel, store=store)

        return self._edit(project_file, substation_id, write)

    @endpoint
    def remove_panel_option(
        self, project_file: str, substation_id: str, key: str, panel: int | None
    ) -> dict[str, Any]:
        """Remove a written option, so the shared value or the default applies again."""

        def write(project: Path, sub: str, *, store: LibraryStore) -> EditResult:
            return edit.remove_option(project, sub, key, panel=panel, store=store)

        return self._edit(project_file, substation_id, write)

    @endpoint
    def set_port_plan(
        self,
        project_file: str,
        substation_id: str,
        equipment_id: str,
        port_plan: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Write (or with ``None`` remove) an equipment row's port plan."""
        return self._edit(project_file, substation_id, edit.set_port_plan, equipment_id, port_plan)

    @endpoint
    def loose_material(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """The substation's loose material, for the Loose material page."""
        with self._substation(substation_id):
            return loose_page(Path(project_file), substation_id, self._library_store())

    @endpoint
    def add_loose_item(
        self,
        project_file: str,
        substation_id: str,
        item: dict[str, Any],
        index: int | None,
        host_panel: str | None,
    ) -> dict[str, Any]:
        """Insert a loose item at ``index`` (``None``: at the end); the first item also
        names ``host_panel``."""
        return self._edit(
            project_file,
            substation_id,
            loose_edit.add_loose_item,
            item,
            index=index,
            host_panel=host_panel,
            page=loose_page,
        )

    @endpoint
    def set_loose_item(
        self, project_file: str, substation_id: str, index: int, item: dict[str, Any]
    ) -> dict[str, Any]:
        """Replace loose item ``index`` with ``item``."""
        return self._edit(
            project_file, substation_id, loose_edit.set_loose_item, index, item, page=loose_page
        )

    @endpoint
    def remove_loose_item(
        self, project_file: str, substation_id: str, index: int
    ) -> dict[str, Any]:
        """Remove loose item ``index``."""
        return self._edit(
            project_file, substation_id, loose_edit.remove_loose_item, index, page=loose_page
        )

    @endpoint
    def move_loose_item(
        self, project_file: str, substation_id: str, source: int, target: int
    ) -> dict[str, Any]:
        """Move loose item ``source`` to position ``target``, the sheet's order."""
        return self._edit(
            project_file,
            substation_id,
            loose_edit.move_loose_item,
            source,
            target,
            page=loose_page,
        )

    @endpoint
    def set_loose_host_panel(
        self, project_file: str, substation_id: str, panel_id: str
    ) -> dict[str, Any]:
        """Issue the Loose Material sheet under ``panel_id``'s document."""
        return self._edit(
            project_file, substation_id, loose_edit.set_host_panel, panel_id, page=loose_page
        )

    @endpoint
    def validate_loose_item(
        self, project_file: str, substation_id: str, index: int | None, item: dict[str, Any]
    ) -> dict[str, str]:
        """The engine's messages for ``item`` as item ``index`` (``None``: a new last item),
        by field; nothing is written."""
        with self._substation(substation_id), _edit_refusals():
            return loose_edit.validate_loose_item(
                Path(project_file), substation_id, index, item, store=self._library_store()
            )

    @endpoint
    def preview_substation(self, project_file: str, substation_id: str) -> dict[str, Any]:
        """The workbook's sheets as the engine computes them, for the Preview screen."""
        with self._substation(substation_id):
            return preview_page(Path(project_file), substation_id, self._library_store())

    @endpoint
    def choose_folder(self) -> str | None:
        """Ask for a folder; None when cancelled."""
        if self._window is None:
            return None
        return _first(self._window.create_file_dialog(FOLDER_DIALOG))

    @endpoint
    def build_workbook(
        self,
        project_file: str,
        substation_id: str,
        folder: str,
        file_name: str | None = None,
        compare: str | None = None,
        replace: bool = False,
    ) -> dict[str, Any]:
        """Write the substation's workbook; ``compare`` marks changes since that issue."""
        with self._substation(substation_id):
            result = build_file(
                Path(project_file),
                substation_id,
                self._library_store(),
                Path(folder),
                file_name or None,
                Path(compare) if compare else None,
                replace,
            )
        self._list(result["path"])
        return result

    @staticmethod
    @contextlib.contextmanager
    def _substation(substation_id: str) -> Iterator[None]:
        """The page's refusals for one substation's endpoints."""
        try:
            yield
        except ProjectInvalidError as exc:
            raise AppError("project_invalid", f"The project cannot be read: {exc}") from None
        except SubstationNotFoundError:
            raise AppError(
                "not_found", f"The project has no substation {substation_id!r}"
            ) from None
        except OutputRefusedError as exc:
            raise AppError(exc.kind, str(exc)) from None

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
