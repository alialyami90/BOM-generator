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

`builders.py` holds small input builders shared by these tests.
