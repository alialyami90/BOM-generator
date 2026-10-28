"""The Loose material page: the substation's own list of items not mounted in a cabinet
(plan M18, ADRs 0020 and 0022). ``bomgen.io.loose_edit`` writes it; this module reads it
for the page, with each library part's make and model and the panels an item can name."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bomgen.app.substations import resolve
from bomgen.library_store.store import LibraryStore


def loose_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The items in sheet order, the host panel, the sheet's name, and the panels the
    sheet can be issued under (``host_options``) and an item can be fed from
    (``fed_options``: the generated cabinets, or every panel when none is generated)."""
    found = resolve(project_file, substation_id, store)
    page: dict[str, Any] = {
        "reason": None,
        "sheet_name": None,
        "title": None,
        "host_panel": None,
        "items": [],
        "host_options": [],
        "fed_options": [],
    }
    loaded = found.loaded or found.source
    if loaded is None:
        count = len(found.problems)
        page["reason"] = f"{count} error{'' if count == 1 else 's'} in the input files"
        return page
    substation = loaded.substation
    panels = [
        {"id": p.id, "name": p.cabinet_name, "sheet": p.sheet_name, "generated": p.generated}
        for p in loaded.panels
    ]
    generated = [p for p in panels if p["generated"]]
    page |= {
        "sheet_name": substation.output.sheet_names.loose_material,
        "host_options": panels,
        "fed_options": generated or panels,
    }
    material = substation.loose_material
    if material is None:
        return page
    page |= {"title": material.title, "host_panel": material.host_panel}
    for item in material.items:
        part = loaded.library.get(item.part_id) if item.part_id else None
        page["items"].append(
            {
                **item.model_dump(mode="json"),
                "make": part.make if part else None,
                "model": part.model if part else None,
                "ordering_code": part.ordering_code if part else None,
            }
        )
    return page
