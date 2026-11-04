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
from bomgen.engine.layout import (
    LayoutResult,
    Unit,
    blank_plates,
    layout_preview,
    network_inputs,
)
from bomgen.engine.rules_text import reserved_rule, spare_ports_rule, switch_count_rule
from bomgen.engine.sizing import NetworkPlan, PortBudget, port_budgets, switch_ports
from bomgen.io.loader import LoadedSubstation
from bomgen.library_store.store import LibraryStore
from bomgen.models.library import DeviceType
from bomgen.models.output import Derived
from bomgen.models.substation import EquipmentRole, Side, Topology


def _label(loaded: LoadedSubstation, unit: Unit) -> str:
    entry = next(e for e in loaded.substation.equipment if e.id == unit.device)
    device = next(d for d in loaded.library.devices if d.part_id == unit.part_id)
    name = " ".join(x for x in (device.make, device.model) if x) or unit.part_id
    return f"{name} {entry.purpose}" if entry.purpose else name


def _plates_below(units: list[Unit], plate_u: int) -> dict[int, int]:
    """Rack units of blank plate under each unit, by the engine's R5 rule on each neighbour pair."""
    rack = [u for u in units if u.block_u > 0]
    return {id(u): blank_plates(rack[i : i + 2]) * plate_u for i, u in enumerate(rack)}


def _board(loaded: LoadedSubstation, result: LayoutResult) -> list[Any]:
    rules = result.rules
    roles = {e.id: e.role for e in loaded.substation.equipment}
    counts = Counter((u.device, u.side) for f in result.fills for u in f.units)
    stacks = [fill.stack() for fill in result.fills]
    plates = {k: v for s in stacks for k, v in _plates_below(s, rules.blank_plate_u).items()}
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
                    "plate_below_u": plates.get(id(unit), 0),
                    "pinned": fill.is_pinned(unit),
                    "position": fill.position(unit),
                }
                for unit in stack
            ],
        }
        for panel, fill, stack in zip(result.panels, result.fills, stacks, strict=True)
    ]


def _base(loaded: LoadedSubstation, part_id: str) -> str:
    """The library part a derived part (ADR 0024) was made from, as the person picked it."""
    found = loaded.library.get(part_id)
    return found.derived_from if found and found.derived_from else part_id


def _ied_ports(loaded: LoadedSubstation) -> list[dict[str, Any]] | None:
    """The schedule's ports per speed and media on each side, by where they land; None for
    the quick count (ADR 0034)."""
    schedule = loaded.substation.network.ied_schedule
    if not schedule:
        return None
    found: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in schedule:
        sides = {"dual": "ab", "single_a": "a", "single_b": "b"}[row.attachment]
        for need in row.ports:
            key = (need.speed.value, need.media.value, row.lands_on)
            entry = found.setdefault(
                key, {"speed": key[0], "media": key[1], "lands_on": key[2], "a": 0, "b": 0}
            )
            for side in sides:
                entry[side] += row.qty * need.count
    return list(found.values())


def _device(loaded: LoadedSubstation, part_id: str) -> DeviceType:
    found = loaded.library.get(part_id)
    assert found is not None  # the sizing picked it from this library
    return found


def _budget(loaded: LoadedSubstation, plan: NetworkPlan) -> list[dict[str, Any]]:
    """Each switch level's ports on the busier side, with the rules behind them (plan M72)."""
    net = network_inputs(loaded)
    l1, l2 = (switch_ports(_device(loaded, p)) for p in (plan.l1_part_id, plan.l2_part_id))
    ring = net.topology is Topology.RING
    uplinks, interlink = net.l1_uplinks_per_switch, net.l1_interlink
    rules = {
        "L1": reserved_rule(uplinks=uplinks, interlink=interlink, ring=ring),
        "L2": reserved_rule(uplinks=net.l3_uplinks_per_l2, interlink=False, ring=False),
    }

    def row(level: str, b: PortBudget) -> dict[str, Any]:
        return {
            "level": level,
            "switches": b.switches,
            "ports": b.ports,
            "reserved": b.reserved,
            "spare": b.spare,
            "used": b.used,
            "free": b.free,
            "reserved_rule": rules[level],
            "spare_rule": spare_ports_rule(net.port_fraction),
        }

    return [
        row(level, b)
        for level, b in zip(("L1", "L2"), port_budgets(plan, net, l1, l2), strict=True)
    ]


def _counts(loaded: LoadedSubstation, plan: NetworkPlan, budget: list[Any]) -> dict[str, Any]:
    """The switch counts per side as derived values: the sizing's, and the engineer's."""
    network = loaded.substation.network
    l1 = switch_count_rule(plan.l1_needed, budget[0]["used"], plan.l1_usable_ports, ieds=True)
    l2 = switch_count_rule(plan.l2_needed, budget[1]["used"], plan.l2_usable_ports, ieds=False)
    return {
        "l1_count": Derived[int](value=plan.l1_needed, rule=l1, override=network.l1_per_side),
        "l2_count": Derived[int](value=plan.l2_needed, rule=l2, override=network.l2_per_side),
    }


def _network(loaded: LoadedSubstation, page: dict[str, Any]) -> None:
    result = layout_preview(loaded)
    plan = result.plan
    l1 = next(e for e in loaded.substation.equipment if e.role is EquipmentRole.L1_SWITCH)
    budget = _budget(loaded, plan)
    counts = {k: v.model_dump(mode="json") for k, v in _counts(loaded, plan, budget).items()}
    page |= {
        "plan": {
            "ied_count": plan.ied_count,
            "topology": loaded.substation.network.topology,
            "l1_part_id": _base(loaded, plan.l1_part_id),
            "l1_pinned": l1.part_id is not None,
            "l1_per_side": plan.l1_per_side,
            "l1_usable_ports": plan.l1_usable_ports,
            "l1_links_per_side": plan.l1_links_per_side,
            "rings_per_side": plan.rings_per_side,
            "l2_part_id": _base(loaded, plan.l2_part_id),
            "l2_per_side": plan.l2_per_side,
            "l2_usable_ports": plan.l2_usable_ports,
            "l2_demand_per_side": plan.l2_demand_per_side,
            "ied_ports": _ied_ports(loaded),
            "budget": budget,  # M72
            **counts,
            "external_links": [
                {
                    "name": x.name,
                    "count": x.count,
                    "speed": x.speed.value,
                    "media": x.media.value,
                    "lands_on": x.lands_on,
                    "a": x.count,
                    "b": x.count if x.redundant else 0,
                }
                for x in loaded.substation.network.external_links
            ],
        },
        "panels": _board(loaded, result),
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
