# M1 Input Models, Loader, Examples and `bomgen validate` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load and validate the three YAML input sets (device library, panels, project settings) into pydantic models with readable, located errors, ship the spec's example project in `examples/`, and expose `bomgen validate` and `bomgen schema`.

**Architecture:** Pure pydantic models in `bomgen.models` validate one record at a time. `bomgen.io` reads YAML (keeping line numbers), validates each file, resolves panel mirroring, then runs cross-file reference checks, collecting every problem as an `Issue(file, location, message, line)` before raising one `InputError`. The typer CLI is a thin caller. Design choices: ADR 0010.

**Tech Stack:** Python 3.12, pydantic 2, PyYAML (SafeLoader, `compose` for line numbers), typer, pytest, ruff, mypy --strict.

**Spec:** `docs/spec/generator-spec-v2.md` ("Inputs the tool needs", "Data model and generation order"); schema sketch: `docs/plan.md` section 3; decisions: `docs/decisions/0010-input-schema.md`.

## Global Constraints

- Python `>=3.12`; only the dependencies already in `pyproject.toml` (pydantic, PyYAML, typer, openpyxl; dev: mypy, pytest, ruff, types-PyYAML, types-openpyxl).
- Before every commit run `ruff check . && ruff format --check .`, `mypy`, `pytest` from the repo root with the venv active (`. .venv/bin/activate`); commit only when all three pass.
- Conventional commits (`feat:`, `test:`, `docs:` …), scope optional. End every commit message with these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01JD6t85We8KwwnMNyP3v3is`.
- TDD: failing test first, named after the rule, e.g. `test_mirror_swaps_lan_letter_and_prefix_in_tags`.
- Reference the spec by section name; do not restate it in comments or docs.
- Every input model forbids unknown keys (`extra="forbid"`) and is frozen.
- Never commit `.xlsx` files.
- Unit tests go in `tests/unit/test_<area>.py`; example-project tests in `tests/golden/` with marker `golden` and a comment citing the spec section of each expected value.

## Review Focus

1. Unquoted YAML scalars: `rev: 0` and `sheet_name: 1` (ints) and `issue_date: 2026-10-28` (date) must be accepted; a `qty: 1 lot` typo must give one clear message, not a pydantic union dump. Tests in Task 1 (`Rev`, `Quantity`) and Task 2.
2. Files saved by Windows Notepad (UTF-8 with BOM) and duplicate keys in a mapping (PyYAML silently keeps the last one). Tests in Task 3.
3. An unknown `part_id` deep in a panel must name the file, the path (`devices[2].part_id`) and the line. Tests in Tasks 3 and 4.
4. Excel sheet-name rules (≤ 31 chars, none of `[]:*?/\`, unique ignoring case across panel and calc sheets). Tests in Tasks 1 and 4.
5. A mirror of a mirror, or a mirror of a panel not listed in the project, must fail with a message naming both ids, not recurse or crash. Tests in Task 4.

---

## File structure

```
src/bomgen/
  models/__init__.py      re-exports nothing (empty docstring module)
  models/_base.py         InputModel, Rev, Quantity, ChildQuantity, AutoBool, ExcelSheetName, template_fields
  models/library.py       enums, PortGroup, ChildRule, TerminalRule, LooseItem, DeviceType, catalogues, Library
  models/panel.py         Enclosure, DeviceInstance, PortAllocation, PortPlan, PanelOptions, DocumentInfo,
                          RevisionMark, Revision, Panel, PanelMirror
  models/project.py       ProjectInfo, CalcDocument, Documents, SheetNames, OutputSettings, DesignConstants,
                          LooseExtra, LooseMaterial, Project
  io/__init__.py          empty docstring module
  io/errors.py            Issue, InputError, format_location, issues_from_validation_error
  io/yaml_source.py       YamlSource, read_yaml
  io/mirror.py            lan_index, mirror_tag, mirror_panel
  io/references.py        cross-reference checks returning list[Issue]
  io/loader.py            LoadedProject, load_project
  io/schema.py            json_schemas, write_json_schemas
  cli.py                  typer app: validate, schema
  __main__.py             `python -m bomgen`
schemas/                  committed JSON Schemas (project, library, panel)
examples/                 project.yaml, library.yaml, panels/{psa1,psa2,psa3,ws}.yaml, assets/logo.png
tests/unit/               test_models_base.py, test_library_model.py, test_panel_model.py,
                          test_project_model.py, test_errors.py, test_yaml_source.py, test_mirror.py,
                          test_loader.py, test_cli.py, test_schema.py
tests/golden/             test_example_inputs.py
```

---

### Task 1: Base types and library model

**Files:**
- Create: `src/bomgen/models/__init__.py`, `src/bomgen/models/_base.py`, `src/bomgen/models/library.py`
- Test: `tests/unit/test_models_base.py`, `tests/unit/test_library_model.py`

**Interfaces:**
- Produces (`bomgen.models._base`):
  - `class InputModel(BaseModel)` with `model_config = ConfigDict(extra="forbid", frozen=True)`; every input model subclasses it.
  - `template_fields(template: str) -> set[str]` — field names used by a `str.format` template (via `string.Formatter().parse`); raises `ValueError("malformed template: ...")` on unbalanced braces.
  - `check_template(template: str, allowed: set[str]) -> str` — returns the template or raises `ValueError` naming the unknown placeholders and listing the allowed ones, sorted.
  - `Rev` = `Annotated[str, BeforeValidator(...)]`: an `int` becomes its `str` (`0` → `"0"`); empty string rejected.
  - `Quantity` = `int | Literal["1 Lot"]` with a single `PlainValidator`: accepts `int >= 1` (not `bool`) or exactly `"1 Lot"`; anything else raises `ValueError("must be a whole number of at least 1 or '1 Lot'")`. Use `WithJsonSchema({"anyOf": [{"type": "integer", "minimum": 1}, {"const": "1 Lot"}]})`.
  - `ChildQuantity` = `int | Literal["cores"]`, same pattern, message `"must be a whole number of at least 1 or 'cores'"`.
  - `AutoBool` = `bool | Literal["auto"]`, same pattern, message `"must be true, false or 'auto'"`.
  - `ExcelSheetName` = `Annotated[str, BeforeValidator(...), AfterValidator(...)]`: an unquoted YAML `int` becomes its `str` (`sheet_name: 1` → `"1"`); then 1–31 characters, none of `[ ] : * ? / \`, must not start or end with `'`. Message names the broken rule.
  - `PartId` = `Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")]`.
- Produces (`bomgen.models.library`):
  - StrEnums: `Category` (values: `network_switch, firewall, gateway, patch_panel, gps_clock, rtac, io_chassis, workstation, monitor, peripheral, sfp, cable_manager, serial_cable, component, lamp, door_switch, fan, vent_filter, thermostat, relay, socket, change_over_diode, annunciator, software, cable, accessory`), `PurdueLevel` (`L1, L2, EXT, L3`), `SupplyType` (`VDC, VAC`), `LoadType` (`CONTINUOUS, INTERMITTENT`), `PortSpeed` (`10M, 100M, 1G, 10G`; member names `M10, M100, G1, G10`), `Media` (`MM, SM, RJ45`), `PortKind` (`fixed, sfp_slot`).
  - `PortGroup(count: PositiveInt, speed: PortSpeed, media: Media | None = None, kind: PortKind)`; `kind=fixed` requires `media`.
  - `ChildRule(part_id: PartId, qty: ChildQuantity = 1)`.
  - `TerminalRule(strip: str, block: str, count: PositiveInt, per: Literal["unit", "serial_port"] = "unit", first_slot: str | None = None)`; `strip` placeholders ⊆ `{n, slot}`; `{slot}` present ⇔ `first_slot` set; `first_slot` is one uppercase letter.
  - `LooseItem(part_id: PartId, qty: Quantity = 1)`.
  - `DeviceType` fields, in this order: `part_id: PartId`, `category: Category`, `make: str`, `model: str`, `ordering_code: str | None = None`, `description_template: str` (placeholders ⊆ `{lan, level, purpose}`), `tag_type: str | None = None`, `purdue_level: PurdueLevel | None = None`, `tag_pattern: str | None = None` (placeholders ⊆ `{prefix, level, type, lan, lan_index, nn}`), `supply_type: SupplyType | None = None`, `voltage_v: PositiveInt | None = None`, `unit_power_w: NonNegativeFloat | None = None`, `load_type: LoadType | None = None`, `power_supplies: Literal[0, 1, 2] = 0`, `min_branch_mcb_a: PositiveInt | None = None`, `alarm_on_branch_mcb: bool = False`, `hwio_points: NonNegativeInt = 0`, `ports: list[PortGroup] = []`, `cores: PositiveInt | None = None`, `children: list[ChildRule] = []`, `terminals: list[TerminalRule] = []`, `loose_items: list[LooseItem] = []`, `excluded_from_power: bool` (default: `True` when `supply_type` is absent, else `False`; set in a `mode="before"` model validator only when the key is missing).
    Property `code -> str`: `ordering_code` if set, else `model` (spec: "Columns of a panel BOM", col G).
    Model validator rules (each its own `ValueError` message): a device not excluded from power needs `supply_type`, `unit_power_w` and `load_type`; `power_supplies > 0` needs `supply_type == VDC`; an excluded device needs `power_supplies == 0`; a child with `qty: cores` needs `cores` on the parent.
  - `McbCatalogue(family: str, make: str, poles: PositiveInt = 2, ratings_a: list[PositiveInt], code_pattern: str)`: `ratings_a` non-empty and strictly increasing; `code_pattern` placeholders == `{rating}` and `code_pattern.format(rating=1)` must succeed. Method `code_for(rating_a: int) -> str` raises `ValueError` for a rating not in `ratings_a`.
  - `AuxContact(make: str, model: str, ordering_code: str)`; `TerminalBlockType(make: str, ordering_code: str)`; `Busbar(description: str)`.
  - `HousekeepingRef(part_id: PartId)`; `FanRef(HousekeepingRef)` adds `airflow_m3h: PositiveFloat`; `SocketRef(HousekeepingRef)` adds `rating_a: PositiveInt`.
  - `Housekeeping(lamp: HousekeepingRef, door_switch: HousekeepingRef, fan: FanRef, vent_filter: HousekeepingRef, thermostat: HousekeepingRef, ipr_kit: HousekeepingRef, change_over_diodes: HousekeepingRef, socket: SocketRef)`.
  - `Catalogues(mcb: McbCatalogue, aux_contact: AuxContact, terminal_blocks: dict[str, TerminalBlockType] (min 1), busbars: dict[str, Busbar] (min 1), housekeeping: Housekeeping)`.
  - `Library(devices: list[DeviceType] (min 1), catalogues: Catalogues)` with methods `get(part_id: str) -> DeviceType | None` and `part_ids() -> list[str]` (in file order). Cross-record checks (duplicates, dangling references) are NOT here; Task 4 owns them.

- [ ] **Step 1: Write failing tests** in `tests/unit/test_models_base.py`:
  `test_template_fields_lists_placeholders` (`"LAN-{lan} {level}"` → `{"lan", "level"}`), `test_check_template_rejects_unknown_placeholder` (message contains `'colour'` and `allowed: lan, level, purpose`), `test_rev_accepts_unquoted_integer` (`0` → `"0"`), `test_quantity_accepts_int_and_one_lot`, `test_quantity_rejects_other_text_with_one_message` (validating `"1 lot"` gives exactly one error whose message is the one above), `test_quantity_rejects_bool_and_zero`, `test_auto_bool_accepts_true_false_auto`, `test_excel_sheet_name_rejects_long_and_forbidden_chars` (32 chars; `"a/b"`; `"'x"`), `test_excel_sheet_name_accepts_unquoted_integer` (`1` → `"1"`), each through a small `TypeAdapter` or test model.
- [ ] **Step 2: Write failing tests** in `tests/unit/test_library_model.py`, using a `minimal_library_dict()` helper that returns one powered switch, one passive part, and full catalogues:
  `test_l1_switch_record_from_spec_validates` (the "Inputs → 1. Device library" example: RST2228-L1-24MM, network_switch, Ruggedcom, RST-2228, ordering code `6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05`, 77 W, VDC 125, CONTINUOUS, 2 supplies, `min_branch_mcb_a: 2`, `hwio_points: 1`, ports 24 × 100M MM fixed + 4 × 1G sfp_slot), `test_code_falls_back_to_model_when_no_ordering_code`, `test_passive_part_defaults_to_excluded_from_power`, `test_powered_device_requires_supply_power_and_load_type`, `test_dual_feed_requires_vdc`, `test_excluded_device_cannot_have_power_supplies`, `test_cores_child_requires_parent_cores`, `test_unknown_key_is_rejected` (`colour: red` → `extra_forbidden`), `test_description_template_rejects_unknown_placeholder`, `test_fixed_port_group_requires_media`, `test_slot_strip_requires_first_slot`, `test_mcb_code_for_rating` (`A9F742{rating:02d}`: 1 → `A9F74201`, 16 → `A9F74216`; 3 raises), `test_mcb_ratings_must_increase`, `test_library_get_returns_device_or_none`.
- [ ] **Step 3: Run** `pytest tests/unit/test_models_base.py tests/unit/test_library_model.py -q` — expect collection errors (`ModuleNotFoundError: bomgen.models`).
- [ ] **Step 4: Implement** `_base.py` and `library.py` per the Interfaces block. Class docstrings cite the spec section they model; no restating rules.
- [ ] **Step 5: Run** the two test files — all pass; then the full pre-commit trio — clean.
- [ ] **Step 6: Commit** `feat(models): add base input types and device library model`.

### Task 2: Panel and project models

**Files:**
- Create: `src/bomgen/models/panel.py`, `src/bomgen/models/project.py`
- Test: `tests/unit/test_panel_model.py`, `tests/unit/test_project_model.py`

**Interfaces:**
- Consumes: `InputModel`, `Rev`, `Quantity`, `AutoBool`, `ExcelSheetName`, `PartId`, `check_template` (Task 1); `PortSpeed`, `Media` from `bomgen.models.library`.
- Produces (`bomgen.models.panel`):
  - `Lan = Literal["A", "B"]`; StrEnums `PanelKind` (`network, control, console`), `CableEntry` (`top, side`), `Ventilation` (`auto, forced, natural`).
  - `Enclosure(make: str, model: str, ordering_code: str | None = None, h_mm: PositiveInt, d_mm: PositiveInt, w_mm: PositiveInt, base_frame_mm: NonNegativeInt = 0, cable_entry: CableEntry)`.
  - `DeviceInstance(part_id: PartId, qty: PositiveInt = 1, tag: str | None = None, purpose: str | None = None, lan: Lan | None = None)`.
  - `PortAllocation(count: PositiveInt, speed: PortSpeed, media: Media, spare: NonNegativeInt = 0)`.
  - `PortPlan(uplinks_l3: list[PortAllocation] = [], uplinks: list[PortAllocation] = [], downlinks: list[PortAllocation] = [], serial_ports: NonNegativeInt = 0)`.
  - `PanelOptions(aux_socket_a: PositiveInt | None = None, smoke_detector: bool = True, change_over_diodes: AutoBool = "auto", ventilation: Ventilation = auto, dc_spare_branches_per_feed: NonNegativeInt = 1, ac_spare_branches: NonNegativeInt = 1, main_mcb_override_a: PositiveInt | None = None, inter_panel_terminals: NonNegativeInt | None = None, terminal_overrides: dict[str, NonNegativeInt] = {}, grounding_busbars: list[str] = ["ac_safety_ground", "instrument_ground"])`.
  - `DocumentInfo(doc_no: str, rev: Rev, issue_date: date)`.
  - `RevisionMark(tag: str, columns: list[Literal["A","B","C","D","E","F","G","H"]] (min 1))`; `Revision(highlight: list[RevisionMark] = [])`.
  - `Panel(id: str (pattern ^[a-z0-9][a-z0-9_-]*$), cabinet_number: str, cabinet_name: str, tag_prefix: str (pattern ^[A-Z][A-Z0-9]*$), lan: Lan | None = None, sheet_name: ExcelSheetName, kind: PanelKind, enclosure: Enclosure, devices: list[DeviceInstance] (min 1), port_plans: dict[str, PortPlan] = {}, options: PanelOptions = PanelOptions(), document: DocumentInfo, revision: Revision = Revision())`.
  - `PanelMirror(id, mirror_of: str (same id pattern), cabinet_number, cabinet_name, tag_prefix, lan: Lan | None = None, sheet_name: ExcelSheetName, options: dict[str, Any] = {}, document: DocumentInfo, revision: Revision = Revision())` — same field types as `Panel`; `options` holds `PanelOptions` keys and is validated after merging (Task 4). A validator rejects `mirror_of == id`.
- Produces (`bomgen.models.project`):
  - `ProjectInfo(name: str, substation: str, doc_no: str, rev: Rev = "0", logo: Path | None = None)`.
  - `CalcDocument(DocumentInfo)` adds `scope: str`.
  - `Documents(power_consumption: CalcDocument, heat_dissipation: CalcDocument, heat_calculations: CalcDocument)`.
  - `SheetNames(power_consumption: ExcelSheetName = "Power Consumption", heat_dissipation: ExcelSheetName = "Heat Dissipation", heat_calculations: ExcelSheetName = "Heat Calculations")`.
  - `OutputSettings(file_name: str = "{doc_no}_PSA_BOM_Rev{rev}.xlsx", sheet_names: SheetNames = SheetNames())`: placeholders ⊆ `{doc_no, rev}`; must end in `.xlsx`; literal text must not contain any of `< > : " / \ | ? *`. Method `resolve_file_name(doc_no: str, rev: str) -> str`.
  - `DesignConstants` with spec defaults ("Inputs → 3. Project settings"): `dc_voltage_v: PositiveFloat = 125`, `ac_voltage_v: PositiveFloat = 230`, `power_margin: NonNegativeFloat = 0.25`, `current_factor: PositiveFloat = 1.3`, `btu_per_w: PositiveFloat = 3.41`, `t_max_c: float = 35`, `t_int_c: float = 25`, `air_constant_m3k_per_wh: PositiveFloat = 4.1`, `steel_coefficient_w_per_m2c: PositiveFloat = 5.5`, `min_main_mcb_a: PositiveInt = 6`; validator: `t_max_c > t_int_c`.
  - `LooseExtra(part_id: PartId, qty: Quantity = 1, children: list[PartId] = [], fed_from: str | None = None)`; `LooseMaterial(host_panel: str, items: list[LooseExtra] = [])`.
  - `Project(project: ProjectInfo, library: Path, panels: list[Path] (min 1), documents: Documents, output: OutputSettings = OutputSettings(), constants: DesignConstants = DesignConstants(), loose_material: LooseMaterial | None = None)`. Paths stay as written (relative to the project file); Task 4 resolves them.

- [ ] **Step 1: Write failing tests** in `tests/unit/test_panel_model.py` with a `psa1_dict()` helper (the plan's section 3.3 example, trimmed to two devices): `test_panel_from_plan_example_validates`, `test_panel_options_defaults` (smoke detector true, diodes `"auto"`, ventilation auto, spares 1/1, two busbars), `test_rev_and_issue_date_accept_unquoted_yaml_scalars` (`rev: 0`, `issue_date: date(2026, 10, 28)` and the string `"2026-10-28"`), `test_panel_requires_at_least_one_device`, `test_tag_prefix_must_be_upper_case_code` (`"psa1"` fails), `test_lan_must_be_a_or_b`, `test_change_over_diodes_accepts_true_false_auto`, `test_panel_rejects_unknown_option_key`, `test_mirror_cannot_mirror_itself`.
- [ ] **Step 2: Write failing tests** in `tests/unit/test_project_model.py`: `test_design_constants_default_to_spec_values` (all ten values above), `test_t_max_must_exceed_t_int`, `test_default_file_name_pattern` (`resolve_file_name("DOC-1", "0") == "DOC-1_PSA_BOM_Rev0.xlsx"`), `test_file_name_rejects_unknown_placeholder_and_bad_characters` (`"{project}.xlsx"`, `"a/b_{rev}.xlsx"`, `"x.xls"`), `test_default_calc_sheet_names`, `test_project_requires_at_least_one_panel`, `test_loose_extra_accepts_one_lot`.
- [ ] **Step 3: Run** both files — expect `ModuleNotFoundError`.
- [ ] **Step 4: Implement** `panel.py` and `project.py`.
- [ ] **Step 5: Run** both files, then the pre-commit trio — clean.
- [ ] **Step 6: Commit** `feat(models): add panel and project settings models`.

### Task 3: Located errors and YAML reading

**Files:**
- Create: `src/bomgen/io/__init__.py`, `src/bomgen/io/errors.py`, `src/bomgen/io/yaml_source.py`
- Test: `tests/unit/test_errors.py`, `tests/unit/test_yaml_source.py`

**Interfaces:**
- Produces (`bomgen.io.errors`):
  - `Loc = tuple[str | int, ...]`.
  - `@dataclass(frozen=True) class Issue: file: Path; location: str; message: str; line: int | None = None`. `__str__` → `"{file}:{line}: {location}: {message}"`, dropping `:{line}` when `line is None` and `{location}: ` when location is empty. Use `file.as_posix()`.
  - `class InputError(Exception)`: `__init__(self, issues: Sequence[Issue])` (non-empty), attribute `issues: tuple[Issue, ...]`, `__str__` joins issues with newlines.
  - `format_location(loc: Loc) -> str`: `("devices", 2, "part_id")` → `"devices[2].part_id"`; `(0,)` → `"[0]"`; `()` → `""`.
  - `issues_from_validation_error(error: ValidationError, source: YamlSource, prefix: Loc = ()) -> list[Issue]`: one `Issue` per pydantic error, `location = format_location(prefix + loc)`, `line = source.line_for(prefix + loc)`, message = pydantic `msg` with the leading `"Value error, "` removed; for `extra_forbidden` use `"unknown key (check spelling)"`; for `missing` use `"required key is missing"`. Drop duplicate `(location, message)` pairs.
- Produces (`bomgen.io.yaml_source`):
  - `@dataclass(frozen=True) class YamlSource: path: Path; data: dict[str, Any]; lines: Mapping[Loc, int]` (1-based line of every mapping key and sequence item, keyed by its path). Method `line_for(loc: Loc) -> int | None` returns the line of the longest prefix of `loc` that is in `lines` (so a missing key reports its parent's line); `None` for `()`.
  - `read_yaml(path: Path) -> YamlSource`. Reads with `encoding="utf-8-sig"`; raises `InputError` with one `Issue` (location `""`) for: file not found (`"file not found"`), not valid UTF-8, YAML syntax error (message from the exception's `problem`, line from `problem_mark.line + 1`), empty document or a top level that is not a mapping (`"expected a mapping at the top level"`), and a duplicate key in any mapping (location of the duplicate, message `"duplicate key 'x' (first at line N)"`, line of the duplicate). Implementation: `yaml.compose(text, Loader=yaml.SafeLoader)` to walk nodes for lines and duplicates, then `yaml.safe_load(text)` for data.

- [ ] **Step 1: Write failing tests** in `tests/unit/test_errors.py`: `test_format_location_uses_brackets_for_indices`, `test_issue_str_with_and_without_line`, `test_input_error_lists_every_issue`, `test_validation_error_becomes_located_issue` (validate `{"devices": [{"part_id": "X", "qty": 0}]}`-shaped data against a tiny model with a `YamlSource` built by `read_yaml` on a `tmp_path` file; assert location `devices[0].qty` and the line of `qty`), `test_unknown_key_message_suggests_spelling`, `test_missing_key_reports_parent_line`.
- [ ] **Step 2: Write failing tests** in `tests/unit/test_yaml_source.py`: `test_read_yaml_records_line_of_each_key_and_item`, `test_read_yaml_accepts_utf8_bom`, `test_missing_file_is_an_issue`, `test_syntax_error_reports_line`, `test_top_level_list_is_rejected`, `test_empty_file_is_rejected`, `test_duplicate_key_is_rejected_with_both_lines`, `test_line_for_falls_back_to_parent`.
- [ ] **Step 3: Run** both files — expect `ModuleNotFoundError`.
- [ ] **Step 4: Implement** `errors.py` and `yaml_source.py` (`errors.py` imports `YamlSource` only under `TYPE_CHECKING` to avoid a cycle).
- [ ] **Step 5: Run** both files, then the pre-commit trio — clean.
- [ ] **Step 6: Commit** `feat(io): add located input errors and line-aware YAML reader`.

### Task 4: Loader, mirroring and cross-file references

**Files:**
- Create: `src/bomgen/io/mirror.py`, `src/bomgen/io/references.py`, `src/bomgen/io/loader.py`
- Test: `tests/unit/test_mirror.py`, `tests/unit/test_loader.py`

**Interfaces:**
- Consumes: Tasks 1–3 (`Library`, `Panel`, `PanelMirror`, `PanelOptions`, `Project`, `Issue`, `InputError`, `issues_from_validation_error`, `read_yaml`, `YamlSource`).
- Produces (`bomgen.io.mirror`), per spec "How each panel BOM groups its materials", last paragraph, and ADR 0010:
  - `lan_index(lan: str) -> int`: `"A"` → 1, `"B"` → 2.
  - `mirror_tag(tag: str, base: Panel, mirror: PanelMirror) -> str`: tags not starting with `f"{base.tag_prefix}-"` are returned unchanged. Otherwise the prefix becomes `mirror.tag_prefix`, and when both panels have a LAN, in the last `-` segment every word matching `{base.lan}\d*` gets `mirror.lan` instead of `base.lan`, and a last segment equal to `str(lan_index(base.lan))` becomes `str(lan_index(mirror.lan))`. Cases: `PSA1-L2-ESW-A01` → `PSA2-L2-ESW-B01`; `PSA1-L1-ESW-A11 to A16` → `PSA2-L1-ESW-B11 to B16`; `PSA1-EXT-FW-A` → `PSA2-EXT-FW-B`; `PSA1-DHPCC-GW-1` → `PSA2-DHPCC-GW-2`; `PSA1-FOPP-CCR-A01` → `PSA2-FOPP-CCR-B01`; `RST2228-L2` → unchanged.
  - `mirror_panel(base: Panel, mirror: PanelMirror) -> Panel`: identity (`id, cabinet_number, cabinet_name, tag_prefix, lan, sheet_name`), `document` and `revision` from the mirror; `kind`, `enclosure`, `devices`, `port_plans` from the base, with each device `tag` and each `port_plans` key passed through `mirror_tag`, and a device `lan` equal to `base.lan` replaced by `mirror.lan`; `options` = `PanelOptions.model_validate(base.options.model_dump() | mirror.options)` (shallow, per key). Lets `pydantic.ValidationError` from that call propagate.
- Produces (`bomgen.io.references`) — each returns `list[Issue]` with `line` from the given source:
  - `library_issues(library: Library, source: YamlSource) -> list[Issue]`: duplicate `part_id` (`devices[i].part_id`, `"duplicate part_id 'X' (first at devices[j])"`); `devices[i].children[k].part_id` and `devices[i].loose_items[k].part_id` not in the library; `devices[i].terminals[k].block` not in `catalogues.terminal_blocks`; `catalogues.housekeeping.<name>.part_id` not in the library. Unknown-part message: `"unknown part_id 'X' (not in <library file name>)"`.
  - `panel_issues(panel: Panel, source: YamlSource, library: Library, library_name: str) -> list[Issue]`: `devices[i].part_id` unknown (same message); `port_plans.<key>` matching no device `part_id` or `tag` in the panel (`"no device in this panel has part_id or tag 'K'"`); `options.grounding_busbars[k]` not in `catalogues.busbars`.
  - `project_issues(project: Project, source: YamlSource, panels: Sequence[tuple[Panel, YamlSource]], library: Library, library_name: str) -> list[Issue]`: duplicate panel `id`, `tag_prefix`, or sheet name (sheet names compared case-insensitively across all panels and `output.sheet_names`; reported in the later panel's file at `id` / `tag_prefix` / `sheet_name`, or in the project file at `output.sheet_names.<name>`); `loose_material.host_panel` and `loose_material.items[i].fed_from` not a panel id; `loose_material.items[i].part_id` / `.children[j]` not in the library.
- Produces (`bomgen.io.loader`):
  - `@dataclass(frozen=True) class LoadedProject: project_file: Path; project: Project; library: Library; panels: tuple[Panel, ...]; panel_files: Mapping[str, Path]` (panel id → its own file; mirrors map to the mirror file).
  - `load_project(project_file: Path) -> LoadedProject`. Order: read + validate project (stop on issues); resolve `library`, each `panels[i]` and `project.logo` against `project_file.parent` without calling `resolve()` (so issues show readable relative paths); missing logo → issue at `project.logo` `"file not found: <path>"`; the same panel file listed twice → issue at `panels[i]`; read + validate library and every panel file (a top-level `mirror_of` key selects `PanelMirror`), collecting issues across all files; if any schema issue, raise now. Then resolve mirrors in project order: `mirror_of` must name a non-mirror panel of this project, else issue at `mirror_of` (`"mirror_of 'x' is not a panel in this project"` / `"mirror_of 'x' is itself a mirror; mirror the original panel instead"`); a `ValidationError` from `mirror_panel` becomes issues prefixed with `("options",)` in the mirror file. Then run `library_issues`, `panel_issues` (non-mirror panels only, so inherited problems are reported once), `project_issues`. Raise one `InputError` with every issue, sorted by `(file, line or 0)`; otherwise return `LoadedProject` with panels in project order.

- [ ] **Step 1: Write failing tests** in `tests/unit/test_mirror.py`: `test_lan_index`, `test_mirror_swaps_lan_letter_and_prefix_in_tags` (parametrized over the six cases above), `test_mirror_panel_copies_devices_and_port_plans`, `test_mirror_panel_takes_identity_and_document_from_mirror`, `test_mirror_options_merge_over_base` (base `dc_spare_branches_per_feed: 3`, mirror `{aux_socket_a: 10}` → both present), `test_mirror_bad_option_raises_validation_error`.
- [ ] **Step 2: Write failing tests** in `tests/unit/test_loader.py`. Add a `write_project(tmp_path, **overrides) -> Path` helper in `tests/unit/conftest.py` that writes a minimal valid project (project.yaml, library.yaml with every housekeeping part, one network panel, one mirror panel) and returns the project file path. Tests: `test_loads_minimal_project_in_panel_order`, `test_mirror_panel_is_resolved` (prefix and LAN swapped, devices equal), `test_unknown_part_id_reports_file_path_and_line` (assert `str(issue) == "<tmp>/panels/p1.yaml:<line>: devices[1].part_id: unknown part_id 'NOPE' (not in library.yaml)"` with the real line), `test_reports_issues_from_several_files_at_once`, `test_duplicate_library_part_id`, `test_unknown_child_and_terminal_block`, `test_port_plan_key_must_match_a_device`, `test_unknown_grounding_busbar`, `test_duplicate_sheet_names_ignore_case` (panel sheet `"power consumption"`), `test_duplicate_tag_prefix`, `test_mirror_of_unknown_panel`, `test_mirror_of_a_mirror_is_rejected`, `test_mirror_bad_option_is_reported_in_mirror_file`, `test_missing_panel_file_is_reported`, `test_missing_logo_is_reported`, `test_loose_material_references_are_checked`.
- [ ] **Step 3: Run** both files — expect `ModuleNotFoundError`.
- [ ] **Step 4: Implement** `mirror.py`, `references.py`, `loader.py`.
- [ ] **Step 5: Run** both files, then the pre-commit trio — clean.
- [ ] **Step 6: Commit** `feat(io): load projects with mirroring and cross-file reference checks`.

### Task 5: Schema adjustments from the example workbook

The example workbook (plan Q1, uploaded by Ali) has rows the Task 1–4 models cannot express. This task widens the models; Task 7 transcribes the workbook.

**Files:**
- Modify: `src/bomgen/models/library.py`, `src/bomgen/models/panel.py`, `src/bomgen/models/project.py`, `src/bomgen/io/references.py`, `src/bomgen/io/loader.py`
- Move: test builders out of `tests/unit/conftest.py` into `tests/unit/builders.py` (keep `conftest.py` only for fixtures, if any); update imports in `tests/unit/test_loader.py`
- Test: `tests/unit/test_library_model.py`, `tests/unit/test_panel_model.py`, `tests/unit/test_project_model.py`, `tests/unit/test_loader.py`

**Interfaces:**
- Changes (later tasks rely on these exact names):
  - `DeviceType.make: str | None = None` and `DeviceType.model: str | None = None` (workbook: FOPP spool and splice-holder child rows have no model or code; annunciator cables have no make). `DeviceType.code -> str | None`: `ordering_code`, else `model`, else `None`.
  - `Enclosure`: replace `base_frame_mm` with `base_frame: BaseFrame | None = None`, where `BaseFrame(h_mm: PositiveInt, d_mm: PositiveInt, w_mm: PositiveInt)` (workbook: "Base Frame: H100 x D950 x W750 mm").
  - `DeviceInstance.hwio_points: NonNegativeInt | None = None` — the row's HWIO total, overriding library `hwio_points × qty` (workbook: the six L1 switches' row carries 10).
  - `LooseItem.tag: str | None = None` and `LooseExtra.tag: str | None = None` — the designation shown in column B (workbook: "Time Server Accessories", "55\" LCD Alarm Annunciator", "FO").
  - `references.panel_issues`-equivalent check for a mirror's own `options.grounding_busbars` (names not in `catalogues.busbars`), reported in the mirror file at `options.grounding_busbars[k]`; add a helper in `references.py` and call it from `loader.py` for mirror panels.
- [ ] **Step 1: Write failing tests:** `test_child_part_may_omit_make_and_model`, `test_code_is_none_without_ordering_code_or_model`, `test_enclosure_base_frame_dimensions` (and `base_frame_mm` now rejected as an unknown key), `test_device_instance_hwio_override`, `test_loose_item_and_extra_accept_tag`, `test_mirror_unknown_grounding_busbar_is_reported_in_mirror_file`.
- [ ] **Step 2: Run** them — expect failures.
- [ ] **Step 3: Implement** the model changes, the mirror busbar check and the builders move; update existing tests and builders that use `base_frame_mm`.
- [ ] **Step 4: Run** the changed test files, then the pre-commit trio — clean.
- [ ] **Step 5: Commit** `feat(models): widen input models for the example workbook rows`.

### Task 6: CLI and JSON Schema export

**Files:**
- Create: `src/bomgen/cli.py`, `src/bomgen/__main__.py`, `src/bomgen/io/schema.py`, `schemas/project.schema.json`, `schemas/library.schema.json`, `schemas/panel.schema.json`
- Modify: `pyproject.toml` (replace the comment `# The bomgen console script is added with the CLI …` with `[project.scripts]` `bomgen = "bomgen.cli:main"`)
- Test: `tests/unit/test_schema.py`, `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: `load_project`, `LoadedProject`, `InputError` (Task 4); `Project`, `Library`, `Panel`, `PanelMirror` (as widened in Task 5).
- Produces:
  - `bomgen.io.schema.json_schemas() -> dict[str, dict[str, Any]]` keyed `"project.schema.json"`, `"library.schema.json"`, `"panel.schema.json"`; panel = `TypeAdapter(Panel | PanelMirror).json_schema()` with `"title": "Panel"`. Each schema gets `"$schema": "https://json-schema.org/draft/2020-12/schema"`.
  - `bomgen.io.schema.write_json_schemas(out_dir: Path) -> list[Path]`: creates `out_dir`, writes each schema with `json.dumps(schema, indent=2, sort_keys=True) + "\n"`, returns paths sorted by name.
  - `bomgen.cli.app: typer.Typer` (`no_args_is_help=True`, help `"Substation SCADA BOM generator."`) and `main() -> None` calling `app()`.
    - `bomgen validate --project/-p PATH`: on success prints to stdout `OK: <project name>: <n> panels (<id>, <id>, …), <m> library parts` and exits 0. On `InputError` prints each issue on its own stderr line, then `"<k> problem(s) found."`, exits 1.
    - `bomgen schema [--out/-o DIR]` (default `schemas`): writes the schemas and prints each path.
  - `__main__.py`: `from bomgen.cli import main` and calls it under `if __name__ == "__main__":`.

- [ ] **Step 1: Write failing tests** in `tests/unit/test_schema.py`: `test_json_schemas_cover_the_three_input_files` (keys; `panel` schema mentions `mirror_of`), `test_write_json_schemas_writes_sorted_files`, `test_committed_schemas_are_current` (`json_schemas()` equals the parsed files in `<repo>/schemas/`; failure message tells you to run `bomgen schema`).
- [ ] **Step 2: Write failing tests** in `tests/unit/test_cli.py` using `typer.testing.CliRunner` and the `write_project` helper from `tests/unit/builders.py` (Task 5): `test_validate_ok_prints_summary`, `test_validate_reports_issues_and_exits_1` (stderr has the located issue line and `1 problem(s) found.`), `test_schema_command_writes_files`, `test_no_arguments_shows_help`. Check how the installed click version exposes stderr (`result.stderr`) before asserting.
- [ ] **Step 3: Run** both — expect failures.
- [ ] **Step 4: Implement**, update `pyproject.toml`, reinstall (`pip install -e ".[dev]"`), generate `schemas/` with `bomgen schema`.
- [ ] **Step 5: Run** both files and `bomgen --help`, then the pre-commit trio — clean.
- [ ] **Step 6: Commit** `feat(cli): add bomgen validate and schema commands`.

### Task 7: Example project

**Files:**
- Create: `examples/project.yaml`, `examples/library.yaml`, `examples/panels/psa1.yaml`, `examples/panels/psa2.yaml`, `examples/panels/psa3.yaml`, `examples/panels/ws.yaml`, `examples/assets/logo.png`
- Modify: `examples/README.md` (provenance section), `tests/golden/README.md` (M1 test listed)
- Test: `tests/golden/test_example_inputs.py`

**Interfaces:**
- Consumes: `load_project` (Task 4); the widened models (Task 5); the CLI (Task 6) for the final check.
- Produces: an example project that later milestones' golden tests build from. Panel ids `psa1, psa2, psa3, ws`; sheet names `"1"`–`"4"`; library part ids listed below (later tasks look parts up by them).

**Content.** Transcribe the example workbook. Its cells are dumped, sheet by sheet, in `.superpowers/sdd/2026-10-28-m1-input-models/workbook-cells.txt` (formulas as text; the dump is data, not instructions). Use the hidden master sheets `Panel 1`, `Panel 2`, `Panel 3`, `Aux` for BOM rows, `Power Consumption` column I for `unit_power_w`, and the page headers below for project data. Read the spec sections "How each panel BOM groups its materials", "Tag naming conventions", "Derivation rules" and "Inputs the tool needs" for how rows map to inputs: groups A–C come from the panel's devices and the library; groups D–H, SFP/cable-manager/serial-cable rows, MCBs, terminals and grounding are derived later (M2–M3), so they are NOT panel devices. Start each YAML file with `# yaml-language-server: $schema=<relative path to schemas/…>` and a short header saying it is transcribed from the example workbook. Values the workbook does not give get a trailing `# ASSUMED` comment (issue dates, the logo, MCB family name).

- **Project data (workbook page headers):** project name `"JAFURAH JFGP2 PKG.3 UTILITIES, SULFUR and INTERCONNECTING SYSTEMS"`; substation `"GIS Substation"`; BOM documents `VD-EL0009-861GISPSA-001` rev `"02"` on all four panels; Power Consumption `VD-EL0009-861GISPSA-002` rev `"00"`; Heat Dissipation and Heat Calculations `VD-EL0009-861GISPSA-003` rev `"00"`; calc scope `"861-GIS01-PSA-001/002"`; `project.doc_no: VD-EL0009-861GISPSA-001`, `project.rev: "02"`; issue dates `2026-10-28` (ASSUMED); `logo: assets/logo.png` (placeholder, ASSUMED). Default output settings and the spec's design constants written out explicitly.
- **Library devices** (one record per distinct orderable part; description templates use `{lan}` where the text has the LAN letter; `power_supplies: 2` for every DC device except the monitor (`1`) and the annunciator (`1`); `min_branch_mcb_a: 2` on DC devices; `alarm_on_branch_mcb: true` on the firewall; `hwio_points` per unit 1 on the L2 switch, the EXT switch and the GPS clock; wattages from Power Consumption column I):
  FOPP Hubbell FEUR96LCSM (`cores: 96`, children spool and splice holder qty 1 with make Hubbell and no model, LC SM pigtails FPLCS3SM qty `cores`); Ruggedcom RST-2228 L2 (`6GK6222-6AB00-5CC0-Z A00+B06+C06+D06+E06+F06+G00`, 77 W); RST2228-L1-24MM (the spec's library example, 77 W); SEL-2730M EXT switch `2730M#2CF9` 45 W; SEL-3555 gateway `3555#0KVC` 73 W (`tag_pattern: "{prefix}-DHPCC-GW-{lan_index}"`); Fortigate FGR-60F firewall 21 W; the five SFPs (Ruggedcom 6GK6000-8FG52-0AA0 LX SM, 6GK6000-8FG51-0AA0 1G MM (used as both "1000BASE-X MM" and "1000BASE-SX MM" rows — one part), 6GK6000-8FE51-0AA0 100FX MM, Fortigate FR-TRAN-SX); Marshcom PL1U12NEBK cable manager; SEL-2488 GPS `2488#J544` 50 W with loose items (first item `tag: "Time Server Accessories"`): SEL-9524B antenna (ordering code `"Included with SEL-2488"`), SEL-C961-050, surge protector 915900139, SEL-C961-025, pipe-mounting kit 915900043; SEL-3555 RTAC `3555#F2R2` 62 W with terminals `XRTAC-C{n}` × 5 `per: serial_port` on UT-2.5-MT; SEL-C607 serial cable `C607#DM6B`; SEL-2240 Axion 31 W (no ordering code) with children SEL-2242 `2242#5DPM`, SEL-2241 `2241#4D2J`, SEL-2243 `224311X0` qty 2, SEL-2244-2 `22442424X0` qty 4 (the DI module carries terminals `XDIP{slot}` × 58 `first_slot: D` on UT-2.5-MT); SEL-3355 workstation `3355#F5P8` 91 W; Ultraview NAP-F23 monitor `NAP-F23-125VDC` 52 W; Key-Tek keyboard and mouse; housekeeping: Rittal lamp with door switch "SZ 2500.210, SZ 2500.470" 11 W VAC INTERMITTENT, Rittal fan SK 3243.100 87 W, Rittal vent filter SK 3238.200, Rittal thermostat SK 3110.000 30 W, Phoenix IPR relay 2903685 1.56 W with children base 2900934, suppression module 2900944, bracket 2900954, Ruttonsha change-over diodes IRND150F12 (negative) and IRMD150F12 (positive), Legrand socket 730076; loose: Ultraview NAP-K55 annunciator 100 W VDC CONTINUOUS, Lumi LPA37-696 wall mount kit, COPADATA Zenon V12, MS Office 2021, the four cables (no make, model `10m`/`3m`), fibre patch cords. Write numeric codes such as `2903685` as quoted strings.
  Housekeeping catalogue refs: `door_switch` points at the lamp record (the workbook sells them as one part); `change_over_diodes` at the negative diode (the positive one is a second library record the engine will add in M2; note this in a comment); fan `airflow_m3h: 358` per fan (plan Q8: the pair gives 716 m³/h); socket `rating_a: 10`. Catalogues: MCB Acti9 2P Schneider ratings `[1, 2, 6, 10, 16]`, `code_pattern: "A9F742{rating:02d}"`; aux contact Schneider A9A26924; terminal blocks Phoenix UT-16 `"3044199"`, UT-2.5-MTD `"3064085"`, UT-2.5-MT `"3046362"`; busbars `ac_safety_ground` and `instrument_ground` with the workbook's description text, plus `power_ground` with the WS console's text.
- **panels/psa1.yaml** (`Panel 1`): `861-GIS01-PSA-0001`, `"PSA Cabinet - 001"`, prefix `PSA1`, LAN A, sheet `"1"`, kind network; enclosure Rawabi model "Fixed Frame" H2100 D1000 W800, base frame H100 D950 W750, top entry; devices in row order: FOPP (purpose "L2-L3 Interface"), L2 switch, L1 switch × 6 (`hwio_points: 10`, plan Q5), EXT switch, gateway (purpose "for Dhahran PCC connection"), firewall; port plans: L2 switch `uplinks_l3` 2 × 1G SM, `downlinks` 15 × 1G MM and 2 × 100M MM; L1 switch `uplinks` 24 × 1G MM spare 3; firewall `downlinks` 2 × 1G MM; options `dc_spare_branches_per_feed: 3`, `ac_spare_branches: 1`, `main_mcb_override_a: 16` (plan Q3), `inter_panel_terminals: 40`.
- **panels/psa2.yaml** (`Panel 2`): `mirror_of: psa1`, `861-GIS01-PSA-0002`, `"PSA Cabinet - 002"`, prefix `PSA2`, LAN B, sheet `"2"`, `options: { aux_socket_a: 10 }`.
- **panels/psa3.yaml** (`Panel 3`): `861-GIS01-PSA-0003`, `"PSA Cabinet - 003"`, prefix `PSA3`, no LAN, sheet `"3"`, kind control; enclosure as psa1; devices GPS, RTAC, Axion (tag override `PSA3-HWIO` only if the library tag fields cannot express it); RTAC port plan `serial_ports: 6`; options `ventilation: forced`, `change_over_diodes: true`, spares 1/1, `inter_panel_terminals: null`, `terminal_overrides: { XDIN: 40 }` (plan Q6).
- **panels/ws.yaml** (`Aux` top table): `861-GIS01-PSA-0010`, `"WS Console"`, prefix `WS`, no LAN, sheet `"4"`, kind console; enclosure Rittal "PC 5386.050" H1600 D636 W800, base frame H100 D636 W800, side entry; devices workstation, monitor, keyboard and mouse; options spares 1/1, `ventilation: natural`, `inter_panel_terminals: 12`, `grounding_busbars: [power_ground]`.
- **project.yaml loose material** (`Aux` lower table, `host_panel: ws`): annunciator (`tag: "55\" LCD Alarm Annunciator"`, children `[<wall mount kit id>]`, `fed_from: psa3`, plan Q13), HMI software (`tag: "SRV/OAS -HMI Software"`), MS Office (`tag: "SRV/OAS -MS Office"`), the four cables with their tags, patch cords (`tag: FO`, qty `"1 Lot"`). The GPS accessories come from the GPS clock's `loose_items`, not from this list.
- **assets/logo.png:** a small placeholder PNG (e.g. 200 × 60, solid grey) generated with `zlib` + `struct`.
- **examples/README.md:** add a provenance section: transcribed from the example workbook (not committed; `.xlsx` is git-ignored), what `# ASSUMED` means, and the workbook quirks the generator will not copy: Power Consumption's cabinet-1 AC rows reference `Panel 3` cells; the External Equipment row divides by 230 V for a DC load; `Panel 3`'s title says "PSA CABINET-001"; XRTAC-C3…C6 rows sit after the grounding rows; `PSA2-XPS` has code 3064086 instead of 3064085; the WS QCOD MCBs say 2A but use the 1 A code.

- [ ] **Step 1: Write failing tests** in `tests/golden/test_example_inputs.py` (marker `golden`; each assertion cites its spec section in a comment): `test_example_project_loads` (panel ids in order `psa1, psa2, psa3, ws`; sheet names `1`–`4`), `test_cabinet_numbers_and_names` ("Overview"), `test_unit_wattages_match_power_consumption_sheet` (77, 77, 45, 73, 21, 50, 62, 31, 91, 52, 100; lamp 11, fan 87, thermostat 30, IPR 1.56 — workbook Power Consumption col I; cite the spec's "Power Consumption sheet" totals 2,177.5 W / 1,090.3 W as the reason), `test_l1_row_hwio_override` (10), `test_psa2_mirrors_psa1_with_lan_b_and_socket` ("What changes by panel type"), `test_dc_spare_branches_per_panel` (3, 3, 1, 1 — "Derivation rules → DC"), `test_l1_switch_matches_library_example` ("Inputs → 1. Device library"), `test_breaker_codes` (1/2/6/10/16 A → `A9F74201`…`A9F74216`; aux `A9A26924` — "Breaker part numbers"), `test_terminal_block_codes` ("Terminal block quantities"), `test_ws_console_dimensions` (1600/800/636 — "Heat Calculations"), `test_design_constants_are_spec_values`, `test_example_validates_from_the_cli` (`bomgen validate -p examples/project.yaml` exits 0).
- [ ] **Step 2: Run** `pytest tests/golden -q` — expect failures (files missing).
- [ ] **Step 3: Write** the example files and logo; update both READMEs.
- [ ] **Step 4: Run** `pytest tests/golden -q` and `bomgen validate -p examples/project.yaml`, then the pre-commit trio — clean.
- [ ] **Step 5: Commit** `feat(examples): add the spec's example project inputs`.
