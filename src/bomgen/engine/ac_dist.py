"""Group E: AC distribution (spec: Derivation rules -> AC distribution (group E);
Data model and generation order, step 6)."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from bomgen.engine.dc_dist import _unit_name, branch_sizing, unit_current
from bomgen.engine.housekeeping import FORCED_FANS, FORCED_THERMOSTATS, NATURAL_THERMOSTATS
from bomgen.engine.items import BomItem
from bomgen.engine.mcb import (
    alarms_wired,
    aux_contact_line,
    mcb_line,
    rating_above,
    rating_at_least,
)
from bomgen.engine.units import DeviceRow
from bomgen.models.bom import Group
from bomgen.models.calc import BranchMcb
from bomgen.models.library import Library, SupplyType
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.project import DesignConstants

CINC_A = 6
LAMP_A = 1
FAN_AND_THERMOSTAT_A = 2
THERMOSTAT_A = 1


@dataclass(frozen=True)
class AcCircuits:
    items: list[BomItem]
    mcbs: int  # breakers including CINC, for the X3-AC strip
    branch_mcbs: list[BranchMcb] = field(default_factory=list)  # the AC units' branches


def ac_distribution(
    panel: Panel,
    library: Library,
    ventilation: Ventilation,
    rows: Sequence[DeviceRow],
    constants: DesignConstants,
) -> AcCircuits:
    """CINC, lamp, fan + thermostat and thermostat branches, socket, one branch per AC
    unit (sized as the DC branches are, M25), spares, aux contacts."""
    loads: list[tuple[str, int]] = [("Illumination Lamp", LAMP_A)]
    fans = FORCED_FANS if ventilation is Ventilation.FORCED else 0
    thermostats = FORCED_THERMOSTATS if fans else NATURAL_THERMOSTATS
    loads += [(f"Fan-{n} and TH-{n}", FAN_AND_THERMOSTAT_A) for n in range(1, fans + 1)]
    loads += [(f"TH-{n}", THERMOSTAT_A) for n in range(fans + 1, thermostats + 1)]
    spare_a = max(rating for _load, rating in loads)
    socket_a = panel.options.aux_socket_a
    if socket_a is not None:
        loads.append(("Aux PS", socket_a))
    prefix = panel.tag_prefix
    first = len(loads) + 1  # the first AC unit's C number
    units = [
        (row.device, tag)
        for row in rows
        if row.device.supply_type is SupplyType.VAC and not row.device.excluded_from_power
        for tag in row.unit_tags
    ]
    branch_mcbs: list[BranchMcb] = []
    alarmed_units: list[str] = []
    for n, (device, tag) in enumerate(units, start=first):
        sizing = branch_sizing(device, library, constants)
        name = _unit_name(tag, device, prefix)
        loads.append((name, sizing.rating_a))
        branch_mcbs.append(
            BranchMcb(
                panel_id=panel.id,
                tag=f"{prefix}-C{n}",
                load=name,
                unit_tag=tag,
                **sizing.model_dump(),
            )
        )
        if device.alarm_on_branch_mcb:
            alarmed_units.append(f"C{n}")
    loads += [("SPARE", spare_a)] * panel.options.ac_spare_branches

    mcb = library.catalogues.mcb  # the AC choice; the DC branches take dc_mcb (ADR 0023)
    cinc_a = CINC_A if socket_a is None else rating_above(mcb, socket_a)
    if branch_mcbs:  # CINC carries the AC units too (ADR 0025)
        largest = max(b.rating_a for b in branch_mcbs)
        design = sum(unit_current(device, constants) for device, _tag in units)
        cinc_a = max(cinc_a, rating_above(mcb, largest), rating_at_least(mcb, design))
    lines = [mcb_line(mcb, Group.E, f"{prefix}-CINC", cinc_a, "Main Auxiliary AC Supply")]
    lines += [
        mcb_line(mcb, Group.E, f"{prefix}-C{n}", rating, load)
        for n, (load, rating) in enumerate(loads, start=1)
    ]
    # One aux contact on CINC and one on each fan circuit (C2, C3 after the lamp's C1).
    alarmed = ["CINC", *(f"C{n}" for n in range(2, fans + 2)), *alarmed_units]
    description = f"AC Auxiliary Contacts (for MCB {', '.join(alarmed)})"
    hwio = len(alarmed) if alarms_wired(panel) else 0
    lines.append(aux_contact_line(library, Group.E, description, len(alarmed), hwio))
    return AcCircuits([BomItem(line) for line in lines], len(loads) + 1, branch_mcbs)
