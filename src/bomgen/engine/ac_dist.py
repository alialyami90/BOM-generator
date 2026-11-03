"""Group E: AC distribution (spec: Derivation rules -> AC distribution (group E);
Data model and generation order, step 6)."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from bomgen.engine.dc_dist import branch_sizing, unit_current
from bomgen.engine.errors import EngineError
from bomgen.engine.housekeeping import kit_counts, kit_role
from bomgen.engine.items import BomItem
from bomgen.engine.mcb import (
    alarms_wired,
    aux_contact_line,
    mcb_line,
    rating_above,
    rating_at_least,
)
from bomgen.engine.tags import short_tag
from bomgen.engine.units import DeviceRow, lookup
from bomgen.models.bom import Group
from bomgen.models.calc import BranchMcb, HousekeepingBranch
from bomgen.models.library import DeviceType, FanRef, Library, McbCatalogue, SupplyType
from bomgen.models.panel import HousekeepingLoad, Panel, Ventilation
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
    rule_spare_a: int = 0  # the spare's rating without ac_spare_rating_a (plan M58)
    housekeeping: list[HousekeepingBranch] = field(default_factory=list)  # ADR 0032


def ac_distribution(
    panel: Panel,
    library: Library,
    ventilation: Ventilation,
    rows: Sequence[DeviceRow],
    constants: DesignConstants,
    fan: FanRef | None = None,
) -> AcCircuits:
    """CINC, lamp, fan + thermostat and thermostat branches, socket, one branch per AC
    unit (sized as the DC branches are, M25), spares, aux contacts."""
    mcb = library.catalogues.mcb  # the AC choice; the DC branches take dc_mcb (ADR 0023)
    kit = housekeeping_branches(panel, library, ventilation, constants, mcb, fan)
    loads: list[tuple[str, int]] = [(b.load, b.rating_a) for b in kit]
    spare_a = max((rating for _load, rating in loads), default=LAMP_A)
    socket_a = panel.options.aux_socket_a
    if socket_a is not None:
        loads.append(("Aux PS", socket_a))
    prefix = panel.tag_prefix
    first = len(loads) + 1  # the first AC unit's C number
    units = [
        (row, tag)
        for row in rows
        if row.device.supply_type is SupplyType.VAC and not row.device.excluded_from_power
        for tag in row.unit_tags
    ]
    branch_mcbs: list[BranchMcb] = []
    alarmed_units: list[str] = []
    for n, (row, tag) in enumerate(units, start=first):
        device = row.device
        sizing = branch_sizing(device, library, constants)
        name = short_tag(tag, device, prefix)
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
        if row.alarmed:
            alarmed_units.append(f"C{n}")
    own_spare_a = panel.options.ac_spare_rating_a or spare_a
    loads += [("SPARE", own_spare_a)] * panel.options.ac_spare_branches

    cinc_a = CINC_A if socket_a is None else rating_above(mcb, socket_a)
    if branch_mcbs:  # CINC carries the AC units too (ADR 0025)
        largest = max(b.rating_a for b in branch_mcbs)
        design = sum(unit_current(row.device, constants) for row, _tag in units)
        cinc_a = max(cinc_a, rating_above(mcb, largest), rating_at_least(mcb, design))
    lines = [mcb_line(mcb, Group.E, f"{prefix}-CINC", cinc_a, "Main Auxiliary AC Supply")]
    lines += [
        mcb_line(mcb, Group.E, f"{prefix}-C{n}", rating, load)
        for n, (load, rating) in enumerate(loads, start=1)
    ]
    # One aux contact on CINC and one on each fan circuit (C2, C3 after the lamp's C1).
    fan_circuits = [f"C{n}" for n, b in enumerate(kit, start=1) if b.key == "fan"]
    alarmed = ["CINC", *fan_circuits, *alarmed_units]
    description = f"AC Auxiliary Contacts (for MCB {', '.join(alarmed)})"
    hwio = len(alarmed) if alarms_wired(panel) else 0
    lines.append(aux_contact_line(library, Group.E, description, len(alarmed), hwio))
    return AcCircuits([BomItem(line) for line in lines], len(loads) + 1, branch_mcbs, spare_a, kit)


FIXED_A: dict[HousekeepingLoad, int] = {
    "lamp": LAMP_A,
    "fan": FAN_AND_THERMOSTAT_A,
    "thermostat": THERMOSTAT_A,
}


def housekeeping_branches(
    panel: Panel,
    library: Library,
    ventilation: Ventilation,
    constants: DesignConstants,
    mcb: McbCatalogue,
    fan: FanRef | None = None,
) -> list[HousekeepingBranch]:
    """The lamp, fan + thermostat, thermostat, heater and hygrostat branches in C order,
    each rated by ADR 0032 item 4 with the rule that gave it."""
    kit = library.catalogues.housekeeping
    counts = kit_counts(panel, ventilation)
    lamp, fan_part, thermostat = (
        lookup(library, kit.lamp.part_id),
        lookup(library, (fan or kit.fan).part_id),
        lookup(library, kit.thermostat.part_id),
    )
    plan: list[tuple[str, HousekeepingLoad, list[tuple[DeviceType, int]]]] = []
    if counts.lamps:
        plan.append(("Illumination Lamp", "lamp", [(lamp, counts.lamps)]))
    for n in range(1, counts.fans + 1):
        paired = n <= counts.thermostats
        name = f"Fan-{n} and TH-{n}" if paired else f"Fan-{n}"
        plan.append((name, "fan", [(fan_part, 1), *([(thermostat, 1)] if paired else [])]))
    for n in range(counts.fans + 1, counts.thermostats + 1):
        plan.append((f"TH-{n}", "thermostat", [(thermostat, 1)]))
    if counts.heater:
        plan.append(
            ("Heater", "heater", [(lookup(library, kit_role(panel, library, "heater").part_id), 1)])
        )
    if counts.hygrostat:
        hygrostat = lookup(library, kit_role(panel, library, "hygrostat").part_id)
        plan.append(("Hygrostat", "thermostat", [(hygrostat, 1)]))
    own = panel.options.housekeeping.branch_ratings
    branches = []
    for n, (load, key, parts) in enumerate(plan, start=1):
        rule_a, rule = _housekeeping_rating(panel, key, parts, mcb, constants)
        branches.append(
            HousekeepingBranch(
                panel_id=panel.id,
                tag=f"{panel.tag_prefix}-C{n}",
                load=load,
                key=key,
                rating_a=own.get(key, rule_a),
                rule_rating_a=rule_a,
                rule=rule,
            )
        )
    return branches


def _housekeeping_rating(
    panel: Panel,
    key: HousekeepingLoad,
    parts: list[tuple[DeviceType, int]],
    mcb: McbCatalogue,
    constants: DesignConstants,
) -> tuple[int, str]:
    """The part's watts when it gives them, never below the spec's fixed rating (ADR 0032)."""
    fixed = FIXED_A.get(key)
    powered = [(d, q) for d, q in parts if d.unit_power_w and d.supply_type is SupplyType.VAC]
    if powered:
        running = sum(unit_current(d, constants) * q for d, q in powered)
        sized = rating_at_least(mcb, running)
        if fixed is None or sized > fixed:
            return sized, f"{sized} A: carries {running:.2f} A running, from the part's watts"
        return fixed, f"{fixed} A: the spec's {key} rating; the parts draw {running:.2f} A"
    if fixed is None:
        raise EngineError(
            f"{panel.id}: the {key} part gives no AC watts; set its unit_power_w or the "
            f"panel's housekeeping branch_ratings.{key}"
        )
    return fixed, f"{fixed} A: the spec's {key} rating"
