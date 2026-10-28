"""JSON Schemas for the input files, so editors can validate and complete YAML as it is typed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from bomgen.models.library import Library
from bomgen.models.panel import Panel, PanelMirror
from bomgen.models.project import Project

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def json_schemas() -> dict[str, dict[str, Any]]:
    """Return the schema of each input file, keyed by the file name it is written to."""
    panel = TypeAdapter(Panel | PanelMirror).json_schema()
    panel["title"] = "Panel"
    schemas = {
        "project.schema.json": Project.model_json_schema(),
        "library.schema.json": Library.model_json_schema(),
        "panel.schema.json": panel,
    }
    return {name: {"$schema": JSON_SCHEMA_DIALECT, **schema} for name, schema in schemas.items()}


def write_json_schemas(out_dir: Path) -> list[Path]:
    """Write every schema into ``out_dir`` (created if missing); return the paths by name."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, schema in sorted(json_schemas().items()):
        path = out_dir / name
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written
