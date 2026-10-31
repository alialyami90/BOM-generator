"""One panel for the panel editor (plan M32a; ``docs/ui/screens.md``, Panel editor).

Generated panels come from the layout as ``bomgen build`` makes them: their devices are
the board's units, their options are read with ``bomgen.io.edit.panel_options``, and
their port plans are the equipment rows' with the BOM lines the engine made of them.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from bomgen.app.network import _board
from bomgen.app.output import problems_of
from bomgen.app.substations import resolve
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import layout_preview
from bomgen.engine.pipeline import build
from bomgen.io.edit import panel_options
from bomgen.io.loader import LoadedSubstation
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.store import LibraryStore
from bomgen.models.bom import BomLine, Group, QtySum
from bomgen.models.panel import Panel, PanelOptions
from bomgen.models.substation import EquipmentRole

SIZED = (EquipmentRole.L1_SWITCH, EquipmentRole.L2_SWITCH)  # their port plans are computed


class PanelNotFoundError(LookupError):
    """The substation has no panel with this id."""


def _qty(line: BomLine) -> str:
    return "+".join(map(str, line.qty.parts)) if isinstance(line.qty, QtySum) else str(line.qty)


def _ports(
    loaded: LoadedSubstation, panel: Panel, units: list[dict[str, Any]], lines: Sequence[BomLine]
) -> list[Any]:
    """Each device's port plan: its own (editable unless sized), the panel's, the engine's lines."""
    equipment = loaded.substation.equipment
    rows = []
    for device in dict.fromkeys(u["device"] for u in units):
        index, entry = next((i, e) for i, e in enumerate(equipment) if e.id == device)
        part_id = next(u["part_id"] for u in units if u["device"] == device)
        tag = next((x.tag for x in lines if x.group is Group.B and x.part_id == part_id), None)
        short = (tag or "").removeprefix(f"{panel.tag_prefix}-")
        used = panel.port_plans.get(tag or "") or panel.port_plans.get(part_id)
        rows.append(
            {
                "device": device,
                "role": entry.role.value,
                "part_id": part_id,
                "editable": entry.role not in SIZED,
                "equipment": index,
                "own": entry.port_plan.model_dump(mode="json") if entry.port_plan else None,
                "used": used.model_dump(mode="json") if used else None,
                "l2": {
                    "ports": entry.l2_ports,
                    "speed": entry.l2_speed.value,
                    "media": entry.l2_media.value,
                },
                "lines": [
                    {"description": x.description, "part_id": x.part_id, "qty": _qty(x)}
                    for x in lines
                    if x.group is Group.C and tag and (x.tag or "").startswith(f"{short} ")
                ],
            }
        )
    return rows


def _part_label(loaded: LoadedSubstation, part_id: str) -> str:
    found = loaded.library.get(part_id)
    return " ".join(x for x in (found.make, found.model) if x) if found else part_id


def part_list(loaded: LoadedSubstation) -> list[dict[str, str]]:
    """Every part of the substation's library, for the hand-written panels' device picker."""
    return [
        {
            "part_id": d.part_id,
            "label": _part_label(loaded, d.part_id),
            "category": d.category.value,
        }
        for d in loaded.library.devices
    ]


def panel_page(
    project_file: Path, substation_id: str, panel_id: str, store: LibraryStore
) -> dict[str, Any]:
    """The panel editor's view of one panel, or the substation's problems when it can't load."""
    found = resolve(project_file, substation_id, store)
    page: dict[str, Any] = {
        "problems": problems_of(project_file, found, store),
        "reason": None,
        "engine_error": None,
        "panel": None,
    }
    loaded = found.loaded
    if loaded is None:
        count = len(found.problems)
        page["reason"] = f"{count} error{'' if count == 1 else 's'} in the input files"
        return page
    panel = next((p for p in loaded.panels if p.id == panel_id), None)
    if panel is None:
        raise PanelNotFoundError(panel_id)
    file = loaded.panel_files[panel.id]
    board = (
        next(
            b for b in _board(loaded, layout_preview(found.source or loaded)) if b["id"] == panel.id
        )
        if panel.generated
        else None
    )
    units = board["units"] if board else []
    defaults = PanelOptions().model_dump(mode="json")
    written = panel.options.model_fields_set
    lines: Sequence[BomLine] = []
    try:
        lines = next(b.lines for b in build(loaded).panels if b.panel_id == panel.id)
    except EngineError as exc:
        page["engine_error"] = str(exc)
    page |= {
        "panel": {
            "id": panel.id,
            "number": board["number"] if board else None,
            "cabinet_number": panel.cabinet_number,
            "cabinet_name": panel.cabinet_name,
            "sheet": panel.sheet_name,
            "kind": panel.kind.value,
            "side": board["side"] if board else panel.lan,
            "pair": board["pair"] if board else None,
            "tag_prefix": panel.tag_prefix,
            "lan": panel.lan,
            "generated": panel.generated,
            "manual": panel.id in loaded.manual_panel_ids,
            "mirror_of": read_yaml(file).data.get("mirror_of"),
            "file": str(file),
        },
        "enclosure": panel.enclosure.model_dump(mode="json", exclude_none=True),
        "document": panel.document,
        "documents": [
            e.model_dump(mode="json")
            for e in loaded.project.documents
            if e.substation == substation_id
        ],
        "options": (
            [dataclasses.asdict(o) for o in panel_options(loaded, board["number"])]
            if board
            else [  # a hand-written panel's own values; "shared" is the default
                {"key": k, "value": v, "shared": defaults[k], "own": k in written}
                for k, v in panel.options.model_dump(mode="json").items()
            ]
        ),
        "devices": (
            [
                {
                    **{k: u[k] for k in ("device", "part_id", "label", "role", "side", "n")},
                    **{k: u[k] for k in ("height_u", "position")},
                    "origin": "pinned" if u["pinned"] else "layout",
                }
                for u in units
            ]
            if board
            else [
                {
                    **d.model_dump(mode="json", exclude_none=True),
                    "label": _part_label(loaded, d.part_id),
                }
                for d in panel.devices
            ]
        ),
        "ports": _ports(loaded, panel, units, lines) if board else [],
        "parts": [] if board else part_list(loaded),
        "yaml": file.read_text(encoding="utf-8"),
    }
    return page
