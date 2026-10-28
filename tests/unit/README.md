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

`builders.py` holds small input builders shared by these tests.
