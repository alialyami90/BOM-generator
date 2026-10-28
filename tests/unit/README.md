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
| `test_cli.py` | M1 | `bomgen validate`, `bomgen schema`, `--version` |
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
| `engine/test_engine_pipeline.py` | M2 | `pipeline.build` for groups A–D and the loose-material table |
| `writer/test_sheet_model.py` | M6 | sheet model defaults and the inputs it rejects before writing |
| `writer/test_xlsx_cells.py`, `test_xlsx_layout.py` | M6 | values, live formulas, styles, merges, column widths, row heights, hidden columns, read back with openpyxl |
| `writer/test_xlsx_print.py`, `test_xlsx_header_footer.py` | M6 | print setup, sheet view, page header and footer |
| `writer/test_no_xlsx_in_repo.py` | M6 | no generated `.xlsx` is committed |

`builders.py`, `engine/engine_factories.py`, `project_store/project_builders.py`
and `writer/writer_helpers.py` hold the small builders those tests share.
