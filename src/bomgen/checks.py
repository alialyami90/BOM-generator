"""Step 15: the check report on a built substation (spec: Data model and generation
order, step 15; plan M7, Q3).

Checks SFPs against the hosts' slots, DC mains against ΣQ, each branch MCB's sizing
(plan Q35), the DC MCBs and DC-fed devices against the battery float voltage, fans
and natural
convection against the heat, DI capacity against the HWIO total, and the library
version a project recorded. The CLI
renders the report as text or JSON and exits non-zero when a check fails.
"""

import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from bomgen.engine.network import port_plan
from bomgen.engine.units import DeviceRow, expand_devices
from bomgen.io.loader import LoadedSubstation
from bomgen.io.parts_edit import CATEGORY_LINKS
from bomgen.library_store.store import LibraryRef, library_mismatch
from bomgen.models.bom import BomTable, BuildResult, LooseTable, PanelBom, QtySum
from bomgen.models.calc import BranchMcb, DcMains, HeatResult
from bomgen.models.library import (
    DEFAULT_BRAND,
    CatalogueChoice,
    Category,
    Library,
    Media,
    PortKind,
    PortSpeed,
    PurdueLevel,
    SupplyType,
)
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.project import DesignConstants, RegisterEntry, VendorList, merge_defaults
from bomgen.models.report import CheckItem, CheckReport, CheckStatus
from bomgen.models.substation import (
    AcceptedWarning,
    DesignBasis,
    Equipment,
    EquipmentRole,
    ExternalLink,
)

SPEED_ORDER = (PortSpeed.M10, PortSpeed.M100, PortSpeed.G1, PortSpeed.G10)


def check_report(loaded: LoadedSubstation, result: BuildResult) -> CheckReport:
    """Every engine check of one built substation, panel by panel."""
    items: list[CheckItem] = []
    expanded = [
        (panel, expand_devices(panel, loaded.library, tagging=loaded.tagging))
        for panel in loaded.panels
    ]
    for panel, rows in expanded:
        items += sfp_slot_checks(panel, rows)
    items += duplicate_tag_checks(expanded)
    items += untagged_device_checks(expanded)
    items += dc_main_checks(result.mains)
    items += branch_mcb_checks(result.branch_mcbs)
    tables: list[BomTable] = [*result.panels, *([result.loose] if result.loose else [])]
    items += dc_float_checks(tables, result.mains, loaded.library, loaded.constants)
    if result.heat is not None:
        items += ventilation_checks(result.heat)
    di = di_capacity_check(result.panels, loaded.library)
    if di is not None:
        items.append(di)
    items += part_number_checks(loaded.substation.equipment, loaded.library)
    items += part_source_checks(loaded.substation.equipment, loaded.library)
    items += l2_link_checks(loaded.substation.equipment, loaded.library)
    items += external_link_checks(
        loaded.substation.network.external_links, loaded.substation.equipment
    )
    items += external_ac_checks(result.loose, loaded.library)
    items += document_number_checks(loaded.documents)
    parts = picked_parts(loaded)
    items += part_state_checks(parts, loaded.library)
    basis = loaded.substation.design_basis
    if basis is not None:
        items += design_basis_checks(parts, loaded.library, basis)
    avl = loaded.project.vendor_list(basis.vendor_list) if basis is not None else None
    if avl is not None:
        choice = merge_defaults(
            loaded.project.defaults.catalogue_choice, loaded.substation.catalogue_choice
        )
        items += vendor_list_checks(parts, choice, loaded.library, avl)
    report = CheckReport(items=tuple(items))
    checks = loaded.substation.checks
    return apply_acceptances(report, checks.accepted) if checks else report


def _matches(item: CheckItem, accepted: AcceptedWarning) -> bool:
    return (accepted.check, accepted.panel_id, accepted.subject) == (
        item.check,
        item.panel_id,
        item.subject,
    )


def apply_acceptances(report: CheckReport, accepted: Sequence[AcceptedWarning]) -> CheckReport:
    """Each warning an acceptance matches carries its reason (ADR 0036); failures never."""
    items = []
    for item in report.items:
        found = next((a for a in accepted if _matches(item, a)), None)
        if item.status is CheckStatus.WARN and found is not None:
            item = item.model_copy(update={"accepted": found.reason})
        items.append(item)
    return CheckReport(items=tuple(items))


def unused_acceptances(
    report: CheckReport, accepted: Sequence[AcceptedWarning]
) -> list[AcceptedWarning]:
    """Acceptances no warning in ``report`` matches any more, kept until removed."""
    warnings = [i for i in report.items if i.status is CheckStatus.WARN]
    return [a for a in accepted if not any(_matches(i, a) for i in warnings)]


def sfp_slot_checks(panel: Panel, rows: Sequence[DeviceRow]) -> list[CheckItem]:
    """The SFPs a port plan fits (spares excluded) against the host's SFP slots; an SFP
    fits a slot of its speed or faster."""
    items = []
    for row in rows:
        plan = port_plan(panel, row)
        if plan is None:
            continue
        needed: Counter[PortSpeed] = Counter()
        for allocation in (*plan.uplinks_l3, *plan.uplinks, *plan.downlinks):
            if allocation.media is not Media.RJ45:
                needed[allocation.speed] += allocation.count
        if not needed:
            continue
        subject = row.tag or row.device.part_id
        sfps = sum(needed.values())
        if not row.device.ports:
            items.append(
                CheckItem(
                    check="sfp_slots",
                    status=CheckStatus.WARN,
                    panel_id=panel.id,
                    subject=subject,
                    message=f"{sfps} SFPs; the library lists no ports for "
                    f"{row.device.part_id}, so the slots cannot be checked",
                    values={"sfps": sfps},
                )
            )
            continue
        slots: Counter[PortSpeed] = Counter()
        for group in row.device.ports:
            if group.kind is PortKind.SFP_SLOT:
                slots[group.speed] += group.count * row.instance.qty
        short = _short_speeds(needed, slots)
        total_slots = sum(slots.values())
        message = f"{sfps} SFPs in {total_slots} SFP slots"
        values: dict[str, int | float | str] = {"sfps": sfps, "slots": total_slots}
        status = CheckStatus.FAIL if short else CheckStatus.PASS
        if short:
            message += f"; too few slots for the {', '.join(s.value for s in short)} SFPs"
        # extra SFPs (plan M49) warn, never fail, when the free slots can't take them
        extra: Counter[PortSpeed] = Counter()
        for choice in row.device.sfp_choice:
            if choice.extra and choice.media is not Media.RJ45:
                extra[choice.speed] += choice.extra
        if extra:
            values["extra"] = sum(extra.values())
            over = _short_speeds(needed + extra, slots)
            if over and not short:
                status = CheckStatus.WARN
                message += (
                    f"; the {values['extra']} extra SFPs need more "
                    f"{', '.join(s.value for s in over)} slots than are free"
                )
        items.append(
            CheckItem(
                check="sfp_slots",
                status=status,
                panel_id=panel.id,
                subject=subject,
                message=message,
                values=values,
            )
        )
    return items


def duplicate_tag_checks(
    panels: Iterable[tuple[Panel, Sequence[DeviceRow]]],
) -> list[CheckItem]:
    """A failure per tag that two device units share (ADR 0030). Units of parts with no
    type code carry a label, such as "Keyboard & Mouse", not a device tag."""
    owners: dict[str, list[str]] = {}
    for panel, rows in panels:
        for row in rows:
            if row.instance.tag_type is None and row.device.tag_type is None:
                continue
            for tag in row.unit_tags:
                if tag is not None:
                    owners.setdefault(tag, []).append(panel.id)
    return [
        CheckItem(
            check="duplicate_tag",
            status=CheckStatus.FAIL,
            panel_id=panel_ids[0],
            subject=tag,
            message=f"{len(panel_ids)} device units share this tag "
            f"({', '.join(dict.fromkeys(panel_ids))}): each needs its own",
        )
        for tag, panel_ids in owners.items()
        if len(panel_ids) > 1
    ]


# Device categories whose units carry a device tag (spec: Tag naming conventions; ADR 0030).
TAGGED_CATEGORIES = frozenset(
    {
        Category.NETWORK_SWITCH,
        Category.FIREWALL,
        Category.GATEWAY,
        Category.PATCH_PANEL,
        Category.GPS_CLOCK,
        Category.RTAC,
        Category.IO_CHASSIS,
        Category.WORKSTATION,
    }
)


def untagged_device_checks(
    panels: Iterable[tuple[Panel, Sequence[DeviceRow]]],
) -> list[CheckItem]:
    """A warning per part, per panel, of a tagged category whose rows print no tag (M45):
    duplicate_tag cannot see them, and they get no nameplate."""
    items: dict[tuple[str, str], CheckItem] = {}
    for panel, rows in panels:
        for row in rows:
            if row.device.category in TAGGED_CATEGORIES and row.tag is None:
                items.setdefault(
                    (panel.id, row.device.part_id),
                    CheckItem(
                        check="untagged_device",
                        status=CheckStatus.WARN,
                        panel_id=panel.id,
                        subject=row.device.part_id,
                        message=f"{row.device.model or row.device.part_id} prints with no "
                        "device tag, so it gets no nameplate and its MCB is named by its "
                        "model: give the library part a tag_type and purdue_level",
                    ),
                )
    return list(items.values())


def _short_speeds(needed: Counter[PortSpeed], slots: Counter[PortSpeed]) -> list[PortSpeed]:
    """Speeds s whose SFPs at s or faster outnumber the slots at s or faster."""
    short = []
    for index, speed in enumerate(SPEED_ORDER):
        if not needed[speed]:
            continue
        faster = SPEED_ORDER[index:]
        if sum(needed[s] for s in faster) > sum(slots[s] for s in faster):
            short.append(speed)
    return short


def dc_main_checks(mains: Iterable[DcMains]) -> list[CheckItem]:
    """Q1/Q2 against ΣQ; an override that differs from the rule is a warning (Q3)."""
    items = []
    for main in mains:
        if not main.rating_a:
            continue
        current = main.design_current_a
        message = f"Q1/Q2 {main.rating_a} A for ΣQ {current:.2f} A"
        status = CheckStatus.PASS
        if main.rating_a < current:
            status = CheckStatus.FAIL
            message += "; the main is below the design current"
        elif main.rating_a != main.rule_rating_a:
            status = CheckStatus.WARN
            message += f"; main_mcb_override_a, the rule gives {main.rule_rating_a} A (plan Q3)"
        items.append(
            CheckItem(
                check="dc_main",
                status=status,
                panel_id=main.panel_id,
                message=message,
                values={
                    "design_current_a": round(current, 3),
                    "rating_a": main.rating_a,
                    "rule_rating_a": main.rule_rating_a,
                },
            )
        )
    return items


def branch_mcb_checks(branches: Iterable[BranchMcb]) -> list[CheckItem]:
    """Each branch MCB with the needs behind its rating (plan Q35, ADR 0019); a warning
    when the inrush could not be checked or the library's old floor asks for more."""
    items = []
    for branch in branches:
        status = CheckStatus.PASS
        needs = [f"running {branch.running_a:.2f} A"]
        if branch.inrush_a is not None and not branch.inrush_counted:
            needs.append(
                f"inrush {branch.inrush_a:g} A for {branch.inrush_ms:g} ms, too short to trip"
            )
        elif branch.inrush_a is not None:
            if branch.trip_multiple is None or branch.inrush_need_a is None:
                status = CheckStatus.WARN
                needs.append(
                    f"inrush {branch.inrush_a:g} A, but the MCB catalogue has no trip curve"
                )
            else:
                needs.append(
                    f"inrush {branch.inrush_a:g} A / {branch.trip_multiple:g} = "
                    f"{branch.inrush_need_a:.2f} A"
                )
        needs.append(f"floor {branch.floor_a} A")
        message = (
            f"{branch.rating_a} A for {branch.load}: {', '.join(needs)}; "
            f"set by {', '.join(branch.set_by)}"
        )
        if branch.library_min_a is not None and branch.library_min_a > branch.rating_a:
            status = CheckStatus.WARN
            message += (
                f"; the library's min_branch_mcb_a {branch.library_min_a} A is no longer "
                "used (plan Q35)"
            )
        values: dict[str, int | float | str] = {
            "rating_a": branch.rating_a,
            "running_a": round(branch.running_a, 3),
        }
        for key in ("inrush_a", "inrush_ms", "trip_multiple", "inrush_need_a"):
            value = getattr(branch, key)
            if value is not None:
                values[key] = round(value, 3)
        values |= {"floor_a": branch.floor_a, "set_by": ",".join(branch.set_by)}
        items.append(
            CheckItem(
                check="branch_mcb",
                status=status,
                panel_id=branch.panel_id,
                subject=branch.tag,
                message=message,
                values=values,
            )
        )
    return items


def dc_float_checks(
    tables: Sequence[BomTable],
    mains: Iterable[DcMains],
    library: Library,
    constants: DesignConstants,
) -> list[CheckItem]:
    """The DC MCB set's rating (ADR 0023), once, when any panel has DC feeds, and each DC-fed
    device type's highest input voltage, where the library gives one, against the
    battery float voltage."""
    float_v = constants.dc_float_v
    items = []
    if any(main.rating_a for main in mains):
        mcb = library.catalogues.dc_mcb
        if mcb.dc_rating_v is None:
            status = CheckStatus.WARN
            message = (
                f"{mcb.make} {mcb.family}: the catalogue gives no dc_rating_v, so the DC "
                f"MCBs cannot be checked against the {float_v:g} V float"
            )
        else:
            status = CheckStatus.PASS if mcb.dc_rating_v >= float_v else CheckStatus.WARN
            message = (
                f"{mcb.make} {mcb.family} rated {mcb.dc_rating_v:g} V DC for the "
                f"{float_v:g} V float"
            )
        values: dict[str, int | float | str] = {"dc_float_v": float_v}
        if mcb.dc_rating_v is not None:
            values = {"dc_rating_v": mcb.dc_rating_v, **values}
        items.append(
            CheckItem(
                check="dc_float", status=status, subject=mcb.family, message=message, values=values
            )
        )
    seen: set[str] = set()
    for table in tables:
        for line in table.lines:
            device = library.get(line.part_id) if line.part_id else None
            if device is None or device.part_id in seen or device.input_v_max is None:
                continue
            if device.supply_type is not SupplyType.VDC:
                continue
            seen.add(device.part_id)
            ok = device.input_v_max >= float_v
            items.append(
                CheckItem(
                    check="dc_float",
                    status=CheckStatus.PASS if ok else CheckStatus.WARN,
                    subject=device.part_id,
                    message=f"input up to {device.input_v_max:g} V DC for the {float_v:g} V float",
                    values={"input_v_max": device.input_v_max, "dc_float_v": float_v},
                )
            )
    return items


def ventilation_checks(heat: HeatResult) -> list[CheckItem]:
    """Fans against the required airflow, or the natural rise against TMax - TInt, as
    the cabinet was built; then the line-up of the fan-ventilated cabinets."""
    items = []
    for cabinet in heat.cabinets:
        if cabinet.ventilation is Ventilation.FORCED:
            forced = cabinet.forced
            items.append(
                CheckItem(
                    check="airflow",
                    status=_status(forced.passes),
                    panel_id=cabinet.panel_id,
                    message=f"fans {forced.fan_m3h:.0f} m³/h for {forced.required_m3h:.1f} "
                    "m³/h required",
                    values={
                        "required_m3h": round(forced.required_m3h, 1),
                        "fan_m3h": forced.fan_m3h,
                    },
                )
            )
        else:
            natural = cabinet.natural
            items.append(
                CheckItem(
                    check="natural_convection",
                    status=_status(natural.passes),
                    panel_id=cabinet.panel_id,
                    message=f"ΔT {natural.delta_t_c:.2f} °C, limit {natural.limit_c:.0f} °C",
                    values={
                        "delta_t_c": round(natural.delta_t_c, 2),
                        "limit_c": natural.limit_c,
                    },
                )
            )
    line_up = heat.line_up
    if line_up is not None:
        items.append(
            CheckItem(
                check="line_up",
                status=_status(line_up.passes),
                message=f"{', '.join(line_up.panel_ids)}: fans {line_up.fan_m3h:.0f} m³/h for "
                f"{line_up.required_m3h:.1f} m³/h required",
                values={
                    "required_m3h": round(line_up.required_m3h, 1),
                    "fan_m3h": line_up.fan_m3h,
                },
            )
        )
    return items


def di_capacity_check(panels: Sequence[PanelBom], library: Library) -> CheckItem | None:
    """The hardwired DIs of every row and kit child against the substation's HWIO
    total; None when there is neither."""
    hwio = sum(line.hwio for panel in panels for line in panel.lines)
    inputs = 0
    for panel in panels:
        for line in panel.lines:
            device = library.get(line.part_id) if line.part_id else None
            if device is not None and device.di_inputs:
                qty = line.qty.value if isinstance(line.qty, QtySum) else line.qty
                inputs += device.di_inputs * (qty if isinstance(qty, int) else 1)
    if not hwio and not inputs:
        return None
    message = f"{inputs} DIs for {hwio} HWIO points"
    if not inputs:
        status = CheckStatus.WARN
        message += "; the library lists no DI inputs, so the capacity cannot be checked"
    elif inputs < hwio:
        status = CheckStatus.FAIL
        message += "; too few DIs"
    else:
        status = CheckStatus.PASS
    return CheckItem(
        check="di_capacity",
        status=status,
        message=message,
        values={"di_inputs": inputs, "hwio": hwio},
    )


def part_number_checks(equipment: Iterable[Equipment], library: Library) -> list[CheckItem]:
    """A warning per equipment entry with no part number whose library part has no
    ordering code either (ADR 0024)."""
    items = []
    for entry in equipment:
        part = library.get(entry.part_id) if entry.part_id is not None else None
        if part is None or entry.ordering_code is not None or part.ordering_code is not None:
            continue
        items.append(
            CheckItem(
                check="part_number",
                status=CheckStatus.WARN,
                subject=entry.id,
                message="no part number; the BOM prints the library model",
            )
        )
    return items


def part_source_checks(equipment: Iterable[Equipment], library: Library) -> list[CheckItem]:
    """A warning per equipment entry whose part's power or inrush is assumed (ADR 0037)."""
    items = []
    for entry in equipment:
        part = library.get(entry.part_id) if entry.part_id is not None else None
        if part is None:
            continue
        assumed = [
            (name, source.ref)
            for name in ("unit_power_w", "inrush_a")
            if (source := part.sources.get(name)) is not None and source.kind == "assumed"
        ]
        if not assumed:
            continue
        names = [name for name, _ref in assumed]
        refs = "; ".join(dict.fromkeys(ref for _name, ref in assumed))
        verb, them = ("is", "it") if len(names) == 1 else ("are", "them")
        items.append(
            CheckItem(
                check="part_source",
                status=CheckStatus.WARN,
                subject=entry.id,
                message=f"{part.part_id}: {' and '.join(names)} {verb} assumed ({refs}); "
                f"confirm {them} against a datasheet or a measurement",
                values={"part_id": part.part_id, "fields": ", ".join(names)},
            )
        )
    return items


def l2_link_checks(equipment: Iterable[Equipment], library: Library) -> list[CheckItem]:
    """A warning per networked equipment entry with no L2 link (M31)."""
    items = []
    for entry in equipment:
        part = library.get(entry.part_id) if entry.part_id is not None else None
        if part is None or part.category not in CATEGORY_LINKS or entry.l2_ports:
            continue
        items.append(
            CheckItem(
                check="l2_link",
                status=CheckStatus.WARN,
                subject=entry.id,
                message="no L2 link (l2_ports is 0), so the L2 switch gets no SFP for it",
            )
        )
    return items


def external_link_checks(
    links: Iterable[ExternalLink], equipment: Iterable[Equipment]
) -> list[CheckItem]:
    """A failure per external link whose firewall or external switch has no row (M61)."""
    roles = {entry.role for entry in equipment}
    items = []
    for link in links:
        if link.through_firewall and EquipmentRole.FIREWALL not in roles:
            message = "the link goes through the firewall, but no equipment row is a firewall"
        elif link.lands_on == "ext" and EquipmentRole.EXT_SWITCH not in roles:
            message = "the link lands on the external switch, but no equipment row is one"
        else:
            continue
        items.append(
            CheckItem(
                check="external_link", status=CheckStatus.FAIL, subject=link.name, message=message
            )
        )
    return items


def external_ac_checks(loose: LooseTable | None, library: Library) -> list[CheckItem]:
    """A warning per AC loose load: Power Consumption's External Equipment block holds
    station DC loads only, so the load is in neither the power nor the heat totals."""
    items = []
    for line in loose.lines if loose is not None else ():
        part = library.get(line.part_id) if line.part_id is not None else None
        if part is None or part.excluded_from_power or part.supply_type is not SupplyType.VAC:
            continue
        items.append(
            CheckItem(
                check="external_ac",
                status=CheckStatus.WARN,
                subject=line.part_id or line.description,
                message=f"{line.qty} x {part.unit_power_w:g} W AC left out of the power and heat "
                "totals: External Equipment counts station DC loads only",
            )
        )
    return items


def document_number_checks(documents: Mapping[str, RegisterEntry]) -> list[CheckItem]:
    """A warning per register document of the substation still numbered "TBD" (plan M51)."""
    return [
        CheckItem(
            check="document_number_placeholder",
            status=CheckStatus.WARN,
            subject=key,
            message="document number is still TBD; type it in the register before issuing",
        )
        for key, entry in documents.items()
        if entry.doc_no.strip().upper() == "TBD"
    ]


def vendor_list_checks(
    part_ids: Iterable[str],
    choice: CatalogueChoice,
    library: Library,
    vendor_list: VendorList,
) -> list[CheckItem]:
    """A warning per picked part, and per chosen brand set, outside the design basis's
    vendor list (ADR 0031, plan M53)."""
    items = []
    for part_id in sorted(set(part_ids)):
        part = library.get(part_id)
        if part is None or vendor_list.allows(part_id, part.make):
            continue
        items.append(
            CheckItem(
                check="vendor_list",
                status=CheckStatus.WARN,
                subject=part_id,
                message=f"{part.make} {part_id} is not on {vendor_list.name}"
                if part.make
                else f"{part_id} (no make) is not on {vendor_list.name}",
            )
        )
    for kind in CatalogueChoice.model_fields:
        brand = getattr(choice, kind) or DEFAULT_BRAND
        if not vendor_list.allows_brand(kind, brand):
            items.append(
                CheckItem(
                    check="vendor_list",
                    status=CheckStatus.WARN,
                    subject=kind,
                    message=f"the {kind} brand set '{brand}' is not on {vendor_list.name}",
                )
            )
    return items


def part_state_checks(part_ids: Iterable[str], library: Library) -> list[CheckItem]:
    """A warning per picked part that is a draft or obsolete (ADR 0037, plan M53)."""
    items = []
    for part_id in sorted(set(part_ids)):
        part = library.get(part_id)
        if part is None or part.state not in ("draft", "obsolete"):
            continue
        message = f"{part_id} is a draft: its values are not checked yet"
        if part.state == "obsolete":
            message = f"{part_id} is obsolete" + (
                f"; replaced by {part.successor}" if part.successor else ""
            )
        items.append(
            CheckItem(check="part_state", status=CheckStatus.WARN, subject=part_id, message=message)
        )
    return items


def _basis_item(status: CheckStatus, subject: str, message: str, field: str) -> CheckItem:
    return CheckItem(
        check="design_basis",
        status=status,
        subject=subject,
        message=message,
        values={"field": f"design_basis.{field}"},  # where Checks' "Go to the field" leads
    )


def design_basis_checks(
    part_ids: Iterable[str], library: Library, basis: DesignBasis
) -> list[CheckItem]:
    """The picked parts against the design basis (ADR 0031, plan M54): a DC part rated
    outside its voltage fails; an AC part at another voltage, a level out of the Purdue
    scope, a GPS clock without time sync, and EXT devices without a firewall warn."""
    parts = [p for i in sorted(set(part_ids)) if (p := library.get(i)) is not None]
    items = []
    dc = basis.dc_voltage_v
    for part in parts:
        low, high = part.input_v_min, part.input_v_max
        if dc is None or part.supply_type is not SupplyType.VDC or (low is None and high is None):
            continue
        if (low is not None and dc < low) or (high is not None and dc > high):
            rated = f"{low or 0:g}-{high:g} V" if high is not None else f"from {low:g} V"
            message = f"{part.part_id} is rated {rated} DC, outside the {dc:g} V design basis"
            items.append(_basis_item(CheckStatus.FAIL, part.part_id, message, "dc_voltage_v"))
    ac = basis.ac_voltage_v
    for part in parts:
        if ac is None or part.supply_type is not SupplyType.VAC or part.voltage_v is None:
            continue
        if part.voltage_v != ac:
            message = f"{part.part_id} takes {part.voltage_v} V AC; the design basis says {ac:g} V"
            items.append(_basis_item(CheckStatus.WARN, part.part_id, message, "ac_voltage_v"))
    scope = basis.purdue_scope
    if scope is not None:
        named = ", ".join(level for level in ("L1", "L2", "EXT") if level in scope)
        for level in PurdueLevel:
            at = [p.part_id for p in parts if p.purdue_level is level]
            if at and level.value not in scope:
                message = f"{', '.join(at)} at {level.value}, outside the Purdue scope {named}"
                items.append(_basis_item(CheckStatus.WARN, level.value, message, "purdue_scope"))
        ext = [p.part_id for p in parts if p.purdue_level is PurdueLevel.EXT]
        if "EXT" in scope and ext and not any(p.category is Category.FIREWALL for p in parts):
            message = f"{', '.join(ext)} at EXT with no firewall picked"
            items.append(_basis_item(CheckStatus.WARN, "EXT", message, "purdue_scope"))
    if basis.time_sync == "none":
        for part in parts:
            if part.category is Category.GPS_CLOCK:
                message = f"{part.part_id} is a GPS clock, but the design basis has no time sync"
                items.append(_basis_item(CheckStatus.WARN, part.part_id, message, "time_sync"))
    if not items:
        message = "the parts match the design basis"
        items.append(_basis_item(CheckStatus.PASS, "Design basis", message, "dc_voltage_v"))
    return items


def picked_parts(loaded: LoadedSubstation) -> set[str]:
    """Every part the substation's panels and loose material use."""
    parts = {d.part_id for panel in loaded.panels for d in panel.devices}
    loose = loaded.substation.loose_material
    if loose is not None:
        parts |= {i.part_id for i in loose.items if i.part_id is not None}
        parts |= {child for i in loose.items for child in i.children}
    return parts


def library_check(recorded: LibraryRef, active: LibraryRef | None) -> CheckItem:
    """The library the project recorded against the one it was built with (plan M8)."""
    problem = library_mismatch(recorded, active)
    return CheckItem(
        check="library_version",
        status=CheckStatus.WARN if problem else CheckStatus.PASS,
        message=problem or f"library {recorded.name} {recorded.version}",
    )


def _status(passes: bool) -> CheckStatus:
    return CheckStatus.PASS if passes else CheckStatus.FAIL


def render_text(report: CheckReport) -> str:
    """One line per check, then the counts."""
    lines = []
    for item in report.items:
        where = "  ".join(part for part in (item.panel_id, item.subject) if part)
        head = (
            f"{item.status.value.upper():<4}  {where}  "
            if where
            else f"{item.status.value.upper():<4}  "
        )
        note = f"  (accepted: {item.accepted})" if item.accepted else ""
        lines.append(f"{head}{item.check}  {item.message}{note}")
    warnings = report.count(CheckStatus.WARN)
    accepted = warnings - report.open_warnings
    warned = (
        f"{report.open_warnings} open warnings ({accepted} accepted)"
        if accepted
        else f"{warnings} warnings"
    )
    lines.append(
        f"{report.count(CheckStatus.FAIL)} failed, {warned}, "
        f"{report.count(CheckStatus.PASS)} passed"
    )
    return "\n".join(lines) + "\n"


def render_json(report: CheckReport) -> str:
    data = {
        "failed": report.failed,
        # an acceptance's reason only when there is one, so older reports read the same
        "items": [
            item.model_dump(mode="json", exclude=None if item.accepted else {"accepted"})
            for item in report.items
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
