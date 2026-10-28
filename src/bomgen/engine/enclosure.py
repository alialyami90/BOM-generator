"""Group A: the enclosure row (spec: How each panel BOM groups its materials)."""

from bomgen.engine.items import BomItem
from bomgen.models.bom import BomLine, Group
from bomgen.models.panel import Panel


def enclosure_item(panel: Panel) -> BomItem:
    """The PANEL row: cabinet size, base frame and cable entry."""
    enclosure = panel.enclosure
    text = [f"Cabinet : H{enclosure.h_mm} x D{enclosure.d_mm} x W{enclosure.w_mm} mm"]
    frame = enclosure.base_frame
    if frame is not None:
        text.append(f"Base Frame: H{frame.h_mm} x D{frame.d_mm} x W{frame.w_mm} mm")
    text.append(f"Cable Entry: {enclosure.cable_entry.value.capitalize()} Entry")
    return BomItem(
        BomLine(
            group=Group.A,
            tag="PANEL",
            description="\n".join(text),
            qty=1,
            make=enclosure.make,
            model=enclosure.model,
            ordering_code=enclosure.ordering_code,
        )
    )
