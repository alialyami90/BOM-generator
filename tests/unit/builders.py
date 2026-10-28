"""Builders for a minimal valid project written to disk, with per-file overrides."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


def _passive(part_id: str, category: str) -> dict[str, Any]:
    return {
        "part_id": part_id,
        "category": category,
        "make": "Acme",
        "model": part_id,
        "description_template": part_id,
    }


def default_library() -> dict[str, Any]:
    """A library with a switch, an SFP, and one record per housekeeping role."""
    switch = {
        "part_id": "RST2228-L2",
        "category": "network_switch",
        "make": "Ruggedcom",
        "model": "RST-2228",
        "description_template": "LAN-{lan} switch",
        "tag_type": "ESW",
        "purdue_level": "L2",
        "supply_type": "VDC",
        "voltage_v": 125,
        "unit_power_w": 77,
        "load_type": "CONTINUOUS",
        "power_supplies": 2,
        "min_branch_mcb_a": 2,
        "ports": [{"count": 24, "speed": "1G", "media": "RJ45", "kind": "fixed"}],
    }
    return {
        "devices": [
            switch,
            _passive("SFP-1G-SM", "sfp"),
            _passive("LAMP", "lamp"),
            _passive("DOOR-SWITCH", "door_switch"),
            _passive("FAN-110", "fan"),
            _passive("VENT-FILTER", "vent_filter"),
            _passive("THERMOSTAT", "thermostat"),
            _passive("IPR-KIT", "accessory"),
            _passive("COD-NEG", "change_over_diode"),
            _passive("COD-POS", "change_over_diode"),
            _passive("SOCKET-10", "socket"),
        ],
        "catalogues": {
            "mcb": {
                "family": "Acti9 iC60N",
                "make": "Schneider",
                "ratings_a": [1, 2, 6, 10, 16],
                "code_pattern": "A9F742{rating:02d}",
            },
            "aux_contact": {"make": "Schneider", "model": "iACT24", "ordering_code": "A9A26924"},
            "terminal_blocks": {"UT-16": {"make": "Phoenix", "ordering_code": "3044199"}},
            "busbars": {
                "ac_safety_ground": {"description": "AC safety ground busbar"},
                "instrument_ground": {"description": "Instrument ground busbar"},
            },
            "housekeeping": {
                "lamp": {"part_id": "LAMP"},
                "door_switch": {"part_id": "DOOR-SWITCH"},
                "fan": {"part_id": "FAN-110", "airflow_m3h": 110.0},
                "vent_filter": {"part_id": "VENT-FILTER"},
                "thermostat": {"part_id": "THERMOSTAT"},
                "ipr_kit": {"part_id": "IPR-KIT"},
                "change_over_diodes": {"negative": "COD-NEG", "positive": "COD-POS"},
                "socket": {"part_id": "SOCKET-10", "rating_a": 10},
            },
        },
    }


def default_project() -> dict[str, Any]:
    """Project ``gis`` with one substation ``s1`` and its register entries."""

    def entry(key: str, doc_no: str) -> dict[str, Any]:
        return {
            "key": key,
            "substation": "s1",
            "doc_no": doc_no,
            "rev": 0,
            "issue_date": "2026-10-28",
        }

    return {
        "project": {"id": "gis", "name": "GIS 01"},
        "library": {"name": "test-lib", "version": "1.0.0", "file": "library.yaml"},
        "documents": [
            entry("s1-bom", "DOC-1"),
            entry("p1-bom", "DOC-1"),
            entry("p2-bom", "DOC-2"),
            entry("s1-calc", "DOC-9"),
        ],
        "substations": ["substations/s1/substation.yaml"],
    }


def default_substation() -> dict[str, Any]:
    """Substation ``s1`` (Dhahran) with the panels p1 and p2."""
    calc = {"document": "s1-calc", "scope": "Whole substation"}
    return {
        "substation": {"id": "s1", "name": "Dhahran"},
        "document": "s1-bom",
        "calculations": {
            "power_consumption": calc,
            "heat_dissipation": calc,
            "heat_calculations": calc,
        },
        "panels": ["panels/p1.yaml", "panels/p2.yaml"],
    }


def default_p1() -> dict[str, Any]:
    """Network panel, prefix P1, LAN A."""
    return {
        "id": "p1",
        "cabinet_number": "CAB-001",
        "cabinet_name": "Cabinet 1",
        "tag_prefix": "P1",
        "lan": "A",
        "sheet_name": "1",
        "kind": "network",
        "enclosure": {
            "make": "Rawabi",
            "model": "ENC-2100",
            "h_mm": 2100,
            "d_mm": 1000,
            "w_mm": 800,
            "cable_entry": "top",
        },
        "devices": [
            {"part_id": "RST2228-L2", "tag": "P1-L2-ESW-A01"},
            {"part_id": "SFP-1G-SM", "qty": 2},
        ],
        "port_plans": {
            "P1-L2-ESW-A01": {"downlinks": [{"count": 2, "speed": "1G", "media": "RJ45"}]},
        },
        "document": "p1-bom",
    }


def default_p2() -> dict[str, Any]:
    """Mirror of p1, prefix P2, LAN B."""
    return {
        "id": "p2",
        "mirror_of": "p1",
        "cabinet_number": "CAB-002",
        "cabinet_name": "Cabinet 2",
        "tag_prefix": "P2",
        "lan": "B",
        "sheet_name": "2",
        "document": "p2-bom",
    }


def write_yaml(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(dict(data), sort_keys=False), encoding="utf-8")


SUBSTATION_DIR = Path("substations") / "s1"


def write_project(
    tmp_path: Path,
    *,
    library: Mapping[str, Any] | None = None,
    project: Mapping[str, Any] | None = None,
    substation: Mapping[str, Any] | None = None,
    panels: Mapping[str, Mapping[str, Any]] | None = None,
) -> Path:
    """Write a minimal valid project under ``tmp_path`` and return its project file.

    The substation file is ``substations/s1/substation.yaml``. Each keyword replaces
    the whole contents of that file. ``panels`` maps a file name under the substation's
    ``panels/`` to its contents; it is merged over the defaults ``p1.yaml`` and
    ``p2.yaml``, so a name not among them adds a file.
    """
    project_file = tmp_path / "project.yaml"
    write_yaml(project_file, default_project() if project is None else project)
    write_yaml(tmp_path / "library.yaml", default_library() if library is None else library)
    substation_dir = tmp_path / SUBSTATION_DIR
    write_yaml(
        substation_dir / "substation.yaml",
        default_substation() if substation is None else substation,
    )
    files = {"p1.yaml": default_p1(), "p2.yaml": default_p2()} | dict(panels or {})
    for name, data in files.items():
        write_yaml(substation_dir / "panels" / name, data)
    return project_file
