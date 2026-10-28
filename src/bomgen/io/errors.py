"""Located input errors: every problem names its file, location and line where known."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

if TYPE_CHECKING:
    from bomgen.io.yaml_source import YamlSource

Loc = tuple[str | int, ...]

_VALUE_ERROR_PREFIX = "Value error, "


@dataclass(frozen=True)
class Issue:
    """One problem in one input file."""

    file: Path
    location: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        where = self.file.as_posix()
        if self.line is not None:
            where += f":{self.line}"
        if self.location:
            where += f": {self.location}"
        return f"{where}: {self.message}"


class InputError(Exception):
    """Raised when inputs are unusable; carries every issue found, not just the first."""

    def __init__(self, issues: Sequence[Issue]) -> None:
        if not issues:
            raise ValueError("InputError needs at least one issue")
        super().__init__("\n".join(str(issue) for issue in issues))
        self.issues: tuple[Issue, ...] = tuple(issues)

    def __str__(self) -> str:
        return "\n".join(str(issue) for issue in self.issues)


def format_location(loc: Loc) -> str:
    """Render a path as ``devices[2].part_id``."""
    text = ""
    for part in loc:
        if isinstance(part, int):
            text += f"[{part}]"
        else:
            text += f".{part}" if text else part
    return text


def issues_from_validation_error(
    error: ValidationError, source: YamlSource, prefix: Loc = ()
) -> list[Issue]:
    """Turn a pydantic error into located issues, one per distinct (location, message)."""
    issues: list[Issue] = []
    seen: set[tuple[str, str]] = set()
    for item in error.errors():
        loc = prefix + tuple(item["loc"])
        location = format_location(loc)
        match item["type"]:
            case "extra_forbidden":
                message = "unknown key (check spelling)"
            case "missing":
                message = "required key is missing"
            case _:
                message = item["msg"].removeprefix(_VALUE_ERROR_PREFIX)
        if (location, message) in seen:
            continue
        seen.add((location, message))
        issues.append(Issue(source.path, location, message, source.line_for(loc)))
    return issues
