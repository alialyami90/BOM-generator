"""Run the derivation steps over a loaded project (spec: Data model and generation order).

Steps 1, 2, 3 and 5 so far: groups A-D per panel and the loose-material table.
"""

from bomgen.engine.enclosure import enclosure_item
from bomgen.engine.housekeeping import housekeeping, needs_change_over, resolve_ventilation
from bomgen.engine.items import flatten
from bomgen.engine.kits import loose_table, main_equipment
from bomgen.engine.network import accessories
from bomgen.engine.units import DeviceRow, expand_devices
from bomgen.io.loader import LoadedProject
from bomgen.models.bom import BuildResult, PanelBom
from bomgen.models.panel import Panel


def build(loaded: LoadedProject) -> BuildResult:
    """Every panel's BOM lines and the loose-material table."""
    library = loaded.library
    material = loaded.project.loose_material
    loose_items = material.items if material is not None else []
    substation = loaded.project.project.substation
    panel_rows: list[tuple[Panel, tuple[DeviceRow, ...]]] = []
    panels = []
    for panel in loaded.panels:
        rows = expand_devices(panel, library)
        panel_rows.append((panel, rows))
        change_over = needs_change_over(panel, library, loose_items)
        items = [
            enclosure_item(panel),
            *main_equipment(rows, library),
            *accessories(panel, rows, library),
            *housekeeping(panel, library, resolve_ventilation(panel), change_over),
        ]
        panels.append(
            PanelBom(
                panel_id=panel.id,
                sheet_name=panel.sheet_name,
                title=(panel.cabinet_number, f"{substation} - {panel.cabinet_name}"),
                lines=flatten(items),
            )
        )
    loose = loose_table(material, substation, panel_rows, library)
    return BuildResult(panels=tuple(panels), loose=loose)
