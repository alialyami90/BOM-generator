"""Group E: AC distribution (spec: Derivation rules -> AC distribution (group E);
Data model and generation order, step 6)."""

from dataclasses import dataclass

from bomgen.engine.housekeeping import FORCED_FANS, FORCED_THERMOSTATS, NATURAL_THERMOSTATS
from bomgen.engine.items import BomItem
from bomgen.engine.mcb import alarms_wired, aux_contact_line, mcb_line, rating_above
from bomgen.models.bom import Group
from bomgen.models.library import Library
from bomgen.models.panel import Panel, Ventilation

CINC_A = 6
LAMP_A = 1
FAN_AND_THERMOSTAT_A = 2
THERMOSTAT_A = 1


@dataclass(frozen=True)
class AcCircuits:
    items: list[BomItem]
    mcbs: int  # breakers including CINC, for the X3-AC strip


def ac_distribution(panel: Panel, library: Library, ventilation: Ventilation) -> AcCircuits:
    """CINC, lamp, fan + thermostat and thermostat branches, socket, spares, aux contacts."""
    loads: list[tuple[str, int]] = [("Illumination Lamp", LAMP_A)]
    fans = FORCED_FANS if ventilation is Ventilation.FORCED else 0
    thermostats = FORCED_THERMOSTATS if fans else NATURAL_THERMOSTATS
    loads += [(f"Fan-{n} and TH-{n}", FAN_AND_THERMOSTAT_A) for n in range(1, fans + 1)]
    loads += [(f"TH-{n}", THERMOSTAT_A) for n in range(fans + 1, thermostats + 1)]
    spare_a = max(rating for _load, rating in loads)
    socket_a = panel.options.aux_socket_a
    if socket_a is not None:
        loads.append(("Aux PS", socket_a))
    loads += [("SPARE", spare_a)] * panel.options.ac_spare_branches

    prefix = panel.tag_prefix
    mcb = library.catalogues.mcb  # the AC choice; the DC branches take dc_mcb (ADR 0023)
    cinc_a = CINC_A if socket_a is None else rating_above(mcb, socket_a)
    lines = [mcb_line(mcb, Group.E, f"{prefix}-CINC", cinc_a, "Main Auxiliary AC Supply")]
    lines += [
        mcb_line(mcb, Group.E, f"{prefix}-C{n}", rating, load)
        for n, (load, rating) in enumerate(loads, start=1)
    ]
    # One aux contact on CINC and one on each fan circuit (C2, C3 after the lamp's C1).
    alarmed = ["CINC", *(f"C{n}" for n in range(2, fans + 2))]
    description = f"AC Auxiliary Contacts (for MCB {', '.join(alarmed)})"
    hwio = len(alarmed) if alarms_wired(panel) else 0
    lines.append(aux_contact_line(library, Group.E, description, len(alarmed), hwio))
    return AcCircuits(items=[BomItem(line) for line in lines], mcbs=len(loads) + 1)
