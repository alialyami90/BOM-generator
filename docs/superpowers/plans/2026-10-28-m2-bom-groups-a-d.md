# M2 BOM Groups A–D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the loaded example project into BOM lines for groups A–D of every cabinet (enclosure, main equipment with kit children, network and IO accessories, housekeeping) plus the loose-material table.

**Architecture:** Pure functions in `bomgen.engine` over the M1 models (ADR 0005). Each group builder returns `BomItem`s (a line plus its child lines); `engine.pipeline.build()` flattens them into `PanelBom.lines` with absolute parent indices, which is the shape A10's sheet layer reads (`models/bom.py`). Ventilation comes from the panel option; `auto` is treated as forced until M4 adds the heat check.

**Tech Stack:** Python 3.12, pydantic v2 (frozen models), pytest.

**Spec:** `docs/spec/generator-spec-v2.md` → "How each panel BOM groups its materials", "Columns of a panel BOM", "Tag naming conventions", "Derivation rules → Network accessories (group C)" and "Housekeeping kit (group D)", "Data model and generation order" steps 1, 2, 3, 5. Plan M2 and section 5.

## Global Constraints

- Engine never imports XlsxWriter, openpyxl or `models/sheet.py`; it never writes files.
- Models are frozen pydantic (`ConfigDict(frozen=True, extra="forbid")`).
- Quantities: `int`, `"1 Lot"` or `QtySum(parts=(24, 3))` (rendered `=24+3` by the sheet layer).
- Tags: `<PANEL>-<LEVEL>-<TYPE>-<LAN><NN>`; L2 numbers from 01, L1 from 11, EXT is the LAN letter only; a multi-unit row is one range tag `PSA1-L1-ESW-A11 to A16`; FAN/TH number their units `PSA1-FAN-1,2`, `WS-TH-1`; a library `tag_pattern` or panel `tag` wins.
- SFP rows are tagged by host switch without the panel prefix: `L2-ESW-A01 SFP (SM)`.
- Group D: lamp (+ door switch), 2 fans + 3 thermostats (forced) or 2 vent filters + 1 thermostat (natural), IPR kit with children, COD-1/COD-2 when change-over diodes apply, socket when `aux_socket_a` is set.
- Workbook text the generator deliberately does not copy (one library record, one description; tags trimmed) is listed in `tests/golden/expected_groups_a_d.py` next to the value.

## Review Focus

1. A port-plan allocation with no matching SFP in the library → `EngineError` naming the host tag, speed and media.
2. Two SFP records match one allocation → the host's make wins, else library order.
3. `aux_socket_a` that differs from the catalogue socket rating → `EngineError`.
4. A `cores` child of a parent with qty 2 → pigtails = cores × 2.
5. Mirrored panel 002 produces LAN-B tags and the same quantities as 001.

---

### Task 1: BOM models

**Files:** Create `src/bomgen/models/bom.py`; Test `tests/unit/engine/test_engine_bom_model.py`.

**Produces:** `Group(StrEnum)` A–H; `QtySum(parts: tuple[PositiveInt, ...])` with `value -> int`; `Qty = int | Literal["1 Lot"] | QtySum`; `BomLine(group, tag, description, qty, make, model, ordering_code, hwio=0, part_id=None, parent=None, merge_fg=False, revised=frozenset())`; `BomTable(title: tuple[str, str], lines)` with `separators_before() -> tuple[int, ...]` (first line of each of groups E–H present); `PanelBom(BomTable)` + `panel_id`, `sheet_name`; `LooseTable(BomTable)` + `host_panel`; `BuildResult(panels, loose)`.

- [ ] Tests: `test_qty_sum_value_is_sum_of_parts`, `test_qty_sum_needs_two_parts`, `test_separator_before_groups_e_to_h_only`, `test_bom_line_is_frozen`.
- [ ] Fail → implement → pass → commit `feat(engine): add BOM line models`.

### Task 2: Tags and device rows (step 1)

**Files:** Create `src/bomgen/engine/{__init__.py,errors.py,tags.py,units.py}`; Test `tests/unit/engine/test_engine_tags.py`.

**Produces:** `EngineError(Exception)`; `tags.unit_tags(device, panel, qty, start, lan, override) -> tuple[str | None, ...]`; `tags.row_tag(units) -> str | None` (range/list form); `tags.without_prefix(tag, prefix) -> str`; `units.DeviceRow(device, instance, tag, unit_tags, lan)`; `units.expand_devices(panel, library, instances) -> tuple[DeviceRow, ...]` (numbering counters per (tag_type, level) across rows); `units.describe(device, lan, purpose) -> str`.

- [ ] Tests named after the rules: `test_l2_switch_is_lan_letter_plus_01`, `test_l1_switches_number_from_11_as_one_range_row`, `test_ext_switch_and_firewall_take_lan_letter_only`, `test_fopp_tag_pattern`, `test_gateway_numbers_by_lan_index`, `test_lan_b_swaps_letter_and_prefix`, `test_fans_and_thermostats_number_units`, `test_panel_tag_override_wins`, `test_part_without_tag_type_has_no_tag`, `test_description_fills_lan_level_purpose`.
- [ ] Fail → implement → pass → commit `feat(engine): build device tags and rows`.

### Task 3: Group A and B with kit children (steps 1–2)

**Files:** Create `src/bomgen/engine/{items.py,enclosure.py,kits.py}`; Test `tests/unit/engine/test_engine_kits.py`.

**Produces:** `items.BomItem(line, children=())`, `items.flatten(items) -> tuple[BomLine, ...]`; `enclosure.enclosure_item(panel) -> BomItem` (tag `PANEL`, description `Cabinet : H… x D… x W… mm` / `Base Frame: …` / `Cable Entry: Top Entry|Side Entry`); `kits.device_item(row, library, group) -> BomItem` (children: qty × parent qty, `cores` × parent qty; `merge_fg` on parents with children; hwio = instance override or `hwio_points × qty`); `kits.main_equipment(rows, library) -> list[BomItem]`.

- [ ] Tests: `test_enclosure_row_states_size_base_frame_and_entry`, `test_children_follow_parent_with_blank_designation`, `test_pigtails_equal_cores_times_parent_qty`, `test_row_hwio_override_wins_over_library`, `test_flatten_sets_absolute_parent_indices`.
- [ ] Fail → implement → pass → commit `feat(engine): groups A and B with kit children`.

### Task 4: Group C network accessories (step 3)

**Files:** Create `src/bomgen/engine/network.py`; Test `tests/unit/engine/test_engine_network.py`.

**Produces:** `network.accessories(panel, rows, library) -> list[BomItem]`: SFPs per host in group B order (allocations `uplinks_l3`, `uplinks`, `downlinks`; RJ45 skipped; same part on one host combined), then cable managers (Σ units of `network_switch` + `patch_panel`), then serial cables (Σ `serial_ports`).

- [ ] Tests: `test_l2_switch_gets_sm_sfps_for_l3_uplinks`, `test_spare_ports_give_formula_quantity`, `test_sfp_choice_prefers_host_make`, `test_missing_sfp_is_an_error`, `test_cable_managers_one_per_switch_and_patch_panel`, `test_serial_cables_one_per_used_rtac_port`.
- [ ] Fail → implement → pass → commit `feat(engine): group C network accessories`.

### Task 5: Group D housekeeping (step 5)

**Files:** Create `src/bomgen/engine/housekeeping.py`; Test `tests/unit/engine/test_engine_housekeeping.py`.

**Produces:** `housekeeping.resolve_ventilation(panel) -> Ventilation` (`auto` → `FORCED` until M4); `housekeeping.needs_change_over(panel, library, loose) -> bool`; `housekeeping.housekeeping(panel, library, ventilation, change_over) -> list[BomItem]`.

- [ ] Tests: `test_forced_ventilation_gives_two_fans_and_three_thermostats`, `test_natural_ventilation_gives_filters_and_one_thermostat`, `test_ipr_kit_has_relay_base_suppression_bracket`, `test_change_over_diodes_auto_follow_single_fed_loads`, `test_loose_load_fed_from_panel_needs_change_over`, `test_socket_only_when_aux_socket_set`, `test_socket_rating_must_match_catalogue`.
- [ ] Fail → implement → pass → commit `feat(engine): group D housekeeping`.

### Task 6: Loose material, pipeline and golden

**Files:** Modify `src/bomgen/engine/kits.py` (+ `loose_table`); Create `src/bomgen/engine/pipeline.py`; Create `tests/golden/expected_groups_a_d.py`, `tests/golden/test_engine_groups_a_d.py`; Test `tests/unit/engine/test_engine_pipeline.py`.

**Produces:** `kits.loose_table(material: LooseMaterial | None, substation: str, panel_rows, library) -> LooseTable | None` (project items in order, then each device's `loose_items` as one parent block, plan Q30); `pipeline.build(loaded: LoadedProject) -> BuildResult` (groups A–D per panel; title `(cabinet_number, f"{substation} - {cabinet_name}")`).

- [ ] Golden: every A–D row of 001, 002, 003 and WS (tag, description, qty, make, model, code, hwio) and the loose table, each list citing the workbook rows; spec tags from plan section 5.
- [ ] Fail → implement → pass; ruff, mypy, pytest; commit `test(golden): groups A–D of the example cabinets`.
