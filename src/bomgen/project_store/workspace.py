"""The folder that holds the user's projects."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

WORKSPACE_ENV = "BOMGEN_WORKSPACE"


def default_workspace(env: Mapping[str, str] = os.environ, home: Path | None = None) -> Path:
    """`BOMGEN_WORKSPACE`, else `Documents/BOM Generator` in the user's home folder."""
    if override := env.get(WORKSPACE_ENV, "").strip():
        return Path(override)
    return (home or Path.home()) / "Documents" / "BOM Generator"
