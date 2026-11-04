"""The Suggest cables dialog on Loose material: the cords the port plans call for, each
with the loose item it becomes once accepted (plan M65, Q66, Q71)."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from bomgen.app.substations import resolve
from bomgen.engine.cables import loose_item, suggest_cables
from bomgen.engine.errors import EngineError
from bomgen.engine.pipeline import build
from bomgen.library_store.store import LibraryStore


def cables_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The suggested rows and the warnings; ``reason`` says why there are none to show."""
    found = resolve(project_file, substation_id, store)
    page: dict[str, Any] = {"reason": None, "rows": [], "warnings": []}
    loaded = found.loaded
    if loaded is None:
        count = len(found.problems)
        page["reason"] = f"{count} error{'' if count == 1 else 's'} in the input files"
        return page
    try:
        result = suggest_cables(loaded, build(loaded))
    except EngineError as exc:
        page["reason"] = f"The engine stopped: {exc}"
        return page
    page["rows"] = [
        {**asdict(row), "media": row.media, "speed": row.speed, "item": loose_item(row)}
        for row in result.rows
    ]
    page["warnings"] = list(result.warnings)
    return page
