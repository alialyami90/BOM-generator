# Implementation plan for AI agents: engineer-controlled BOM workflow

2026-11-03 · Ali. Source: [Claude Doc](https://claude.ai/artifact/YDdzKyCumpJ1bgdeqwQbnn).

This plan turns the review *Engineering workflow review: the SCADA engineer's BOM* into milestones an agent can execute one PR at a time. It names files, fields, endpoints, screens, tests and acceptance criteria for each. Numbers start at the project's next free ones: milestone M48, ADR 0031, question Q62.

## How to use this plan

One milestone is one PR, executed by one agent in one session, in the order given unless a dependency note says otherwise. Before starting any milestone the agent reads `CLAUDE.md`, `docs/handoff/STATE.md`, `NEXT.md`, `LESSONS.md`, the spec section the milestone names, and the milestone's entry here. Nothing here overrides `CLAUDE.md`.

**Fixed rules for every milestone**

1. **Branch from `main`**, one milestone per PR, conventional commit message with the milestone in scope, e.g. `feat(parts): M49 SFP quantities per switch`.
2. **Decision first.** A milestone marked *ADR needed* starts with the ADR (`docs/decisions/`, next free number, status Proposed) and a decision card to Ali; code starts only after Ali accepts. A milestone marked *Q* adds the question to `docs/plan.md` §6 and asks it as a card. A milestone marked *spec* changes `docs/spec/generator-spec-v2.md` only with Ali's go-ahead, in the same PR, one sentence where the rule lives, never restated in code comments.
3. **TDD in this order:** model test, engine test, io round-trip test, app API test, UI asset test (`node --check`, Playwright E2E where the screen changes). Tests are named after the rule they prove, `test_<rule>` as the existing files do.
4. **Golden values don't move.** Every new input defaults to today's behaviour, so `tests/golden/` passes unchanged. A milestone that must move a golden value says so in its ADR.
5. **The automation contract.** A derived value the engineer can override is: computed by the engine, returned with a `rule` text, stored as an override only when set, shown with the marker, reset to automatic. The UI never re-implements a rule.
6. **Every new field** lands in: the model (`src/bomgen/models/`), the JSON schema export (`schemas/`, regenerate), the round-trip writer path (`src/bomgen/io/fields.py` and the page module's `spec()`), the CSV export and import when it is a library field (ADR 0018), `docs/plan.md` §3 input schema, `docs/ui/editing.md` field inventory.
7. **Gate before every commit:** `ruff check . && ruff format --check .`, `python -m mypy`, `python -m pytest -q -p no:cacheprovider`. PRs touching `src/bomgen/app/`, `packaging/` or `pyproject.toml` also need a green "Build Windows installer".
8. **Screenshots.** A milestone with a screen change saves Playwright screenshots of each new state under `/mnt/project-files/a11-screens/<milestone>/` and links them in the PR.
9. **Handoff.** The PR updates `docs/plan.md` §4 (the milestone's status), `CHANGELOG.md` `[Unreleased]`, and when the agent's session ends, `docs/handoff/` in a docs-only PR.
10. **Ask Ali only on a card** with a recommended option, and record the answer as a plan question.

**Roles** (from the audit's team): lead and reviewer plans, reviews, merges and keeps these docs; engine owns `models/`, `engine/`, `sheets/`, `writer/`, `checks.py`; app owns `app/` and `app/ui/`; data and docs owns `data/`, `library_store/`, `docs/`. A milestone that spans engine and app is one PR by one agent, engine first.

**Milestone entry format.** Goal; Depends on; Decision; Model; Engine; IO; API; UI; Tests; Acceptance; Size (S under 300 lines of source, M under 800, L above; split an L).

**Milestone map**

| Phase | Milestones | Decision needed |
| --- | --- | --- |
| A Foundations | M48 derived-value component · M49 SFP quantities · M50 per-panel enclosure and kind · M51 new-substation setup | Q on seeds; spec for bottom entry |
| B Design basis | M52 design basis model and tab · M53 vendor list and part states · M54 design-basis checks · M55 templates | ADR 0031 design basis |
| C Panel detailing | M56 housekeeping editor · M57 terminals tab · M58 grounding, spare ratings, alarm toggle · M59 BOM text per row | ADR 0032 housekeeping as inputs; ADR 0033 terminal rules as inputs |
| D Network inputs | M60 IED schedule · M61 external links · M62 panel count control | ADR 0034 IED schedule |
| E Issue outputs | M63 summary BOM · M64 spares list · M65 cable schedule · M66 revision history and recorded issues | ADR 0035 extra sheets; ADR 0036 recorded issues |
| F Library | M67 record sources and lifecycle · M68 review queue and health · M69 propose from project | ADR 0037 record lifecycle |

## Phase A: Foundations

### M48 Derived-value component and the override contract

- **Goal.** One UI component and one engine convention for every derived value the engineer may override: value, rule text, override input, marker, reset.
- **Depends on.** Nothing. Everything later uses it.
- **Decision.** None. Document the contract in `docs/ui/components.md` ("Derived value") and `docs/ui/editing.md` ("Overrides").
- **Model.** A generic `Derived[T]` output type in `src/bomgen/models/output.py`: `value: T`, `rule: str`, `override: T | None`, `source: Literal["engine","override"]`. No input model change.
- **Engine.** No rule changes. Add `rule` strings where values are already computed and exposed to the app: `engine/network.py` SFP quantities ("24 links + 3 spare"), `engine/dc_dist.py` main MCB ("next standard size above 7.1 A, minimum 6 A"), `engine/terminals.py` per strip ("2 × 6 AC MCBs"), `engine/housekeeping.py` counts. Return them through the existing preview and page builders, not new endpoints.
- **IO.** None.
- **API.** `panel_page` and `parts_page` carry `rule` next to each derived value they already return.
- **UI.** `ui.js`: `derived(key, {value, rule, override, unit})` renders the value, a muted rule line, becomes an input on click, shows the Changed marker when an override exists, and a "Use automatic" ghost button. Apply it first to the three places that already override (main MCB override, panel option placeholders, part overrides on Parts) so the look is one.
- **Tests.** `tests/unit/engine/test_rules_text.py`: each rule string names the numbers it used. `tests/unit/app/test_app_derived_values.py`: pages carry `rule`. UI: `node --check`, an E2E that clicks a derived value, types, saves, resets.
- **Acceptance.** Main MCB override on the panel editor shows "16 A: next standard size above 7.1 A" under the input; typing 20 marks it; reset clears it; golden unchanged.
- **Size.** M.

### M49 SFP quantities per switch

- **Goal.** The engineer sets spare and extra SFPs per switch, speed and media; the BOM quantity stays a formula.
- **Depends on.** M48.
- **Decision.** None; the spec already says SFP quantity may be `=24+3`. Add Q62 only if Ali wants extras to count against the port budget (recommend: they don't).
- **Model.** `models/substation.py`: `SfpChoice` gains `spare: NonNegativeInt | None = None` (overrides `spares.sfp_per_l1` for that speed and media) and `extra: NonNegativeInt = 0`. Keep `Equipment._consistent`'s refusal of a hand-written `port_plan` on L1 and L2.
- **Engine.** `engine/network.py` `_sfp_items`: quantity becomes `QtySum((used, spare, extra))` with zero parts dropped, `rule` = "24 links + 3 spare + 2 extra". `engine/sizing.py` is untouched. `checks.py` `sfp_slot_checks`: extras count toward the slot check with a warning, not a failure, when they exceed free slots.
- **IO.** `io/parts_edit.py`: write `sfp[i].spare` and `sfp[i].extra`; `fields.py` paths `("equipment", i, "sfp", j, "spare")`.
- **API.** `parts_page` returns per switch row `sfp[]` with `used`, `spare`, `extra`, `total`, `rule`, `candidates` (exists). `set_sfp_choice` accepts `spare` and `extra`.
- **UI.** `screens-parts.js`: under each L1 and L2 row's SFP sub-rows add Used (read-only, rule on hover), Spare and Extra as derived values, Total. Keys `f.<row>.<speed>.<media>.spare|extra`.
- **Tests.** `test_engine_network.py::test_sfp_qty_is_used_plus_spare_plus_extra`, `::test_sfp_spare_per_choice_overrides_project_spare`, `test_checks.py::test_sfp_extra_beyond_slots_warns`, `test_parts_edit.py::test_sfp_spare_and_extra_round_trip`, `test_app_parts_api.py::test_parts_page_sfp_counts_carry_rule`. Golden: example still `=24+3`.
- **Acceptance.** On the example, setting extra 2 on the L1 MM 1G row builds `=24+3+2` in group C of Cabinets 001 and 002, Checks shows a warning if slots are short, Preview shows the breakdown.
- **Size.** M.

### M50 Enclosure and kind per generated panel, bottom entry

- **Goal.** Each generated panel may have its own enclosure and kind; cable entry gains bottom.
- **Depends on.** M48 (for the shared/own display pattern, already used by options).
- **Decision.** *Spec*: add "bottom" to cable entry (Inputs, 2. Enclosure) and say a generated panel may set its own enclosure and kind. One sentence each, Ali's go-ahead.
- **Model.** `models/panel.py` `CableEntry.BOTTOM`. `models/substation.py` `GeneratedPanels`: `enclosure_by_panel: dict[PositiveInt, Enclosure]`, `kind_by_panel: dict[PositiveInt, PanelKind]`.
- **Engine.** `engine/layout.py` where generated panels are written: enclosure and kind from `*_by_panel` when set, else the shared ones. `engine/enclosure.py`: "Bottom Entry". `engine/thermal.py` reads the panel's own enclosure for the natural-convection area (it already reads `panel.enclosure`).
- **IO.** `fields.py` paths `("generated_panels", "enclosure_by_panel", n, ...)` and `kind_by_panel`; `remove_field` returns the panel to shared.
- **API.** `panel_page` returns `enclosure` with `own: bool` and `shared`; `set_enclosure` takes `scope: "all" | n`. `set_panel_field` for kind the same way.
- **UI.** `screens-panel-editor.js` Enclosure tab: the Options tab's "All generated panels / This panel only" segmented control; Kind select added to the tab; bottom in the cable entry select. Hand-written panels: bottom only.
- **Tests.** `test_substation_model.py::test_generated_panels_may_set_enclosure_and_kind_per_panel`, `test_engine_layout.py::test_generated_panel_takes_its_own_enclosure`, `test_engine_enclosure.py::test_bottom_entry_text`, `test_engine_thermal.py::test_natural_convection_uses_own_enclosure`, `test_app_panel_page.py::test_enclosure_scope_own_and_shared`, round-trip for both dicts.
- **Acceptance.** Panel 3 set to 600 mm wide and kind control builds a different PANEL row and X4-DC step 1 while panels 1 and 2 keep the shared values.
- **Size.** M.

### M51 New-substation setup instead of ASSUMED seeds

- **Goal.** A new substation asks for what no source gives, instead of seeding the example's values silently.
- **Depends on.** M50.
- **Decision.** *Q62* to Ali: keep today's seeds as the dialog's prefilled defaults (recommended), or start blank.
- **Model.** None.
- **Engine.** None.
- **IO.** `io/lifecycle.py` `_blank` takes a `setup` dict: cabinet number pattern, cabinet name pattern, tag prefix pattern, enclosure, cable entry, document numbers for BOM, power and heat. Values not given keep today's seed with the ASSUMED comment; values given write without it. `create_substation` passes the dict through.
- **API.** `new_substation_form` returns the defaults (last substation's values when one exists, else today's seeds). `create_substation(..., setup)`.
- **UI.** `screens-projects.js` New substation dialog gains a second step "Cabinets and documents": the patterns, enclosure (make, model, H × D × W, base frame, entry), three document numbers with revision and date. "Use the previous substation's values" when one exists.
- **Checks.** `checks.py`: `document_number_placeholder` warns while any register entry used by the substation is "TBD" or marked ASSUMED.
- **Tests.** `test_lifecycle.py::test_a_new_substation_writes_given_values_without_assumed`, `::test_unset_values_keep_assumed_seed`, `test_app_lifecycle_api.py::test_new_substation_form_prefills_from_previous`, `test_checks.py::test_tbd_document_number_warns`.
- **Acceptance.** Creating a substation with numbers typed produces YAML with no ASSUMED comment on those keys; Checks is clean of the new warning; a blank one still works as today.
- **Size.** M.

## Phase B: Design basis

### M52 Design basis model and tab

- **Goal.** One place, first on a new substation, where the engineer states the design basis; every later default reads from it and says so.
- **Depends on.** M51.
- **Decision.** *ADR 0031 Design basis*: what it holds, that it only sets defaults (never a rule), and how it maps onto today's constants, spares, brands and generated-panel settings. Proposed by the agent, accepted by Ali before code.
- **Model.** `models/substation.py` new `DesignBasis(InputModel)`: `dc_voltage_v: Literal[48,110,125,220] | PositiveFloat`, `ac_voltage_v`, `redundancy: Literal["duplicated_lan"]` (PRP and HSR reserved, refused with a message), `purdue_scope: set[Literal["L1","L2","EXT"]]`, `time_sync: Literal["gps_clock","ptp_from_clock","none"]`, `tagging: Tagging` (prefix pattern, side letters `("A","B")`, first numbers per level), `spares_policy: SparesPolicy` (percent per category, minimum per part, categories included; used by M64), `vendor_list: str | None` (key into the project's lists, M53), `notes: str | None`. `Substation.design_basis: DesignBasis | None`. The loader derives `constants.dc_voltage_v` and `ac_voltage_v` from it when the substation's constants don't set them, and reports the source.
- **Engine.** `engine/tags.py` reads side letters and first numbers from `Tagging` instead of the module constants `DEFAULT_SIDE` and the per-level starts; defaults equal today's. Nothing else.
- **IO.** `fields.py` paths under `("design_basis", ...)`; `lifecycle._blank` writes a `design_basis` from the M51 setup step.
- **API.** `design_basis_page(project_file, sub)` returns the fields with `source` per derived default; `set_substation_field` covers the paths. `parts_page` and the settings page return `source: "design_basis"` on the constants and spares it feeds.
- **UI.** `screens-substation.js`: a *Design basis* tab before *General*, a form with the save bar; the New substation dialog's step 2 (M51) becomes this tab's first fill. Settings › Design constants shows "From the design basis" under DC and AC voltage.
- **Tests.** `test_substation_model.py::test_design_basis_defaults_match_today`, `test_substation_loader.py::test_constants_take_voltage_from_design_basis_unless_set`, `test_engine_tags.py::test_tagging_first_numbers_from_design_basis`, `test_app_substation_api.py::test_design_basis_page_reports_sources`, round-trip, E2E of the tab.
- **Acceptance.** Example builds unchanged with no `design_basis`; a substation with DC 110 V shows 110 in Design constants with the source line and Power Consumption prints 110V.
- **Size.** L; split the ADR and model (M52a) from the tab (M52b) if over 800 lines.

### M53 Vendor list and part lifecycle states

- **Goal.** A client's approved vendor list filters pickers and raises warnings; library parts carry a lifecycle state.
- **Depends on.** M52; M67 for the state field (do M67's model part first, or include it here and let M67 build on it).
- **Decision.** Inside ADR 0031 (vendor list) and ADR 0037 (lifecycle, M67).
- **Model.** `models/project.py`: `VendorList(InputModel)`: `key`, `name`, `brands: dict[kind, list[BrandId]]` (allowed brand sets per catalogue), `makes: list[str]` (allowed manufacturers), `parts_allowed: list[PartId]`, `parts_banned: list[PartId]`. `Project.vendor_lists: list[VendorList]`. `models/library.py` `DeviceType.state: Literal["draft","reviewed","released","obsolete"] = "released"`, `successor: PartId | None`.
- **Engine.** None.
- **IO.** Project paths; CSV column `state`, `successor` in `devices.csv` (ADR 0018 round-trip test).
- **API.** `parts_page` and `panel_parts` take the substation's vendor list into account: parts outside it are listed under "Not on the vendor list" and marked; `library_overview` shows state.
- **UI.** Project › a *Vendor lists* tab (table of lists, each a dialog with brand checkboxes, makes, allowed and banned parts). Parts: the part picker groups allowed first; a picked part outside the list shows a warning chip. Library: state badge in the table and the device editor Identity tab.
- **Checks.** `vendor_list_checks`: a picked part, brand set or make outside the list warns; `part_state_checks`: draft warns, obsolete warns and names the successor.
- **Tests.** `test_project_model.py::test_vendor_list_keys_unique`, `test_checks.py::test_part_outside_vendor_list_warns`, `::test_obsolete_part_names_successor`, `test_app_parts_api.py::test_picker_groups_vendor_list_parts_first`, CSV round-trip with `state`.
- **Acceptance.** With a list allowing Siemens only, picking a Ruggedcom L1 switch builds but Checks warns with the list's name.
- **Size.** M.

### M54 Design-basis checks

- **Goal.** Checks compares the substation with its design basis.
- **Depends on.** M52, M53.
- **Decision.** None.
- **Engine / checks.** `checks.py`: `design_basis_checks`: a DC-fed part whose `input_v_min..max` excludes the DC voltage fails; an AC part at another voltage warns; a Purdue level present on Parts but out of scope warns; `time_sync: none` with a GPS clock row warns; EXT devices without a firewall when the scope has EXT warns.
- **API / UI.** Checks page lists them under a new group "Design basis" with "Go to field" to the tab.
- **Tests.** One test per check in `test_checks.py`, named after the rule.
- **Acceptance.** Example clean; a 220 V design basis with the example's 125 V parts fails with the part named.
- **Size.** S.

### M55 Substation templates

- **Goal.** Start a substation from a saved template (design basis, brands, options, loose list, spares policy), not only from a copy of a sibling.
- **Depends on.** M52.
- **Decision.** *Q63*: templates stored per project folder (`templates/*.yaml`, recommended) or in the app home for all projects.
- **Model.** `models/template.py` `SubstationTemplate`: name, description, `design_basis`, `catalogue_choice`, `spares`, `generated_panels` options and enclosure, `loose_material.items`, `equipment` roles with parts (no quantities, no layout).
- **IO.** `lifecycle.py` `_from_template`: writes the substation from the template as `_copy` does from a sibling, minus panels and documents. `save_template(sub)` writes a template from a substation.
- **API.** `list_templates`, `save_template`, `create_substation(from_template=)`.
- **UI.** New substation dialog: "Start from" gains the templates; Substation › Settings › General: "Save as template…".
- **Tests.** `test_lifecycle.py::test_substation_from_template_has_no_panels_or_documents`, `::test_template_round_trips_a_substation`, API tests.
- **Acceptance.** Save the example as a template, create a new substation from it, set an IED count, generate: the parts and brands match the example.
- **Size.** M.

## Phase C: Panel detailing

These milestones turn quantities the spec states as fixed into inputs whose defaults equal the spec. Each needs an ADR accepted before code, and a spec sentence saying the quantity is a panel input with the stated default.

### M56 Housekeeping editor

- **Goal.** Per panel, the engineer sees and changes each housekeeping item's quantity and breaker rating, adds a heater and hygrostat, and says whether the smoke detector is supplied.
- **Depends on.** M48, M50.
- **Decision.** *ADR 0032 Housekeeping as inputs*: counts and branch ratings become panel options with the spec's defaults; heater and hygrostat roles; smoke detector choice; housekeeping breakers sized from the part's watts when the part gives them, else the spec's fixed rating. Spec sentence in "Housekeeping kit (group D)" and "AC distribution (group E)".
- **Model.** `models/panel.py` `PanelOptions.housekeeping: HousekeepingOptions | None`: `fans: NonNegativeInt | None`, `thermostats_forced`, `thermostats_natural`, `filters`, `lamps`, `heater: bool`, `hygrostat: bool`, `smoke_detector: Literal["none","terminals","supplied"]` (replaces the bool; loader maps `true` to `terminals`), `branch_ratings: dict[str, PositiveInt]` keyed by load name (`lamp`, `fan`, `thermostat`, `heater`). `models/library.py` `Housekeeping.heater`, `hygrostat`, `smoke_detector: HousekeepingRef | None`.
- **Engine.** `engine/housekeeping.py`: counts from options, defaults from the module constants; heater and hygrostat rows when set. `engine/ac_dist.py`: loads built from the housekeeping rows (lamp, fan + TH pairs, extra TH, heater) with ratings from `branch_ratings`, else sized from watts when the part has `unit_power_w` and `supply_type: VAC`, else the spec's constants. `engine/terminals.py` THF from the actual fan and thermostat count (12 and 5 at the defaults). `engine/power.py`: heater and hygrostat in the AC block. Every count and rating returned with its `rule`.
- **IO.** Option paths; CSV `housekeeping.csv` roles `heater`, `hygrostat`, `smoke_detector`.
- **API.** `panel_options` returns the housekeeping block with values, rules, shared and own; `set_panel_option` covers the nested keys.
- **UI.** Panel editor › Options: a *Cabinet housekeeping* section, one derived-value row per item (quantity, breaker), heater and hygrostat switches, smoke detector select, socket as a pick list from the library's sockets (closes the earlier review's gap 11). Library › Catalogues › Housekeeping: the three new roles.
- **Tests.** `test_engine_housekeeping.py::test_defaults_give_two_fans_three_thermostats`, `::test_heater_adds_row_and_ac_branch`, `test_engine_ac_dist.py::test_branch_rating_from_part_watts_when_given`, `::test_fixed_rating_when_part_has_no_watts`, `test_engine_terminals.py::test_thf_follows_fan_and_thermostat_count`, `test_engine_power.py::test_heater_in_ac_block`, option round-trip, panel page tests. Golden unchanged.
- **Acceptance.** Example unchanged. A panel with heater on gets a group D heater row, a C-branch sized from its watts, THF unchanged, AC power total up by its watts.
- **Size.** L; split engine (M56a) and app (M56b).

### M57 Terminals tab

- **Goal.** Every strip shows its rule and quantity, each overridable; a spare percent per substation.
- **Depends on.** M48.
- **Decision.** *ADR 0033 Terminal rules as inputs*: fixed quantities become panel-kind defaults the engineer may override per strip, plus a spare percent applied before overrides. Spec sentence under "Terminal block quantities (group G)".
- **Model.** `models/panel.py` `PanelOptions.terminal_overrides` stays (exists); add `terminal_block_overrides: dict[str, str]` (strip code to block type name, for fused or test terminals). `models/project.py` `Spares.terminals_fraction: float = 0.0` (project default, substation override as other spares).
- **Engine.** `engine/terminals.py`: `terminal_strips` returns each strip with `rule` ("2 × 6 AC MCBs = 12", "+10% spare = 14"), applies `terminals_fraction` (round up) before overrides, takes the block type override. Export a pure `strip_table(panel, ...)` the app calls without building the workbook.
- **IO.** Paths for both dicts and the spare fraction.
- **API.** `panel_terminals(project, sub, panel)` returns the strip table; `set_panel_option` writes an override; `remove_panel_option` resets one strip.
- **UI.** Panel editor: a *Terminals* tab: table of strip, block type (select), rule, automatic quantity, override (derived value). Settings › Design constants gains "Spare terminals" with the others.
- **Tests.** `test_engine_terminals.py::test_spare_fraction_rounds_up_before_override`, `::test_block_type_override_changes_part_number`, `::test_rule_text_names_the_mcb_count`, API and round-trip tests. Golden unchanged at fraction 0.
- **Acceptance.** On Cabinet 001, 10% spare makes X3-AC 14 and X4-DC1 36; overriding XIP to 60 keeps the rule visible and the marker on.
- **Size.** M.

### M58 Grounding, spare breaker ratings, alarm on branch trip

- **Goal.** Three panel-level choices that are YAML-only or library-only today become screen inputs.
- **Depends on.** M48.
- **Decision.** None; `grounding_busbars` and `alarm_on_branch_mcb` exist. Spare ratings: a spec sentence ("one 2A spare" becomes a default).
- **Model.** `PanelOptions.ac_spare_rating_a: PositiveInt | None`, `dc_spare_rating_a: PositiveInt | None`. `DeviceInstance.alarm_on_branch_mcb: bool | None` and `Equipment.alarm_on_branch_mcb: bool | None` (None = library value).
- **Engine.** `ac_dist.py` and `dc_dist.py` take the spare rating when set; aux contacts from the row's value over the library's. Rules returned.
- **IO / API / UI.** Options tab: busbars as checkboxes from the busbar catalogue; spare ratings as derived values; Parts row and hand-written panel row: "Alarm on branch MCB trip" switch with the library value as default and the HWIO effect shown.
- **Tests.** `test_engine_grounding.py::test_busbar_choice_from_options`, `test_engine_ac_dist.py::test_spare_rating_override`, `test_engine_dc_dist.py::test_alarm_toggle_adds_aux_contact_and_hwio`, round-trip and page tests.
- **Acceptance.** Turning the firewall's alarm off on Cabinet 001 drops DC aux contacts to 3 and HWIO by one; the example unchanged otherwise.
- **Size.** S.

### M59 BOM text per row on Parts

- **Goal.** Purpose, tag override, type code, first number and HWIO points editable where the part is picked.
- **Depends on.** M48.
- **Decision.** None; the fields exist on `Equipment` and `DeviceInstance` (`purpose`, `hwio_points`, `tag`, `tag_type`, `first_nn`). Add `tag` and `tag_type`, `first_nn` to `Equipment` so the layout copies them onto the generated rows as it does `purpose`.
- **Engine.** `engine/layout.py`: copy the three fields onto `DeviceInstance` rows. `engine/tags.py` unchanged.
- **IO / API / UI.** `parts_edit.py` paths; `parts_page` returns the generated tag per unit as the placeholder; Parts row gains a *BOM text* expander with the five fields; hand-written panel rows gain tag, type code and first number next to purpose and HWIO. Duplicate-tag check result shown inline from the existing `duplicate_tag_checks`.
- **Tests.** `test_engine_layout.py::test_equipment_tag_fields_copied_to_generated_rows`, `test_parts_edit.py::test_bom_text_fields_round_trip`, `test_app_parts_api.py::test_parts_page_gives_generated_tag_as_placeholder`.
- **Acceptance.** Setting first number 21 on the L1 row prints PSA1-L1-ESW-A21 to A26 and the MCB descriptions follow.
- **Size.** S.

## Phase D: Network inputs

### M60 IED schedule

- **Goal.** The L1 network is sized from the real IED list (ports per speed, media and attachment), not one count; the one count stays as a quick mode.
- **Depends on.** M52 (the design basis names the redundancy scheme).
- **Decision.** *ADR 0034 IED schedule*: the schedule is the source of `ied_count`; each IED row needs its ports; single-attached IEDs land on side A only; a row may land on L2 directly. Spec change under "Automatic panel layout" and "Inputs, 2": `network.ied_count` becomes derived when a schedule exists.
- **Model.** `models/substation.py` `IedRow(InputModel)`: `bay: str`, `name: str` (type or tag), `qty: PositiveInt`, `ports: list[PortNeed]` (`count`, `speed`, `media`), `attachment: Literal["dual","single_a","single_b"] = "dual"`, `lands_on: Literal["l1","l2"] = "l1"`, `notes`. `Network.ied_schedule: list[IedRow]`; `Network._consistent`: `ied_count` must be unset when a schedule exists.
- **Engine.** `engine/sizing.py`: `NetworkInputs` gains `ied_ports_per_side: dict[(speed, media), int]` per side; `usable_ports` and `l1_links` size per speed and media against the switch's port groups (`PortGroup.speed`, `media`, `usable_for`); L2 demand adds the rows that land on L2. The L1 port plan's downlinks follow the mix, so M49's SFP "used" follows it. `SizingError` names the speed and media that don't fit.
- **IO.** `parts_edit.py`: list paths `("network", "ied_schedule", i, ...)`; CSV import of a schedule (`bay,name,qty,ports,attachment,lands_on`) through a small reader in `io/ied_csv.py`.
- **API.** `parts_page` returns the schedule and the derived count per side and speed; `add_ied_row`, `set_ied_field`, `remove_ied_row`, `import_ied_csv` with a dry-run preview as the library CSV has.
- **UI.** Parts: *IED schedule* section above Network with a mode switch (Quick count / Schedule), the table, *Add row*, *Import CSV…*, and the Result card showing ports per speed and media per side.
- **Tests.** `test_engine_sizing.py::test_schedule_sums_ports_per_speed_and_media_per_side`, `::test_single_attached_ied_counts_on_side_a_only`, `::test_row_landing_on_l2_adds_l2_demand`, `::test_quick_count_equals_schedule_of_100m_mm_dual`, `test_substation_model.py::test_ied_count_refused_with_schedule`, IED CSV tests, page tests. Golden: the example keeps `ied_count` and sizes as today.
- **Acceptance.** A schedule of 40 dual MM 100M plus 8 copper 1G IEDs picks an L1 switch with RJ45 ports or fails naming "1G RJ45"; the quick count of 48 equals the old behaviour.
- **Size.** L; split engine (M60a) and app (M60b).

### M61 External links

- **Goal.** Links to the control centre, PCC and third parties are rows with media, speed, count and landing switch, not a port count on a device row.
- **Depends on.** M60.
- **Decision.** *Q64*: keep `l2_ports` on equipment rows for devices in the cabinets (recommended) and add external links as their own list, or fold both into one.
- **Model.** `Network.external_links: list[ExternalLink]`: `name`, `count`, `speed`, `media`, `lands_on: Literal["l2","ext"]`, `through_firewall: bool`, `redundant: bool` (one per side), `cable_length_m: PositiveFloat | None` (M65).
- **Engine.** `sizing.py`: adds the L2 or EXT demand; `network.py`: port plan uplinks for them; `checks.py`: a link through the firewall needs a firewall row; EXT landing needs an ext\_switch row.
- **IO / API / UI.** Paths and endpoints as M60; Parts › Network: *External links* table.
- **Tests.** `test_engine_sizing.py::test_external_link_adds_l2_demand`, `test_checks.py::test_firewall_link_needs_firewall_row`, round-trip, page tests.
- **Acceptance.** Two SM 1G links to the CCR add 2 SM SFPs on each L2 switch (as the example's `uplinks_l3`) and show on the Result card.
- **Size.** M.

### M62 Panel count control

- **Goal.** The engineer fixes or caps the number of generated panels; the layout fits or reports exactly what doesn't.
- **Depends on.** None after M48.
- **Decision.** None; a layout input (ADR 0013 amendment paragraph in `docs/plan.md`).
- **Model.** `Layout.panel_count: PositiveInt | None`, `Layout.max_panels: PositiveInt | None` (one or the other).
- **Engine.** `layout.py`: with `panel_count`, the fill opens exactly that many (pairs rounded up) and a unit that doesn't fit is a layout error naming the unit and the U short; with `max_panels`, the same cap. `preview.py` reports `panels_limit` and the shortfall.
- **IO / API / UI.** Path; `substation_layout` returns the limit; Parts › Network fine tuning: "Panels" as Automatic / Exactly n / At most n. Device preview shows the error banner as it does for overflow.
- **Tests.** `test_engine_layout.py::test_fixed_panel_count_errors_on_overflow_naming_unit`, `::test_max_panels_caps_fill`, round-trip, API.
- **Acceptance.** Example with exactly 2 panels reports Cabinet 003's units as not fitting with the U short; with 4 it builds as today.
- **Size.** S.

## Phase E: Issue outputs

All four add sheets after Heat Calculations, each written only when its data exists, each with the BOM header and footer under the substation's main document, A4, Calibri, the calculation-sheet styles (`sheets/styles.py`). Sheet names join `OutputSettings.sheet_names`. One ADR covers the sheet set.

### M63 Summary BOM

- **Goal.** One sheet consolidated by ordering code across every panel and the loose material, with where-used, for procurement; a CSV extract of it.
- **Depends on.** M48.
- **Decision.** *ADR 0035 Issue sheets*: Summary BOM, Spare Parts, Cable Schedule and Revision History; their order, columns and when each is written. Spec: new rows in the Workbook map and OUT-3.
- **Model.** `models/sheet.py` `SummaryLine`: `make`, `model`, `ordering_code`, `description` (first seen), `qty` (sum, "1 Lot" rows listed separately), `where_used: tuple[(sheet, tag, qty), ...]`. `BuildResult.summary: SummaryTable`.
- **Engine.** `engine/summary.py`: group `flatten(items)` of every panel and the loose table by `(make, model, ordering_code)`; free-text loose items grouped by description; quantities that are formulas resolve to their value; enclosure rows included; busbars (description only) included with blank make.
- **Sheets / writer.** `sheets/summary_sheet.py`: columns SR.NO, DESCRIPTION, QUANTITY, MAKE, MODEL, ORDERING CODE, WHERE USED ("001: PSA1-L1-ESW-A11 to A16 (6); 002: …"). Quantity cells are formulas summing the source BOM cells (`='Panel 1'!D12+'Panel 2'!D12`) so OUT-5 holds. Landscape A4.
- **IO / API / UI.** `OutputSettings.sheet_names.summary_bom`, `OutputSettings.include: set["summary_bom","spares","cables","history"]` (default all that have data). Build page: checkboxes per optional sheet; "Export summary as CSV" after a build (`export_summary_csv`). Preview: a *Summary BOM* tab.
- **Tests.** `test_engine_summary.py::test_same_ordering_code_across_panels_sums_qty`, `::test_free_text_items_group_by_description`, `::test_where_used_lists_sheet_tag_qty`, `tests/unit/sheets/test_summary_sheet.py` (formulas reference source cells), writer test reopening the file, golden `tests/golden/test_summary.py` with the example's totals (the agent computes them from the example and cites the panel rows).
- **Acceptance.** Example: A9F74202 sums every 2 A MCB across the four cabinets with where-used; the CSV opens in Excel with the same rows.
- **Size.** M.

### M64 Spares list

- **Goal.** A spare parts list from the spares policy, editable, as a sheet.
- **Depends on.** M52 (policy), M63 (grouping).
- **Decision.** In ADR 0035; *Q65*: percent with a minimum of one (recommended) or a typed list.
- **Model.** `DesignBasis.spares_policy: SparesPolicy`: `percent_by_category: dict[Category, float]`, `minimum: NonNegativeInt = 1`, `categories: set[Category]`, `round: Literal["up","nearest"]`. `Substation.spares_list: SparesOverrides`: `items: dict[ordering_code, NonNegativeInt]` (overrides), `extra: list[SpareExtra]` (part or free text with qty), `excluded: set[ordering_code]`.
- **Engine.** `engine/spares.py`: from the summary table, per line in an included category: `max(minimum, round(percent × installed))`, then overrides, extras, exclusions; each with `rule` ("10% of 27, min 1 = 3").
- **Sheets.** `sheets/spares_sheet.py`: SR.NO, DESCRIPTION, INSTALLED QTY, SPARE QTY, MAKE, MODEL, ORDERING CODE, BASIS (the rule).
- **API / UI.** `spares_page`, `set_spare_override`, `add_spare_extra`, `exclude_spare`. A *Spares* page in the rail under Loose material: policy summary from the design basis with a link, the table with derived-value spare quantities, Add item, Exclude. Preview tab.
- **Tests.** `test_engine_spares.py::test_percent_with_minimum_one`, `::test_override_replaces_computed_qty`, `::test_excluded_line_absent`, sheet and writer tests, page tests.
- **Acceptance.** Policy 10% on SFPs and MCBs on the example gives 3 spare 1G MM SFPs per type and the MCB lines at their minimums; editing one shows the marker and prints the edited value.
- **Size.** M.

### M65 Cable schedule

- **Goal.** Suggested patch cords and cables from the links, editable as loose material, and a Cable Schedule sheet.
- **Depends on.** M61, M63.
- **Decision.** In ADR 0035; *Q66*: default lengths per link class (in-cabinet 2 m, inter-cabinet 5 m, external from the link row) as design-basis defaults, recommended.
- **Model.** `DesignBasis.cables: CableDefaults` (lengths per class, connector types per media). `LooseExtra.cable: CableRef | None` (`from_tag`, `to_tag`, `length_m`, `media`, `speed`) so a suggested cord is an ordinary loose row with cable data. `Library`: `Category.CABLE` parts gain `media`, `connectors`, `length_m` fields.
- **Engine.** `engine/cables.py`: from the port plans and external links, one cord per link end pair (A side and B side), part picked from the library by media, connector and length class, quantity per class; `rule` names the links. Returns suggestions; nothing is written until accepted.
- **Sheets.** `sheets/cable_sheet.py`: SR.NO, FROM, TO, TYPE, LENGTH, QTY, MAKE, MODEL, ORDERING CODE; written when any loose row has cable data.
- **API / UI.** `suggest_cables` returns the rows; Loose material: "Suggest cables…" opens a review dialog (accept all, or per row), accepted rows become loose rows with the cable fields editable in the table (extra columns shown when any row has them). Preview tab.
- **Tests.** `test_engine_cables.py::test_one_cord_per_l1_uplink_per_side`, `::test_length_class_from_design_basis`, `::test_no_library_cable_for_media_is_a_warning`, sheet tests, API tests.
- **Acceptance.** Example with the library's LC patch cords: 12 MM cords for the L1 uplinks per side and 2 SM for the CCR links are suggested; accepting them writes loose rows and the sheet.
- **Size.** L; split engine (M65a) and app (M65b).

### M66 Revision history and recorded issues

- **Goal.** Each issue is recorded; the next build compares automatically; a Revision History sheet and prepared / checked / approved names.
- **Depends on.** M63 (sheet conventions).
- **Decision.** *ADR 0036 Recorded issues*: what an issue record holds, where it lives (`substation.yaml` `issues:`), that the compare uses the recorded file when present and the picker otherwise; *Q67*: names in the header, on a cover sheet, or on the history sheet only (recommend the history sheet plus the footer's existing fields).
- **Model.** `Substation.issues: list[IssueRecord]`: `rev`, `date`, `file`, `sha256`, `prepared`, `checked`, `approved`, `description`, `accepted_warnings: list[AcceptedWarning]` (check id, subject, reason). `RegisterEntry` gains `prepared`, `checked`, `approved: str | None`.
- **Engine.** `revision.py`: read the previous issue from the record's file when it exists and its hash matches, else warn and fall back to the picker. `checks.py`: an accepted warning is shown as accepted with its reason, not as open.
- **Sheets.** `sheets/history_sheet.py`: REV, DATE, DESCRIPTION, PREPARED, CHECKED, APPROVED, one row per record plus the current revision; written when the register has at least one record or names.
- **API / UI.** Build: "Build as issued" writes the file, computes the hash, appends the record with the names and a description typed in a dialog; the plain Build stays. Checks: "Accept with reason" on a warning. Settings › Documents: the three names per document. Preview: *Revision History* tab.
- **Tests.** `test_revision.py::test_previous_issue_from_record_when_hash_matches`, `::test_hash_mismatch_warns_and_uses_picker`, `test_checks.py::test_accepted_warning_shows_reason`, sheet tests, `test_app_output_api.py::test_build_as_issued_appends_record`.
- **Acceptance.** Build as issued rev 00, change a part, build rev 01: the compare runs without a picker, Preview highlights the changed cells, the history sheet lists 00 and 01 with names.
- **Size.** M.

## Phase F: Library

### M67 Record sources and lifecycle

- **Goal.** Every library record says where its numbers come from and what state it is in.
- **Depends on.** None; M53 uses the state field (do this first or include the field there).
- **Decision.** *ADR 0037 Record lifecycle and sources*: states draft, reviewed, released, obsolete; a source per sized field; a shipped library is all released.
- **Model.** `models/library.py` `DeviceType.state` and `successor` (M53), `sources: dict[str, Source]` keyed by field name (`unit_power_w`, `inrush_a`, `height_u`, `input_v_max`, `ports`): `Source(kind: Literal["datasheet","contractor","assumed","measured"], ref: str, date: date | None)`. `changed_by`, `changed_on`, `note` on the record, filled by `library_store/local.py` `save_edits` from the pending set's note.
- **Library store.** `library_store/diff.py` shows source and state changes; `device_db.py` seeds `sources` from the device database's `verified` and source lists when a record has none (one-off migration in `data/library/build.py`, every shipped part gets a source or `assumed`).
- **IO.** CSV columns `state`, `successor`, `source_unit_power_w`, `source_inrush_a`, `source_height_u`, `source_input_v_max`, `source_ports` as `kind|ref|date`; round-trip test with every field set.
- **API / UI.** Device editor: a *Sources* column in the Electrical and Ports tabs (kind select, ref text, date); Identity tab: state select and successor picker. Library table: state badge; a filter "Assumed values". Parts: a part with an assumed power shows a warning chip (closes the "watts 0" flag's gap).
- **Checks.** `part_source_checks`: a picked part with an assumed `unit_power_w` or `inrush_a` warns.
- **Tests.** `test_library_model.py::test_source_per_sized_field`, `test_shipped_library.py::test_every_shipped_part_has_a_source_or_assumed`, CSV round-trip, diff tests, `test_checks.py::test_assumed_power_warns`.
- **Acceptance.** Shipped library builds with every part sourced; editing a power without a source is refused with a message naming the field.
- **Size.** M.

### M68 Review queue and health

- **Goal.** The library owner sees what needs review and what is weak.
- **Depends on.** M67.
- **Decision.** None.
- **Library store.** `library_store/health.py`: counts by state; parts with an assumed source; parts without an alternative; obsolete parts used by projects on this PC (scan the workspace's substation files); brand sets missing a rating the sizing can ask for (compare `McbCatalogue` ratings with the standard list); housekeeping roles unfilled per brand.
- **API / UI.** `library_health` endpoint; Library gains *Review* and *Health* tabs. Review: draft and reviewed records with their missing sources, *Mark reviewed*, *Release* (owner), *Send back* with a note; each action is a pending edit as today. Health: the counts as cards with a list under each and "Go to the record".
- **Tests.** `tests/unit/library_store/test_health.py` one test per measure; API tests; E2E of the two tabs.
- **Acceptance.** Shipped library shows 0 draft, the assumed count, and the brand gaps if any; a draft added through CSV appears in Review.
- **Size.** M.

### M69 Propose from project

- **Goal.** A project override that corrects a library value can be sent to the library as a pending edit with its source.
- **Depends on.** M67.
- **Decision.** None.
- **API / UI.** `propose_library_edit(project, sub, equipment_index, field)`: creates a pending library edit for the part with the override's value, state `draft` unless the record is released and the owner confirms, source kind `measured` or `datasheet` chosen in a small dialog with a ref. Parts: on an overridden value's menu, "Propose for the library…". Library review lists it with "From project X".
- **Tests.** `test_app_library_edit.py::test_propose_from_project_creates_pending_edit_with_source`, E2E.
- **Acceptance.** Overriding the RTAC's power on Parts and proposing it shows in Library › Review with the project name and the ref typed.
- **Size.** S.

## Cross-cutting rules and definition of done

**Spec and ADRs.** The spec stays authoritative. A milestone that makes a fixed quantity an input adds one sentence where the rule lives ("Make spare count a panel input" is the existing pattern) and leaves the example values as they are. ADRs 0031 to 0037 are drafted by the agent from `0000-template.md`, listed in `docs/decisions/README.md`, and only Ali marks them Accepted. Questions Q62 to Q67 go to `docs/plan.md` §6 with the card's answer.

**Docs that move with every milestone.** `docs/plan.md` §3 (input schema) and §4 (milestone table, status); `docs/ui/screens.md` and `editing.md` (screen and field inventory); `schemas/` regenerated (`bomgen schema`); `CHANGELOG.md` `[Unreleased]`; `docs/backlog.md` row for Ali's request ("Engineer-controlled workflow", this plan's link); `docs/handoff/` when the session ends.

**Golden and example.** `examples/` reproduces the spec's example with every new input unset. A milestone may add a second example substation (`examples/substations/gis02`) to exercise its inputs, with its own golden file citing the rule it proves, never by editing gis01.

**Library data.** A new library field needs: the model, `data/library/psa-devices.yaml` regenerated through `build.py` (no diff when the field defaults), the CSV table column (ADR 0018), the `.bomlib` schema version bump when a required field is added (ADR 0008), the device-editor field, `docs/plan.md` §3.3.

**Release.** Phases ship as minor versions: A and B as v0.4.0, C and D as v0.5.0, E and F as v0.6.0, each by the release PR that bumps the version and adds the changelog section, as `STATE.md` "How a release happens" says. No tags pushed by anyone.

**Definition of done, per milestone**

- [ ] ADR or question answered by Ali when the entry says so
- [ ] Tests written first and named after the rule; model, engine, io, API, UI assets
- [ ] Golden tests pass unchanged, or the ADR says which value moves and why
- [ ] New inputs default to today's behaviour and round-trip through the YAML writers
- [ ] Derived values carry `rule`; the UI shows value, rule, marker, reset through the M48 component
- [ ] Gate green: ruff, format, mypy, pytest; installer build green when `app/` changed
- [ ] Screenshots of each new state in `/mnt/project-files/a11-screens/<milestone>/`, linked in the PR
- [ ] `docs/plan.md`, `docs/ui/*.md`, `schemas/`, `CHANGELOG.md` updated in the PR
- [ ] PR body starts with the attribution block, ends with the footer; assignee set; subscribed; squash-merged when green with no conflict
- [ ] `docs/handoff/` updated in a docs-only PR when the session stops
