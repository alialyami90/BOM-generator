"""What the workbook will contain, as the Preview screen shows it (plan M10d;
``docs/ui/screens.md``, Preview).

Every value comes from the engine's ``BuildResult`` and its models' own properties;
this module only flattens them into rows and resolves each power line to its BOM row.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bomgen.app.output import problems_of
from bomgen.app.substations import resolve
from bomgen.engine.errors import EngineError
from bomgen.engine.pipeline import build as build_bom
from bomgen.library_store.store import LibraryStore
from bomgen.models.bom import BomLine, BomTable, BuildResult, Qty, QtySum
from bomgen.models.calc import CabinetHeat, LineRef, PowerBlock, PowerLine


def _qty(qty: Qty) -> int | str:
    """The quantity as the sheet shows it: ``24+3`` for a sum."""
    return "+".join(str(part) for part in qty.parts) if isinstance(qty, QtySum) else qty


def _rows(table: BomTable) -> list[dict[str, Any]]:
    separators = set(table.separators_before())
    last_child: dict[int, int] = {}
    for index, line in enumerate(table.lines):
        if line.parent is not None:
            last_child[line.parent] = max(last_child.get(line.parent, index), index)
    return [
        {
            "sr": index + 1,
            "group": line.group,
            "tag": line.tag,
            "parent": line.parent,
            "tag_rows": last_child[index] - index + 1 if index in last_child else 1,
            "description": line.description,
            "qty": _qty(line.qty),
            "make": line.make,
            "model": line.model,
            "ordering_code": line.ordering_code,
            "hwio": line.hwio,
            "revised": sorted(line.revised),
            "separator_before": index in separators,
        }
        for index, line in enumerate(table.lines)
    ]


def _bom_line(result: BuildResult, ref: LineRef) -> BomLine:
    if ref.panel_id is None:
        assert result.loose is not None
        return result.loose.lines[ref.line]
    panel = next(p for p in result.panels if p.panel_id == ref.panel_id)
    return panel.lines[ref.line]


def _power_line(result: BuildResult, line: PowerLine) -> dict[str, Any]:
    bom = _bom_line(result, line.source)
    return {
        "panel_id": line.source.panel_id,
        "tag": bom.tag,
        "description": bom.description,
        "make": bom.make,
        "model": bom.model,
        "supply": line.supply_label,
        "supply_type": line.supply_type,
        "load_type": line.load_type,
        "qty": line.qty,
        "unit_w": line.unit_w,
        "total_w": line.total_w,
        "current_a": line.current_a,
        "current_with_margin_a": line.current_with_margin_a,
        "device_mcb_a": line.device_mcb_a,
    }


def _block(result: BuildResult, block: PowerBlock | None) -> dict[str, Any] | None:
    if block is None:
        return None
    return {
        "supply_type": block.supply_type,
        "margin": block.margin,
        "subtotal_w": block.subtotal_w,
        "total_w": block.total_w,
        "lines": [_power_line(result, line) for line in block.lines],
    }


def _dissipation(
    result: BuildResult, cabinet: CabinetHeat, names: dict[str, str]
) -> dict[str, Any]:
    return {
        "panel_id": cabinet.panel_id,
        "cabinet": names.get(cabinet.panel_id) if cabinet.panel_id else None,
        "total_w": cabinet.total_w,
        "total_btu_h": cabinet.total_btu_h,
        "lines": [
            {
                **_power_line(result, line.power),
                "unit_btu_h": line.unit_btu_h,
                "total_btu_h": line.total_btu_h,
            }
            for line in cabinet.lines
        ],
    }


def _sheets(result: BuildResult, names: dict[str, str]) -> dict[str, Any]:
    power = result.power
    heat = result.heat
    return {
        "panels": [
            {
                "panel_id": panel.panel_id,
                "sheet": panel.sheet_name,
                "cabinet": names.get(panel.panel_id),
                "title": panel.title,
                "rows": _rows(panel),
                "hwio_total": sum(line.hwio for line in panel.lines),
            }
            for panel in result.panels
        ],
        "power": None
        if power is None
        else {
            "dc_total_w": power.dc_total_w,
            "ac_total_w": power.ac_total_w,
            "total_w": power.total_w,
            "cabinets": [
                {
                    "panel_id": c.panel_id,
                    "cabinet": names.get(c.panel_id),
                    "dc": _block(result, c.dc),
                    "ac": _block(result, c.ac),
                }
                for c in power.cabinets
            ],
            "external": _block(result, power.external),
        },
        "heat_dissipation": None
        if heat is None
        else [_dissipation(result, cabinet, names) for cabinet in heat.dissipation],
        "heat_calculations": None
        if heat is None
        else {
            "cabinets": [
                {
                    "panel_id": c.panel_id,
                    "cabinet": names.get(c.panel_id),
                    "ventilation": c.ventilation,
                    "forced": {**c.forced.model_dump(mode="json"), "passes": c.forced.passes},
                    "natural": {**c.natural.model_dump(mode="json"), "passes": c.natural.passes},
                }
                for c in heat.cabinets
            ],
            "line_up": None
            if heat.line_up is None
            else {**heat.line_up.model_dump(mode="json"), "passes": heat.line_up.passes},
        },
    }


def preview_page(project_file: Path, substation_id: str, store: LibraryStore) -> dict[str, Any]:
    """The workbook's sheets for one substation, or why there is nothing to show."""
    found = resolve(project_file, substation_id, store)
    page: dict[str, Any] = {"problems": problems_of(project_file, found, store), "reason": None}
    loaded = found.loaded
    if loaded is None:
        count = len(found.problems)
        page["reason"] = f"{count} error{'' if count == 1 else 's'} in the input files"
        return page
    try:
        result = build_bom(loaded)
    except EngineError as exc:
        page["reason"] = f"The engine stopped: {exc}"
        return page
    names = {panel.id: panel.cabinet_name for panel in loaded.panels}
    sheet_names = loaded.substation.output.sheet_names
    return page | {
        "calc_sheets": {
            "power": sheet_names.power_consumption,
            "heat_dissipation": sheet_names.heat_dissipation,
            "heat_calculations": sheet_names.heat_calculations,
        },
        "loose": None
        if result.loose is None
        else {
            "sheet": sheet_names.loose_material,
            "title": result.loose.title,
            "rows": _rows(result.loose),
            "hwio_total": sum(line.hwio for line in result.loose.lines),
        },
        "nameplates": None  # ADR 0026
        if not result.nameplates
        else {
            "sheet": sheet_names.nameplates,
            "panels": [
                {
                    "panel_id": p.panel_id,
                    "cabinet": names.get(p.panel_id),
                    "plates": [plate.model_dump(mode="json") for plate in p.plates],
                }
                for p in result.nameplates
            ],
        },
        **_sheets(result, names),
    }
