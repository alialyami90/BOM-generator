# M1c Network Sizing and Panel Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Size the L1 and L2 switches of a substation from its IED count and spares, and fill 32U panels automatically (A units in odd panels, B units in even ones, common devices spread, overrides and removals), writing today's `panels/*.yaml`.

**Architecture:** Two pure modules. `engine/sizing.py` turns numbers into a `NetworkPlan` and port plans (R1–R4); `engine/layout.py` turns a list of placeable units into numbered panels plus issues (R5–R9). Both work on small engine dataclasses, not on the M1b models, so their tests are independent of A2's field names; one adapter task (Task 5) maps the loaded substation onto them and the result back onto `Panel` models. Nothing is written to disk by the engine; `bomgen layout` writes the files.

**Tech Stack:** Python 3.12 stdlib (`dataclasses`, `fractions`, `math`), pydantic v2 models from M1/M1b, PyYAML for the generated files, typer for the CLI.

**Spec:** design `docs/superpowers/specs/2026-10-28-substations-and-auto-layout-design.md` (rules R1–R10, section 5), ADR 0013, plan section 4 "M1c". Generator spec sections cited by name: "Tag naming conventions", "Derivation rules → Network accessories", "How each panel BOM groups its materials".

## Global Constraints

- Starts when A2's M1b models are on `main`. Tasks 1–4 only need the M1 enums (`PortSpeed`, `Media`) and can be reviewed against this plan before then.
- Owned files: `src/bomgen/engine/sizing.py`, `src/bomgen/engine/layout.py`, `tests/unit/engine/test_sizing.py`, `tests/unit/engine/test_layout.py`, `tests/golden/layout/`. `src/bomgen/engine/__init__.py` is A9's (import-free); create the same empty file only if M2 is not on `main` yet. `cli.py` gets one `layout` command, after telling A2.
- Port fractions are computed exactly: `Fraction(str(port_fraction))`, never float multiplication (26 × 0.8 must be 20.8, 30 × 0.9 must be 27).
- IEDs never reach a panel, a description, a tag or a generated file (R4). `ied_count` appears only in `LayoutReport` lines.
- Blank space is never a part or a BOM row (Q25); it exists only in the U arithmetic and the report.
- Defaults (all inputs, ADR 0013): `port_fraction` 0.20, `sfp_per_l1` 3, `rack_u_reserved` 10, `enclosure_u` 42, `panel_capacity_u` 32, `blank_plate_u` 1, `ring_max_switches` 6, `l1_uplinks_per_switch` 1, `l1_interlink` true, `l3_uplinks_per_l2` 2.
- Tests are named after the rule they pin: `test_r1_...` to `test_r10_...`.
- Never write `.xlsx`; tests write only under `tmp_path`.

## Review Focus

1. **No IEDs, or an IED count that fits exactly.** `ied_count: 0` gives no L1 switches and no L1 row, but still one L2 per side; 20 IEDs on 20 usable ports gives 1 L1, 21 gives 2. (Task 1: `test_r1_zero_ieds_needs_no_l1_switch`, `test_r1_boundary_counts`.)
2. **Spares that leave no usable port.** `port_fraction: 1.0`, or more reserved ports than the switch has, must give a readable `SizingError` naming the switch, not a `ZeroDivisionError` or zero switches. (Task 1: `test_r1_no_usable_port_is_an_error`.)
3. **A device taller than the usable space.** A 40U device in a 32U panel cannot be placed by any fill; it gets its own panel and a `device-too-tall` error instead of an endless loop or a silent overfill. (Task 3: `test_r5_device_taller_than_capacity_is_reported`.)
4. **Overrides that point at nothing.** A moved or removed unit that no longer exists (`#3` of an equipment entry that now has 2 units, or a deleted equipment id) (fewer IEDs after an edit), or a move to panel 9 of 2, is reported and ignored; the rest of the layout still comes out. (Task 4: `test_r7_stale_override_is_reported_and_ignored`, `test_r7_move_to_unknown_panel_is_reported`.)
5. **Layouts that leave a panel empty.** Only common devices (no redundant pair), or moves that empty panel 3, must not write an empty panel file (the `Panel` model needs one device); an empty trailing panel is dropped and an empty middle one is a `panel-empty` error. (Task 2: `test_r6_only_common_devices_opens_one_pair_and_drops_empty_b`; Task 4: `test_r7_move_that_empties_a_panel_is_reported`.)

## Decisions this plan makes (raise in review if wrong)

- **R1 with port roles.** A port group's `usable_for` is `ied`, `uplink` or `any`. Reserved ports come first from `uplink` groups, then from `any`; IED ports are `ied + any − reserved taken from any`. RST2228-L1-24MM (24 × 100M fixed `ied`, 4 × 1G SFP `any`) gives 24 + 4 − 2 = 26 → 20, the design's number. If its SFP slots were `uplink`, it would be 24 → 19.
- **R3 L1 SFPs.** Each side's L1 row gets `uplinks: count = n_l1 × reserved` (uplink + interlink in a star, two ring ports in a ring), 1G MM, `spare: sfp_per_l1` once per row, as today's `=24+3` adds 3 to the whole row.
- **R3 L2 port plan.** Counts are row totals (as in today's port plans): `uplinks_l3` = `l3_uplinks_per_l2 × n_l2` 1G SM; `downlinks` = the L1 links as 1G MM plus each equipment's L2 ports at the speed and media of its L2 link, grouped by (speed, media) in first-seen order.
- **R7 a move that does not fit** is applied as asked and reported as `move-does-not-fit`, so the Panels board shows the panel over 32U in red; no other device moves.
- **R9 numbering.** Units are numbered per side in fill order (L1 A11, A12, … across panels 1, 3, …; L2 A01, A02). A generated row whose numbering does not start at the tag rule's first number carries it in `first_nn` (A2 field, below); tag text itself is built by A9's `engine/tags.py`, never here.

## Inputs this plan needs from A2 (M1b) and A1

A2 agreed these names for M1b (`models/substation.py` unless noted); Task 5 uses them.

- `Equipment(part_id, role, redundant=False, side=none, qty=1, l2_ports=0, l2_speed="1G", l2_media="MM")`; `qty` is rejected on `l1_switch` (the sizer counts those).
- `Substation.generated_panels: GeneratedPanels | None`: templates `id`, `cabinet_number`, `cabinet_name`, `tag_prefix`, `sheet_name` with one `{n}` placeholder and an optional format spec (`"861-GIS01-PSA-{n:04d}"`, `"PSA{n}"`, `"psa{n}"`); `kind` (default network), `enclosure`, `document` key, `options` for every generated panel and `options_by_panel: dict[int, dict]` merged over them (validated by the loader as `PanelOptions`).
- `Panel.generated: bool = False`; `DeviceInstance.first_nn: PositiveInt | None = None`.
- Library: `DeviceType.height_u: int | None`, `PortGroup.usable_for: PortUse` (`ied | uplink | any`, default `any`), `Catalogues.enclosure_u = 42`.
- `io.loader.load_substation(path, *, store=None) -> LoadedSubstation` with `.substation`, `.project`, `.library`, `.documents`, `.constants`, `.spares` (merged with project defaults), `.panels`, `.panel_files`, `.manual_panel_ids`, `.panel_capacity_u`.
- Example substation: `examples/substations/gis01/substation.yaml` (40 IEDs, star, A3's `height_u` values).

- Every `Equipment` has a required unique `id` (slug: `l2`, `l1`, `ext-esw`, `ext-fw`, `fopp`, `gw`, `gps`, `rtac`, `hwio` in the example). Layout inputs name ids, never tags (A1): `UnitRef(device, unit: int | None, side: "a" | "b" | None)`, `DeviceMove(UnitRef + panel)` (side required on redundant entries), `PairMove(pair, unit: int | None, panel: (a, b))`, `removed: list[UnitRef]`; `None` means every unit or both sides. The loader checks ids exist; a unit number above the computed count is this engine's `stale-override`/`stale-removal`. Task 5 maps these onto the engine's `UnitRef`, `Move`, `PairMove`. Tags stay A9's (`engine/tags.py`) and are not needed here.

Settled by A1:

- **Golden R10:** with 40 IEDs R1 gives 2 L1 switches per side, not the spec example's 6, and the port plans differ from the hand-written ones (L1 SFPs 2 × 2 + 3 = 7, not 24 + 3). The golden records the rule results; the hand-written example panels keep every BOM golden value.
- **UI contract** (`docs/ui/screens.md` → "What the app needs from the engine"): `layout_preview(substation, overrides) -> LayoutResult` with panels, U used, blank plates, DIN-rail counts and move errors; `NetworkPlan` read-only; stable equipment ids.
- **Cable managers** (Q32, Ali 2026-10-28: count them): every rack-mounted switch or patch panel unit (`network_switch`, `firewall`, `patch_panel` with `height_u > 0`) takes a 1U cable manager directly under it. The pair is one block of `height_u + 1` with no blank plate inside it; blank plates go between blocks. `Unit` gets `cable_manager_u: int = 0` (1 for those categories) and `used_u` counts it. The panel's cable-manager count goes to A9's step 3 instead of today's fixed 9.
- **Port spare** (Ali 2026-10-28): default stays 20 %, editable per substation. Each IED has one port on side A and one on side B, so `ied_count` IEDs need `ied_count` ports per side (R1 as written).
- **L1 switch model** (Ali 2026-10-28: the tool picks one, or the engineer selects the model): the sizer tries every library device with `category: network_switch` and `purdue_level: L1` and keeps the one with the fewest switches per side; ties go to the fewest total ports, then the lowest `part_id`. The engineer's selection is an `l1_switch` equipment entry with a `part_id`, which pins the model (asked of A2: make `part_id` optional on that role). L2 stays the engineer's choice.

---

### Task 1: L1 and L2 switch counts (R1, R2)

**Files:** Create `src/bomgen/engine/sizing.py`; Test `tests/unit/engine/test_sizing.py`.

**Produces:**
- `Topology(StrEnum)`: `STAR = "star"`, `RING = "ring"`.
- `SizingError(Exception)` with a readable message naming the switch part.
- `@dataclass(frozen=True) SwitchPorts(part_id: str, ied: int, uplink: int, any: int)` with `total` property.
- `@dataclass(frozen=True) NetworkInputs(ied_count: int, topology: Topology = STAR, ring_max_switches: int = 6, l1_uplinks_per_switch: int = 1, l1_interlink: bool = True, l3_uplinks_per_l2: int = 2, port_fraction: float = 0.20)`.
- `@dataclass(frozen=True) L2Link(owner: str, ports: int, speed: PortSpeed, media: Media)` — one per equipment entry on that side or common.
- `l1_reserved_ports(net: NetworkInputs) -> int`; `l1_usable_ports(ports: SwitchPorts, net: NetworkInputs) -> int`; `l2_usable_ports(ports: SwitchPorts, net: NetworkInputs) -> int`; `l1_links(n_l1: int, net: NetworkInputs) -> int`.
- `@dataclass(frozen=True) NetworkPlan(ied_count, l1_per_side, l1_usable_ports, l1_links_per_side, rings_per_side, l2_per_side, l2_usable_ports, l2_demand_per_side)`.
- `size_network(net: NetworkInputs, l1: SwitchPorts, l2: SwitchPorts, links: Sequence[L2Link]) -> NetworkPlan`.
- `rank_l1_switches(candidates: Sequence[SwitchPorts], net: NetworkInputs) -> list[tuple[SwitchPorts, int]]`: every candidate with a usable port and its L1 count per side, best first (the order above); the Network tab shows it so the engineer can pick another model.
- `pick_l1_switch(candidates, net) -> SwitchPorts`: the first of `rank_l1_switches`; empty → `SizingError`. `rings_per_side` is 0 in a star; `l2_per_side` is at least 1.

- [ ] **Write the failing tests** (RST2228 L1 = `SwitchPorts("RST2228-L1-24MM", ied=24, uplink=0, any=4)`, L2 = `SwitchPorts("RST2228-L2", 0, 0, 28)`):
  - `test_r1_star_reserves_uplink_and_interlink` → 2; `test_r1_star_without_interlink_reserves_one` → 1; `test_r1_ring_reserves_two_ring_ports` → 2.
  - `test_r1_usable_ports_keep_twenty_percent_spare`: RST2228 → 20; with `port_fraction=0.1` → 23 (26 × 0.9 = 23.4); with `SwitchPorts(.., ied=24, uplink=4, any=0)` → 19.
  - `test_r1_forty_ieds_need_two_l1_switches_per_side` (Ali's example): `size_network(NetworkInputs(ied_count=40), ...)`.l1_per_side == 2.
  - `test_r1_boundary_counts`: 20 → 1, 21 → 2, 120 → 6.
  - `test_r1_zero_ieds_needs_no_l1_switch`: l1_per_side 0, l1_links 0, l2_per_side 1.
  - `test_r1_no_usable_port_is_an_error`: `port_fraction=1.0` and `SwitchPorts(.., ied=1, uplink=0, any=1)` each raise `SizingError` whose message contains the part id.
  - `test_r1_tool_picks_l1_switch_with_fewest_switches`: 40 IEDs, candidates 16-port (`ied=14, any=2`, 11 usable → 4), 28-port (`24, 0, 4`, 20 → 2), 48-port (`44, 0, 4`, 36 → 2) → the 28-port (tie with the 48-port on 2 switches, fewer ports).
  - `test_r1_ranking_lists_every_candidate_with_its_count`: `rank_l1_switches` returns `[(28-port, 2), (48-port, 2), (16-port, 4)]`.
  - `test_r1_pick_tie_breaks_on_part_id`; `test_r1_pick_without_a_usable_candidate_is_an_error`.
  - `test_r2_star_links_one_port_per_l1_switch`: 6 L1 → 6; with `l1_uplinks_per_switch=2` → 12.
  - `test_r2_ring_takes_two_ports_per_ring`: 6 L1 → 2; 7 → 4; 13 with `ring_max_switches=6` → 6.
  - `test_r2_l2_usable_ports_reserve_l3_uplinks`: RST2228 L2 → 20.
  - `test_r2_spec_example_needs_one_l2_per_side`: `ied_count=120` (6 L1) + GPS 1 → demand 7, l2_per_side 1.
  - `test_r2_demand_over_capacity_adds_l2_switches`: links summing 30 with 0 IEDs → l2_per_side 2.
- [ ] Run `pytest tests/unit/engine/test_sizing.py -v`; expect ImportError.
- [ ] Implement in `sizing.py`; `math.ceil`, `math.floor` on `Fraction`.
- [ ] Run; all pass. Run the three checks from `CLAUDE.md`.
- [ ] Commit `feat(sizing): size L1 and L2 switches from the IED count (R1, R2)`.

### Task 2: Port plans and the IED rule (R3, R4)

**Files:** Modify `src/bomgen/engine/sizing.py`; Test `tests/unit/engine/test_sizing.py`.

**Consumes:** Task 1. `PortPlan`, `PortAllocation` from `bomgen.models.panel`.
**Produces:** `l2_port_plan(plan: NetworkPlan, net: NetworkInputs, links: Sequence[L2Link]) -> PortPlan`; `l1_port_plan(plan: NetworkPlan, net: NetworkInputs, sfp_per_l1: int) -> PortPlan | None` (None when there is no L1 switch).

- [ ] **Write the failing tests:**
  - `test_r3_l2_plan_has_l3_uplinks_as_single_mode`: `uplinks_l3 == [PortAllocation(count=2, speed="1G", media="SM")]`; with 2 L2 per side → count 4.
  - `test_r3_l2_downlinks_group_l1_links_and_equipment_by_speed_and_media`: 2 L1 + FW 1 × 1G MM + GPS 1 × 100M MM + RTAC 2 × 1G MM → `[(5, 1G, MM), (1, 100M, MM)]` in that order.
  - `test_r3_l1_plan_is_used_ports_plus_spare_per_row`: 2 L1, star → `uplinks == [PortAllocation(count=4, speed="1G", media="MM", spare=3)]`; ring → count 4; `sfp_per_l1=0` → spare 0.
  - `test_r3_no_l1_switch_has_no_l1_plan`.
  - `test_r4_ied_count_never_reaches_a_port_plan`: build both plans with `ied_count=37` and assert neither `model_dump_json()` contains `"37"` nor `"ied"` (case-insensitive).
- [ ] Run; fail. Implement. Run; pass. Checks. Commit `feat(sizing): generate L1 and L2 port plans (R3, R4)`.

### Task 3: Panel fill and A/B streams (R5, R6)

**Files:** Create `src/bomgen/engine/layout.py`; Test `tests/unit/engine/test_layout.py`.

**Produces:**
- `Side(StrEnum)`: `A`, `B`, `NONE = "none"`.
- `@dataclass(frozen=True) Unit(key: str, side: Side, part_id: str, rank: int, height_u: int)` — `key` is `<equipment id>#<n>`; a redundant unit's A and B halves share the key and differ in `side`, so `(key, side)` identifies one unit; `rank` is the equipment's position in BOM group order.
- `@dataclass(frozen=True) LayoutRules(capacity_u: int = 32, blank_plate_u: int = 1)`.
- `@dataclass PanelFill(number: int, units: list[Unit])` with `used_u(rules) -> int`, `free_u(rules) -> int`, `blank_plates() -> int` (rack units − 1, min 0) and `din_rail_count() -> int` (units with 0U), the numbers the Panels board shows.
- `IssueKind = Literal["device-too-tall", "move-does-not-fit", "stale-override", "stale-removal", "unknown-panel", "panel-empty", "missing-height"]`; `@dataclass(frozen=True) LayoutIssue(kind: IssueKind, subject: str, message: str)`.
- `@dataclass Layout(panels: list[PanelFill], issues: list[LayoutIssue])`.
- `used_u(heights: Sequence[int], blank_plate_u: int) -> int`: `Σ h + (k − 1) × blank_plate_u` over the k units with `h > 0`; 0 for k = 0.
- `fill(units: Sequence[Unit], rules: LayoutRules) -> Layout`: A units in `rank` order into odd panels, B units into even panels, breaking at the same places (lock-step), then each `Side.NONE` unit in `rank` order into the panel with the most free U (ties → lowest number), opening the next odd/even pair when none fits. A trailing empty panel is dropped.

- [ ] **Write the failing tests** (units built with a helper `u(key, h, side, rank, cm=0)`):
  - `test_r5_cable_manager_sits_under_its_switch`: a 1U switch with `cable_manager_u=1` then a 1U device → 1 + 1 + 1 gap + 1 = 4U; the cable manager adds no blank plate.
  - `test_r5_blank_plate_between_neighbours`: `used_u([1, 2, 1], 1) == 6`; `used_u([1], 1) == 1`; `used_u([], 1) == 0`.
  - `test_r5_din_rail_parts_cost_nothing`: `used_u([1, 0, 1], 1) == 3`.
  - `test_r5_fill_stops_at_32u_and_opens_a_new_panel`: 17 A/B pairs of 1U → 1 + 16 × 2 = 33 > 32, so panels 1–2 hold 16 pairs (31U) and panels 3–4 hold 1.
  - `test_r5_exact_fit_stays_in_the_panel`: 11 pairs of 2U → 22 + 10 = 32 → one pair of panels.
  - `test_r5_device_taller_than_capacity_is_reported`: a 40U pair → its own panels and one `device-too-tall` issue per unit; the other units still placed.
  - `test_r6_a_units_odd_panels_b_units_even`: every unit in panel 1, 3 is side A; 2, 4 side B; panel 2n holds the partners (same `key`) of panel 2n − 1, in the same order.
  - `test_r6_units_follow_group_order`: units given out of `rank` order come out sorted by `rank`, then by key.
  - `test_r6_common_devices_go_to_most_free_panel`: panels 1/2 at 13U each; GPS 1U → panel 1 (tie, lowest); RTAC 2U → panel 2; IO 1U → panel 1 (17 free vs 16).
  - `test_r6_common_device_that_fits_nowhere_opens_a_new_pair`: both panels at 31U, a 2U common unit → panel 3, panel 4 not written.
  - `test_r6_only_common_devices_opens_one_pair_and_drops_empty_b`: one common 1U unit → one panel, number 1.
- [ ] Run; fail. Implement. Run; pass. Checks. Commit `feat(layout): fill 32U panels with A/B streams and common devices (R5, R6)`.

### Task 4: Overrides, removals and the fill report (R7, R8)

**Files:** Modify `src/bomgen/engine/layout.py`; Test `tests/unit/engine/test_layout.py`.

**Consumes:** Task 3.
**Produces:**
- `@dataclass(frozen=True) UnitRef(key: str, side: Side)`; `@dataclass(frozen=True) Move(unit: UnitRef, panel: int)`; `@dataclass(frozen=True) PairMove(key: str, panels: tuple[int, int])` (A half to `panels[0]`, B half to `panels[1]`).
- `auto_layout(units: Sequence[Unit], rules: LayoutRules, *, removed: Sequence[UnitRef] = (), moves: Sequence[Move | PairMove] = ()) -> Layout`: drop `removed` units, `fill`, then apply moves in order. A move to panel `count + 1` or `count + 2` opens the next pair; a higher number is `unknown-panel`. Within a panel, units stay sorted by `rank`, then key.
- `fill_lines(layout: Layout, rules: LayoutRules) -> list[str]`: one `"Panel {n}: {used} U / {capacity} U"` line per panel, gaps included.

- [ ] **Write the failing tests:**
  - `test_r7_removed_unit_is_dropped_before_the_fill`: removing a common unit changes where the next common unit goes.
  - `test_r7_move_one_unit_to_another_panel`; `test_r7_move_a_pair_moves_both_sides` (`PairMove("fw#1", (3, 4))` opens panels 3/4).
  - `test_r7_move_that_does_not_fit_is_reported_not_reflowed`: unit lands in the full panel, one `move-does-not-fit` issue, every other unit where `fill` put it.
  - `test_r7_stale_override_is_reported_and_ignored`: `Move(UnitRef("l1#3", A), 1)` when only `l1#1`, `l1#2` exist → `stale-override`; an unknown removed unit → `stale-removal`.
  - `test_r7_move_to_unknown_panel_is_reported`: panel 9 of 2 → `unknown-panel`, unit stays.
  - `test_r7_move_that_empties_a_panel_is_reported`: moving the only unit out of panel 3 of 4 → `panel-empty`; out of the last panel → panel dropped, no issue.
  - `test_r7_overrides_survive_a_rerun`: `auto_layout` twice with the same inputs gives equal layouts.
  - `test_r8_fill_lines_count_the_gaps`: panel with 1U, 2U, 1U → `"Panel 1: 6 U / 32 U"`.
- [ ] Run; fail. Implement. Run; pass. Checks. Commit `feat(layout): apply overrides and removals, report panel fill (R7, R8)`.

### Task 5: Substation adapter, generated panels and `bomgen layout` (R4, R9)

**Files:** Modify `src/bomgen/engine/layout.py`, `src/bomgen/cli.py` (one command, A2 told first); Test `tests/unit/engine/test_layout.py`, `tests/unit/test_cli.py` (layout cases only).

**Consumes:** Tasks 1–4; `load_substation`, `Equipment`, `GeneratedPanels` (names above); no tag function: units are keyed by equipment id. An equipment part with `height_u: None` is a `missing-height` issue and is placed as 0U; an explicit 0 is a DIN-rail part.
**Produces:**
- `@dataclass LayoutReport(ied_count: int, port_lines: list[str], fill_lines: list[str], issues: list[LayoutIssue])` with `lines() -> list[str]` (`"IED count: 40"` first; port lines `"{tag}: {demand} of {usable} usable ports"`; `has_errors`).
- `@dataclass LayoutResult(panels: list[Panel], fills: list[PanelFill], plan: NetworkPlan, report: LayoutReport)` — `fills` carry the unit keys, U used, blank plates and DIN-rail counts for the Panels board.
- `layout_preview(loaded: LoadedSubstation, overrides: LayoutOverrides | None = None) -> LayoutResult`: the UI entry point (`docs/ui/screens.md`); `overrides` (A2's model for `layout.overrides` + `removed`) replaces the file's when given, so the board previews a drag before saving.
- `layout_substation(loaded: LoadedSubstation) -> LayoutResult` = `layout_preview(loaded)`: size (Tasks 1–2), expand equipment into `Unit`s (L1 × `l1_per_side`, L2 × `l2_per_side`, others × `qty`, keys `<id>#1…`; `redundant` → an A and a B unit with the same key), `auto_layout`, then group each panel's units back into `DeviceInstance`s (consecutive units of one part → one row with `qty` and `first_nn`), attach port plans to the panels that hold the switches, and build `Panel` models with `generated=True`. Panels with `kind: console` are not touched.
- `render_panel_yaml(panel: Panel) -> str`: header comment `# Generated by bomgen layout. Edit layout.overrides in substation.yaml, not this file.`, then the model dump with `exclude_defaults=True`.
- CLI: `bomgen layout --substation PATH [--out DIR]` writes `panels/<id>.yaml` next to the substation (or into `--out`), prints `report.lines()`, exits 1 when `has_errors`.

- [ ] **Write the failing tests** (substation built with the M1b builders in `tests/unit/builders.py`):
  - `test_r9_l1_numbering_continues_across_panels`: 24 L1 units per side that need two panel pairs → panel 3's L1 row has `first_nn` equal to panel 1's count + 11.
  - `test_r9_b_panels_are_written_in_full`: every generated panel is a `Panel`, none a `PanelMirror`; panel 2's rows carry `lan: B`.
  - `test_r4_generated_files_never_mention_ieds`: `render_panel_yaml` of every panel contains neither the IED count nor `ied`; `report.lines()[0] == "IED count: 40"`.
  - `test_r3_port_plans_sit_with_their_switches`: panel 1 has the L2 and L1 plans keyed by part id; panel 2 the same counts.
  - `test_r7_console_panels_are_left_alone`.
  - `test_r7_preview_overrides_replace_the_files_overrides`: `layout_preview(loaded, LayoutOverrides(...))` moves the unit; the loaded substation is unchanged.
  - `test_r5_missing_height_is_reported`: an equipment part without `height_u` gives one `missing-height` issue naming the part.
  - `test_cli_layout_writes_panels_and_prints_fill` (`CliRunner`, `tmp_path`): exit 0, two panel files written, output contains `"32 U"`; `test_cli_layout_exits_1_on_layout_errors`.
- [ ] Run; fail. Implement. Run; pass. Checks. Commit `feat(layout): generate panel files and add bomgen layout (R9)`.

### Task 6: Layout golden (R10)

**Files:** Create `tests/golden/layout/expected_panels.yaml`, `tests/golden/layout/test_layout_golden.py`; Modify `tests/golden/README.md` only through A7 (send A7 the line).

**Consumes:** Task 5, A2's `examples/substations/gis01/substation.yaml` (40 IEDs, star) and A3's `height_u` values.

- [ ] Write `expected_panels.yaml`: for each generated panel, its number, used U, and rows (`part_id`, `qty`, `lan`, `first_nn`) and port plans; each value commented with the rule it comes from (R1 → 2 L1 per side, R2 → demand and 1 L2 per side, R3 → plans, R6 → where GPS, RTAC and I/O land). With 1U for every rack device except a 2U RTAC, the design reads panel 1 = A units + GPS + I/O and panel 2 = B units + RTAC; the file records whatever the confirmed heights give.
- [ ] `test_r10_example_substation_layout_matches_golden` loads the example substation, runs `layout_substation` and compares with the YAML; `test_r10_example_substation_has_no_layout_errors`.
- [ ] Run; pass. Checks. Commit `test(layout): golden layout of the example substation (R10)`.
- [ ] Open the PR (draft until Ali confirms the golden through A1), subscribe to it, and send A1 the number.
