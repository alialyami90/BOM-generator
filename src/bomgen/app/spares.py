"""The Spares page: the spares list as the Spare Parts sheet prints it, with the policy it
comes from and the substation's edits (plan M64, ADR 0035). The edits are plain substation
fields (``spares_list.items``, ``excluded``, ``extra``) written by ``set_substation_field``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bomgen.app.substations import resolve
from bomgen.engine.errors import EngineError
from bomgen.engine.pipeline import build
from bomgen.engine.spares import spares
from bomgen.engine.units import describe
from bomgen.library_store.store import LibraryStore


def spares_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The lines with the key an override names, the policy, the codes left out and the
    library parts an extra can name; ``reason`` says why there are none to show."""
    found = resolve(project_file, substation_id, store)
    page: dict[str, Any] = {
        "reason": None,
        "sheet_name": None,
        "policy": None,
        "lines": [],
        "excluded": [],
        "extra": [],
        "parts": [],
    }
    loaded = found.loaded
    if loaded is None:
        count = len(found.problems)
        page["reason"] = f"{count} error{'' if count == 1 else 's'} in the input files"
        return page
    substation = loaded.substation
    page["sheet_name"] = substation.output.sheet_names.spare_parts
    basis = substation.design_basis
    if basis is not None and basis.spares_policy is not None:
        page["policy"] = basis.spares_policy.model_dump(mode="json")
    edits = substation.spares_list
    if edits is not None:
        page["excluded"] = list(edits.excluded)
        page["extra"] = [e.model_dump(mode="json", exclude_none=True) for e in edits.extra]
    page["parts"] = [
        {"part_id": p.part_id, "description": describe(p, None, None).split("\n")[0]}
        for p in loaded.library.devices
    ]
    try:
        table = spares(loaded, build(loaded))
    except EngineError as exc:
        page["reason"] = f"The engine stopped: {exc}"
        return page
    page["lines"] = [
        line.model_dump(mode="json") | {"key": line.ordering_code or line.model}
        for line in table.lines
    ]
    return page
