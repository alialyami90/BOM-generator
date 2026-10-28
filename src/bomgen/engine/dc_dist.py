"""Group F: DC distribution (spec: Derivation rules -> DC distribution (group F);
Data model and generation order, step 7)."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from bomgen.engine.errors import EngineError
from bomgen.engine.items import BomItem
from bomgen.engine.mcb import (
    alarms_wired,
    aux_contact_line,
    mcb_line,
    rating_at_least,
)
from bomgen.engine.tags import without_prefix
from bomgen.engine.units import DeviceRow, lookup
from bomgen.models.bom import BomLine, Group
from bomgen.models.library import DeviceType, Library
from bomgen.models.panel import Panel
from bomgen.models.project import DesignConstants, LooseExtra

FEEDS = (1, 2)
QCOD_SPARES = 1  # "QCOD-2 spare"


@dataclass(frozen=True)
class FedLoad:
    """A single-fed DC load on the change-over diodes, named in its QCOD description."""

    name: str
    device: DeviceType


@dataclass(frozen=True)
class DcCircuits:
    items: list[BomItem]
    branches_per_feed: int  # used + spare, for the X4-DC1/X4-DC2 strips
    qcods: int
    design_current_a: float  # ΣQ per feed
    main_a: int
    rule_main_a: int  # the rating without main_mcb_override_a


@dataclass(frozen=True)
class _Branch:
    load: str
    rating: int
    alarmed: bool


def single_fed_loads(
    panel: Panel, rows: Sequence[DeviceRow], library: Library, loose: Sequence[LooseExtra]
) -> list[FedLoad]:
    """Group B units with one supply, then loose items fed from this panel."""
    devices = [row.device for row in rows for _ in range(row.instance.qty)]
    devices += [lookup(library, item.part_id) for item in loose if item.fed_from == panel.id]
    return [FedLoad(_load_name(d), d) for d in devices if d.power_supplies == 1]


def _load_name(device: DeviceType) -> str:
    return device.category.value.replace("_", " ").title()


def unit_current(device: DeviceType, constants: DesignConstants) -> float:
    """Design current of one unit with margin: current factor x W / V (column O)."""
    voltage = device.voltage_v or constants.dc_voltage_v
    return constants.current_factor * (device.unit_power_w or 0) / voltage


def branch_rating(device: DeviceType, library: Library, constants: DesignConstants) -> int:
    """Smallest catalogue size of at least max(min_branch_mcb_a, ⌈O⌉) (plan Q7)."""
    needed = max(device.min_branch_mcb_a or 1, math.ceil(unit_current(device, constants)))
    return rating_at_least(library, needed)


def dc_distribution(
    panel: Panel,
    library: Library,
    constants: DesignConstants,
    rows: Sequence[DeviceRow],
    fed: Sequence[FedLoad],
    change_over: bool,
) -> DcCircuits:
    """Q1 + Q1.n + spares, Q2 + Q2.n + spares, QCOD circuits, aux contacts."""
    if fed and not change_over:
        names = ", ".join(load.name for load in fed)
        raise EngineError(f"{panel.id}: single-fed loads ({names}) need change-over diodes")
    branches: list[_Branch] = []
    current = 0.0
    for row in rows:
        # ΣQ is the cabinet's own DC loads, its Power Consumption block; loose loads fed
        # from it are "External Equipment" (spec: Power Consumption sheet).
        if row.device.power_supplies:
            current += unit_current(row.device, constants) * row.instance.qty
        if row.device.power_supplies != 2:
            continue
        rating = branch_rating(row.device, library, constants)
        for unit_tag in row.unit_tags:
            name = _unit_name(unit_tag, row.device, panel.tag_prefix)
            branches.append(_Branch(name, rating, row.device.alarm_on_branch_mcb))
    if not branches and not fed:
        return DcCircuits([], 0, 0, 0.0, 0, 0)

    spare_a = max((b.rating for b in branches), default=rating_at_least(library, 2))
    branches += [_Branch("SPARE", spare_a, False)] * panel.options.dc_spare_branches_per_feed
    rule_main_a = rating_at_least(library, max(current, constants.min_main_mcb_a))
    main_a = panel.options.main_mcb_override_a or rule_main_a

    prefix = panel.tag_prefix
    lines: list[BomLine] = []
    for feed in FEEDS:
        lines.append(
            mcb_line(library, Group.F, f"{prefix}-Q{feed}", main_a, f"Main DC supply-{feed}")
        )
        for n, branch in enumerate(branches, start=1):
            load = branch.load if branch.load == "SPARE" else f"{branch.load} PS{feed}"
            lines.append(mcb_line(library, Group.F, f"{prefix}-Q{feed}.{n}", branch.rating, load))

    qcod = [(load.name, branch_rating(load.device, library, constants)) for load in fed]
    if qcod:
        qcod += [("SPARE", max(rating for _name, rating in qcod))] * QCOD_SPARES
    for n, (name, rating) in enumerate(qcod, start=1):
        lines.append(mcb_line(library, Group.F, f"{prefix}-QCOD-{n}", rating, name))

    alarmed = [f"Q{feed}" for feed in FEEDS]
    alarmed += [f"Q{f}.{n}" for n, b in enumerate(branches, 1) if b.alarmed for f in FEEDS]
    description = f"DC Auxiliary Contacts (For MCB {', '.join(alarmed)})"
    hwio = len(FEEDS) if alarms_wired(panel) else 0  # mains only (Columns of a panel BOM, HWIO)
    lines.append(aux_contact_line(library, Group.F, description, len(alarmed), hwio))
    return DcCircuits(
        items=[BomItem(line) for line in lines],
        branches_per_feed=len(branches),
        qcods=len(qcod),
        design_current_a=current,
        main_a=main_a,
        rule_main_a=rule_main_a,
    )


def _unit_name(unit_tag: str | None, device: DeviceType, prefix: str) -> str:
    """The load as named inside MCB descriptions: no panel prefix, underscores."""
    if unit_tag is None:
        return device.model or device.part_id
    return without_prefix(unit_tag, prefix).replace("-", "_")
