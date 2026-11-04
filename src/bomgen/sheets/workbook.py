"""Assemble every sheet of one substation's workbook (spec: OUT-3; plan M5; ADR 0020).

Sheet order: one BOM sheet per panel in panel order, the Loose Material sheet when the
substation has loose material, then Power Consumption, Heat Dissipation and Heat
Calculations, then the Summary BOM when included (ADR 0035), then the Revision History when there is
any (ADR 0036).
"""

from pathlib import Path

from bomgen.engine.spares import spares
from bomgen.engine.summary import summarize
from bomgen.io.loader import LoadedSubstation
from bomgen.models.bom import BomTable, BuildResult
from bomgen.models.calc import LineRef
from bomgen.models.sheet import SheetModel, WorkbookModel
from bomgen.sheets import heat_calc_sheet, heat_diss_sheet, styles
from bomgen.sheets import power_sheet as power_module
from bomgen.sheets.bom_sheet import BomSheet, bom_sheet, loose_sheet
from bomgen.sheets.cable_sheet import cable_sheet, has_cables
from bomgen.sheets.header_footer import bom_header_footer, calc_header_footer, fitting_size
from bomgen.sheets.history_sheet import history_rows, history_sheet
from bomgen.sheets.ied_sheet import ied_sheet
from bomgen.sheets.nameplate_sheet import nameplate_sheet
from bomgen.sheets.notes_sheet import noted_rows, notes_sheet
from bomgen.sheets.power_sheet import BomSource
from bomgen.sheets.spares_sheet import spares_sheet
from bomgen.sheets.summary_sheet import summary_sheet


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
    if result.nameplates:
        # Issued under the first panel's document, as the BOM sheets are (ADR 0026).
        document = loaded.documents[loaded.panels[0].document]
        header_footer = bom_header_footer(project_name, names.nameplates, document, logo)
        numbers = {panel.id: panel.cabinet_number for panel in loaded.panels}
        substation_name = loaded.substation.substation.name
        sheets.append(
            nameplate_sheet(
                names.nameplates, substation_name, result.nameplates, numbers, header_footer
            )
        )

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
    sheets.extend((power.model, dissipation.model, calculations))
    if "summary_bom" in loaded.substation.output.include:
        # Issued under the substation's main document (ADR 0035).
        document = loaded.documents[loaded.substation.document]
        cells = {ref: (source.sheet, source.row) for ref, source in sources.items()}
        tables: dict[str | None, str] = {p.panel_id: p.sheet_name for p in result.panels}
        tables[None] = names.loose_material
        sheets.append(
            summary_sheet(
                names.summary_bom,
                loaded.substation.substation.name,
                summarize(result),
                cells,
                tables,
                bom_header_footer(project_name, loaded.substation.substation.name, document, logo),
            )
        )
    spare_table = spares(loaded, result)
    if spare_table.lines:
        substation = loaded.substation.substation.name
        sheets.append(
            spares_sheet(
                names.spare_parts,
                substation,
                spare_table,
                names.summary_bom if "summary_bom" in loaded.substation.output.include else None,
                bom_header_footer(
                    project_name, substation, loaded.documents[loaded.substation.document], logo
                ),
            )
        )
    if has_cables(result.loose):
        assert result.loose is not None
        substation = loaded.substation.substation.name
        sheets.append(
            cable_sheet(
                names.cable_schedule,
                substation,
                result.loose,
                {ref: (source.sheet, source.row) for ref, source in sources.items()},
                bom_header_footer(
                    project_name, substation, loaded.documents[loaded.substation.document], logo
                ),
            )
        )
    noted = noted_rows(result, names.loose_material)
    if "notes" in loaded.substation.output.include and noted:
        substation = loaded.substation.substation.name
        sheets.append(
            notes_sheet(
                names.notes,
                substation,
                noted,
                bom_header_footer(
                    project_name, substation, loaded.documents[loaded.substation.document], logo
                ),
            )
        )
    schedule = loaded.substation.network.ied_schedule
    if "ied_schedule" in loaded.substation.output.include and schedule:
        substation = loaded.substation.substation.name
        sheets.append(
            ied_sheet(
                names.ied_schedule,
                substation,
                schedule,
                bom_header_footer(
                    project_name, substation, loaded.documents[loaded.substation.document], logo
                ),
            )
        )
    history = history_rows(loaded)
    if history:
        document = loaded.documents[loaded.substation.document]
        substation = loaded.substation.substation.name
        sheets.append(
            history_sheet(
                names.revision_history,
                substation,
                history,
                bom_header_footer(project_name, substation, document, logo),
            )
        )
    return WorkbookModel(sheets=tuple(sheets))
