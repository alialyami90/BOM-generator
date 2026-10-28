"""Import a project under a new id: rewrite `project.id`, and pick a free id (ADR 0012)."""

from __future__ import annotations

import re
from itertools import count
from pathlib import Path

import yaml

from bomgen.bundle.errors import LibraryPackageError, RefusalKind
from bomgen.project_store.manifest import PROJECT_FILE

_ID_LINE = re.compile(r"^(?P<head>\s+id:[ \t]*)(?P<value>\"[^\"]*\"|'[^']*'|[^\s#]+)(?P<tail>.*)$")
_BLANK_OR_COMMENT = re.compile(r"^\s*(#.*)?$")


def _cannot(reason: str) -> LibraryPackageError:
    return LibraryPackageError(
        f"cannot rewrite the project id in {PROJECT_FILE}: {reason}", RefusalKind.INVALID_PROJECT
    )


def _scalar(new_id: str, old: str) -> str:
    """The new id in the old one's quoting, quoted anyway if YAML would not read it as text."""
    if old.startswith('"') or yaml.safe_load(new_id) != new_id:
        return f'"{new_id}"'
    if old.startswith("'"):
        return f"'{new_id}'"
    return new_id


def _read_id(text: str) -> object:
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    project = document.get("project") if isinstance(document, dict) else None
    return project.get("id") if isinstance(project, dict) else None


def rewrite_project_id(text: str, new_id: str) -> str:
    """Replace `project.id` in `project.yaml` text, touching nothing else.

    Only the block style the app writes is handled; anything else is refused
    rather than guessed at.
    """
    bom, body = ("﻿", text[1:]) if text.startswith("﻿") else ("", text)
    lines = body.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if re.match(r"project:\s*(#.*)?$", line)), None)
    if start is None:
        raise _cannot("there is no block-style 'project:' section")
    indent: str | None = None
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if _BLANK_OR_COMMENT.match(line):
            continue
        if not line[0].isspace():
            break
        current = line[: len(line) - len(line.lstrip())]
        indent = current if indent is None else indent
        if current != indent:
            continue
        found = _ID_LINE.match(line.rstrip("\r\n"))
        if found:
            ending = line[len(line.rstrip("\r\n")) :]
            value = _scalar(new_id, found["value"])
            lines[i] = f"{found['head']}{value}{found['tail']}{ending}"
            rewritten = bom + "".join(lines)
            if _read_id(rewritten) != new_id:
                raise _cannot("the result does not read back as the new id")
            return rewritten
    raise _cannot("there is no 'id:' line directly under 'project:'")


def suggest_project_id(project_id: str, workspace: Path) -> str:
    """The first of `<id>-2`, `<id>-3`, ... free in the workspace, at most 64 characters."""
    for number in count(2):
        suffix = f"-{number}"
        candidate = project_id[: 64 - len(suffix)] + suffix
        if not (workspace / candidate).exists():
            return candidate
    raise AssertionError("unreachable")  # pragma: no cover
