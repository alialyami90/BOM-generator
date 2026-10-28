"""Assemble every sheet of one substation's workbook (spec: OUT-3; plan M5).

Sheet order: one BOM sheet per panel in panel order (the loose-material table under
its host), then Power Consumption, Heat Dissipation and Heat Calculations.
"""

from pathlib import Path

from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BuildResult
from bomgen.models.calc import LineRef
from bomgen.models.sheet import SheetModel, WorkbookModel
from bomgen.sheets import heat_calc_sheet, heat_diss_sheet, styles
from bomgen.sheets import power_sheet as power_module
from bomgen.sheets.bom_sheet import bom_sheet
from bomgen.sheets.header_footer import bom_header_footer, calc_header_footer, fitting_size
from bomgen.sheets.power_sheet import BomSource


def build_workbook(
    loaded: LoadedSubstation, result: BuildResult, *, logo: Path | None = None
) -> WorkbookModel:
    """Lay out ``result`` for ``loaded``; ``logo`` is the resolved path of the header picture."""
    project_name = loaded.project.project.name
    panels = {panel.id: panel for panel in loaded.panels}
    cabinet_names = {panel.id: panel.cabinet_name for panel in loaded.panels}
    loose = result.loose
    if loose is not None and loose.host_panel not in {p.panel_id for p in result.panels}:
        raise ValueError(f"loose material host panel {loose.host_panel!r} has no BOM sheet")

    sheets: list[SheetModel] = []
    sources: dict[LineRef, BomSource] = {}
    for table in result.panels:
        panel = panels[table.panel_id]
        hosted = loose if loose is not None and loose.host_panel == table.panel_id else None
        header_footer = bom_header_footer(
            project_name, panel.cabinet_number, loaded.documents[panel.document], logo
        )
        sheet = bom_sheet(table, hosted, header_footer)
        sheets.append(sheet.model)
        for line_ref, row in sheet.rows.items():
            owner = table if line_ref.panel_id is not None else hosted
            assert owner is not None
            sources[line_ref] = BomSource(table.sheet_name, row, owner.lines[line_ref.line])

    if result.power is None or result.heat is None:
        return WorkbookModel(sheets=tuple(sheets))

    names = loaded.substation.output.sheet_names
    calcs = loaded.substation.calculations
    constants = loaded.constants

    power = power_module.power_sheet(
        names.power_consumption,
        result.power,
        sources,
        cabinet_names,
        constants,
        calc_header_footer(
            project_name,
            f"Power Consumption for {calcs.power_consumption.scope}",
            loaded.documents[calcs.power_consumption.document],
            logo,
            fitting_size(styles.CALC_MARGINS, power_module.SCALE),
        ),
    )
    dissipation = heat_diss_sheet.heat_dissipation_sheet(
        names.heat_dissipation,
        result.heat,
        names.power_consumption,
        power.rows,
        sources,
        cabinet_names,
        constants,
        calc_header_footer(
            project_name,
            f"Heat Dissipation for {calcs.heat_dissipation.scope}",
            loaded.documents[calcs.heat_dissipation.document],
            logo,
            fitting_size(styles.CALC_MARGINS, heat_diss_sheet.SCALE),
        ),
    )
    calculations = heat_calc_sheet.heat_calculations_sheet(
        names.heat_calculations,
        result.heat,
        names.heat_dissipation,
        dissipation.totals,
        cabinet_names,
        constants,
        calc_header_footer(
            project_name,
            f"Heat Calculations for {calcs.heat_calculations.scope}",
            loaded.documents[calcs.heat_calculations.document],
            logo,
            fitting_size(styles.CALC_MARGINS, heat_calc_sheet.SCALE),
        ),
    )
    return WorkbookModel(sheets=(*sheets, power.model, dissipation.model, calculations))
