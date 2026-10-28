"""Writers for the substation file, for the app's editors (plan M17, ADR 0021).

Every writer edits ``substation.yaml`` in memory, loads the whole project with the
edit, and writes the file only when the edit causes no new problem. It returns the
problems it caused (nothing written) or, once written, the problems the project still
has and the new layout preview, as the Panels board shows them.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml.comments import CommentedMap

from bomgen.engine.layout import LayoutResult, layout_preview
from bomgen.io.errors import InputError, Issue
from bomgen.io.loader import LoadedProject, LoadedSubstation, load_project
from bomgen.io.round_trip import child_map, dump_text, load_text, merge_value, write_atomic
from bomgen.io.yaml_source import pending_texts, read_yaml
from bomgen.models.panel import PanelOptions

if TYPE_CHECKING:
    from bomgen.library_store.store import LibraryStore


class EditError(Exception):
    """The edit names something the file does not have (no change was made)."""


@dataclass(frozen=True)
class EditResult:
    """What a writer did."""

    written: bool
    issues: tuple[Issue, ...]  # caused by the edit when not written; else still open
    preview: LayoutResult | None = None  # the new layout, when the substation has one


Change = Callable[[CommentedMap], None]


def substation_file(project_file: Path, substation_id: str) -> Path:
    """The listed ``substation.yaml`` whose folder is ``substation_id`` (ADR 0012)."""
    data = read_yaml(project_file).data
    for path in data.get("substations") or []:
        file = project_file.parent / str(path)
        if file.parent.name == substation_id:
            return file
    raise EditError(f"no substation '{substation_id}' in {project_file.name}")


def edit_substation(
    project_file: Path,
    substation_id: str,
    change: Change,
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Apply ``change`` to the substation file's parsed YAML and write it if it is sound."""
    file = substation_file(project_file, substation_id)
    data = load_text(file.read_text(encoding="utf-8-sig"))
    change(data)
    text = dump_text(data)
    before, _ = _load(project_file, store, {})
    after, loaded = _load(project_file, store, {file: text})
    known = {_key(issue) for issue in before}
    caused = tuple(issue for issue in after if _key(issue) not in known)
    if caused:
        return EditResult(False, caused)
    write_atomic(file, text)
    return EditResult(True, tuple(after), _preview(loaded, substation_id))


def _load(
    project_file: Path, store: LibraryStore | None, texts: Mapping[Path, str]
) -> tuple[list[Issue], LoadedProject | None]:
    with pending_texts(texts):
        try:
            return [], load_project(project_file, store=store)
        except InputError as error:
            return list(error.issues), None


def _key(issue: Issue) -> tuple[Path, str, str]:
    return (issue.file.resolve(), issue.location, issue.message)  # lines move with edits


def _preview(loaded: LoadedProject | None, substation_id: str) -> LayoutResult | None:
    target = _substation(loaded, substation_id) if loaded is not None else None
    if target is None or not target.substation.equipment:
        return None
    return layout_preview(target)


def _substation(loaded: LoadedProject, substation_id: str) -> LoadedSubstation | None:
    return next((s for s in loaded.substations if s.file.parent.name == substation_id), None)


def _generated(data: CommentedMap) -> CommentedMap:
    generated = data.get("generated_panels")
    if not isinstance(generated, CommentedMap):
        raise EditError("the substation has no generated_panels")
    return generated


def _remove_key(parent: CommentedMap, key: Any) -> None:
    if key in parent:
        del parent[key]


# --- the generated-panel editor (docs/ui/editing.md, "Back-end needs") ---


def set_enclosure(
    project_file: Path,
    substation_id: str,
    enclosure: Mapping[str, Any],
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Set ``generated_panels.enclosure``, shared by every generated panel."""

    def change(data: CommentedMap) -> None:
        generated = _generated(data)
        generated["enclosure"] = merge_value(generated.get("enclosure"), enclosure)

    return edit_substation(project_file, substation_id, change, store=store)


def set_generated_document(
    project_file: Path, substation_id: str, document: str, *, store: LibraryStore | None = None
) -> EditResult:
    """Set ``generated_panels.document``; it must be one of the substation's register keys."""

    def change(data: CommentedMap) -> None:
        generated = _generated(data)
        generated["document"] = merge_value(generated.get("document"), document)

    return edit_substation(project_file, substation_id, change, store=store)


def set_option(
    project_file: Path,
    substation_id: str,
    key: str,
    value: Any,
    *,
    panel: int | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Set a panel option for every generated panel, or for panel ``panel`` only."""
    _check_option(key)

    def change(data: CommentedMap) -> None:
        options = _options(_generated(data), panel, create=True)
        assert options is not None
        options[key] = merge_value(options.get(key), value)

    return edit_substation(project_file, substation_id, change, store=store)


def remove_option(
    project_file: Path,
    substation_id: str,
    key: str,
    *,
    panel: int | None = None,
    store: LibraryStore | None = None,
) -> EditResult:
    """Remove a written option: panel ``panel`` then uses the shared value, and the shared
    value goes back to its default. An empty panel entry is removed too."""
    _check_option(key)

    def change(data: CommentedMap) -> None:
        generated = _generated(data)
        options = _options(generated, panel, create=False)
        if options is None or key not in options:
            return
        del options[key]
        if panel is not None and not options:
            by_panel = generated["options_by_panel"]
            del by_panel[panel]
            if not by_panel:
                del generated["options_by_panel"]

    return edit_substation(project_file, substation_id, change, store=store)


def _check_option(key: str) -> None:
    if key not in PanelOptions.model_fields:
        raise EditError(f"unknown panel option '{key}'")


def _options(generated: CommentedMap, panel: int | None, *, create: bool) -> CommentedMap | None:
    if panel is None:
        if create:
            return child_map(generated, "options")
        options = generated.get("options")
        return options if isinstance(options, CommentedMap) else None
    if create:
        return child_map(child_map(generated, "options_by_panel"), panel)
    by_panel = generated.get("options_by_panel")
    options = by_panel.get(panel) if isinstance(by_panel, CommentedMap) else None
    return options if isinstance(options, CommentedMap) else None


@dataclass(frozen=True)
class OptionValue:
    """One panel option as the panel editor shows it."""

    key: str
    value: Any  # what the panel uses
    shared: Any  # the value for every generated panel (written, else the default)
    own: bool  # the panel has its own value, overriding ``shared``


def panel_options(target: LoadedSubstation, panel: int) -> list[OptionValue]:
    """Every option of generated panel ``panel``, in model order."""
    generated = target.substation.generated_panels
    if generated is None:
        raise EditError("the substation has no generated_panels")
    own = generated.options_by_panel.get(panel, {})
    shared = PanelOptions.model_validate(generated.options).model_dump(mode="json")
    used = PanelOptions.model_validate(generated.options | own).model_dump(mode="json")
    return [OptionValue(key, used[key], shared[key], key in own) for key in used]


def set_port_plan(
    project_file: Path,
    substation_id: str,
    equipment_id: str,
    port_plan: Mapping[str, Any] | None,
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Set (or with ``None`` remove) an equipment row's per-unit ``port_plan``."""

    def change(data: CommentedMap) -> None:
        row = _equipment_row(data, equipment_id)
        if port_plan is None:
            _remove_key(row, "port_plan")
        else:
            row["port_plan"] = merge_value(row.get("port_plan"), port_plan)

    return edit_substation(project_file, substation_id, change, store=store)


def _equipment_row(data: CommentedMap, equipment_id: str) -> CommentedMap:
    for row in data.get("equipment") or []:
        if isinstance(row, CommentedMap) and row.get("id") == equipment_id:
            return row
    raise EditError(f"no equipment row '{equipment_id}'")


# --- the Panels board ---


def set_layout_overrides(
    project_file: Path,
    substation_id: str,
    overrides: Sequence[Mapping[str, Any]],
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Set ``layout.overrides``, the board's moves and pins in order."""
    return _set_layout(project_file, substation_id, "overrides", overrides, store)


def set_layout_removed(
    project_file: Path,
    substation_id: str,
    removed: Sequence[Mapping[str, Any]],
    *,
    store: LibraryStore | None = None,
) -> EditResult:
    """Set ``layout.removed``, the units left out of the layout."""
    return _set_layout(project_file, substation_id, "removed", removed, store)


def _set_layout(
    project_file: Path,
    substation_id: str,
    key: str,
    items: Sequence[Mapping[str, Any]],
    store: LibraryStore | None,
) -> EditResult:
    cleaned = [{k: v for k, v in item.items() if v is not None} for item in items]

    def change(data: CommentedMap) -> None:
        layout = data.get("layout")
        if not cleaned and not (isinstance(layout, CommentedMap) and key in layout):
            return
        layout = child_map(data, "layout")
        layout[key] = merge_value(layout.get(key), cleaned)
        for item in layout[key]:
            item.fa.set_flow_style()  # one move per line, as the example writes them

    return edit_substation(project_file, substation_id, change, store=store)
