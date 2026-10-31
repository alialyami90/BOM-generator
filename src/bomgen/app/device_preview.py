"""The Device preview page (plan M24; docs/ui/screens.md "Device preview").

The engine's ``device_preview`` as the screen reads it, with each unit named as Parts names
its row. Pins are written through the board's ``set_layout_overrides``, so the page also
carries the layout inputs they replace.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bomgen.app.output import problems_of
from bomgen.app.parts import row_label
from bomgen.app.substations import resolve
from bomgen.engine.preview import device_preview
from bomgen.library_store.store import LibraryStore


def device_preview_page(
    project_file: Path, substation_id: str, store: LibraryStore
) -> dict[str, Any]:
    """The preview of the saved substation, or why there is none (``reason``)."""
    found = resolve(project_file, substation_id, store)
    page: dict[str, Any] = {
        "problems": problems_of(project_file, found, store),
        "reason": None,
        "saved_at": datetime.fromtimestamp(found.file.stat().st_mtime, UTC).isoformat(),
    }
    loaded = found.source or found.loaded
    if loaded is None:
        count = len(found.problems)
        return page | {"reason": f"{count} error{'' if count == 1 else 's'} in the input files"}
    preview = device_preview(loaded).model_dump(mode="json")
    labels = {e.id: row_label(e, loaded.library) for e in loaded.substation.equipment}
    for panel in preview["panels"]:
        for unit in panel["units"]:
            unit["label"] = labels.get(unit["device"], unit["device"])
    for issue in preview["issues"]:  # a check about an equipment row names it as its subject
        if issue["device"] is None and issue["subject"] in labels:
            issue["device"] = issue["subject"]
    layout = loaded.substation.layout.model_dump(mode="json", exclude_none=True)
    generated = any(p.generated for p in loaded.panels)  # pins reach only generated panels
    extra = {"generated": generated, "overrides": layout["overrides"], "removed": layout["removed"]}
    return page | preview | extra
