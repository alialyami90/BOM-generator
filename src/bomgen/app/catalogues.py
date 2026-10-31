"""The library's commodity catalogues for the Library screen (backlog v0.2 point 1).

Read-only: each entry carries the device-database record that names it in
``library_refs`` (data/device-db/README.md), or ``None`` when there is none.
"""

from collections.abc import Mapping
from typing import Any

from bomgen.library_store.device_db import DeviceRecord
from bomgen.models.library import Catalogues


def _refs(records: Mapping[str, DeviceRecord]) -> dict[str, str]:
    """Map each ``library_refs`` entry to the part id of its record (first one wins)."""
    found: dict[str, str] = {}
    for record in records.values():
        for ref in record.library_refs or ():
            found.setdefault(ref, record.part_id)
    return found


def _housekeeping(catalogues: Catalogues) -> list[tuple[str, str, str | None]]:
    kit = catalogues.housekeeping
    roles: list[tuple[str, str, str | None]] = [("lamp", kit.lamp.part_id, None)]
    if kit.door_switch is not None:
        roles.append(("door_switch", kit.door_switch.part_id, None))
    roles += [
        ("fan", kit.fan.part_id, f"{kit.fan.airflow_m3h:g} m³/h per fan"),
        ("vent_filter", kit.vent_filter.part_id, None),
        ("thermostat", kit.thermostat.part_id, None),
        ("ipr_kit", kit.ipr_kit.part_id, None),
        ("change_over_diode_negative", kit.change_over_diodes.negative, None),
        ("change_over_diode_positive", kit.change_over_diodes.positive, None),
        ("socket", kit.socket.part_id, f"{kit.socket.rating_a} A"),
    ]
    if kit.nameplate is not None:
        roles.append(("nameplate", kit.nameplate.part_id, None))
    return roles


def catalogues_page(
    catalogues: Catalogues, part_ids: set[str], records: Mapping[str, DeviceRecord]
) -> dict[str, Any]:
    """The catalogues as rows, each with its device-database record part id."""
    refs = _refs(records)
    mcb = catalogues.mcb
    aux = catalogues.aux_contact
    return {
        "enclosure_u": catalogues.enclosure_u,
        "mcb": {
            "family": mcb.family,
            "make": mcb.make,
            "poles": mcb.poles,
            "ratings": [
                {"rating_a": a, "code": mcb.code_for(a), "record": refs.get(f"mcb.{a}")}
                for a in mcb.ratings_a
            ],
        },
        "aux_contact": {
            "make": aux.make,
            "model": aux.model,
            "ordering_code": aux.ordering_code,
            "record": refs.get("aux_contact"),
        },
        "terminal_blocks": [
            {
                "type": name,
                "make": block.make,
                "ordering_code": block.ordering_code,
                "record": refs.get(f"terminal_blocks.{name}"),
            }
            for name, block in catalogues.terminal_blocks.items()
        ],
        "busbars": [
            {
                "key": key,
                "tag": busbar.tag,
                "description": busbar.description,
                "record": refs.get(f"busbars.{key}"),
            }
            for key, busbar in catalogues.busbars.items()
        ],
        "housekeeping": [
            {"role": role, "part_id": part_id, "detail": detail, "in_library": part_id in part_ids}
            for role, part_id, detail in _housekeeping(catalogues)
        ],
    }
