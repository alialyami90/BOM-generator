# M20 Part overrides and derived parts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a substation's equipment entry carry a BOM part number, overrides of the library
data and an SFP choice, and make every engine step use them, with no engine step changed except
the layout's part lookup and the SFP pick.

**Architecture:** The loader turns each equipment entry that has `ordering_code`, `overrides` or
`sfp` into a *derived part*: a copy of the library part with those values, id
`<part_id>+<equipment id>`, `derived_from` set, added to that substation's resolved library only.
The layout writes the derived id into generated panels, so the BOM, MCB sizing, power and heat
steps read the derived part like any other.

**Tech Stack:** Python 3.12, pydantic v2, pytest, ruff, mypy (CLAUDE.md).

**Spec:** `docs/superpowers/specs/2026-10-31-part-picking-design.md` §2, §4, §7.1, §9.

## Global Constraints

- Gate before every commit: `ruff check . && ruff format --check .`, `python -m mypy`,
  `python -m pytest -q -p no:cacheprovider`.
- TDD; tests named after the rule. Conventional commits. One PR for the milestone.
- Golden values must not move (`pytest tests/golden`); the example has no overrides.
- `schemas/*.json` regenerated in the same PR (`bomgen schema`).
- Every `examples/` file still round-trips byte-identical (`tests/unit/test_round_trip.py`).
- New defaults that no source gives carry `# ASSUMED` (waist 1000 mm, rack start 200 mm).

## Review Focus

1. An override on an L1 or L2 switch entry with no `part_id` (sized switch): refused with a
   located message "pick the switch to override its data" — not silently ignored.
2. A derived id that collides with a library part id: located loader issue, no crash.
3. An override that breaks a library rule (e.g. `power_supplies: 2` with `supply_type: VAC`):
   located issue on the equipment entry, same message the library check gives.
4. The L1 ranking (Network page) must not list derived parts as extra candidates.
5. Two substations overriding the same part differently: each gets its own derived part; the
   project library is unchanged.

---

### Task 1: Model fields

**Files:**
- Modify: `src/bomgen/models/substation.py` (`EquipmentRole`, `Equipment`)
- Modify: `src/bomgen/models/library.py` (`Category`, `DeviceType`)
- Modify: `src/bomgen/models/project.py` (`Defaults`)
- Test: `tests/unit/test_substation_model.py`, `tests/unit/test_library_model.py`,
  `tests/unit/test_project_model.py`

**Interfaces:**
- Produces:
  - `class PartOverrides(InputModel)` in `models/substation.py`: all optional —
    `height_u: NonNegativeInt | None`, `unit_power_w: NonNegativeFloat | None`,
    `supply_type: SupplyType | None`, `voltage_v: PositiveInt | None`,
    `power_supplies: Literal[0, 1, 2] | None`, `inrush_a: PositiveFloat | None`,
    `load_type: LoadType | None`; method `values() -> dict[str, object]` (only the set ones).
  - `class SfpChoice(InputModel)`: `speed: PortSpeed`, `media: Media`, `part_id: PartId`.
  - `Equipment.ordering_code: str | None = None`, `Equipment.overrides: PartOverrides | None = None`,
    `Equipment.sfp: list[SfpChoice] = []`.
  - `EquipmentRole` adds `TIME_SERVER="time_server"`, `OPERATOR_WS="operator_ws"`,
    `ENGINEERING_WS="engineering_ws"`, `DA_SERVER="da_server"`, `KVM="kvm"`, `CONSOLE="console"`,
    `ANNUNCIATOR="annunciator"`, `TIME_ACCESSORY="time_accessory"`.
  - `Category` adds `KVM="kvm"`, `CONSOLE="console"`.
  - `DeviceType.derived_from: PartId | None = None`, `DeviceType.sfp_choice: list[SfpChoice] = []`
    (move `SfpChoice` to `models/library.py` and import it in `substation.py` to avoid a cycle).
  - `class LayoutDefaults(InputModel)` in `models/project.py`: `waist_height_mm: PositiveInt = 1000`,
    `rack_start_mm: NonNegativeInt = 200`; `Defaults.layout: LayoutDefaults = LayoutDefaults()`.

- [ ] **Step 1: Write the failing tests**

```python
def test_overrides_need_a_part_id_on_a_sized_switch():
    with pytest.raises(ValidationError, match="pick the switch to override its data"):
        Equipment(id="l1", role="l1_switch", redundant=True, overrides={"height_u": 2})


def test_sfp_choice_is_for_l1_and_l2_switches_only():
    with pytest.raises(ValidationError, match="sfp is for L1 and L2 switches"):
        Equipment(
            id="gw",
            part_id="X",
            role="other",
            sfp=[{"speed": "1G", "media": "MM", "part_id": "SFP-1"}],
        )


def test_partoverrides_values_lists_only_what_was_set():
    assert PartOverrides(height_u=2).values() == {"height_u": 2}


def test_layout_defaults_are_1000_and_200_mm():
    assert Defaults().layout == LayoutDefaults(waist_height_mm=1000, rack_start_mm=200)
```

Plus one test that `Category("kvm")` and `Category("console")` parse, and one that a library file
device with `derived_from` set is refused by `Library` ("derived_from is set by the loader").

- [ ] **Step 2: Run, expect FAIL** — `python -m pytest tests/unit/test_substation_model.py tests/unit/test_library_model.py tests/unit/test_project_model.py -q`
- [ ] **Step 3: Implement the fields and validators above.** `Equipment._consistent` adds the two
  refusals (overrides or ordering_code with `part_id is None`; `sfp` on a role other than L1/L2).
  `Library` refuses a device with `derived_from` or `sfp_choice` set (the loader builds derived
  parts with `model_construct`-free `model_copy`, after validation).
- [ ] **Step 4: Run, expect PASS**, then `bomgen schema` and the full gate.
- [ ] **Step 5: Commit** `feat(models): part overrides, BOM part number and SFP choice on equipment`

### Task 2: Derived parts in the loader

**Files:**
- Create: `src/bomgen/io/derived.py`
- Modify: `src/bomgen/io/loader.py` (`_load_substation`, before `_resolve_panels`)
- Test: `tests/unit/test_derived_parts.py`

**Interfaces:**
- Consumes: Task 1 fields.
- Produces:
  - `derived_id(entry: Equipment) -> str` → `f"{entry.part_id}+{entry.id}"`.
  - `needs_derived(entry: Equipment) -> bool` → any of ordering_code, overrides, sfp is set.
  - `effective_part_id(entry: Equipment) -> str | None` → derived id if needed, else `entry.part_id`.
  - `derive_parts(library: Library, substation: Substation) -> tuple[Library, list[tuple[Loc, str]]]`
    → library with derived devices appended, plus `(location, message)` problems.

- [ ] **Step 1: Write the failing tests**

```python
def test_part_number_box_is_the_bom_ordering_code():
    lib, problems = derive_parts(
        LIB,
        sub_with(
            Equipment(id="ows", part_id="SEL-3355", role="operator_ws", ordering_code="3355#ABC")
        ),
    )
    part = next(d for d in lib.devices if d.part_id == "SEL-3355+ows")
    assert (part.code, part.derived_from, problems) == ("3355#ABC", "SEL-3355", [])


def test_override_replaces_only_the_values_given():
    lib, _ = derive_parts(
        LIB,
        sub_with(
            Equipment(
                id="ows", part_id="SEL-3355", role="operator_ws", overrides={"unit_power_w": 120}
            )
        ),
    )
    part = next(d for d in lib.devices if d.part_id == "SEL-3355+ows")
    assert (part.unit_power_w, part.height_u) == (120, 3)


def test_an_override_that_breaks_a_library_rule_is_a_located_problem():
    _, problems = derive_parts(
        LIB,
        sub_with(
            Equipment(
                id="ows", part_id="SEL-3355", role="operator_ws", overrides={"supply_type": "VAC"}
            )
        ),
    )
    assert problems == [
        (("equipment", 0, "overrides"), "power_supplies above 0 needs supply_type VDC")
    ]


def test_a_derived_id_taken_by_a_library_part_is_a_problem(): ...
def test_two_substations_get_their_own_derived_parts(): ...  # load_project on a two-sub fixture
def test_no_overrides_leaves_the_library_unchanged():
    lib, _ = derive_parts(LIB, EXAMPLE_SUB)
    assert lib is LIB
```

`LIB` is `examples/library.yaml` loaded; `sub_with` builds on `tests/unit/builders.py`.

- [ ] **Step 2: Run, expect FAIL** — `python -m pytest tests/unit/test_derived_parts.py -q`
- [ ] **Step 3: Implement.** Re-validate each derived part with
  `DeviceType.model_validate({**base.model_dump(exclude_unset=True), **overrides.values(),
  "ordering_code": ..., "part_id": derived_id, "derived_from": base.part_id,
  "sfp_choice": entry.sfp})` (the pydantic error's first message becomes the problem), and append
  with `library.model_copy(update={"devices": [...]})`. Bypass the Task 1 `Library` refusal by
  building the new list after `Library` validation (`model_copy` does not re-validate).
  In `_load_substation`, call it after `resolve_catalogues` and turn problems into `Issue`s with
  `source.line_for(loc)`.
- [ ] **Step 4: Run, expect PASS**; run `pytest tests/golden tests/unit/test_round_trip.py`.
- [ ] **Step 5: Commit** `feat(io): derived parts carry an equipment entry's overrides`

### Task 3: Layout and sizing use the derived part

**Files:**
- Modify: `src/bomgen/engine/layout.py` (`_part_id`, `l1_candidates`)
- Test: `tests/unit/engine/test_layout.py` (or the existing layout test module)

**Interfaces:**
- Consumes: `effective_part_id` (Task 2).

- [ ] **Step 1: Failing tests**
  - `test_override_height_moves_the_layout`: example substation with the gateway entry overridden
    to `height_u: 10`; `layout_preview` shows the gateway unit `height_u == 10` and the written
    panel row has `part_id == "SEL-3555-GW+gw"`.
  - `test_l1_ranking_ignores_derived_parts`: an L1 entry with `part_id` and `ordering_code`;
    `l1_candidates` lists no id containing `+`.
  - `test_an_l1_override_applies_to_the_sized_switch`: L1 entry `part_id="RST2228-L1-24MM"`,
    `overrides={"unit_power_w": 50}`: every written L1 row names `RST2228-L1-24MM+l1`.
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement.** `_part_id` returns `effective_part_id(entry)` when it is set for L1/L2
  too, else the plan's pick; `l1_candidates` filters `d.derived_from is None`. Port data for the
  derived L1 comes from the derived part, which copies the base's ports.
- [ ] **Step 4: Run, expect PASS**; full gate.
- [ ] **Step 5: Commit** `feat(layout): place derived parts`

### Task 4: SFP choice

**Files:**
- Modify: `src/bomgen/engine/network.py` (`_sfp_for`)
- Test: `tests/unit/engine/test_network.py` (existing SFP tests' module)

- [ ] **Step 1: Failing tests**
  - `test_sfp_choice_replaces_the_automatic_pick`: an L2 row whose device has
    `sfp_choice=[SfpChoice(speed="1G", media="MM", part_id=<second matching SFP>)]` gets that SFP.
  - `test_sfp_choice_for_another_media_keeps_the_automatic_pick`.
  - `test_an_sfp_choice_that_does_not_fit_the_ports_is_an_engine_error` (wrong speed → message
    "<host>: SFP <id> is not <speed> <media>").
- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Implement.** In `_sfp_for`, look up `row.device.sfp_choice` for the allocation's
  speed and media first; check the chosen part is an SFP with a matching port; else today's pick.
- [ ] **Step 4: Run, expect PASS**; full gate.
- [ ] **Step 5: Commit** `feat(network): honour the equipment's SFP choice`

### Task 5: Docs, ADR, check-report warning

**Files:**
- Create: `docs/decisions/0024-part-overrides-and-derived-parts.md`; row in `docs/decisions/README.md`
- Modify: `docs/spec/generator-spec-v2.md` ("Inputs the tool needs": equipment fields; "Data model
  and generation order": derived parts), Ali approved the design 2026-10-31
- Modify: `docs/plan.md` (milestones M19–M24, questions Q42–Q50 with Ali's card answers a–i)
- Modify: `src/bomgen/checks.py` + test: warning "`<equipment id>`: no part number; the BOM prints
  the library model" for a placed entry without `ordering_code` whose library part has none
  (spec §7.1). Test `test_a_device_without_a_part_number_warns`.
- Modify: `CHANGELOG.md` `[Unreleased]` Added.

- [ ] **Step 1:** failing warning test → implement → pass.
- [ ] **Step 2:** write ADR 0024 (Proposed; Ali marks Accepted), spec, plan, changelog.
- [ ] **Step 3:** full gate; `python data/library/build.py` shows no diff.
- [ ] **Step 4: Commit** `docs: ADR 0024 part overrides and derived parts` and open the PR.
