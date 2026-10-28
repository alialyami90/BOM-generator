# M1b: Projects, Substations and Sizing Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-system `project.yaml` with a project file that holds substations, each with its own substation file, panels and the inputs A8's sizing and layout engine needs.

**Architecture:** New pydantic models in `models/project.py` (rewritten) and `models/substation.py`. The loader resolves project → substations → panels and applies the project defaults key by key. Panels keep their schema except `document` (now a register key) and an optional `generated` flag. `bomgen validate` accepts either file. The example project gets one substation, and every M1 golden value stays the same.

**Tech Stack:** Python 3.12, pydantic v2, PyYAML (`io/yaml_source.py`), typer.

**Spec:** `docs/superpowers/specs/2026-10-28-substations-and-auto-layout-design.md` sections 2–3, ADR 0012, ADR 0013. Also `docs/spec/generator-spec-v2.md` → Inputs the tool needs.

## Global Constraints

- ADR 0010 conventions hold: `extra=forbid`, frozen models, located issues `file:line: path: message`, and every issue from every file collected before the run stops.
- Defaults (design 3.2): `port_fraction 0.20`, `sfp_per_l1 3`, `dc_branches_per_feed 3`, `ac_branches 1`, `rack_u_reserved 10`, `ring_max_switches 6`, `l1_uplinks_per_switch 1`, `l1_interlink true`, `l3_uplinks_per_l2 2`, `topology star`, `blank_plate_u 1`, catalogue `enclosure_u 42`.
- IEDs never appear in the BOM (R4). `ied_count` is only an input.
- No blank-plate part (Q25).
- Readings sent to A1 on 2026-10-28, items (a)–(i), are the decisions below.

## Review Focus

- A substation file opened on its own, with no `project.yaml` above it, should give one clear issue naming the file, not a traceback. Task 5 adds `test_substation_without_project_is_reported`.
- A project that lists a substation file the project folder doesn't hold, or lists it twice, should get a located issue. Task 5 adds `test_substation_listed_twice` and `test_missing_substation_file_is_reported`.
- A substation that overrides only `constants.t_int_c` above the project's `t_max_c` should fail the cross-field rule after the merge, not pass. Task 4 adds `test_merged_constants_recheck_t_max_above_t_int`.
- A panel whose `document` key belongs to another substation should be rejected. Task 5 adds `test_panel_document_key_of_other_substation`.
- `rack_u_reserved` greater than or equal to `enclosure_u` should be reported, not produce a capacity of 0 or less. Task 5 adds `test_rack_u_reserved_must_leave_capacity`.

---

### Task 1: Library additions

**Files:** Modify `src/bomgen/models/library.py`. Test in `tests/unit/test_library_model.py`.

**Interfaces:**
- Produces:
  - `DeviceType.height_u: NonNegativeInt | None = None`, where 0 means a DIN-rail part and None means not yet given.
  - `PortGroup.usable_for: PortUse = PortUse.ANY`, with `class PortUse(StrEnum): IED="ied"; UPLINK="uplink"; ANY="any"`.
  - `Catalogues.enclosure_u: PositiveInt = 42`.

- [ ] Tests:
  - `test_height_u_defaults_to_none_and_accepts_zero` (asserts None, then 0 and 2).
  - `test_height_u_rejects_negative`.
  - `test_port_group_usable_for_defaults_to_any_and_rejects_other` (`"ied"` passes, `"field"` raises).
  - `test_catalogue_enclosure_u_defaults_to_42`.
- [ ] Run them and see them fail. Implement. Run the full suite.
- [ ] Commit `feat(models): library height_u, port usable_for, enclosure_u`.

### Task 2: Panels reference a register key

**Files:** Modify `src/bomgen/models/panel.py`. Test in `tests/unit/test_panel_model.py`, update `tests/unit/builders.py`.

**Interfaces:**
- Produces:
  - `DocumentKey = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]*$")]` in `models/_base.py`.
  - `Panel.document: DocumentKey` and `PanelMirror.document: DocumentKey`.
  - `Panel.generated: bool = False` and `PanelMirror.generated: bool = False`.
  - `DocumentInfo` stays, because register entries use it (Task 3).

- [ ] Tests:
  - `test_panel_document_is_a_register_key` (`"psa1-bom"` passes; the old mapping raises).
  - `test_panel_generated_defaults_false`.
- [ ] Implement. The builders' `default_p1`/`default_p2` use `document: "p1-bom"` and `"p2-bom"`. Run the panel tests. The loader tests stay red until Task 5.
- [ ] Commit `feat(models): panels name a document register key`.

### Task 3: Project model

**Files:** Rewrite `src/bomgen/models/project.py`. Test in `tests/unit/test_project_model.py`.

**Interfaces:**
- Produces:
  - `ProjectInfo(id: PanelId, name: str, client: str | None = None, logo: Path | None = None)`.
  - `LibrarySelection(name: str, version: str, file: Path | None = None)`, where `version` must parse with `library_store.versions.Version.parse`.
  - `RegisterEntry(DocumentInfo)` adding `key: DocumentKey`, `substation: PanelId` and `title: str | None = None`.
  - `Spares(port_fraction: float in [0, 1) = 0.20, sfp_per_l1: NonNegativeInt = 3, dc_branches_per_feed: NonNegativeInt = 3, ac_branches: NonNegativeInt = 1, rack_u_reserved: NonNegativeInt = 10)`.
  - `Defaults(constants: DesignConstants = default, spares: Spares = default)`.
  - `Project(project: ProjectInfo, library: LibrarySelection, documents: list[RegisterEntry], defaults: Defaults = default, substations: list[Path] (min 1))`. Duplicate register keys raise at model level, with the message `duplicate document key '<key>'`.
  - `DesignConstants`, `OutputSettings`, `SheetNames`, `LooseExtra` and `LooseMaterial` stay unchanged here; Task 4 imports them.
  - `def merge_defaults[M: InputModel](base: M, override: M | None) -> M`: copy `base`, update only the fields in `override.model_fields_set`, and re-validate with `type(base).model_validate(...)` so cross-field rules run on the merged values.

- [ ] Tests:
  - `test_project_from_design_example_validates`.
  - `test_register_keys_must_be_unique`.
  - `test_library_version_must_be_semver` (`"1.0.0"` passes, `"one"` raises).
  - `test_spares_defaults_are_design_values` (asserts the five values above).
  - `test_port_fraction_must_be_below_one`.
  - `test_merge_defaults_overrides_only_written_keys` (base `t_max_c` 35, override `{dc_voltage_v: 110}` gives 110 and 35).
- [ ] Implement and run. Commit `feat(models): project file with document register and defaults`.

### Task 4: Substation model

**Files:** Create `src/bomgen/models/substation.py`. Test in `tests/unit/test_substation_model.py`.

**Interfaces:**
- Consumes: Task 3 types, `PartId`, `DocumentKey`, `PanelId`.
- Produces:
  - `SubstationInfo(id: PanelId, name: str)`.
  - `CalcSheet(document: DocumentKey, scope: str)`.
  - `Calculations(power_consumption: CalcSheet, heat_dissipation: CalcSheet, heat_calculations: CalcSheet)`.
  - `EquipmentRole(StrEnum)` with the values `l1_switch, l2_switch, ext_switch, firewall, fopp, other`.
  - `Side(StrEnum)` with the values `none, a, b`.
  - `Equipment(part_id, role, redundant: bool = False, side: Side = Side.NONE, l2_ports: NonNegativeInt = 0)`. Validator: `redundant` with a side other than `none` raises "a redundant device has one unit per side; leave side out".
  - `Topology(StrEnum)` with the values `star, ring`.
  - `Network(ied_count: NonNegativeInt = 0, topology = star, ring_max_switches: PositiveInt = 6, l1_uplinks_per_switch: PositiveInt = 1, l1_interlink: bool = True, l3_uplinks_per_l2: NonNegativeInt = 2)`.
  - `DeviceMove(device: str, panel: PositiveInt)` and `PairMove(pair: str, panel: tuple[PositiveInt, PositiveInt])`, where the two panels must differ.
  - `Layout(blank_plate_u: NonNegativeInt = 1, overrides: list[DeviceMove | PairMove] = [], removed: list[str] = [])`. `panel_capacity_u` is not a field.
  - `Substation(substation: SubstationInfo, document: DocumentKey, calculations: Calculations, panels: list[Path] = [], manual_panels: list[Path] = [], output = default, constants: DesignConstants | None = None, spares: Spares | None = None, loose_material: LooseMaterial | None = None, equipment: list[Equipment] = [], network: Network = default, layout: Layout = default)`.
  - Validators on `Substation`:
    - `panels` and `manual_panels` together hold at least one file.
    - No path appears in both lists.
    - When `equipment` is non-empty, it has exactly one `l1_switch` and one `l2_switch`, both `redundant`.

- [ ] Tests:
  - `test_substation_from_design_example_validates`.
  - `test_redundant_equipment_cannot_name_a_side`.
  - `test_equipment_needs_one_l1_and_one_l2_switch`.
  - `test_pair_move_needs_two_different_panels`.
  - `test_panel_file_cannot_be_both_generated_and_manual`.
  - `test_network_defaults_are_design_values`.
  - `test_panel_capacity_is_not_an_input` (`layout.panel_capacity_u` raises an extra-key error).
  - `test_merged_constants_recheck_t_max_above_t_int` (project `t_max_c` 35 with substation `t_int_c` 40 makes `merge_defaults` raise).
- [ ] Implement and run. Commit `feat(models): substation file with equipment, network, spares, layout`.

### Task 5: Loader and reference checks

**Files:**
- Rewrite `src/bomgen/io/loader.py`, and extend `src/bomgen/io/references.py`.
- Tests in `tests/unit/test_loader.py`. Rework `tests/unit/builders.py` to `write_project(tmp_path, *, library=None, project=None, substation=None, panels=None) -> Path`. It writes `project.yaml`, `library.yaml` and `substations/s1/substation.yaml` with `panels/p1.yaml` and `p2.yaml`, and returns the project file. Add a `default_substation()` builder.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces:
  - `LoadedSubstation`, a frozen dataclass with:
    - `file: Path`, `substation: Substation`, `project: Project`, `library: Library`.
    - `documents: Mapping[str, RegisterEntry]` (this substation's entries).
    - `constants: DesignConstants` and `spares: Spares` (merged).
    - `panels: tuple[Panel, ...]` (`panels` then `manual_panels`, mirrors resolved) and `panel_files: Mapping[str, Path]`.
    - `manual_panel_ids: frozenset[str]`.
    - A `panel_capacity_u -> int` property returning `library.catalogues.enclosure_u - spares.rack_u_reserved`.
  - `LoadedProject`, a frozen dataclass with `file: Path`, `project: Project`, `library: Library` and `substations: tuple[LoadedSubstation, ...]`.
  - `load_project(project_file: Path, *, store: LibraryStore | None = None) -> LoadedProject`.
  - `load_substation(substation_file: Path, *, store: LibraryStore | None = None) -> LoadedSubstation`. It finds the nearest `project.yaml` in a parent folder that lists this file, then loads that project and returns this substation.
  - `load_inputs(path: Path, *, store=None) -> LoadedProject | LoadedSubstation`. A file whose top-level mapping has `substations` is a project; otherwise it is a substation.
  - `load_library(library_file)` stays.
  - Library resolution: `project.library.file` is resolved against the project folder when it is given. Otherwise the library is `(store or LibraryStore(default_library_home())).library_file(name, version)`, and a `LibraryPackageError` becomes an issue at `library`.
- Checks:
  - Each check from M1 now runs per substation. `project_issues` becomes `substation_issues(substation, source, panels, library, library_name)`.
  - `project_issues` is new:
    - substation ids are unique;
    - a substation file listed twice is reported;
    - each register entry's `substation` is a listed id;
    - a listed substation with no register entries is not an error.
  - Each substation:
    - its `document` and each `calculations.*.document` is a key of this substation;
    - each panel's `document` is a key of this substation, reported in the panel file at `document`;
    - equipment `part_id`s are known;
    - equipment parts have `height_u` (message `height_u is needed for the panel layout`);
    - the `l1_switch`/`l2_switch` parts have category `network_switch`;
    - `rack_u_reserved < enclosure_u` holds.
  - The logo is checked against the project folder.

- [ ] Port every existing `test_loader.py` test to the new builders, keeping its assertions (locations and messages) and changing only paths and the panel `document` shape.
- [ ] New tests:
  - `test_load_project_returns_substations_with_merged_defaults` (project spares `sfp_per_l1: 4`, substation spares `port_fraction: 0.1` give 4 and 0.1).
  - `test_load_substation_finds_its_project`.
  - `test_substation_without_project_is_reported`.
  - `test_load_inputs_detects_file_kind`.
  - `test_substation_listed_twice`.
  - `test_missing_substation_file_is_reported`.
  - `test_duplicate_substation_id`.
  - `test_register_entry_names_unknown_substation`.
  - `test_panel_document_key_must_exist`.
  - `test_panel_document_key_of_other_substation`.
  - `test_calculation_document_key_must_exist`.
  - `test_equipment_part_needs_height_u`.
  - `test_equipment_unknown_part`.
  - `test_rack_u_reserved_must_leave_capacity`.
  - `test_library_from_store_by_name_and_version` (pack `default_library()` into a `LibraryStore` under `tmp_path` with `library_store.service.import_library`).
  - `test_library_not_installed_is_reported`.
  - `test_manual_panels_follow_generated_panels`.
- [ ] Implement, then run the full suite. Commit `feat(io): load projects and substations`.

### Task 6: CLI and schemas

**Files:**
- Modify `src/bomgen/cli.py` and `src/bomgen/io/schema.py`. Tests in `tests/unit/test_cli.py` and `tests/unit/test_schema.py`.
- Regenerate `schemas/`, which adds `substation.schema.json`.

**Interfaces:**
- Produces:
  - `bomgen validate [FILE] [-p/--project FILE]`: exactly one of the two, auto-detected by `load_inputs`. For a project, the output is `OK: <project name>: <n> substation(s); <id>: <k> panels (<ids>); <m> library parts`. For a substation, it is `OK: <project name> / <substation id>: <k> panels (<ids>), <m> library parts`.
  - `json_schemas()` adds `"substation.schema.json"`.

- [ ] Tests:
  - `test_validate_project_positional`.
  - `test_validate_substation_file`.
  - `test_validate_needs_exactly_one_file` (exits 2).
  - Keep `test_validate_accepts_short_option` and the version test.
  - `test_schema_writes_four_files`.
- [ ] Implement, run `bomgen schema`, and run the suite. Commit `feat(cli): validate a project or a substation`.

### Task 7: Example project with one substation

**Files:**
- Rewrite `examples/project.yaml`.
- Create `examples/substations/gis01/substation.yaml`.
- Move `examples/panels/*.yaml` to `examples/substations/gis01/panels/` with `git mv`.
- Modify `examples/library.yaml` and `examples/README.md`, and `tests/golden/test_example_inputs.py`.

- [ ] `project.yaml`:
  - `project: {id: jfgp2-pkg3, name: <today's>}` and `library: {name: psa-devices, version: 1.0.0, file: library.yaml}`.
  - The register holds `gis01-bom` (…-001 rev 02), `gis01-power` (…-002 rev 00) and `gis01-heat` (…-003 rev 00), all with `substation: gis01`.
  - `defaults` keeps today's constants.
  - `substations: [substations/gis01/substation.yaml]`.
- [ ] `substation.yaml`:
  - `substation: {id: gis01, name: GIS Substation}`, `document: gis01-bom`, and `calculations` with today's scopes.
  - `panels: [psa1, psa2, psa3]` and `manual_panels: [ws]`.
  - `output` and `loose_material` as today.
  - `equipment` from design 3.2, plus the gateway as `other, redundant`.
  - `network: {ied_count: 40, topology: star}`.
  - `spares` with the defaults written out, and `layout: {blank_plate_u: 1}`.
- [ ] Panels use `document: gis01-bom`, and the `$schema` comments point at `../../../../schemas/panel.schema.json`.
- [ ] Library: add `height_u` to each equipment part with a `# ASSUMED (A3 to confirm)` comment: switches 1, FOPP 1, firewall 1, gateway 1, GPS 1, RTAC 1, Axion 2, EXT switch 1. Add `catalogues.enclosure_u: 42`.
- [ ] Golden tests:
  - Load via `load_substation(EXAMPLES / "substations/gis01/substation.yaml")`. Every M1 value is unchanged.
  - Add `test_example_project_has_one_substation`.
  - Add `test_example_substation_layout_inputs`: 40 IEDs, star, capacity 32, sfp_per_l1 3.
  - The CLI test runs `validate examples/project.yaml`.
- [ ] Run the suite and `bomgen validate examples/project.yaml`. Commit `feat(examples): one project with the gis01 substation`.

### Task 8: Docs

**Files:** `docs/plan.md` (section 3 rewritten, plus the M1b section), `docs/decisions/0010-input-schema.md` (new "M1b additions" section), and the M1 follow-up commit (already on the branch).

- [ ] Plan section 3:
  - project file sketch, substation file sketch, panel delta, library delta;
  - the loader resolution rules (key-by-key defaults, register keys, `panels` vs `manual_panels`, library by name/version or file).
- [ ] ADR 0010: readings (a)–(i), stated as decisions.
- [ ] Run ruff, format, mypy and pytest. Commit `docs: plan section 3 and ADR 0010 for projects and substations`.
