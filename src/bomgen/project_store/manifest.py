"""The `manifest.json` of a `.bomproj` project file (ADR 0012)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Self, TypeGuard

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from bomgen.bundle.container import check_file_table
from bomgen.bundle.paths import is_safe_name
from bomgen.library_store.manifest import is_valid_library_name
from bomgen.library_store.versions import Version

PROJECT_FORMAT_VERSION = 1
PROJECT_SUFFIX = ".bomproj"
PROJECT_FILE = "project.yaml"

_PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def is_valid_project_id(value: object) -> TypeGuard[str]:
    """A project id becomes a folder name in the workspace, so it must be a safe one."""
    return (
        isinstance(value, str)
        and len(value) <= 64
        and _PROJECT_ID.fullmatch(value) is not None
        and is_safe_name(value)
    )


class ProjectManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: Literal[1]
    project_id: str
    library_name: str | None
    library_version: str | None
    app_version: str
    created: datetime
    files: dict[str, str]

    @field_validator("project_id")
    @classmethod
    def _check_project_id(cls, value: str) -> str:
        if not is_valid_project_id(value):
            raise ValueError(f"unsafe project id {value!r}")
        return value

    @field_validator("library_name")
    @classmethod
    def _check_library_name(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_library_name(value):
            raise ValueError(f"unsafe library name {value!r}")
        return value

    @field_validator("library_version", "app_version")
    @classmethod
    def _check_version(cls, value: str | None) -> str | None:
        if value is not None:
            Version.parse(value)
        return value

    @model_validator(mode="after")
    def _library_is_both_or_none(self) -> Self:
        if (self.library_name is None) != (self.library_version is None):
            raise ValueError("library_name and library_version go together")
        return self

    @field_validator("files")
    @classmethod
    def _check_files(cls, files: dict[str, str]) -> dict[str, str]:
        return check_file_table(files)
