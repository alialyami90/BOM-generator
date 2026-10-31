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
from bomgen.engine.grounding import grounding
from bomgen.engine.housekeeping import FORCED_FANS, housekeeping, needs_change_over
from bomgen.engine.items import BomItem, flatten
from bomgen.engine.kits import loose_table, main_equipment
from bomgen.engine.nameplates import nameplate_item, nameplates
from bomgen.engine.network import accessories
from bomgen.engine.power import power_consumption
from bomgen.engine.terminals import StripInputs, terminal_strips
from bomgen.engine.thermal import choose_ventilation, heat_result, ventilation_heat_w
from bomgen.engine.units import DeviceRow, expand_devices, lookup
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BuildResult, PanelBom
from bomgen.models.calc import BranchMcb, DcMains
from bomgen.models.library import Category, Library
from bomgen.models.panel import Panel, Ventilation
from bomgen.models.project import DesignConstants, LooseExtra


@dataclass(frozen=True)
class _PanelDraft:
    """A panel's groups A-F and what groups G-H need from them."""

    panel: Panel
    rows: tuple[DeviceRow, ...]
    ventilation: Ventilation
    items: list[BomItem]
    strip_inputs: StripInputs
    mains: DcMains
    branch_mcbs: tuple[BranchMcb, ...]

    @property
    def hwio(self) -> int:
        return sum(line.hwio for line in flatten(self.items))


def build(loaded: LoadedSubstation) -> BuildResult:
    """Every panel's BOM lines and the loose-material table."""
    library = loaded.library
    material = loaded.substation.loose_material
    loose_items = material.items if material is not None else []
    substation = loaded.substation.substation.name
    drafts = [_draft(p, library, loaded.constants, loose_items) for p in loaded.panels]
    hwio_total = sum(draft.hwio for draft in drafts)
    plates = [nameplates(d.panel, d.rows) for d in drafts]
    panels = tuple(
        _finish(draft, library, substation, hwio_total, len(panel_plates.plates))
        for draft, panel_plates in zip(drafts, plates, strict=True)
    )
    if library.catalogues.housekeeping.nameplate is None:
        plates = []
    loose = loose_table(material, substation, [(d.panel, d.rows) for d in drafts], library)
    fed = {item.part_id for item in loose_items if item.part_id and item.fed_from}
    power = power_consumption(panels, loose, library, loaded.constants, fed)
    fan_pair_m3h = FORCED_FANS * library.catalogues.housekeeping.fan.airflow_m3h
    heat = heat_result(
        [(d.panel, d.ventilation) for d in drafts], power, fan_pair_m3h, loaded.constants
    )
    return BuildResult(
        panels=panels,
        loose=loose,
        power=power,
        heat=heat,
        mains=tuple(d.mains for d in drafts),
        branch_mcbs=tuple(b for d in drafts for b in d.branch_mcbs),
        nameplates=tuple(p for p in plates if p.plates),
    )


def _draft(
    panel: Panel, library: Library, constants: DesignConstants, loose: Sequence[LooseExtra]
) -> _PanelDraft:
    rows = expand_devices(panel, library)
    change_over = needs_change_over(panel, library, loose)
    equipment = [
        enclosure_item(panel),
        *main_equipment(rows, library),
        *accessories(panel, rows, library),
    ]
    trial = [*equipment, *housekeeping(panel, library, Ventilation.NATURAL, change_over)]
    heat_w = ventilation_heat_w(flatten(trial), library)
    ventilation = choose_ventilation(panel, heat_w, constants)
    ac = ac_distribution(panel, library, ventilation, rows, constants)
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
        *housekeeping(panel, library, ventilation, change_over),
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
    )
    mains = DcMains(
        panel_id=panel.id,
        design_current_a=dc.design_current_a,
        rating_a=dc.main_a,
        rule_rating_a=dc.rule_main_a,
    )
    branch_mcbs = (*dc.branch_mcbs, *ac.branch_mcbs)
    return _PanelDraft(panel, rows, ventilation, items, strip_inputs, mains, branch_mcbs)


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
    ]
    return PanelBom(
        panel_id=panel.id,
        sheet_name=panel.sheet_name,
        title=(panel.cabinet_number, f"{substation} - {panel.cabinet_name}"),
        lines=mark_revisions(panel, flatten(items)),
    )
