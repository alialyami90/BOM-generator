"""Device nameplates: one group H row per panel and each plate's text (ADR 0026)."""

from collections.abc import Sequence

from bomgen.engine.items import BomItem
from bomgen.engine.kits import device_item
from bomgen.engine.tags import short_tag
from bomgen.engine.units import DeviceRow, describe, expand_devices
from bomgen.models.bom import Group, Nameplate, PanelNameplates
from bomgen.models.library import Library
from bomgen.models.panel import DeviceInstance, Panel


def nameplates(panel: Panel, rows: Sequence[DeviceRow]) -> PanelNameplates:
    """A plate per tagged group B unit, named as the MCB rows name it."""
    plates = [
        Nameplate(
            text=short_tag(tag, row.device, panel.tag_prefix),
            device=describe(row.device, row.lan, row.instance.purpose),
        )
        for row in rows
        for tag in row.unit_tags
        if tag is not None
    ]
    return PanelNameplates(panel_id=panel.id, plates=tuple(plates))


def nameplate_item(panel: Panel, library: Library, count: int) -> BomItem | None:
    """The nameplate row, ``count`` plates of the library's nameplate part; none without
    the part or the plates."""
    role = library.catalogues.housekeeping.nameplate
    if role is None or count == 0:
        return None
    instance = DeviceInstance(part_id=role.part_id, qty=count)
    [row] = expand_devices(panel, library, [instance])
    return device_item(row, library, Group.H)
