"""Power Consumption rows and totals (spec: Power Consumption sheet; Data model and
generation order, step 4)."""

from collections.abc import Collection, Sequence

from bomgen.engine.dc_dist import branch_sizing
from bomgen.engine.errors import EngineError
from bomgen.engine.units import lookup
from bomgen.models.bom import BomLine, BomTable, Group, LooseTable, PanelBom
from bomgen.models.calc import CabinetPower, LineRef, PowerBlock, PowerConsumption, PowerLine
from bomgen.models.library import DeviceType, Library, SupplyType
from bomgen.models.project import DesignConstants


def powered_lines(
    table: BomTable,
    panel_id: str | None,
    library: Library,
    constants: DesignConstants,
    fed: Collection[str] = (),
) -> list[PowerLine]:
    """One power line per BOM row whose part draws power, in BOM order; ``fed`` names
    the loose parts a panel feeds."""
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
        system = (
            constants.dc_voltage_v
            if device.supply_type is SupplyType.VDC
            else constants.ac_voltage_v
        )
        own_branch = _has_own_branch(line, device, panel_id, fed)
        branch_a = branch_sizing(device, library, constants).rating_a if own_branch else None
        result.append(
            PowerLine(
                source=LineRef(panel_id=panel_id, line=index),
                supply_type=device.supply_type,
                voltage_v=device.voltage_v or system,
                qty=count(line),
                unit_w=device.unit_power_w,
                load_type=device.load_type,
                current_factor=constants.current_factor,
                branch_mcb_a=branch_a,
            )
        )
    return result


def _has_own_branch(
    line: BomLine, device: DeviceType, panel_id: str | None, fed: Collection[str]
) -> bool:
    """Whether the row's units each have their own branch MCB (ADR 0028): a group B
    device on Q1.n/Q2.n, a QCOD or an AC branch (ADR 0025), or a loose load on a QCOD."""
    if panel_id is None:
        return line.part_id in fed and device.power_supplies == 1
    if line.group is not Group.B or line.parent is not None:
        return False
    return device.supply_type is SupplyType.VAC or device.power_supplies in (1, 2)


def count(line: BomLine) -> int:
    """A powered row's quantity, which must be a plain count."""
    if not isinstance(line.qty, int):
        raise EngineError(
            f"{line.tag or line.part_id}: a powered row needs a count, not {line.qty!r}"
        )
    return line.qty


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
    loose: LooseTable | None,
    library: Library,
    constants: DesignConstants,
    fed: Collection[str] = (),
) -> PowerBlock | None:
    """ "Power Consumption for External Equipment": loose items drawing station DC."""
    if loose is None:
        return None
    lines = powered_lines(loose, None, library, constants, fed)
    return _block(lines, SupplyType.VDC, constants)


def power_consumption(
    panels: Sequence[PanelBom],
    loose: LooseTable | None,
    library: Library,
    constants: DesignConstants,
    fed: Collection[str] = (),
) -> PowerConsumption:
    return PowerConsumption(
        cabinets=tuple(cabinet_power(p, library, constants) for p in panels),
        external=external_power(loose, library, constants, fed),
    )
