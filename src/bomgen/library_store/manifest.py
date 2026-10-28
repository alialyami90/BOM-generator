"""The `manifest.json` at the root of every `.bomlib` package (ADR 0008)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bomgen.bundle.container import check_file_table
from bomgen.library_store.versions import Version

FORMAT_VERSION = 1
LIBRARY_SCHEMA_VERSION = 1
LIBRARY_FILE = "library.yaml"


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: Literal[1]
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$", max_length=64)
    version: str
    schema_version: int
    min_app_version: str
    release_notes: str = ""
    created: datetime
    files: dict[str, str]

    @field_validator("version", "min_app_version")
    @classmethod
    def _check_version(cls, value: str) -> str:
        Version.parse(value)
        return value

    @field_validator("files")
    @classmethod
    def _check_files(cls, files: dict[str, str]) -> dict[str, str]:
        return check_file_table(files)

    @property
    def parsed_version(self) -> Version:
        return Version.parse(self.version)
