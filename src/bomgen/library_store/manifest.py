"""The `manifest.json` at the root of every `.bomlib` package (ADR 0008)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bomgen.library_store.versions import Version

FORMAT_VERSION = 1
LIBRARY_SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"
LIBRARY_FILE = "library.yaml"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_DRIVE = re.compile(r"[A-Za-z]:")


def is_safe_member(path: str) -> bool:
    """True if `path` is a plain relative POSIX path that cannot escape its directory."""
    if not path or "\\" in path or path.startswith("/") or _DRIVE.match(path):
        return False
    return all(part not in ("", ".", "..") for part in path.split("/"))


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
        for path, digest in files.items():
            if not is_safe_member(path) or path == MANIFEST_NAME:
                raise ValueError(f"unsafe file path {path!r}")
            if not _SHA256.fullmatch(digest):
                raise ValueError(f"{path}: checksum must be 64 lowercase hex digits")
        return files

    @property
    def parsed_version(self) -> Version:
        return Version.parse(self.version)
