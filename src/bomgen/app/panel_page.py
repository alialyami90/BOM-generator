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
from bomgen.checks import duplicate_tag_checks
from bomgen.engine.errors import EngineError
from bomgen.engine.layout import layout_preview
from bomgen.engine.mcb import has_branch_mcb
from bomgen.engine.pipeline import build
from bomgen.engine.units import expand_devices
from bomgen.io.edit import panel_options
from bomgen.io.loader import LoadedSubstation
from bomgen.io.yaml_source import read_yaml
from bomgen.library_store.store import LibraryStore
from bomgen.models.bom import BomLine, Group, QtySum, StripRow
from bomgen.models.calc import DcMains, SpareRatings
from bomgen.models.output import Derived
from bomgen.models.panel import Panel, PanelOptions
from bomgen.models.substation import EquipmentRole, GeneratedPanels

SIZED = (EquipmentRole.L1_SWITCH, EquipmentRole.L2_SWITCH)  # their port plans are computed
TEMPLATE = ("cabinet_name", "cabinet_number", "tag_prefix", "sheet_name")


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


def _alarm(loaded: LoadedSubstation, part_id: str) -> dict[str, bool]:
    """Whether the part has a branch MCB, and the library's alarm on its trip (plan M58)."""
    found = loaded.library.get(part_id)
    if found is None:
        return {"branch_mcb": False, "alarm_default": False}
    return {"branch_mcb": has_branch_mcb(found), "alarm_default": found.alarm_on_branch_mcb}


def _tagging(loaded: LoadedSubstation, panel: Panel) -> list[dict[str, Any]]:
    """Per device row: its units' tags (the placeholders of the tag fields) and the
    duplicate-tag check's sentence when one of them is another unit's too (plan M59)."""
    blank: list[dict[str, Any]] = [{"tags": [], "duplicate": None} for _ in panel.devices]
    try:
        expanded = [
            (p, expand_devices(p, loaded.library, tagging=loaded.tagging)) for p in loaded.panels
        ]
    except EngineError:
        return blank
    rows = next((r for p, r in expanded if p.id == panel.id), ())
    if len(rows) != len(panel.devices):
        return blank
    duplicate = {
        item.subject: f"{item.subject}: {item.message}" for item in duplicate_tag_checks(expanded)
    }
    return [
        {
            "tags": [t for t in row.unit_tags if t is not None],
            "duplicate": next((duplicate[t] for t in row.unit_tags if t in duplicate), None),
        }
        for row in rows
    ]


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
    main: DcMains | None = None
    spares: SpareRatings | None = None
    strips: Sequence[StripRow] = ()
    try:
        result = build(loaded)
        lines = next(b.lines for b in result.panels if b.panel_id == panel.id)
        main = next((m for m in result.mains if m.panel_id == panel.id), None)
        spares = next((s for s in result.spares if s.panel_id == panel.id), None)
        strips = next((s.strips for s in result.strips if s.panel_id == panel.id), ())
    except EngineError as exc:
        page["engine_error"] = str(exc)
    tagging = _tagging(loaded, panel)
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
        # the numbering every generated panel shares (ALI-5, ALI-13); {n} is the panel number
        "template": {k: getattr(loaded.substation.generated_panels, k) for k in TEMPLATE}
        if panel.generated and loaded.substation.generated_panels
        else None,
        "enclosure": panel.enclosure.model_dump(mode="json", exclude_none=True),
        # what every generated panel shares, and whether this one has its own (plan M50)
        "shared": _shared(loaded.substation.generated_panels, board["number"]) if board else None,
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
                    **_alarm(loaded, d.part_id),
                    **tagging[i],
                }
                for i, d in enumerate(panel.devices)
            ]
        ),
        # values the engine derives, each with its rule (plan M48)
        "derived": {
            "main_mcb_a": Derived[int](
                value=main.rule_rating_a,
                rule=main.rule,
                override=panel.options.main_mcb_override_a,
                unit="A",
            ).model_dump(mode="json")
            if main is not None and main.rule_rating_a
            else None,
            # the spare breakers' ratings (plan M58)
            "ac_spare_a": Derived[int](
                value=spares.ac_rule_a,
                rule=spares.ac_rule,
                override=panel.options.ac_spare_rating_a,
                unit="A",
            ).model_dump(mode="json")
            if spares is not None
            else None,
            "dc_spare_a": Derived[int](
                value=spares.dc_rule_a,
                rule=spares.dc_rule,
                override=panel.options.dc_spare_rating_a,
                unit="A",
            ).model_dump(mode="json")
            if spares is not None and spares.dc_rule_a
            else None,
        },
        # the busbar catalogue, for the grounding choice (plan M58)
        "busbars": [
            {"key": k, "tag": b.tag, "description": b.description}
            for k, b in loaded.library.catalogues.busbars.items()
        ],
        # group G's strips, each quantity with its rule (ADR 0033)
        "terminals": [
            {
                **s.model_dump(mode="json", include={"code", "description", "block", "spared"}),
                "block_override": s.block_override,
                "qty": Derived[int](value=s.auto_qty, rule=s.rule, override=s.override).model_dump(
                    mode="json"
                ),
            }
            for s in strips
        ],
        "terminal_blocks": list(loaded.library.catalogues.terminal_blocks),
        "ports": _ports(loaded, panel, units, lines) if board else [],
        "parts": [] if board else part_list(loaded),
        "yaml": file.read_text(encoding="utf-8"),
    }
    return page


def _shared(generated: GeneratedPanels | None, number: int) -> dict[str, Any] | None:
    if generated is None:
        return None
    return {
        "enclosure": generated.enclosure.model_dump(mode="json", exclude_none=True),
        "kind": generated.kind.value,
        "own_enclosure": number in generated.enclosure_by_panel,
        "own_kind": number in generated.kind_by_panel,
    }
