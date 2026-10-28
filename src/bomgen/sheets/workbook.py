"""Assemble every sheet of one substation's workbook (spec: OUT-3; plan M5; ADR 0020).

Sheet order: one BOM sheet per panel in panel order, the Loose Material sheet when the
substation has loose material, then Power Consumption, Heat Dissipation and Heat
Calculations.
"""

from pathlib import Path

from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BomTable, BuildResult
from bomgen.models.calc import LineRef
from bomgen.models.sheet import SheetModel, WorkbookModel
from bomgen.sheets import heat_calc_sheet, heat_diss_sheet, styles
from bomgen.sheets import power_sheet as power_module
from bomgen.sheets.bom_sheet import BomSheet, bom_sheet, loose_sheet
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
    if loose is not None and loose.host_panel not in panels:
        # The host panel's document heads the Loose Material sheet (ADR 0020).
        raise ValueError(f"loose material host panel {loose.host_panel!r} is not a panel")

    names = loaded.substation.output.sheet_names
    sheets: list[SheetModel] = []
    sources: dict[LineRef, BomSource] = {}

    def add(sheet: BomSheet, table: BomTable) -> None:
        sheets.append(sheet.model)
        for line_ref, row in sheet.rows.items():
            sources[line_ref] = BomSource(sheet.model.name, row, table.lines[line_ref.line])

    for table in result.panels:
        panel = panels[table.panel_id]
        header_footer = bom_header_footer(
            project_name, panel.cabinet_number, loaded.documents[panel.document], logo
        )
        add(bom_sheet(table, header_footer), table)
    if loose is not None:
        document = loaded.documents[panels[loose.host_panel].document]
        header_footer = bom_header_footer(project_name, names.loose_material, document, logo)
        add(loose_sheet(names.loose_material, loose, header_footer), loose)

    if result.power is None or result.heat is None:
        return WorkbookModel(sheets=tuple(sheets))

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
        loaded.substation.output.power_footnotes,
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
