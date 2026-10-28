"""Load a project: the project file, its library, its substations and their panels.

A project lists substations (ADR 0012); each substation lists its panel files, whose
mirrors are resolved here, and inherits the project defaults key by key. Every problem
found in every file is collected into one :class:`InputError` (ADR 0010 item 7).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ValidationError

from bomgen.io.errors import InputError, Issue, Loc, issues_from_validation_error
from bomgen.io.mirror import mirror_panel
from bomgen.io.references import (
    document_issues,
    equipment_issues,
    library_issues,
    mirror_issues,
    panel_issues,
    project_issues,
    substation_issues,
)
from bomgen.io.yaml_source import YamlSource, read_yaml
from bomgen.models._base import InputModel
from bomgen.models.library import Library
from bomgen.models.panel import Panel, PanelMirror, PanelOptions
from bomgen.models.project import (
    DesignConstants,
    Project,
    RegisterEntry,
    Spares,
    merge_defaults,
)
from bomgen.models.substation import Substation

if TYPE_CHECKING:
    from bomgen.library_store.store import LibraryStore

PROJECT_FILE = "project.yaml"


@dataclass(frozen=True)
class LoadedSubstation:
    """A validated substation: its settings merged with the project's, panels resolved."""

    file: Path
    substation: Substation
    project: Project
    library: Library
    documents: Mapping[str, RegisterEntry]  # this substation's register entries by key
    constants: DesignConstants
    spares: Spares
    panels: tuple[Panel, ...]  # ``panels`` then ``manual_panels``, in sheet order
    panel_files: Mapping[str, Path]  # panel id -> its own file (a mirror's is the mirror file)
    manual_panel_ids: frozenset[str]

    @property
    def panel_capacity_u(self) -> int:
        """Rack units the layout may fill in one panel (ADR 0013)."""
        return self.library.catalogues.enclosure_u - self.spares.rack_u_reserved


@dataclass(frozen=True)
class LoadedProject:
    """A validated project with its library and every substation resolved."""

    file: Path
    project: Project
    library: Library
    substations: tuple[LoadedSubstation, ...]


def load_inputs(
    path: Path, *, store: LibraryStore | None = None
) -> LoadedProject | LoadedSubstation:
    """Load a project file or a substation file, told apart by the project's ``substations``."""
    source = read_yaml(path)
    if isinstance(source.data, dict) and "substations" in source.data:
        return load_project(path, store=store)
    return load_substation(path, store=store)


def load_substation(
    substation_file: Path, *, store: LibraryStore | None = None
) -> LoadedSubstation:
    """Load the project that lists ``substation_file`` and return that substation."""
    target = substation_file.resolve()
    for folder in target.parents:
        candidate = folder / PROJECT_FILE
        if candidate.is_file() and target in _listed_substations(candidate):
            loaded = load_project(candidate, store=store)
            return next(s for s in loaded.substations if s.file.resolve() == target)
    if not substation_file.is_file():
        read_yaml(substation_file)  # raises "file not found"
    message = (
        f"no {PROJECT_FILE} in a folder above lists this substation; "
        "add it to the project's substations"
    )
    raise InputError([Issue(substation_file, "", message)])


def _listed_substations(project_file: Path) -> set[Path]:
    try:
        data = read_yaml(project_file).data
    except InputError:
        return set()
    listed = data.get("substations") if isinstance(data, dict) else None
    if not isinstance(listed, list):
        return set()
    return {(project_file.parent / str(p)).resolve() for p in listed if isinstance(p, str)}


def load_project(project_file: Path, *, store: LibraryStore | None = None) -> LoadedProject:
    """Load ``project_file`` and everything it names, or raise :class:`InputError`."""
    project_source = read_yaml(project_file)
    project = _validate(Project, project_source)
    base = project_file.parent

    issues: list[Issue] = []
    if project.project.logo is not None:
        logo = base / project.project.logo
        if not logo.is_file():
            message = f"file not found: {logo.as_posix()}"
            line = project_source.line_for(("project", "logo"))
            issues.append(Issue(project_file, "project.logo", message, line))

    library_file = _library_file(project, project_source, store, issues)
    library_source = _read(library_file, issues) if library_file is not None else None
    library = _validate_into(Library, library_source, issues)

    substation_sources: list[tuple[Substation, YamlSource]] = []
    panel_sources: dict[Path, list[tuple[YamlSource, Panel | PanelMirror]]] = {}
    seen: dict[Path, int] = {}
    for index, path in enumerate(project.substations):
        file = base / path
        key = file.resolve()
        if key in seen:
            message = f"substation file listed twice (first at substations[{seen[key]}])"
            line = project_source.line_for(("substations", index))
            issues.append(Issue(project_file, f"substations[{index}]", message, line))
            continue
        seen[key] = index
        source = _read(file, issues)
        substation = _validate_into(Substation, source, issues)
        if source is not None and substation is not None:
            substation_sources.append((substation, source))
            panel_sources[source.path] = _read_panels(substation, source, issues)

    if issues or library is None:
        raise InputError(_sorted(issues))
    assert library_file is not None
    assert library_source is not None
    issues.extend(library_issues(library, library_source))
    issues.extend(project_issues(project, project_source, substation_sources))

    loaded: list[LoadedSubstation] = []
    for substation, source in substation_sources:
        result = _load_substation(
            project,
            project_source,
            substation,
            source,
            panel_sources[source.path],
            library,
            library_file.name,
            issues,
        )
        if result is not None:
            loaded.append(result)
    if issues:
        raise InputError(_sorted(issues))
    return LoadedProject(project_file, project, library, tuple(loaded))


def _library_file(
    project: Project, source: YamlSource, store: LibraryStore | None, issues: list[Issue]
) -> Path | None:
    """The library named by the project: its ``file``, or the installed version."""
    selection = project.library
    if selection.file is not None:
        return source.path.parent / selection.file
    from bomgen.library_store.errors import LibraryPackageError
    from bomgen.library_store.store import LibraryStore, default_library_home

    try:
        store = store or LibraryStore(default_library_home())
        return store.library_file(selection.name, selection.version)
    except LibraryPackageError as error:
        issues.append(Issue(source.path, "library", str(error), source.line_for(("library",))))
        return None


def _load_substation(
    project: Project,
    project_source: YamlSource,
    substation: Substation,
    source: YamlSource,
    panel_sources: Sequence[tuple[YamlSource, Panel | PanelMirror]],
    library: Library,
    library_name: str,
    issues: list[Issue],
) -> LoadedSubstation | None:
    """Resolve one substation's panels and defaults, adding every problem to ``issues``."""
    found: list[Issue] = []
    base = source.path.parent
    manual_files = {(base / p).resolve() for p in substation.manual_panels}
    resolved = _resolve_panels(panel_sources, library, library_name, found)
    manual_ids = frozenset(p.id for p, s in resolved if s.path.resolve() in manual_files)

    sub_id = substation.substation.id
    register = {entry.key: entry for entry in project.documents}
    found.extend(substation_issues(substation, source, resolved, library, library_name))
    found.extend(document_issues(substation, source, resolved, register))
    found.extend(equipment_issues(substation, source, library, library_name))
    found.extend(_generated_panel_issues(substation, source))

    constants = _merged(
        project.defaults.constants, substation.constants, source, ("constants",), found
    )
    spares = _merged(project.defaults.spares, substation.spares, source, ("spares",), found)
    if spares is not None and spares.rack_u_reserved >= library.catalogues.enclosure_u:
        message = (
            f"rack_u_reserved {spares.rack_u_reserved} leaves no usable rack space "
            f"(catalogues.enclosure_u is {library.catalogues.enclosure_u})"
        )
        if (
            substation.spares is not None
            and "rack_u_reserved" in substation.spares.model_fields_set
        ):
            found.append(
                Issue(
                    source.path,
                    "spares.rack_u_reserved",
                    message,
                    source.line_for(("spares", "rack_u_reserved")),
                )
            )
        else:
            loc: Loc = ("defaults", "spares", "rack_u_reserved")
            found.append(
                Issue(
                    project_source.path,
                    "defaults.spares.rack_u_reserved",
                    message,
                    project_source.line_for(loc),
                )
            )

    issues.extend(found)
    if found or constants is None or spares is None:
        return None
    return LoadedSubstation(
        file=source.path,
        substation=substation,
        project=project,
        library=library,
        documents={k: e for k, e in register.items() if e.substation == sub_id},
        constants=constants,
        spares=spares,
        panels=tuple(panel for panel, _ in resolved),
        panel_files={panel.id: panel_source.path for panel, panel_source in resolved},
        manual_panel_ids=manual_ids,
    )


def _read_panels(
    substation: Substation, substation_source: YamlSource, issues: list[Issue]
) -> list[tuple[YamlSource, Panel | PanelMirror]]:
    """Read and validate every panel file the substation lists, in sheet order."""
    base = substation_source.path.parent
    listed = [("panels", i, p) for i, p in enumerate(substation.panels)]
    listed += [("manual_panels", i, p) for i, p in enumerate(substation.manual_panels)]
    panel_sources: list[tuple[YamlSource, Panel | PanelMirror]] = []
    seen: dict[Path, str] = {}
    for key_name, index, path in listed:
        panel_file = base / path
        key = panel_file.resolve()
        listed_as = f"{key_name}[{index}]"
        if key in seen:
            message = f"panel file listed twice (first at {seen[key]})"
            line = substation_source.line_for((key_name, index))
            issues.append(Issue(substation_source.path, listed_as, message, line))
            continue
        seen[key] = listed_as
        panel_source = _read(panel_file, issues)
        if panel_source is None:
            continue
        panel: Panel | PanelMirror | None
        if isinstance(panel_source.data, dict) and "mirror_of" in panel_source.data:
            panel = _validate_into(PanelMirror, panel_source, issues)
        else:
            panel = _validate_into(Panel, panel_source, issues)
        if panel is not None:
            panel_sources.append((panel_source, panel))
    return panel_sources


def _resolve_panels(
    panel_sources: Sequence[tuple[YamlSource, Panel | PanelMirror]],
    library: Library,
    library_name: str,
    issues: list[Issue],
) -> list[tuple[Panel, YamlSource]]:
    """Resolve mirrors and check each panel against the library; problems go to ``issues``."""
    originals = {p.id: p for _, p in panel_sources if isinstance(p, Panel)}
    mirror_ids = {p.id for _, p in panel_sources if isinstance(p, PanelMirror)}
    resolved: list[tuple[Panel, YamlSource]] = []
    for source, entry in panel_sources:
        if isinstance(entry, Panel):
            resolved.append((entry, source))
            # a mirror inherits these, so reporting them there would repeat them
            issues.extend(panel_issues(entry, source, library, library_name))
            continue
        issues.extend(mirror_issues(entry, source, library))
        original = originals.get(entry.mirror_of)
        if original is None:
            if entry.mirror_of in mirror_ids:
                message = (
                    f"mirror_of '{entry.mirror_of}' is itself a mirror; "
                    "mirror the original panel instead"
                )
            else:
                message = f"mirror_of '{entry.mirror_of}' is not a panel in this substation"
            issues.append(Issue(source.path, "mirror_of", message, source.line_for(("mirror_of",))))
            continue
        try:
            resolved.append((mirror_panel(original, entry), source))
        except ValidationError as error:
            issues.extend(issues_from_validation_error(error, source, prefix=("options",)))
    return resolved


def _generated_panel_issues(substation: Substation, source: YamlSource) -> list[Issue]:
    """Each generated panel's options, merged, must be valid panel options."""
    generated = substation.generated_panels
    if generated is None:
        return []
    issues: list[Issue] = []
    combos: list[tuple[Loc, dict[str, object]]] = [
        (("generated_panels", "options"), generated.options)
    ]
    for number, options in generated.options_by_panel.items():
        combos.append(
            (("generated_panels", "options_by_panel", number), generated.options | options)
        )
    for loc, options in combos:
        try:
            PanelOptions.model_validate(options)
        except ValidationError as error:
            issues.extend(issues_from_validation_error(error, source, prefix=loc))
    return issues


def _merged[M: InputModel](
    base: M, override: InputModel | None, source: YamlSource, prefix: Loc, issues: list[Issue]
) -> M | None:
    try:
        return merge_defaults(base, override)
    except ValidationError as error:
        issues.extend(issues_from_validation_error(error, source, prefix=prefix))
        return None


def load_library(library_file: Path) -> Library:
    """Load a library file on its own, or raise one :class:`InputError` with every issue."""
    source = read_yaml(library_file)
    library = _validate(Library, source)
    issues = library_issues(library, source)
    if issues:
        raise InputError(_sorted(issues))
    return library


def _sorted(issues: Sequence[Issue]) -> list[Issue]:
    """Order issues by file, then line; ties keep the order they were found in."""
    return sorted(issues, key=lambda issue: (issue.file.as_posix(), issue.line or 0))


def _read(path: Path, issues: list[Issue]) -> YamlSource | None:
    try:
        return read_yaml(path)
    except InputError as error:
        issues.extend(error.issues)
        return None


def _validate[M: BaseModel](model_type: type[M], source: YamlSource) -> M:
    """Validate ``source`` as ``model_type``, or raise :class:`InputError` at once."""
    try:
        return model_type.model_validate(source.data)
    except ValidationError as error:
        raise InputError(issues_from_validation_error(error, source)) from None


def _validate_into[M: BaseModel](
    model_type: type[M], source: YamlSource | None, issues: list[Issue]
) -> M | None:
    """Validate ``source`` as ``model_type``, adding any problems to ``issues``."""
    if source is None:
        return None
    try:
        return model_type.model_validate(source.data)
    except ValidationError as error:
        issues.extend(issues_from_validation_error(error, source))
        return None
