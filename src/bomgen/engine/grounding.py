"""Group H: grounding busbars (spec: How each panel BOM groups its materials; Data model
and generation order, step 9)."""

from bomgen.engine.errors import EngineError
from bomgen.engine.items import BomItem
from bomgen.models.bom import BomLine, Group
from bomgen.models.library import Library
from bomgen.models.panel import Panel


def grounding(panel: Panel, library: Library) -> list[BomItem]:
    """One row per busbar the panel names, description only."""
    busbars = library.catalogues.busbars
    items = []
    for key in panel.options.grounding_busbars:
        busbar = busbars.get(key)
        if busbar is None:
            raise EngineError(f"{panel.id}: busbar '{key}' is not in the library catalogue")
        items.append(
            BomItem(BomLine(group=Group.H, tag=busbar.tag, description=busbar.description, qty=1))
        )
    return items
