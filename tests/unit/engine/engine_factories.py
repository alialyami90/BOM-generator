"""In-memory input models for engine tests: small, valid, overridable per field."""

from typing import Any

from bomgen.models.library import DeviceType, Library
from bomgen.models.panel import DeviceInstance, Panel
from bomgen.models.project import LooseExtra


def device(part_id: str, category: str = "component", **fields: Any) -> dict[str, Any]:
    """A library device record as a mapping (validated by :func:`library`)."""
    record: dict[str, Any] = {
        "part_id": part_id,
        "category": category,
        "make": "Acme",
        "model": part_id,
        "ordering_code": part_id,
        "description_template": part_id,
    }
    return record | fields


def powered(part_id: str, category: str, **fields: Any) -> dict[str, Any]:
    """A dual-fed 125 V DC device record."""
    defaults: dict[str, Any] = {
        "supply_type": "VDC",
        "voltage_v": 125,
        "unit_power_w": 10,
        "load_type": "CONTINUOUS",
        "power_supplies": 2,
        "min_branch_mcb_a": 2,
    }
    return device(part_id, category, **(defaults | fields))


def switch(part_id: str, level: str, **fields: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "make": "Ruggedcom",
        "tag_type": "ESW",
        "purdue_level": level,
        "description_template": "LAN-{lan} switch ({level})",
    }
    return powered(part_id, "network_switch", **(defaults | fields))


def sfp(part_id: str, speed: str, media: str, make: str = "Ruggedcom") -> dict[str, Any]:
    return device(
        part_id,
        "sfp",
        make=make,
        ports=[{"count": 1, "speed": speed, "media": media, "kind": "fixed"}],
    )


HOUSEKEEPING_DEVICES = [
    device("LAMP", "lamp", tag_type="IL", tag_pattern="{prefix}-IL"),
    device("FAN", "fan", tag_type="FAN"),
    device("FILTER", "vent_filter", tag_type="FILTER", tag_pattern="{prefix}-FILTER"),
    device("TH", "thermostat", tag_type="TH"),
    device(
        "IPR",
        "relay",
        tag_type="IPR",
        tag_pattern="{prefix}-IPR",
        children=[{"part_id": "IPR-BASE"}, {"part_id": "IPR-SUPP"}, {"part_id": "IPR-BRKT"}],
    ),
    device("IPR-BASE"),
    device("IPR-SUPP"),
    device("IPR-BRKT"),
    device("COD-NEG", "change_over_diode", tag_type="COD", tag_pattern="{prefix}-COD-1"),
    device("COD-POS", "change_over_diode", tag_type="COD", tag_pattern="{prefix}-COD-2"),
    device("SOCKET", "socket", tag_type="AUX PS", tag_pattern="{prefix}-AUX PS"),
]


def library(
    *devices: dict[str, Any], mcb: dict[str, Any] | None = None, **housekeeping: Any
) -> Library:
    """A library holding ``devices`` plus one record per housekeeping role; ``mcb``
    overrides fields of the MCB catalogue."""
    roles: dict[str, Any] = {
        "lamp": {"part_id": "LAMP"},
        "fan": {"part_id": "FAN", "airflow_m3h": 358},
        "vent_filter": {"part_id": "FILTER"},
        "thermostat": {"part_id": "TH"},
        "ipr_kit": {"part_id": "IPR"},
        "change_over_diodes": {"negative": "COD-NEG", "positive": "COD-POS"},
        "socket": {"part_id": "SOCKET", "rating_a": 10},
    }
    roles.update(housekeeping)
    return Library.model_validate(
        {
            "devices": [*devices, *HOUSEKEEPING_DEVICES],
            "catalogues": {
                "mcb": {
                    "family": "Acti9 2P",
                    "make": "Schneider",
                    "ratings_a": [1, 2, 6, 10, 16],
                    "code_pattern": "A9F742{rating:02d}",
                }
                | (mcb or {}),
                "aux_contact": {
                    "make": "Schneider",
                    "model": "A9A26924",
                    "ordering_code": "A9A26924",
                },
                "terminal_blocks": {
                    "UT-16": {"make": "Phoenix", "ordering_code": "3044199"},
                    "UT-2.5-MTD": {"make": "Phoenix", "ordering_code": "3064085"},
                    "UT-2.5-MT": {"make": "Phoenix", "ordering_code": "3046362"},
                },
                "busbars": {
                    "ac_safety_ground": {"tag": "AC SAFETY POWER-GROUND", "description": "AC"},
                    "instrument_ground": {"tag": "INSTRUMENT-GROUND", "description": "INST"},
                    "power_ground": {"tag": "POWER-GROUND", "description": "POWER"},
                },
                "housekeeping": roles,
            },
        }
    )


def panel(devices: list[dict[str, Any]], **fields: Any) -> Panel:
    """A network panel, LAN A, prefix PSA1, holding ``devices`` (instance mappings)."""
    data: dict[str, Any] = {
        "id": "psa1",
        "cabinet_number": "861-GIS01-PSA-0001",
        "cabinet_name": "PSA Cabinet - 001",
        "tag_prefix": "PSA1",
        "lan": "A",
        "sheet_name": "1",
        "kind": "network",
        "enclosure": {
            "make": "Rawabi",
            "model": "Fixed Frame",
            "ordering_code": "Fixed Frame",
            "h_mm": 2100,
            "d_mm": 1000,
            "w_mm": 800,
            "base_frame": {"h_mm": 100, "d_mm": 950, "w_mm": 750},
            "cable_entry": "top",
        },
        "devices": devices,
        "document": "p1-bom",
    }
    data.update(fields)
    return Panel.model_validate(data)


def get(lib: Library, part_id: str) -> DeviceType:
    found = lib.get(part_id)
    assert found is not None, part_id
    return found


def instance(part_id: str, **fields: Any) -> DeviceInstance:
    return DeviceInstance.model_validate({"part_id": part_id, **fields})


def loose(part_id: str, **fields: Any) -> LooseExtra:
    return LooseExtra.model_validate({"part_id": part_id, **fields})
