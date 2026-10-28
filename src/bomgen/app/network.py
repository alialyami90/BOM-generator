"""The Network result, the L1 ranking and the Panels board (plan M10c;
``docs/ui/screens.md``, Network and Panels).

Every value comes from M1c's ``layout_preview`` on the substation as written; this
module only flattens the result. The board is read-only until substation writers exist.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from bomgen.app.output import problems_of
from bomgen.app.substations import layout_message, resolve
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import LayoutResult, Unit, layout_preview
from bomgen.io.loader import LoadedSubstation
from bomgen.library_store.store import LibraryStore
from bomgen.models.substation import EquipmentRole, Side


def _label(loaded: LoadedSubstation, unit: Unit) -> str:
    entry = next(e for e in loaded.substation.equipment if e.id == unit.device)
    device = next(d for d in loaded.library.devices if d.part_id == unit.part_id)
    name = " ".join(x for x in (device.make, device.model) if x) or unit.part_id
    return f"{name} {entry.purpose}" if entry.purpose else name


def _placed(result: LayoutResult) -> dict[tuple[str, Side], int]:
    return {(u.key, u.side): f.number for f in result.fills for u in f.units}


def _board(loaded: LoadedSubstation, result: LayoutResult, auto: LayoutResult) -> list[Any]:
    automatic = _placed(auto)
    rules = result.rules
    roles = {e.id: e.role for e in loaded.substation.equipment}
    counts = Counter((u.device, u.side) for f in result.fills for u in f.units)
    return [
        {
            "number": fill.number,
            "id": panel.id,
            "cabinet_name": panel.cabinet_name,
            "cabinet_number": panel.cabinet_number,
            "side": panel.lan,
            "pair": (fill.number + 1) // 2,
            "capacity_u": rules.capacity_u,
            "used_u": fill.used_u(rules),
            "free_u": fill.free_u(rules),
            "blank_plates": fill.blank_plates(),
            "din_rail": fill.din_rail_count(),
            "units": [
                {
                    "key": unit.key,
                    "device": unit.device,
                    "role": roles[unit.device],
                    "n": unit.n,
                    "of": counts[unit.device, unit.side],
                    "side": None if unit.side is Side.NONE else unit.side.value.upper(),
                    "part_id": unit.part_id,
                    "label": _label(loaded, unit),
                    "height_u": unit.height_u,
                    "cable_manager_u": unit.cable_manager_u,
                    "block_u": unit.block_u,
                    "moved": automatic.get((unit.key, unit.side)) != fill.number,
                }
                for unit in fill.units
            ],
        }
        for panel, fill in zip(result.panels, result.fills, strict=True)
    ]


def _network(loaded: LoadedSubstation, page: dict[str, Any]) -> None:
    result = layout_preview(loaded)
    inputs = loaded.substation.layout
    auto = layout_preview(loaded, inputs.model_copy(update={"overrides": []}))
    plan = result.plan
    devices = {d.part_id: d for d in loaded.library.devices}
    l1 = next(e for e in loaded.substation.equipment if e.role is EquipmentRole.L1_SWITCH)
    page |= {
        "plan": {
            "ied_count": plan.ied_count,
            "topology": loaded.substation.network.topology,
            "l1_part_id": plan.l1_part_id,
            "l1_pinned": l1.part_id is not None,
            "l1_per_side": plan.l1_per_side,
            "l1_usable_ports": plan.l1_usable_ports,
            "l1_links_per_side": plan.l1_links_per_side,
            "rings_per_side": plan.rings_per_side,
            "l2_part_id": plan.l2_part_id,
            "l2_per_side": plan.l2_per_side,
            "l2_usable_ports": plan.l2_usable_ports,
            "l2_demand_per_side": plan.l2_demand_per_side,
        },
        "l1_ranking": [
            {
                "part_id": c.ports.part_id,
                "make": devices[c.ports.part_id].make,
                "model": devices[c.ports.part_id].model,
                "ports": c.ports.total,
                "per_side": c.per_side,
                "usable_ports": c.usable_ports,
            }
            for c in result.l1_candidates
        ],
        "panels": _board(loaded, result, auto),
        "issues": [
            {
                "level": "error" if i.is_error else "warning",
                "subject": i.subject,
                "message": layout_message(i),
            }
            for i in result.report.issues
        ],
    }


def layout_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The engine's sizing and layout for one substation, or why there is none."""
    found = resolve(project_file, substation_id, store)
    page: dict[str, Any] = {
        "problems": problems_of(project_file, found, store),
        "reason": None,
        "generated": False,
        "reserved_u": None,
        "plan": None,
        "l1_ranking": [],
        "panels": [],
        "issues": [],
        "overrides": [],
        "removed": [],
        "list": [],
    }
    loaded = found.source or found.loaded
    if loaded is None:
        count = len(found.problems)
        page["reason"] = f"{count} error{'' if count == 1 else 's'} in the input files"
        return page
    built = found.loaded or loaded
    layout = loaded.substation.layout
    page |= {
        "generated": any(p.generated for p in loaded.panels),
        "reserved_u": loaded.spares.rack_u_reserved,
        "overrides": [m.model_dump(mode="json") for m in layout.overrides],
        "removed": [r.model_dump(mode="json") for r in layout.removed],
        "list": [
            {
                "id": p.id,
                "sheet": p.sheet_name,
                "cabinet_number": p.cabinet_number,
                "cabinet_name": p.cabinet_name,
                "side": p.lan,
                "generated": p.generated,
                "manual": p.id in loaded.manual_panel_ids,
            }
            for p in built.panels
        ],
    }
    if not loaded.substation.equipment:
        return page
    try:
        _network(loaded, page)
    except EngineError as exc:
        page["reason"] = f"The engine stopped: {exc}"
    return page
