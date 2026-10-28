"""Power Consumption rows and totals (spec: Power Consumption sheet; Data model and
generation order, step 4)."""

from collections.abc import Sequence

from bomgen.engine.errors import EngineError
from bomgen.engine.units import lookup
from bomgen.models.bom import BomTable, LooseTable, PanelBom
from bomgen.models.calc import CabinetPower, LineRef, PowerBlock, PowerConsumption, PowerLine
from bomgen.models.library import Library, SupplyType
from bomgen.models.project import DesignConstants


def powered_lines(
    table: BomTable, panel_id: str | None, library: Library, constants: DesignConstants
) -> list[PowerLine]:
    """One power line per BOM row whose part draws power, in BOM order."""
    result = []
    for index, line in enumerate(table.lines):
        if line.part_id is None:
            continue
        device = lookup(library, line.part_id)
        if device.excluded_from_power:
            continue
        assert device.supply_type
        assert device.unit_power_w is not None
        assert device.load_type
        if not isinstance(line.qty, int):
            raise EngineError(
                f"{line.tag or line.part_id}: a powered row needs a count, not {line.qty!r}"
            )
        voltage = (
            constants.dc_voltage_v
            if device.supply_type is SupplyType.VDC
            else constants.ac_voltage_v
        )
        result.append(
            PowerLine(
                source=LineRef(panel_id=panel_id, line=index),
                supply_type=device.supply_type,
                voltage_v=voltage,
                qty=line.qty,
                unit_w=device.unit_power_w,
                load_type=device.load_type,
                current_factor=constants.current_factor,
            )
        )
    return result


def _block(
    lines: Sequence[PowerLine], supply: SupplyType, constants: DesignConstants
) -> PowerBlock | None:
    chosen = tuple(line for line in lines if line.supply_type is supply)
    if not chosen:
        return None
    return PowerBlock(supply_type=supply, lines=chosen, margin=constants.power_margin)


def cabinet_power(table: PanelBom, library: Library, constants: DesignConstants) -> CabinetPower:
    """A cabinet's DC LOAD and AUX AC LOAD blocks."""
    lines = powered_lines(table, table.panel_id, library, constants)
    return CabinetPower(
        panel_id=table.panel_id,
        dc=_block(lines, SupplyType.VDC, constants),
        ac=_block(lines, SupplyType.VAC, constants),
    )


def external_power(
    loose: LooseTable | None, library: Library, constants: DesignConstants
) -> PowerBlock | None:
    """ "Power Consumption for External Equipment": loose items drawing station DC."""
    if loose is None:
        return None
    return _block(powered_lines(loose, None, library, constants), SupplyType.VDC, constants)


def power_consumption(
    panels: Sequence[PanelBom],
    loose: LooseTable | None,
    library: Library,
    constants: DesignConstants,
) -> PowerConsumption:
    return PowerConsumption(
        cabinets=tuple(cabinet_power(p, library, constants) for p in panels),
        external=external_power(loose, library, constants),
    )
