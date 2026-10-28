# Unit tests

One module per rule area of the spec (tags, DC distribution, AC distribution,
terminal blocks, HWIO, power, heat, writer). Each test names the rule it pins.
A milestone with several modules may group them in a subfolder,
`tests/unit/<area>/`.

| Module | Milestone | What it checks |
| --- | --- | --- |
| `test_models_base.py` | M1 | shared field types: quantities, revisions, Excel sheet names, text templates |
| `test_library_model.py`, `test_panel_model.py`, `test_project_model.py` | M1 | input models: accepted and rejected values, defaults, cross-field rules |
| `test_yaml_source.py`, `test_loader.py`, `test_mirror.py`, `test_errors.py` | M1 | YAML loading, relative file references, panel mirroring, readable errors with file and path |
| `test_schema.py` | M1 | JSON Schema export, and that `schemas/` matches the models |
| `test_cli.py` | M1, M7 | `bomgen validate`, `bomgen build` (input problems, unknown substation), `bomgen schema`, `--version`, UTF-8 output on a Windows console |
| `test_device_db.py` | device DB | `data/device-db/` covers every example-library part both ways, cites sources, gives two alternative brands with low/mid/high parts, repeats no library fields |
| `library_store/test_library_manifest.py`, `test_library_package.py` | M8 | `.bomlib` manifest and versions; packing, checksums, tampered or mismatched packages rejected |
| `library_store/test_library_store.py`, `test_library_diff.py` | M8 | per-user store: install, activate, downgrade refusal, rollback, safe failed imports; part diff |
| `library_store/test_library_service.py`, `test_library_cli.py`, `test_library_wiring.py` | M8 | `bomgen library` commands and their wiring into `bomgen`, schema validation on pack and import |
| `test_launcher.py` | M11 | frozen-app entry points: `.bomlib` double-click import, `.bomproj` and window placeholders, `BOMGEN_NO_DIALOGS`, CLI delegation, self-test module manifest |
| `test_packaging.py` | M11 | Inno Setup script and PyInstaller spec: per-user install, Windows versions, `.bomlib` and `.bomproj` associations, kept libraries on uninstall |
| `test_bundle_container.py` | M8b | the zip container `.bomlib` and `.bomproj` packages share: round trip, changed-file and size-cap checks, Windows-unsafe or case-clashing names, skipped symlinks |
| `project_store/test_project_export.py`, `test_project_import.py`, `test_project_backup.py`, `test_project_workspace.py` | M8b | `.bomproj` export without `out/`, import into the workspace with overwrite refusal and safety backup, library-version note, `Backups/`, workspace location |
| `project_store/test_project_cli.py`, `test_project_public_api.py` | M8b | `bomgen project export\|import\|backup` and what the launcher and app may import |
| `engine/test_engine_bom_model.py` | M2 | BOM line, quantity, separator and table models (ADR 0014) |
| `engine/test_engine_tags.py` | M2 | tag naming: range tags, LAN and level tokens, gateway numbering, FOPP tag |
| `engine/test_engine_kits.py`, `test_engine_network.py`, `test_engine_housekeeping.py` | M2 | groups A–D: enclosure and devices with kit children, network accessories (SFPs, FOPP, cable managers, serial cables), housekeeping kit |
| `engine/test_engine_pipeline.py` | M2–M4 | `pipeline.build`: groups A–H in two passes, the loose-material table, power and heat |
| `writer/test_sheet_model.py` | M6 | sheet model defaults and the inputs it rejects before writing |
| `writer/test_xlsx_cells.py`, `test_xlsx_layout.py` | M6 | values, live formulas, styles, merges, column widths, row heights, hidden columns, read back with openpyxl |
| `writer/test_xlsx_print.py`, `test_xlsx_header_footer.py` | M6 | print setup, sheet view, page header and footer |
| `writer/test_no_xlsx_in_repo.py` | M6 | no generated `.xlsx` is committed |
| `writer/test_xlsx_replace.py` | M6 | a workbook replaces the file at its path only once complete, so a failed write or replace keeps the issued one |
| `test_substation_model.py` | M1b | substation model: documents, panels, equipment, network, spares, layout (ADR 0012/0013) |
| `test_substation_loader.py` | M1b | loading a project with substations: key-by-key defaults, document register keys, equipment, library |
| `library_store/test_library_preview.py` | M8b | library import dry-run: every check listed, nothing written |
| `project_store/test_project_preview.py`, `test_project_backups.py` | M8b | project import dry-run; listing and restoring the backups in `Backups/` |
| `project_store/test_project_restore_preview.py` | M8b | the restore dry-run: `restore_backup`'s two refusals as checks before the import checks, nothing written |
| `project_store/test_project_rename.py` | M8b | importing under a new id (keep both): only `project.id` changes, taken and unsafe ids refused, the suggested free id |
| `app/test_app_window.py`, `test_app_api.py` | M10a | the pywebview window and its refusals (missing UI files or WebView2), the Python API the UI calls (ADR 0015) |
| `app/test_app_ui_assets.py` | M10a | the app's UI files are complete, offline and in step with the M9 design |
| `engine/test_engine_ac_dist.py` | M3 | group E AC distribution: branches in load order with spares, CINC, breaker catalogue codes, MCB count |
| `engine/test_engine_dc_dist.py` | M3 | group F DC distribution: branches per feed, spares, branch and main MCB ratings, overrides, aux contacts |
| `engine/test_engine_terminals.py` | M3 | group G terminal strips: the terminal block table per panel kind, X3/X4 rules, device strips (XDIP, XDIN, XRTAC) |
| `engine/test_engine_grounding.py` | M3 | group H grounding busbars |
| `engine/test_engine_assemble.py` | M3 | revision marks per cell (OUT-8) |
| `library_store/test_library_device_db.py` | M8 | device-database records packed in a `.bomlib`, checked on pack and loaded after import |
| `engine/test_engine_calc_model.py` | M4 | power and heat formulas: total power, sizing columns N–R, supply label, block margin, BTU |
| `engine/test_engine_power.py` | M4 | Power Consumption rows: powered rows DC then AC in BOM order, voltages, external block at 125 V, summary |
| `engine/test_engine_thermal.py` | M4 | required airflow, surface area, natural-convection rise, line-up check, the automatic ventilation choice |
| `sheets/test_grid.py` | M5 | sheet builder helpers: quoted sheet references, frames, merges |
| `sheets/test_bom_sheet.py` | M5 | panel BOM sheet: title, header row, SR.NO formula, separators, quantities |
| `sheets/test_power_sheet.py` | M5 | Power Consumption sheet: layout, references to the BOM sheets, power, sizing and block-total formulas |
| `sheets/test_heat_sheets.py` | M5 | Heat Dissipation and Heat Calculations sheets: blocks, formulas, notes, frames, print setup |
| `sheets/test_header_footer.py` | M5 | page header and footer per sheet, logo, calculation-sheet header size |
| `app/test_app_library_api.py` | M10b | the Library screens' API: browse with device-database records, import review, import, versions |
| `app/test_app_projects_api.py` | M10b | the Home and Project page API: the project list and status, recent folders in the app home, open, export, backup, import and restore, `show_in_folder` limited to listed files |
| `engine/test_sizing.py` | M1c | network sizing rules R1–R4 (ADR 0013): reserved and spare ports, L1 and L2 switch counts, the L1 switch the tool picks |
| `engine/test_layout.py` | M1c | panel layout rules R5–R8: 32U fill, blank plates, cable managers, A/B streams, common devices, overrides and removals |
| `engine/test_layout_cli.py` | M1c | `bomgen layout` writes and relists the generated panel files and keeps hand-written ones; `bomgen build` lays them out again unless `--no-layout` |
| `engine/test_checks.py` | M7 | the step 15 check report: SFPs against slots, DC mains against ΣQ, ventilation, DI capacity (ADR 0016) |
| `test_revision.py` | M7 | comparison with the previous issue (OUT-8, Q10): changed, added and removed rows and sheets |
| `app/test_app_substation_api.py` | M10c | the Settings and Network API, read-only: register documents, output file name, constants against the project defaults, equipment, located problems |
| `app/test_app_output_api.py` | M10d | the Checks and Build API: checks, build target, the workbook and its report, the `file_exists`, `bad_name`, `has_errors`, `file_open` and `bad_folder` refusals |

`builders.py`, `engine/engine_factories.py`, `project_store/project_builders.py`
and `writer/writer_helpers.py` hold the small builders those tests share.
