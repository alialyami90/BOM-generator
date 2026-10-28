"""Load a project: the project file, its library and panel files, mirrors resolved.

Every problem found in every file is collected into one :class:`InputError`
(ADR 0010 item 7).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from bomgen.io.errors import InputError, Issue, issues_from_validation_error
from bomgen.io.mirror import mirror_panel
from bomgen.io.references import library_issues, mirror_issues, panel_issues, project_issues
from bomgen.io.yaml_source import YamlSource, read_yaml
from bomgen.models.library import Library
from bomgen.models.panel import Panel, PanelMirror
from bomgen.models.project import Project


@dataclass(frozen=True)
class LoadedProject:
    """A validated project with its library and every panel fully resolved."""

    project_file: Path
    project: Project
    library: Library
    panels: tuple[Panel, ...]
    panel_files: Mapping[str, Path]  # panel id -> its own file (a mirror's is the mirror file)


def load_project(project_file: Path) -> LoadedProject:
    """Load ``project_file`` and everything it names, or raise :class:`InputError`."""
    project_source = read_yaml(project_file)
    project = _validate(Project, project_source)
    base = project_file.parent
    library_file = base / project.library
    panel_files = [base / path for path in project.panels]

    issues: list[Issue] = []
    if project.project.logo is not None:
        logo = base / project.project.logo
        if not logo.is_file():
            message = f"file not found: {logo.as_posix()}"
            line = project_source.line_for(("project", "logo"))
            issues.append(Issue(project_file, "project.logo", message, line))

    library_source = _read(library_file, issues)
    library = _validate_into(Library, library_source, issues)

    panel_sources: list[tuple[YamlSource, Panel | PanelMirror]] = []
    seen: dict[Path, int] = {}
    for index, panel_file in enumerate(panel_files):
        key = panel_file.resolve()
        if key in seen:
            message = f"panel file listed twice (first at panels[{seen[key]}])"
            line = project_source.line_for(("panels", index))
            issues.append(Issue(project_file, f"panels[{index}]", message, line))
            continue
        seen[key] = index
        panel_source = _read(panel_file, issues)
        if panel_source is None:
            continue
        panel: Panel | PanelMirror | None
        if "mirror_of" in panel_source.data:
            panel = _validate_into(PanelMirror, panel_source, issues)
        else:
            panel = _validate_into(Panel, panel_source, issues)
        if panel is not None:
            panel_sources.append((panel_source, panel))

    if issues or library is None:
        raise InputError(_sorted(issues))

    originals = {p.id: p for _, p in panel_sources if isinstance(p, Panel)}
    mirror_ids = {p.id for _, p in panel_sources if isinstance(p, PanelMirror)}
    resolved: list[tuple[Panel, YamlSource]] = []
    own: list[tuple[Panel, YamlSource]] = []  # panels defined in full, not mirrors
    for source, entry in panel_sources:
        if isinstance(entry, Panel):
            resolved.append((entry, source))
            own.append((entry, source))
            continue
        original = originals.get(entry.mirror_of)
        if original is None:
            if entry.mirror_of in mirror_ids:
                message = (
                    f"mirror_of '{entry.mirror_of}' is itself a mirror; "
                    "mirror the original panel instead"
                )
            else:
                message = f"mirror_of '{entry.mirror_of}' is not a panel in this project"
            line = source.line_for(("mirror_of",))
            issues.append(Issue(source.path, "mirror_of", message, line))
            continue
        try:
            resolved.append((mirror_panel(original, entry), source))
        except ValidationError as error:
            issues.extend(issues_from_validation_error(error, source, prefix=("options",)))

    assert library_source is not None  # library is set only when its file was read
    library_name = library_file.name
    issues.extend(library_issues(library, library_source))
    for panel, source in own:  # a mirror inherits these, so reporting them there would repeat them
        issues.extend(panel_issues(panel, source, library, library_name))
    for source, entry in panel_sources:
        if isinstance(entry, PanelMirror):
            issues.extend(mirror_issues(entry, source, library))
    issues.extend(project_issues(project, project_source, resolved, library, library_name))
    if issues:
        raise InputError(_sorted(issues))

    return LoadedProject(
        project_file=project_file,
        project=project,
        library=library,
        panels=tuple(panel for panel, _ in resolved),
        panel_files={panel.id: source.path for panel, source in resolved},
    )


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
