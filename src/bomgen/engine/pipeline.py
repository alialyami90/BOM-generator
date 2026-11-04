"""Run the derivation steps over a loaded substation (spec: Data model and generation order).

Steps 1-12: groups A-H per panel, the loose-material table, power and heat. Step 4
chooses each panel's ventilation from the heat of its other parts (plan Q4). Step 8
needs the substation's HWIO total (the XDIN default), so groups A-F of every panel are
built before any panel's groups G and H.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace

from bomgen.engine.ac_dist import ac_distribution
from bomgen.engine.assemble import mark_revisions
from bomgen.engine.dc_dist import dc_distribution, single_fed_loads
from bomgen.engine.enclosure import enclosure_item
from bomgen.engine.grounding import grounding, misc_items
from bomgen.engine.housekeeping import housekeeping, kit_counts, needs_change_over
from bomgen.engine.items import BomItem, flatten
from bomgen.engine.kits import annunciator_items, loose_table, main_equipment
from bomgen.engine.nameplates import nameplate_item, nameplates
from bomgen.engine.network import accessories
from bomgen.engine.power import power_consumption
from bomgen.engine.rules_text import ac_spare_rule, dc_spare_rule, fan_rule, main_mcb_rule
from bomgen.engine.tags import DEFAULT_TAGGING
from bomgen.engine.terminals import StripInputs, strip_table, terminal_strips
from bomgen.engine.thermal import choose_fan, choose_ventilation, heat_result, ventilation_heat_w
from bomgen.engine.units import DeviceRow, expand_devices, lookup
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BuildResult, PanelBom, PanelStrips
from bomgen.models.calc import BranchMcb, DcMains, FanChoice, HousekeepingBranch, SpareRatings
from bomgen.models.library import Category, FanRef, Library
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.project import DesignConstants, LooseExtra, LooseMaterial
from bomgen.models.substation import Tagging


@dataclass(frozen=True)
class _PanelDraft:
    """A panel's groups A-F and what groups G-H need from them."""

    panel: Panel
    rows: tuple[DeviceRow, ...]
    ventilation: Ventilation
    fan: FanRef  # fitted when forced, else the one the forced check assumes
    items: list[BomItem]
    strip_inputs: StripInputs
    mains: DcMains
    branch_mcbs: tuple[BranchMcb, ...]
    spares: SpareRatings
    housekeeping: tuple[HousekeepingBranch, ...]

    @property
    def hwio(self) -> int:
        return sum(line.hwio for line in flatten(self.items))


def build(loaded: LoadedSubstation) -> BuildResult:
    """Every panel's BOM lines and the loose-material table."""
    library = loaded.library
    material = loaded.substation.loose_material
    loose_items = [
        *(material.items if material is not None else []),
        *annunciator_items(loaded.substation.equipment, library, loaded.panels),
    ]
    substation = loaded.substation.substation.name
    fraction = loaded.spares.terminals_fraction
    drafts = [
        _draft(p, library, loaded.constants, loose_items, fraction, loaded.tagging)
        for p in loaded.panels
    ]
    hwio_total = sum(draft.hwio for draft in drafts)
    plates = [nameplates(d.panel, d.rows, loaded.tagging) for d in drafts]
    panels = tuple(
        _finish(draft, library, substation, hwio_total, len(panel_plates.plates))
        for draft, panel_plates in zip(drafts, plates, strict=True)
    )
    if library.catalogues.housekeeping.nameplate is None:
        plates = []
    if material is None and loaded.panels:  # devices' own loose items still need a sheet
        material = LooseMaterial(host_panel=loaded.panels[0].id)
    if material is not None and len(loose_items) > len(material.items):  # annunciator rows
        material = material.model_copy(update={"items": loose_items})
    loose = loose_table(material, substation, [(d.panel, d.rows) for d in drafts], library)
    power = power_consumption(panels, loose, library, loaded.constants)
    heat = heat_result(
        [
            (
                d.panel,
                d.ventilation,
                kit_counts(d.panel, Ventilation.FORCED).fans * d.fan.airflow_m3h,
            )
            for d in drafts
        ],
        power,
        loaded.constants,
    )
    catalogue_fan = library.catalogues.housekeeping.fan.part_id
    fans = []
    for draft, cabinet in zip(drafts, heat.cabinets, strict=True):
        if draft.ventilation is not Ventilation.FORCED:
            continue
        count = kit_counts(draft.panel, Ventilation.FORCED).fans
        airflow = count * draft.fan.airflow_m3h
        required = cabinet.forced.required_m3h
        fans.append(
            FanChoice(
                panel_id=draft.panel.id,
                part_id=draft.fan.part_id,
                fans=count,
                airflow_m3h=airflow,
                required_m3h=required,
                rule=fan_rule(count, airflow, required, larger=draft.fan.part_id != catalogue_fan),
            )
        )
    return BuildResult(
        panels=panels,
        loose=loose,
        power=power,
        heat=heat,
        fans=tuple(fans),
        mains=tuple(d.mains for d in drafts),
        branch_mcbs=tuple(b for d in drafts for b in d.branch_mcbs),
        spares=tuple(d.spares for d in drafts),
        housekeeping=tuple(b for d in drafts for b in d.housekeeping),
        strips=tuple(
            PanelStrips(
                panel_id=d.panel.id,
                strips=tuple(
                    strip_table(
                        d.panel, library, d.rows, replace(d.strip_inputs, xdin_default=hwio_total)
                    )
                ),
            )
            for d in drafts
        ),
        nameplates=tuple(p for p in plates if p.plates),
    )


def _draft(
    panel: Panel,
    library: Library,
    constants: DesignConstants,
    loose: Sequence[LooseExtra],
    spare_fraction: float = 0.0,
    tagging: Tagging = DEFAULT_TAGGING,
) -> _PanelDraft:
    rows = expand_devices(panel, library, tagging=tagging)
    change_over = needs_change_over(panel, library, loose)
    equipment = [
        enclosure_item(panel),
        *main_equipment(rows, library),
        *accessories(panel, rows, library),
    ]
    trial = [*equipment, *housekeeping(panel, library, Ventilation.NATURAL, change_over)]
    heat_w = ventilation_heat_w(flatten(trial), library)
    ventilation = choose_ventilation(panel, heat_w, constants)
    forced = kit_counts(panel, Ventilation.FORCED)
    fan = choose_fan(heat_w, library, constants, forced.fans, forced.thermostats)
    ac = ac_distribution(panel, library, ventilation, rows, constants, fan)
    fed = single_fed_loads(panel, rows, library, loose)
    dc = dc_distribution(panel, library, constants, rows, fed, change_over)
    annunciators = [
        item
        for item in loose
        if item.part_id is not None
        and item.fed_from == panel.id
        and lookup(library, item.part_id).category is Category.ANNUNCIATOR
    ]
    items = [
        *equipment,
        *housekeeping(panel, library, ventilation, change_over, fan),
        *ac.items,
        *dc.items,
    ]
    strip_inputs = StripInputs(
        ventilation=ventilation,
        ac_mcbs=ac.mcbs,
        dc_branches_per_feed=dc.branches_per_feed,
        change_over=change_over,
        annunciator_feeds=len(annunciators),
        xdin_default=0,
        spare_fraction=spare_fraction,
        kit=kit_counts(panel, ventilation),
    )
    mains = DcMains(
        panel_id=panel.id,
        design_current_a=dc.design_current_a,
        rating_a=dc.main_a,
        rule_rating_a=dc.rule_main_a,
        rule=main_mcb_rule(dc.rule_main_a, dc.design_current_a, constants.min_main_mcb_a),
    )
    branch_mcbs = (*dc.branch_mcbs, *ac.branch_mcbs)
    used = dc.branches_per_feed - panel.options.dc_spare_branches_per_feed
    spares = SpareRatings(
        panel_id=panel.id,
        ac_rule_a=ac.rule_spare_a,
        ac_rule=ac_spare_rule(ac.rule_spare_a),
        dc_rule_a=dc.rule_spare_a,
        dc_rule=dc_spare_rule(dc.rule_spare_a, branches=used) if dc.rule_spare_a else "",
    )
    return _PanelDraft(
        panel,
        rows,
        ventilation,
        fan,
        items,
        strip_inputs,
        mains,
        branch_mcbs,
        spares,
        tuple(ac.housekeeping),
    )


def _finish(
    draft: _PanelDraft,
    library: Library,
    substation: str,
    hwio_total: int,
    plates: int,
) -> PanelBom:
    panel = draft.panel
    strip_inputs = replace(draft.strip_inputs, xdin_default=hwio_total)
    nameplate = nameplate_item(panel, library, plates)
    items = [
        *draft.items,
        *terminal_strips(panel, library, draft.rows, strip_inputs),
        *grounding(panel, library),
        *([nameplate] if nameplate is not None else []),
        *misc_items(panel),
    ]
    return PanelBom(
        panel_id=panel.id,
        sheet_name=panel.sheet_name,
        kind=panel.kind,
        title=(panel.cabinet_number, f"{substation} - {panel.cabinet_name}"),
        lines=mark_revisions(panel, flatten(items)),
    )
