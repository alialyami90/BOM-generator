# Plan: Substation SCADA BOM generator

Status: implemented. M0–M11 are on main (v0.1.1); M12–M18 are the next version, tracked in
[`backlog.md`](backlog.md). Changes go through the review flow in `docs/agents.md`.
Spec: [`docs/spec/generator-spec-v2.md`](spec/generator-spec-v2.md). Sections are
cited by name; this plan does not restate them.

## 1. Scope and approach

`bomgen` reads three YAML input sets (device library, panel definitions, project
settings) and writes the single .xlsx workbook the spec describes, plus a check
report. The pipeline follows "Data model and generation order" and is split into
three layers (ADR 0005):

```
YAML ──load/validate──▶ input models ──engine (steps 1–11, 15)──▶ BomLines, PowerLines,
                                                                   HeatLines, HeatChecks
      ──sheets (steps 12–13)──▶ sheet models (cells, formulas, styles, merges, print, header/footer)
      ──writer (step 14)──▶ .xlsx
```

Python computes every value (so rules and golden numbers are tested without
Excel), and the sheet layer emits the same values as live formulas (OUT-5).

The generator is delivered as a CLI first (M1–M7), then as an installable
Windows desktop app with shareable device-library update packages (M8–M11).

Milestones are built by agents working in parallel; who owns which milestone and
files, and the review and merge order, are in [`agents.md`](agents.md).

Stack: as briefed (ADR 0002), with one agreed deviation: write the file with
**XlsxWriter** because openpyxl cannot put the logo picture in the page header
(ADR 0003). openpyxl stays for reading files back in tests.

### Glossary

Terms from ADR 0012 and ADR 0013; the rules themselves are in those ADRs and the
design they cite.

| Term | Meaning |
| --- | --- |
| Project | A folder with `project.yaml` (project info, library name and version, document register, defaults) and its substations. Exported, imported and backed up as one `.bomproj` file. |
| Substation | One site of a project, in `substations/<id>/` with `substation.yaml`, its `panels/` and its `out/`. Its constants and spares override the project defaults key by key. |
| System | Everything one substation produces: its panels, BOM, calculation sheets and workbook. Each substation has exactly one. |
| Side | A or B: which unit of a redundant pair a device is. A device with `side: none` belongs to neither side. |
| Stream | The panels one side fills: stream A in the odd panels (1, 3, …), stream B in the even panels (2, 4, …), so panel 2n holds the partners of panel 2n − 1 (ADR 0013, rule R6). |
| Common device | A device with no side (`side: none`), such as the GPS clock, RTAC or Axion I/O. It shares the A/B panels; there is no separate common panel (Q26). |
| Override | An engineer's change to the automatic layout: `layout.overrides` moves a device or pair after the fill, `layout.removed` drops one before it. Overrides survive re-running the layout. |

## 2. Module breakdown

### 2.1 Package layout

```
src/bomgen/
  models/
    library.py      DeviceType, PortGroup, ChildRule, TerminalRule, LooseItem,
                    commodity catalogues (MCB, aux contact, terminal blocks,
                    busbars, housekeeping kits)
    panel.py        Panel, Enclosure, DeviceInstance, PortPlan, PanelOptions,
                    DocumentInfo, RevisionMarks
    project.py      Project, DesignConstants, OutputSettings, LooseExtra
    bom.py          Group (A–H), BomLine, Qty (int | "1 Lot" | formula), MergeSpan
    calc.py         PowerLine, HeatLine, ForcedVentCheck, NaturalConvCheck
    sheet.py        SheetModel, Cell, StyleToken, PrintSetup, SheetHeaderFooter
  io/
    loader.py       YAML → models; resolves file references and panel mirroring
    errors.py       readable validation errors (file, path, message)
  engine/
    units.py        step 1  expand instances into units (multi-qty, mirroring)
    tags.py         step 1  tag + description building ("Tag naming conventions")
    kits.py         step 2  child kit rows, loose items
    network.py      step 3  SFPs per host switch, FOPP pigtails, cable managers,
                            serial cables
    power.py        step 4a per-device power, current, MCB sizing columns (N–R)
    thermal.py      step 4b forced-vent and natural-convection checks, ventilation choice
    housekeeping.py step 5  group D kit
    ac_dist.py      step 6  group E
    dc_dist.py      step 7  group F (mains from ΣQ, branches, spares, QCOD, aux)
    terminals.py    step 8  group G
    grounding.py    step 9  group H
    hwio.py         step 10 HWIO per row, per panel, DI capacity
    assemble.py     step 11 order A→H, separators, SR.NO, parent/child merges
    pipeline.py     runs steps 1–11 per panel, then 12, 15; returns BuildResult
  sheets/
    styles.py       style tokens from "Formatting" (fonts, fills, borders, sizes)
    bom_sheet.py    step 12 panel BOM sheet (+ loose-material table on the WS sheet)
    power_sheet.py  step 12 Power Consumption
    heat_diss_sheet.py  step 12 Heat Dissipation
    heat_calc_sheet.py  step 12 Heat Calculations
    header_footer.py    step 13 page header / footer per sheet
  writer/
    xlsx.py         step 14 SheetModel → .xlsx (only module importing XlsxWriter)
  checks.py         step 15 check report
  revision.py       OUT-8 revised-cell highlighting
  library_store/    M8  .bomlib pack/import/verify, installed-library store, diff, rollback
  app/              M10 Windows desktop app: pywebview window + Python API for the UI
    __init__.py     import-free (ADR 0009), so launcher.py never pulls in the window
    launcher.py     M11 frozen-app entry points (app_main, cli_main, --self-test);
                    M10 plugs the window in here, M8 the .bomlib import
    ui/             M9 HTML/CSS/JS from the impeccable design
  cli.py            typer app: build, validate, library pack/import/list/rollback
packaging/          M11 PyInstaller spec, Inno Setup script, icons
```

### 2.2 Mapping to "Data model and generation order"

| Spec step | What | Module(s) | Produces |
| --- | --- | --- | --- |
| Entities: Project, DeviceType, Panel, DeviceInstance | input entities | `models/*`, `io/loader.py` | validated models |
| 1 | expand units, build tags | `engine/units.py`, `engine/tags.py` | group A–B `BomLine`s |
| 2 | child kit rows, loose items | `engine/kits.py` | child `BomLine`s (parent link), loose list |
| 3 | network accessories | `engine/network.py` | group C `BomLine`s |
| 4 | device power, heat checks, ventilation | `engine/power.py`, `engine/thermal.py` | `PowerLine`s, `HeatLine`s, checks, ventilation mode |
| 5 | housekeeping kit | `engine/housekeeping.py` | group D |
| 6 | AC distribution | `engine/ac_dist.py` | group E |
| 7 | DC distribution, mains from ΣQ | `engine/dc_dist.py` | group F |
| 8 | terminal strips | `engine/terminals.py` | group G |
| 9 | grounding busbars | `engine/grounding.py` | group H |
| 10 | HWIO sums, DI coverage | `engine/hwio.py` | per-row `hwio`, panel totals |
| 11 | ordering, SR.NO, separators, merges | `engine/assemble.py` | ordered `BomLine`s with `sr_no`, `merge span` |
| 12 | calc sheets, loose-material table | `sheets/*.py` | `SheetModel`s |
| 13 | page header/footer | `sheets/header_footer.py` | `SheetHeaderFooter` per sheet |
| 14 | write .xlsx | `writer/xlsx.py` | the workbook |
| 15 | check report | `checks.py` | report (text/JSON), CLI exit code |
| Entity: BomLine | | `models/bom.py` | |
| Entity: PowerLine / HeatLine | | `models/calc.py` | |
| Entity: SheetHeaderFooter | | `models/sheet.py` | |

Step 4 needs groups D–E (fans and thermostats draw AC power) before it can
decide whether those fans exist. `thermal.py` resolves this explicitly; see open
question Q4.

## 3. Input file schemas

A project is a folder (ADR 0012): `project.yaml` lists substations, each
substation file lists its panel files, and every path is relative to the file
that holds it. `bomgen validate FILE` loads a project or a substation (found
through the nearest `project.yaml` above it that lists it) and runs every
check without writing a workbook. All models use `extra="forbid"` so typos fail
validation. JSON Schemas are exported from the models into `schemas/` (for
editor completion and the UI). Layout of the example: `examples/project.yaml`,
`examples/library.yaml`, `examples/substations/gis01/{substation.yaml,panels/}`.

### 3.1 `project.yaml` (spec: Inputs → 3. Project settings; ADR 0012)

```yaml
project:
  id: jfgp2-pkg3
  name: "<project name>"               # header centre line 1
  client: null
  logo: assets/logo.png                # header left (&G)
library:                               # the installed library (ADR 0008)
  name: psa-devices
  version: 1.0.0
  file: library.yaml                   # optional: load this file instead of the store
documents:                             # the register (Q24); every key names its substation
  - { key: gis01-bom,   substation: gis01, doc_no: "...-001", rev: "02", issue_date: 2026-10-28 }
  - { key: gis01-power, substation: gis01, doc_no: "...-002", rev: "00", issue_date: 2026-10-28 }
defaults:                              # inherited key by key by every substation
  constants:                           # defaults = spec values
    dc_voltage_v: 125
    ac_voltage_v: 230
    power_margin: 0.25
    current_factor: 1.3
    btu_per_w: 3.41
    t_max_c: 35
    t_int_c: 25
    air_constant_m3k_per_wh: 4.1
    steel_coefficient_w_per_m2c: 5.5
    min_main_mcb_a: 6
    min_branch_mcb_a: 2                # ADR 0017, used by M15
    inrush_min_ms: 10                  # ADR 0017, used by M15
    dc_float_v: 140                    # battery float; checked against devices' input_v_max
  catalogue_choice: { mcb: default }   # brand set per catalogue (ADR 0017); unset = default
  spares:                              # ADR 0013; every spare is an input
    port_fraction: 0.20
    sfp_per_l1: 3                      # today's "=24+3"
    dc_branches_per_feed: 3            # for generated panels; panel options keep their own
    ac_branches: 1
    rack_u_reserved: 10                # 42U enclosure → 32U usable
substations:
  - substations/gis01/substation.yaml
```

### 3.2 `substation.yaml` (ADR 0012/0013)

```yaml
substation: { id: gis01, name: "GIS Substation" }   # BOM title line 2
document: gis01-bom                    # the workbook's document: OUT-2 file name
calculations:                          # calc sheets: register key + scope line
  power_consumption: { document: gis01-power, scope: "861-GIS01-PSA-001/002" }
  heat_dissipation:  { document: gis01-heat,  scope: "..." }
  heat_calculations: { document: gis01-heat,  scope: "..." }
panels:                                # sheet order (OUT-3); the layout (M1c) rewrites these
  - panels/psa1.yaml
  - panels/psa2.yaml
  - panels/psa3.yaml
manual_panels: [panels/ws.yaml]        # never touched by the layout; after `panels`
output:
  file_name: "{doc_no}_PSA_BOM_Rev{rev}.xlsx"   # OUT-2
  sheet_names: { loose_material: "Loose Material", power_consumption: "Power Consumption",
                 heat_dissipation: "Heat Dissipation", heat_calculations: "Heat Calculations" }
  power_footnotes: ["*Printer Power Consumption: 622 watts (Printing), …"]  # rows after NOTES; optional
constants: { t_max_c: 40 }             # optional overrides of the project defaults
spares: { port_fraction: 0.25 }        # optional overrides of the project defaults
catalogue_choice: { mcb: abb-s200m, mcb_dc: schneider-c60h-dc }   # optional; key by key; mcb_dc unset = as mcb (ADR 0023)
loose_material:                        # extras not tied to a device
  title: "PSA Panels Loose Material and Auxiliary Equipment"   # the table's title row
  host_panel: ws                       # its document heads the Loose Material sheet (ADR 0020)
  items:
    - { part_id: NAP-K55, children: [LPA37-696], fed_from: psa3 }   # Q13
    - { part_id: FO-PATCH-CORDS, qty: "1 Lot" }
    - { description: "Cable tray, 300 mm", qty: "1 Lot", tag: Tray }   # free text (ADR 0022)
equipment:                             # what the layout places (design 3.2)
  - { id: l2, part_id: RST2228-L2, role: l2_switch, redundant: true }       # exactly one
  - { id: l1, part_id: RST2228-L1-24MM, role: l1_switch, redundant: true }  # exactly one; no qty
  # l1_switch part_id is optional: left out, the tool picks an L1 network_switch
  # from the library; given, the engineer pinned it (must be L1 network_switch)
  - { id: ext-fw, part_id: FGR-60F, role: firewall, redundant: true, l2_ports: 1 }
  - { id: gps, part_id: SEL-2488, role: other, l2_ports: 1, l2_speed: 100M } # side: none
  # id: unique; overrides and the UI name ids, never tags
  # role: l1_switch | l2_switch | ext_switch | firewall | fopp | other
  # redundant (one unit per side) or side: none | a | b; qty (not on l1_switch);
  # l2_ports, l2_speed (default 1G), l2_media (default MM)
  # purpose, hwio_points: copied onto each row the layout writes (as on a panel row)
  # port_plan: per unit, scaled by the row's qty; not on l1_switch or l2_switch (sized)
network:
  ied_count: 40                        # never a BOM row (R4)
  topology: star                       # star | ring
  ring_max_switches: 6
  l1_uplinks_per_switch: 1
  l1_interlink: true
  l3_uplinks_per_l2: 2
layout:                                # panel capacity = enclosure_u − rack_u_reserved
  blank_plate_u: 1                     # space only, no BOM row (Q25)
  overrides:                           # written by the UI's Panels board; equipment ids
    - { device: l1, unit: 3, side: a, panel: 3 }   # unit 1-based; side for redundant
    - { pair: l1, unit: 2, panel: [3, 4] }         # both sides; no unit = every pair
  removed:                             # None = every unit / both sides
    - { device: gw, side: a }          # GW-1 only
generated_panels:                      # needed when equipment is given; {n} = panel number
  id: "psa{n}"
  cabinet_number: "861-GIS01-PSA-{n:04d}"
  cabinet_name: "PSA Cabinet - {n:03d}"
  tag_prefix: "PSA{n}"
  sheet_name: "{n}"
  kind: network
  enclosure: { make: Rawabi, model: "Fixed Frame", h_mm: 2100, d_mm: 1000, w_mm: 800,
               cable_entry: top }
  document: gis01-bom
  options: { dc_spare_branches_per_feed: 3 }   # every generated panel
  options_by_panel: { 2: { aux_socket_a: 10 } }
```

**Loading rules.** Substation `constants`, `spares` and `catalogue_choice` replace only the keys
they write; the merged constants are checked again (`t_max_c > t_int_c`). Every
document key a substation, its calculation sheets, `generated_panels` and its
panels name must be one of that substation's register entries. Equipment parts
must exist and carry `height_u`, and the two switch roles must be
`network_switch` parts. `rack_u_reserved` must be below `enclosure_u`. A
library given by name and version comes from the installed store; a missing
version is a located error. Validating one substation loads the whole project
that lists it, so a sibling substation's errors are reported too.

### 3.3 `library.yaml` (spec: Inputs → 1. Device library)

```yaml
devices:
  - part_id: RST2228-L1-24MM
    category: network_switch           # enum; decides group A–H and rules
    make: Ruggedcom
    model: RST-2228
    ordering_code: "6GK6222-6AB00-5CC0-Z A05+B05+C05+D05+E05+F05+G05"
    description_template: "LAN-{lan} Industrial Ethernet switch (Level-1) (24 MM FO Ports)"
    tag_type: ESW
    purdue_level: L1                   # L1 | L2 | EXT | L3 | null
    tag_pattern: null                  # optional, see Q12 (FOPP, gateway)
    supply_type: VDC                   # VDC | VAC | null
    voltage_v: 125
    unit_power_w: 77
    load_type: CONTINUOUS              # CONTINUOUS | INTERMITTENT
    power_supplies: 2                  # 2 dual feed | 1 via change-over diodes | 0 passive
    min_branch_mcb_a: 2
    alarm_on_branch_mcb: false
    hwio_points: 1
    di_inputs: 0                       # hardwired DIs one unit provides (check report)
    height_u: 1                        # rack units (ADR 0013); 0 = DIN rail; null = not given
    ports:                             # usable_for: ied | uplink | any (default any)
      - { count: 24, speed: 100M, media: MM, kind: fixed, usable_for: ied }
      - { count: 4, speed: 1G, kind: sfp_slot, usable_for: uplink }
    cores: null                        # fibre cores, for children with qty "cores"
    children: []                       # [{ part_id, qty: <per parent unit> | "cores" }]
    terminals: []                      # [{ strip: "XDIP{slot}", block: UT-2.5-MT, count: 58,
                                       #    per: unit | serial_port, first_slot: D,
                                       #    description: "... {slot} ..." }]  # column C
    loose_items: []                    # [{ part_id, qty }]
    excluded_from_power: false
    alt_group: L1-SWITCH-24P           # optional; same key = interchangeable parts (ADR 0017)
    tier: mid                          # optional: low | mid | high
    inrush_a: 20                       # optional peak inrush current (M15)
    inrush_ms: 5                       # optional inrush duration (M15)
    input_v_min: 88                    # optional rated input range, V (check report)
    input_v_max: 150

catalogues:                            # the brand set named default
  enclosure_u: 42                      # rack units of the enclosure (ADR 0013)
  mcb:          { family: "Acti9 2P", make: Schneider, ratings_a: [1, 2, 6, 10, 16],
                  code_pattern: "A9F742{rating:02d}",   # or codes: {1: ..., 2: ...}
                  trip_curve: C, magnetic_trip_multiple: 5,      # optional (ADR 0017)
                  magnetic_trip_multiple_dc: 7, dc_rating_v: 125 }
  aux_contact:  { make: Schneider, model: A9A26924, ordering_code: A9A26924 }
  terminal_blocks:
    UT-16:      { make: Phoenix Contact, ordering_code: "3044199" }
    UT-2.5-MTD: { make: Phoenix Contact, ordering_code: "3064085" }
    UT-2.5-MT:  { make: Phoenix Contact, ordering_code: "3046362" }
  busbars:
    ac_safety_ground:  { tag: "AC SAFETY POWER-GROUND", description: "..." }  # tag = column B
    instrument_ground: { tag: "INSTRUMENT-GROUND", description: "..." }
  housekeeping:                        # part_ids of device records (ADR 0010)
    lamp:        { part_id: ... }
    door_switch: { part_id: ... }        # optional; omit when the lamp part includes it
    fan:         { part_id: ..., airflow_m3h: 358 }   # per fan (Q8)
    vent_filter: { part_id: ... }
    thermostat:  { part_id: ... }
    ipr_kit:     { part_id: ... }        # its device record lists relay, base, suppression, bracket
    change_over_diodes: { negative: ..., positive: ... }   # COD-1, COD-2
    socket:      { part_id: ..., rating_a: 10 }

catalogue_brands:                      # optional further brand sets (ADR 0017)
  mcb:             [{ id: abb-s200m, name: ABB S200M, family: ..., make: ABB, ... }]
  aux_contact:     [{ id: abb, make: ABB, model: ..., ordering_code: ... }]
  terminal_blocks: [{ id: weidmuller, name: ..., types: { UT-16: {...}, ... } }]  # all keys
  busbars:         [{ id: copper, entries: { ac_safety_ground: {...}, ... } }]      # all keys
  housekeeping:    [{ id: rittal, lamp: {...}, fan: {...}, ... }]                   # all roles
```

### 3.4 `panels/<id>.yaml` (spec: Inputs → 2. Panel definition)

```yaml
id: psa1
generated: false                       # true when the layout (M1c) wrote this file
cabinet_number: 861-GIS01-PSA-0001
cabinet_name: "PSA Cabinet - 001"
tag_prefix: PSA1
lan: A                                 # A | B | null
sheet_name: "1"
kind: network                          # network | control | console (selects terminal defaults)
enclosure:
  make: Rawabi
  model: "..."
  ordering_code: "..."
  h_mm: 2100
  d_mm: 1000
  w_mm: 800
  base_frame: { h_mm: 100, d_mm: 950, w_mm: 750 }   # optional plinth
  cable_entry: top                     # top | side
devices:                               # group B display order
  - { part_id: FOPP-96SM, qty: 1, purpose: "L2-L3 uplink to CCR" }
  - { part_id: RST2228-L2, qty: 1 }
  - { part_id: RST2228-L1-24MM, qty: 6 }   # first_nn: 15 continues a range (A15 to A16)
  - { part_id: RST2228-EXT, qty: 1 }
  - { part_id: GW-DHPCC, qty: 1, purpose: "for Dhahran PCC connection" }
  - { part_id: FW-EXT, qty: 1 }
port_plans:                            # per device, by part_id or tag; allocations are lists
  RST2228-L2:
    uplinks_l3: [{ count: 2, speed: 1G, media: SM }]
    downlinks:
      - { count: 6, speed: 1G, media: MM }
      - { count: 1, speed: 100M, media: MM }   # GPS clock
  RST2228-L1-24MM:
    uplinks: [{ count: 24, speed: 1G, media: MM, spare: 3 }]   # → "=24+3"
  # SEL-3555: { serial_ports: 6 }      # RTAC COM ports used (psa3)
options:
  aux_socket_a: null                   # e.g. 10 in psa2
  smoke_detector: true
  change_over_diodes: auto             # auto | true | false
  ventilation: auto                    # auto | forced | natural
  dc_spare_branches_per_feed: 3        # default 1
  ac_spare_branches: 1
  main_mcb_override_a: null
  inter_panel_terminals: 40
  terminal_overrides: {}               # e.g. { X4-DC1: 32 } where the spec gives no rule
  grounding_busbars: [ac_safety_ground, instrument_ground]
document: gis01-bom                    # register key: this panel's BOM header/footer
revision:
  highlight: []                        # [{ tag: PSA1-Q1.3, columns: [D] }] → yellow (OUT-8)
```

Mirroring (spec: "What changes by panel type", last paragraph; rules in ADR 0010):

```yaml
id: psa2
mirror_of: psa1                        # copy devices, port plans, options
cabinet_number: 861-GIS01-PSA-0002
cabinet_name: "PSA Cabinet - 002"
tag_prefix: PSA2
lan: B                                 # swaps A→B and 1→2 in tags
sheet_name: "2"
options: { aux_socket_a: 10 }          # merged over the mirrored options
document: gis01-bom
```

## 4. Milestones

Each milestone is one PR, starts with failing tests, and ends with lint, mypy and
tests green. Golden values come from the spec and are listed in section 5.

### M0 — Repo, spec, plan, CI (this PR)
Scaffold, spec in `docs/spec/`, ADRs, this plan, CI with docs-only gating.
**Done when:** Ali approves the plan; CI's `ci-status` is green.

### M1 — Input models, loaders, examples, `bomgen validate`
- pydantic models for library, panels, project (section 3); YAML loader with
  relative paths, mirroring, readable errors; JSON Schema export.
- `examples/` reproducing the spec's example project, transcribed from the
  example workbook (Q1).
- Typer app with `validate`, `schema` (writes the committed JSON Schemas in
  `schemas/`) and `--version`.
- Tests: schema accept/reject cases, mirroring swaps LAN and prefix, every
  example file loads, unknown `part_id` is reported with file and path, the
  committed schemas are current, and `tests/golden/test_example_inputs.py`
  checks the example inputs against the workbook and spec values.

### M1b — Projects, substations and the sizing inputs (A2, ADR 0012/0013)
- `project.yaml` (project info, library name/version, document register,
  defaults, substations) and `substation.yaml` (today's project settings plus
  `equipment`, `network`, `spares`, `layout`); loader resolves project →
  substations with key-by-key defaults; library `height_u`, port roles,
  `enclosure_u`; JSON Schemas; `bomgen validate` on a project or a substation.
- `examples/` becomes one project with one substation; the hand-written panels
  and every golden value stay as they are.
- Section 3 of this plan is rewritten by A2 with the new schemas (done).
- Also for M1c: `generated_panels` (identity of generated panels), equipment
  `qty`/`l2_speed`/`l2_media`, panel `generated` and device-row `first_nn`.

### M1c — Network sizing and automatic panel layout (A8, ADR 0013)
- `engine/sizing.py` (rules R1–R4 of the design) and `engine/layout.py`
  (R5–R9): L1/L2 counts from the IED count and spares, port plans, 32U fill
  with blank space, A/B streams, common devices spread, overrides and removals.
- `bomgen layout`; `bomgen build` runs it first unless `--no-layout`; generated
  `panels/*.yaml` with a `generated` header; check-report lines for port
  demand, panel fill, stale overrides and the IED count.
- The layout takes over a substation's `panels` list only once one of its files
  is `generated: true` (written by `bomgen layout`); until then `build` uses the
  hand-written panels as they are, which keeps the spec example and its goldens.
- The layout reports loose material whose `host_panel` or `fed_from` names a
  panel the layout no longer writes, and warns (`replaced-panel`) for each
  hand-written file still listed in `panels` that it replaces.
- `bomgen layout` (default folder) rewrites the `panels:` list to the files it
  wrote, keeping the file's comments, deletes generated files it no longer
  writes, and names hand-written files that left the list.
- Removed units are taken out before sizing the L2 switches: L1 links and
  equipment `l2_ports` (per entry, as R2 counts them) come from the kept units of
  each side, so their SFPs go too. A side whose kept L1 switches cannot carry
  the IEDs, or whose kept L2 switches cannot carry the demand, is a
  `port-capacity` error.
- A move to the next one or two panel numbers opens a new pair; a farther one is
  `unknown-panel`. A `pair` move on an entry without A/B units is a stale override.
- `bomgen build` prints layout warnings to stderr and stops with the whole
  report on errors; these lines join the M7 check report.
- After a layout, the annunciator's change-over diodes are fed from panel 001
  (side A), Ali's answer. `examples/` keeps psa3 for the hand-written goldens;
  the layout golden feeds the annunciator from psa1 through its input fixture.
- Golden R10: the example substation's generated panels in
  `tests/golden/layout/`, confirmed by Ali on 2026-10-28 (3 L1 switches per
  side from the rules, not the spec example's 6).
- Starts when M1b is on main.

### M2 — BOM groups A–D
- Steps 1, 2, 3, 5: enclosure row, group B units and tags (range tags, LAN/level
  tokens, gateway numbering, FOPP tag), kit children and loose items, SFPs per
  host switch from port plans (`=24+3` formula quantities), cable managers,
  RTAC serial cables, housekeeping kit with ventilation taken from the panel
  option (auto arrives in M4).
- Tests: one per rule in "Tag naming conventions" and "Network accessories
  (group C)"; golden group A–D rows for all four cabinets.
- Delivered in M2: `models/bom.py` (`BuildResult`, `PanelBom`, `LooseTable`,
  `BomLine`, `QtySum`) and `engine/` modules `tags`, `units`, `items`, `enclosure`,
  `kits`, `network`, `housekeeping`, `pipeline` (`build(loaded) -> BuildResult`).
  Output model and the SFP, cable-manager and housekeeping rules: ADR 0014. Golden
  rows in `tests/golden/expected_groups_a_d.py`.

### M3 — BOM groups E–H, HWIO, assembly
- Steps 6–11: AC distribution, DC distribution (branch numbering in group B
  order, spares, QCOD, aux contacts, mains from ΣQ), terminal strips, grounding,
  HWIO per row and per panel, ordering with separators, SR.NO, parent/child merges.
- Tests: one per rule in "Derivation rules" (DC, AC, breaker part numbers,
  terminal block table, HWIO); golden: Q1.1–Q1.13, CINC/Q1/Q2 ratings, every
  terminal quantity in the table, HWIO totals 17/17/6, SR.NO 1…71 on cabinet 001.
- Delivered in M3: `engine/` modules `mcb`, `ac_dist`, `dc_dist`, `terminals`
  (fixed strips by panel kind, plan Q6, and the devices' own strips), `grounding`,
  `assemble` (revision marks); `pipeline.build` now runs steps 1–3 and 5–11 in two
  passes, groups A–F of every panel first, because XDIN defaults to the
  substation's HWIO total. Tags honour `first_nn` (ADR 0013). Rules the spec states
  only by example: plan Q34 and ADR 0014. Golden rows in
  `tests/golden/expected_groups_e_h.py`.

### M4 — Power and heat engine
- Step 4 in full: PowerLines (DC/AC/external blocks), sizing columns N–R,
  block totals with margin, HeatLines, forced-vent airflow, natural-convection
  ΔT, combined line-up check, automatic ventilation choice feeding groups D/E/G.
- Tests: formulas from "Power Consumption sheet" and "Heat Dissipation and Heat
  Calculations sheets"; golden 2,177.5 W DC, 1,090.3 W AC, 3,267.8 W total;
  391/391/172 m³/h vs 716; Σ 954.8 vs 2,148 m³/h; WS A = 4.848 m², ΔT = 6.96 °C.
- Delivered in M4: `models/calc.py` (`PowerConsumption`, `HeatResult` and their
  parts, each power line pointing at its BOM row by `LineRef`; `OutputModel` moved
  to `models/output.py`), `engine/power.py`, `engine/thermal.py`. `BuildResult`
  gains `power` and `heat`. Ventilation `auto` follows the Q4 default: the natural
  rise of every powered part except fans, filters and thermostats decides, before
  groups D, E and G are built. The forced check compares each cabinet with the fan
  pair (2 × `fan.airflow_m3h`, Q8); the line-up check covers the fan-ventilated
  cabinets. Cable managers keep the M2 rule until M1c's layout gives a count for
  generated panels (Q32). The choice does not test the fans' throughput against
  the required airflow; each cabinet's `forced.passes` carries that result for the
  check report (step 15, M7).

### M5 — Sheet models with live formulas
- Steps 12–13: BOM sheet (incl. loose-material table), Power Consumption,
  Heat Dissipation, Heat Calculations as `SheetModel`s with formulas built from
  resolved addresses; page header/footer per sheet.
- Tests: every OUT-5 formula present at the right cell and pointing at the right
  source row; evaluating the formulas (Q15) gives the M4 numbers; header/footer
  strings per "Output requirements".
- Delivered in M5: `bomgen.sheets` (`build_workbook(loaded, result, logo=)`
  returns the `WorkbookModel`; one module per sheet, shared `styles` and `grid`).
  Layout decisions are in `docs/superpowers/plans/2026-10-28-m5-sheet-models.md`.
  Calculation-sheet header size comes from the top margin and print scale (Q11,
  at most 20 pt). The header logo is passed in resolved; the loader does not
  resolve `project.logo` yet. `tests/golden/test_workbook.py` evaluates every
  formula with pycel (Q15).

### M6 — Excel writer
- Step 14: XlsxWriter translation of sheet models: fonts, fills, borders,
  widths, heights, merges, number formats, hidden column H, print setup
  (A4, orientation, fit/scale, margins, print area, repeat rows 1:2,
  page-break preview), header logo, full recalculation on load.
- Tests reopen the file with openpyxl and assert formulas, styles, merges, print
  settings, header/footer strings; check the zip holds the header image; check
  no `.xlsx` lands in the repo.
- Delivered in M6: `bomgen.models.sheet` (`WorkbookModel` → `SheetModel` with
  `Cell` value or `Formula`, `CellStyle`, `Merge`, column/row formats,
  `PrintSetup`, `HeaderFooter` zones of runs plus an optional picture) and
  `bomgen.writer.write_workbook(model, path)`. Styles are concrete `CellStyle`
  values; the named styles of "Formatting" (the plan's style tokens) are M5's
  `sheets/styles.py`. Model units follow the spec: widths as Excel shows them,
  heights in points, margins in cm, 1-based rows and columns. Problems XlsxWriter
  would only warn about (header over 255 characters, truncated text, missing or
  unreadable logo) raise `WriterError` and leave no file. Plan:
  `docs/superpowers/plans/2026-10-28-m6-excel-writer.md`.

### M7 — Check report, revision highlighting, CLI polish, docs
- Step 15 check report (SFPs vs port plans, mains vs ΣQ, airflow vs required,
  DI capacity vs HWIO) as text and JSON; non-zero exit on failures.
- OUT-8 yellow highlighting from panel `revision.highlight` and/or a comparison
  with the previous issue (Q10).
- `bomgen build` final options (`--out`, `--compare`), README usage, example
  walkthrough. *`--sheet-name` dropped (A1, 2026-10-28):* sheet names come from the
  inputs (each panel's `sheet_name`, the substation's `output.sheet_names`).

*Engine half delivered (A9, ADR 0016):* `bomgen.checks.check_report(loaded,
result)` with `library_check`, `render_text`, `render_json` and `report.failed` for
the exit code; `bomgen.revision.read_previous_issue(path)` and
`compare_with_previous(result, previous)` mark changed cells and list the changes
(`render_revisions`). `BuildResult.mains` carries each panel's ΣQ, rating and rule
rating. ΣQ is now the cabinet's own DC loads, without loose loads it feeds through a
QCOD. A2 wired them into `bomgen build` and `--compare` (#62); M7 is done.

### M8 — Library update packages
Ali wants the device library updated on every installed copy by sharing an
update package (ADR 0008).
- `.bomlib` package format: a zip holding `manifest.json` (library name,
  version, schema version, minimum app version, release notes, SHA-256 of
  each file) plus `library.yaml` and any assets.
- Installed library store per Windows user under
  `%LOCALAPPDATA%\bomgen\libraries\<name>\<version>\`, with an
  `active` pointer and the previous versions kept for rollback.
- CLI: `bomgen library pack`, `bomgen library import <file.bomlib>`,
  `bomgen library list`, `bomgen library rollback`. Import validates the
  manifest, checksums and schema, shows added / changed / removed parts, and
  refuses downgrades unless forced.
- Projects record the library name and version they were built with; the
  check report warns when a project is rebuilt against a different version.
- `pack --add <dir>` carries extra directories such as `data/device-db/`;
  `import --dry-run` shows the diff without installing (the M10 import screen
  previews the same way).
- Tests: pack/import round-trip, corrupted or tampered package rejected,
  schema-version mismatch rejected, diff summary, rollback.
- Delivered in M8: `bomgen.library_store`, registered as `bomgen library ...`.
  `import` (and `import --dry-run`) validate the package's library with
  `bomgen.io.loader.load_library`, so a schema-invalid library is never
  installed. Recording the library name and version in projects needs the
  project model and the check report, so M7 wires `library_mismatch()` into the
  check report. Refusals carry a `RefusalKind` for the M10 import screen.

### M8b — `.bomproj` export, import and backup (A5, ADR 0012)
- `bomgen project export <project.yaml> [-o file]`, `import <file.bomproj>
  [--workspace dir] [--force]` and `backup <project.yaml>`; public functions
  `export_project`, `import_project`, `backup_project` and `default_workspace` in
  `bomgen.project_store`.
- A `.bomproj` is a zip of the project folder without any `out/` folder, the
  top-level `Backups/` folder, `.git/` and `*.bomproj` files, plus
  `manifest.json` (format version, project id, library name and version, app
  version, SHA-256 per file). The project id and library are read from
  `project.yaml` (`project.id`, `library.name`, `library.version`) as plain
  YAML, so M8b does not wait for the M1b models. Symlinks are never followed.
- The zip container, path and case checks, size cap and checksums are shared
  with `.bomlib` in `bomgen.bundle`; `.bomlib` behaviour did not change.
- Workspace: `BOMGEN_WORKSPACE`, else `Documents\BOM Generator`; a project
  lives in `<workspace>\<id>\`.
- Import verifies every checksum and path before writing. An existing project
  id is refused (`RefusalKind.PROJECT_EXISTS`) unless `--force`; a forced import
  saves the old project to its `Backups/`, keeps its `Backups/` and `out/`
  folders, replaces everything else, and restores the old project if the swap
  fails. Backups are `Backups/<id>-<YYYYMMDD-HHMMSS>.bomproj` and never
  overwrite one another.
- Import compares the manifest's library with the active one and returns a
  `library_note` saying how the library differs and a `library_hint` with the
  command: `bomgen library import <name>-<ver>.bomlib`, or `bomgen library
  rollback --to` when that version is installed but not active (resolves Q21).
  The CLI prints `note: ...` and `hint: ...`.
- Import also keeps `.git/` and `__pycache__/` folders (never packed), and
  refuses a package that holds `out/`, `.git/` or a top-level `Backups/`.
  A leftover `.replaced-<id>` folder in the workspace (Windows file locks) holds
  the previous project and is safe to delete once the new one looks right.
- Sharing the container made `pack --add` and `.bomproj` skip symlinks, where
  the first `.bomlib` code followed them; library names now also refuse
  Windows device names such as `con`.
- A `.bomlib` given to `project import` (and the reverse) gets a one-line
  explanation.
- The id and library are still read as plain YAML on purpose, not through the
  M1b `Project` model: a backup or export must work on a project the model would
  reject (a half-edited file). A test checks that the plain read agrees with the
  model on the example project.
- Device-database records in a `.bomlib` (follow-up for the Library screens,
  amendment to ADR 0008): `pack --add data/device-db` carries the records in a
  `device-db/` folder, validated at pack time; import extracts it; and
  `bomgen.library_store.load_device_records(store, name, version)` returns
  `dict[part_id, DeviceRecord]` (`{}` when absent).
- Dry-runs and backups for the UI (follow-up to M8b):
  Follow-up for the "What the app needs from the engine" rows. Nothing here changes
  how a package is built or installed.
  - Each dry-run returns a list of `Check(id, label, status, detail, kind)` in
    `bomgen.bundle.checks`; `status` is `ok`, `warning`, `failed` or `skipped`, and
    `kind` is the `RefusalKind` of a failed check. A failed check skips every check
    after it (`signature` always reads `skipped`), and the preview never raises for a bad package and writes nothing.
    `can_import` is true when no check failed.
  - `bomgen.library_store.preview_library_import(package, *, force=False, store=None)`
    returns `LibraryImportPreview(checks, manifest, files, previous, diff, can_import)`.
    Checks in order: `package`, `paths`, `size`, `manifest` (`INCOMPATIBLE` for
    a newer format, schema or app version, else `INVALID_PACKAGE`), `files`,
    `checksums`, `library`, `validation` (the build's loader), `version` (`DOWNGRADE` or
    `ALREADY_INSTALLED` fail, and become warnings with `force`), `signature`
    (always `skipped`: packages carry checksums only, plan Q18).
  - `bomgen.project_store.preview_project_import(package, *, workspace=None,
    store=None)` returns `ProjectImportPreview(checks, manifest, files, project_id,
    target_dir, exists, library_note, library_hint, suggested_id, can_import)`. Checks: the six above, then
    `identity` (manifest and `project.yaml` agree), `contents` (no build output),
    `name` (a warning when the project exists: import replaces it after a backup)
    and `library` (a warning carrying the `library_note`; the command is in
    `library_hint`).
  - Keep both: `import_project(..., rename_to=<id>)` imports under a new id
    (see the ADR 0012 amendment); the preview's `suggested_id` is a free id when
    the project exists.
  - Messages describe the state and never give a command. A command-line
    remedy is in `LibraryPackageError.hint` (and `library_hint`), which the CLI
    prints as `hint: ...` and the app can ignore or word its own way.
  - `bomgen.project_store.list_backups(project_file)` lists `Backups/` newest first
    as `BackupInfo(path, saved, size, project_id, library_name, library_version,
    file_count, problem)`, reading manifests only. A damaged file is listed with
    `problem` set. `restore_backup(backup)` is the forced import into the backup's
    own project, with the safety backup of the current state. Review it first with
    `preview_backup_restore(backup)`: a `ProjectImportPreview` whose first two checks,
    `location` (the file is in `<project>/Backups/`) and `folder` (its manifest names
    that project), are `restore_backup`'s two refusals, followed by the normal import
    checks; a failure skips every check after it.
  - Still open: "projects built with it" has no data source until M1b records the
    library on the project, and `InstalledLibrary.problem` needs wording from A4.

### M9 — UI design with impeccable
Use the `impeccable` skill to design the screens and elements: open or create a
project, edit panels and project settings, browse the installed device library
and import an update package, validate with readable errors, preview BOM groups
and the check report, build and save the .xlsx. Deliverables in `docs/ui/`:
- design tokens (colour, type, spacing, radius, elevation) in `tokens.json`
  (W3C design-tokens style);
- component specs (states, sizes, behaviour, accessibility notes) and screen
  layouts with the user flows;
- a clickable HTML/CSS prototype. With the desktop stack in ADR 0007 this
  prototype is the starting point of the real UI, not a throwaway.
Finish with an impeccable critique pass and Ali's review.

Status: accepted as a prototype (#8); design rework for projects/substations and the
panels board follows (`docs/ui/README.md`). ADR 0011 stays; critique pass results are in the README.

### M10 — Windows desktop app
Build the approved design as a Windows desktop app (ADR 0007): the M9 HTML/CSS
UI rendered in a native window with `pywebview` (Microsoft Edge WebView2),
calling `bomgen` in-process through a small Python API. No browser, no local
server port, works offline. The business rules stay in the engine. Ends with an
impeccable polish/audit pass against the M9 design.

Delivered in small PRs by A11, one screen group each (ADR 0015 for the bridge):

- **M10a shell:** the M9 prototype in `src/bomgen/app/ui/`, `bomgen.app.window.run_window`
  (the launcher's one call, wired by A6), `bomgen.app.api.Api` with `app_info`
  (version, the `.bomproj` the app was opened with, workspace, installed libraries),
  `ui/bridge.js`. pywebview is the `app` extra. `run_window` refuses to open when
  the UI files or (on Windows) the WebView2 Runtime are missing. Screens still show
  the prototype's example project and data; their tables are marked "not connected
  yet". A6's launcher wiring adds `bomgen/app/ui` to `packaging/bomgen.spec`
  (`collect_data_files("bomgen.app")`), which `collect_submodules` does not cover.
- **M10b:** Home, Project, Library and Backup and share on `bomgen.library_store` and
  `bomgen.project_store`, in two PRs. Library first: `library_overview` (the active
  library's devices joined to the device-database records it ships, through
  `load_device_records`; a damaged database is reported and the devices still show),
  `library_versions`, `preview_library_import`, `import_library`,
  `activate_library_version` and `choose_file` (the native open dialog). Refusals are
  read from the first failed check's `RefusalKind`; downgrade and reinstall offer the
  force checkbox, which runs the review again with `force`. `index.html` carries a
  Content-Security-Policy (`default-src 'none'`, scripts, styles and fonts from the UI
  folder only); `script-src` needs `'unsafe-eval'` because pywebview's injected
  `api.js` builds the API stubs with `new Function`.
  Projects second (`bomgen.app.projects`): `list_projects` (the workspace's
  `*/project.yaml` plus folders opened from elsewhere, remembered in
  `recent-projects.json` in the app home, `BOMGEN_APP_HOME` or `%LOCALAPPDATA%\bomgen\app`), `open_project`,
  `choose_project_folder`, `export_project` (native save dialog), `backup_project`,
  `list_backups`, `preview_project_import`/`import_project`,
  `preview_backup_restore`/`restore_backup` and `show_in_folder`. A project's status is
  the loader's error count, else "Library out of date" when the recorded library differs
  from the active one. The Project page is read-only: New project, New substation,
  Create from this and editing the overview, documents and defaults need project
  writers that do not exist yet, so they explain that the YAML files are edited for
  now. An import that clashes offers Replace (backed up first), Keep both (imported
  under the preview's `suggested_id` through `import_project(rename_to=)`, #53) or
  Cancel. The restore review runs `preview_backup_restore` (#59), so a backup outside its
  project's Backups folder shows as a failed check. The installed-versions table counts the
  projects built with each version. Until M10c the substation screens of a real project
  kept the example data under a "not connected yet" banner.
- **M10c:** Substation settings, Network and Panels after M1b and M1c. First the
  read side on the M1b models (`bomgen.app.substations`, `open_substation`): Settings
  (general, the calculation sheets' register documents, output file name and its
  result, the ten constants and the spares with the project default and a "Changed
  from" mark for the keys the substation writes, loose material, the YAML with its
  located problems) and Network's inputs (field network, equipment checked against the
  library, spares). Read-only until substation writers exist. Then the L1 ranking, the
  Result card and the Panels board (`bomgen.app.network`, `substation_layout`) on M1c's
  `layout_preview` of the substation as written: the `NetworkPlan` per side, the L1
  candidates in the engine's order (the pinned or picked one marked; usable ports
  rather than spare ports, which the engine does not give), and per generated panel
  its units with height, cable manager, U used and free, blank plates, DIN-rail count
  and a mark on units an override placed away from the automatic fill, plus the layout
  issues. For hand-written panels the board shows what the layout would write. Moves,
  deletions, pins and the panel editor wait for the substation writers.
- **M10d:** Checks, Preview and Build after M4, M5 and M7. First Checks and Build
  (`bomgen.app.output`): `run_checks` gives the substation's located problems (errors,
  plus the library-version note as a warning) and, when the files load, the M7 check
  report; `build_target` the file name from the pattern, the default folder
  (`<substation>/out`), the sheet names, library and revision; `build_workbook` runs the
  steps of `bomgen build` (engine, sheets, the optional comparison with a previous issue,
  the workbook and its `.checks.json`) and refuses `has_errors`, `file_exists` (the page
  asks before replacing), `file_open` (another program holds the file), `bad_name`,
  `bad_folder` (no folder, or not an absolute one), `bad_previous`, `engine` and `write`.
  `open_file` opens a workbook the app wrote. The build is one call, so the page shows
  one busy state rather than four named stages. Then Preview (`bomgen.app.preview`):
  `preview_substation` gives each panel sheet's rows (SR numbers, tag spans, separator
  rows, `24+3` quantities, HWIO, loose material under its host panel) and the Power
  Consumption, Heat Dissipation and Heat Calculations values from the engine's build
  result, or the reason there is nothing to show. The "Show revised cells" toggle is
  left out: cells are marked only by Build's comparison with a previous issue.
  Checks, Build and Preview re-lay out generated panels with M1c's `with_layout`, as
  `bomgen build` does: layout errors are located problems that block Build and Preview,
  warnings show in Checks.
- **M10e:** A4's impeccable polish pass. First round from A4's ranked findings
  (`m10e-polish-findings.md` in the project files): a compact Panels board header, equal
  twin columns, one "not available yet" line under every page's subtitle, an opacity pulse
  for the busy Build bar (the detector's marquee), a neutral "Partial" badge, and smaller
  fixes on the project, Library, Preview, Build, Network and Home screens. Done (#81);
  A4 recorded the departures the built app made from the design in `docs/ui/` (#82).

Status: done (M10a–M10e, #28 to #82). The app stays read-only on projects and
substations until the project and substation writers exist: creating projects and
substations, editing their settings, documents and defaults, and the Panels board's
moves, deletions, pins and panel editor are not available yet, and the app says to
edit the YAML files instead.

### M11 — Windows installer and releases
- Freeze the app with PyInstaller (one folder) and wrap it in an Inno Setup
  installer: per-user install (no admin rights), Start-menu shortcut,
  uninstaller, `.bomlib` file association so double-clicking an update
  package imports it, and a bundled default library.
- GitHub Actions job on `windows-latest` builds the installer when a version
  bump reaches main (or a version tag is pushed), tags the tested commit and
  attaches `bomgen-setup-<version>.exe` and the default `.bomlib` to a GitHub
  Release, so sharing is one download link.
- Code-sign the installer if a certificate is available (Q19), otherwise
  document the SmartScreen "More info → Run anyway" step.
- Tests: smoke test that the frozen app starts and builds the example
  workbook on the Windows runner.

*Built early (ADR 0009):* the installer pipeline landed before M1, M8 and M10.
`bomgen.app.launcher` runs the real CLI (`bomgen.cli`), imports a double-clicked
`.bomlib` through `bomgen.library_store`, and opens `bomgen.app.window` (M10)
for a plain start or a `.bomproj` file; the spec bundles the UI folder and
pywebview. The release workflow installs, checks and uninstalls the installer
on the runner, opens a `.bomlib` with the installed app, and starts the frozen
window, and runs `bomgen validate` and `bomgen build` on `examples/project.yaml`
from the frozen and the installed CLI, asserting the printed workbook exists. The
default library is bundled: the workflow packs `out/default.bomlib`, the installer
ships it, and the first start imports it into an empty library store (smoke-tested,
including that a reinstall leaves the store unchanged).
Releases start from main (ADR 0009, amended): merging a PR that bumps the version
and adds its `CHANGELOG.md` section builds, tags and publishes in one run, so no
one pushes a tag; the steps are in `packaging/README.md`.
The app icon comes with the M9 design (`packaging/icons/bomgen.ico`).

### M12–M18 — Next version (v0.2)

Ali's feedback on v0.1.0, point by point, is in [`backlog.md`](backlog.md). Each
milestone below is one PR (or one PR per owner where two owners share it), and the owner
writes its section's details when the work starts.

- **M12 — Cable managers as the gap (A8).** Backlog point 8. The one-blank-plate gap is only
  between two active devices. A cable manager is a passive plate and sits directly against
  the next device, so a block that ends in a cable manager needs no blank plate after it.
  This amends ADR 0013's R5. The layout goldens change as Ali directed.
- **M13 — Library model for alternatives and catalogue brands (A2, ADR 0017).** Backlog points
  1–3. Alternatives become library parts linked by an alternative-group key. Catalogue
  entries (MCBs, auxiliary contact, terminal blocks, busbars, housekeeping parts) get the
  same treatment, so a project can pick another brand. Devices gain the electrical fields
  that M15's MCB sizing needs, such as inrush current, and MCB catalogues gain their trip
  curve.
  *Details:*
  - Devices gain `alt_group`, `tier`, `inrush_a` and `inrush_ms`.
  - The MCB catalogue gains `trip_curve`, the AC and DC magnetic multiples, `dc_rating_v`,
    and `codes` as an alternative to `code_pattern`.
  - `catalogue_brands` holds further brand sets, and `catalogue_choice` on the project
    defaults or a substation picks one. The loader resolves each substation's
    catalogues, so the engine is unchanged.
  - New constants are `min_branch_mcb_a` and `inrush_min_ms`.
  - The example builds byte-identical apart from the workbook's timestamps.
  - Sections 3.1–3.3 show the keys.
- **M14 — Library data (A3).** Backlog points 2–3. Every alternative in `data/device-db/`
  becomes a full library part with its datasheet electrical data, and the catalogues get
  their alternative brands. The default library becomes psa-devices 1.1.0.
- **M15 — Branch MCB sizing from device data (A9, ADR 0019).** Backlog point 3. Ali's rule (Q35): the
  smallest catalogue MCB ≥ 1.3 × running current, ≥ inrush ÷ magnetic trip multiple, and ≥ 2 A.
  `dc_dist.branch_sizing` sizes every Q1.n, Q2.n and QCOD-n by it; an inrush counts when it
  lasts at least `inrush_min_ms` or its duration is unknown, and DC loads divide by the
  set's DC multiple where given. The device field `min_branch_mcb_a` is deprecated in
  favour of the design constant. `BuildResult.branch_mcbs` carries each sizing and the
  check report prints one `branch_mcb` line per MCB.
- **M16 — Library editing and CSV exchange (A5 store and CSV, ADR 0018; A11 app; A4
  design).** Backlog points 1 and 10. Add and edit devices and catalogue entries, saved as
  a new local library version. Export and import the library as CSV, with alternatives
  linked by their group key. The Library screen gets catalogue tabs and an alternatives
  list for comparing devices. Store side (`library_store`, after M13 is on main): the
  `export_csv`, `preview_csv_import` and `import_csv` functions with the dry-run checks of
  ADR 0018; an edit service (add, edit or delete a device or catalogue entry, validated
  against the model) that saves a new local version and keeps the old one for rollback; and
  the `.bomlib` export of an edited library as the backup. Import and edit share one
  save-a-new-local-version function. The tests include the round trip
  (library, CSV, library is equal).
  The store functions: `save_local_version`, `save_edits` (edit operations by path),
  `check_field`, `export_csv` / `preview_csv_import` / `import_csv`, and
  `LibraryStore.export_package` (the backup), with `bomgen library export`, `export-csv` and
  `import-csv` on the command line.
- **M17 — Project and substation editing (A2 writers; A11 app; A4 design).** Backlog points
  4, 7 and 9. Writers round-trip projects, substations and panels. The app creates projects
  and substations from scratch, every settings field is editable, and the Panels board gets
  drag and drop, pins and the panel editor. YAML and `.bomproj` files are then for import,
  export and backup only.
  *Details (A2 writers, ADR 0021):*
  - The writers round-trip with ruamel.yaml, keeping the files' comments and style.
  - Each writer checks the edited project before writing, writes nothing when the edit
    causes a problem, and returns the problems and the new layout preview.
  - M17a covers the generated-panel editor and the board: enclosure, document, options
    for every panel or one panel, port plans, and `layout.overrides` and `removed`.
  - M17b covers hand-written panel files.
  - M17c covers field writers for project and substation settings, list rows, the
    register's used-by list, per-field validation, confirming `ASSUMED` values and file
    fingerprints.
  - M17d covers create, rename and delete of projects and substations.
- **M18 — Loose material (A2 model; A9 engine; A10 sheet; A11 editor).** Backlog point 6.
  Each substation has its own editable loose-material list, on its own "Loose Material"
  sheet (Q36, ADR 0020) and in Preview.
  - Sheet side (A10, ADR 0020): the table moves off the WS console sheet onto its own
    "Loose Material" sheet (`output.sheet_names.loose_material`), placed after the cabinet
    BOMs and before Power Consumption. It uses the panel BOM layout, print setup and
    header, and its header and footer come from `host_panel`'s document. External Equipment
    references follow it. Revision comparison reads the new sheet and falls back to the
    host sheet's second table for older issues.
  - Model side (A2, ADR 0022): a loose item is a library part or free text (`description`
    in place of `part_id`, with no `children` or `fed_from`). A free-text row prints its
    description with make, model and ordering code left empty. `io/loose_edit.py` adds,
    replaces, removes and moves items, sets `host_panel`, and validates an item by field.

## 5. Testing strategy

- **Unit (TDD):** one test per rule, named after it, in `tests/unit/`.
- **Golden (`tests/golden/`, marker `golden`):** build from `examples/` and assert
  the values the spec states. Initial list:

  | Area | Expected (spec section) |
  | --- | --- |
  | Tags | PSA1-L2-ESW-A01; PSA1-L1-ESW-A11 to A16; PSA1-EXT-ESW-A; PSA1-EXT-FW-A; PSA1-FOPP-CCR-A01; PSA1-DHPCC-GW-1; PSA2-L2-ESW-B01; PSA2-L1-ESW-B11 to B16; PSA2-DHPCC-GW-2 (Tag naming conventions) |
  | DC branches | 13 per feed in 001/002 (10 used + 3 spare), Q1.2–Q1.7 = six L1 switches, firewall on Q1.10/Q2.10; 4 per feed in 003, 2 in WS (Derivation rules → DC) |
  | MCB ratings | branches 2 A; Q1/Q2 16 A in 001/002, 6 A in 003/WS; CINC 6/16/6/6 A; AC branches per the AC rule; codes A9F742xx, aux A9A26924 |
  | Aux contacts | DC 4/4/2/2; AC 3/3/3/1 |
  | Terminal blocks | every cell of the "Terminal block quantities (group G)" table |
  | HWIO | 17, 17, 6 |
  | Power | DC 2,177.5 W, AC 1,090.3 W, total 3,267.8 W |
  | Heat | 391, 391, 172 m³/h vs 716; Σ 954.8 vs 2,148 m³/h; WS A 4.848 m², ΔT 6.96 °C |

- **Writer:** reopen the generated file with openpyxl; assert formulas, styles,
  merges, hidden column H, print settings, header/footer strings.
- **Formula evaluation:** evaluate the written formulas in tests so the live
  workbook gives the same totals as the engine (Q15).

## 6. Open questions

Each has a proposed default that the plan assumes until Ali answers.

**Q35 — Branch MCB sizing rule** (M15; backlog point 3). *Resolved 2026-10-28:* Ali chose
"Computed, 2 A floor". A branch MCB is the smallest catalogue rating that meets all three:
at least 1.3 × the running current, at least the inrush current divided by the MCB set's
magnetic trip multiple (C curve: 5) when the device has an inrush figure, and at least 2 A.
This replaces the per-device `min_branch_mcb_a` as the floor (ADR 0019, A9).
Ali also chose "Ignore spikes under 10 ms": the inrush counts only when it lasts at least
`inrush_min_ms` (10 ms) or no duration is given, and a DC load uses the set's DC trip multiple when
it has one. A device with no inrush figure is sized by the running current and the floor.

**Q39 — Separate AC and DC MCB brands** (M13, M15; backlog point 3). *Resolved 2026-10-28:*
Ali chose "Separate AC and DC choices". A project or substation can choose the DC MCB brand set
apart from the AC one, so a DC-only range (for example C60H-DC under Q37) can feed the DC branches
while the AC branches keep an AC-rated set. The proposed shape, for ADR 0023 (B2): a
`catalogue_choice` key `mcb_dc` that falls back to `mcb` when unset, so existing projects and the
golden values do not change; `mcb` still refuses a brand that is not AC-rated (#145). B2 does the
model, loader and schema; B9 sizes DC branches, mains and CINC from the DC set.

**Q38 — Datasheet data in the shipped library** (M14; backlog point 3). *Resolved 2026-10-28:*
Ali chose "Real data in shipped library only". The researched datasheet inrush (SEL originals) and
DC input ranges go into the library the installer ships (psa-devices 1.1.0), so real projects size
their branch MCBs from them under Q35. `examples/library.yaml` stays the spec's example project
without them, so the golden values do not change. A3 generates both libraries from
`data/device-db`; A6 points `release.yml` at the shipped one.

**Q37 — Default MCB set for the 125 V DC feeds** (M14, M15). *Resolved 2026-10-28:* Ali chose
"Keep iC60N as default". The Schneider iC60N 2P (A9F742xx) is rated to exactly 125 V DC, while the
battery floats at about 135–140 V. It stays the default; the DC-rated ranges (Schneider C60H-DC,
ABB S200M UC, Siemens 5SY5) become selectable brand sets (A3, M14). The check report warns when a
DC MCB's `dc_rating_v` or a DC-fed device's `input_v_max` is below `dc_float_v` (140 V) (A9).

**Q36 — Where loose material goes** (M18; backlog point 6). *Resolved 2026-10-28:* Ali chose
"Its own sheet". Loose material moves off the WS console sheet onto a "Loose Material" sheet,
placed after the cabinet BOM sheets and before Power Consumption. This overrides the spec's
OUT-3 and its loose-material table on sheet 4 (ADR 0020, A10).

**Q1 — Example data is not in the spec (blocks M1 and the golden tests).**
*Resolved 2026-10-28:* Ali uploaded the example workbook; `examples/` is transcribed
from it (ADR 0010). The workbook itself stays out of git.
Still to add: `examples/assets/logo.png` (binary, not yet committed). `logo:` is
commented out in `examples/project.yaml` until it lands; the header writer
milestone needs it.

The spec gives rules and totals but not the per-device data behind them: most
unit wattages, full group B/C/D row lists, ordering codes, descriptions, port
plans, the WS console and loose-material rows, the enclosure codes, document
numbers, and the logo. Without them `examples/` can't reproduce 2,177.5 W /
1,090.3 W except by back-solving.
*Ask:* please upload the example workbook (.xlsx) the spec was written from, or
a device list with wattages. I'll transcribe it into `examples/` and keep the
workbook out of git (or under an explicit, git-allowed `tests/reference/` if you
want a cell-by-cell comparison).

**Q2 — Hidden masters + issued copies, or one sheet per cabinet?**
"Workbook map" lists hidden masters and issued copies; OUT-3/OUT-4 say one BOM
sheet per cabinet with HWIO hidden. *Default:* OUT-4, one sheet per cabinet
(ADR 0004), title row 90 pt, sheets named `1`–`4`.

**Q3 — Main MCB sizing rule doesn't reproduce 16 A.**
"Next standard size above ΣQ, minimum 6 A" with the catalogue sizes 1/2/6/10/16 A
gives 10 A for ΣQ ≈ 7.1 A, but the example uses 16 A. *Default:* implement the
rule with a configurable factor (e.g. size above 2 × ΣQ, or a minimum-16 A rule
for network cabinets) only after you confirm which one; until then the example
uses `main_mcb_override_a: 16` on 001/002 and the check report flags it.

**Q4 — Cabinet 003 ventilation contradicts the rule, and the rule is circular.**
Cabinet 003 needs 172 m³/h ⇒ about 420 W. With the 001 enclosure size
(2100 × 1000 × 800, not stated for 003) natural convection gives
A ≈ 7.92 m², ΔT ≈ 9.6 °C ≤ 10 °C, so the rule picks filters, yet the example
has fans, three thermostats and a 12-way THF strip. Also, the fans and
thermostats are themselves AC loads in the heat total. *Default:* decide
ventilation from the heat of everything except the ventilation parts, apply the
rule, and set `ventilation: forced` on 003 in the example. Alternatively the
rule may need a margin (e.g. ΔT ≤ 0.9 × (TMax − TInt)).

**Q5 — HWIO contributions don't add up to 17.**
*Workbook:* the rows are L2 switch 1, the six-L1-switch row 10, EXT switch 1, AC aux
contacts 3, DC aux contacts 2 (= 17); cabinet 003 is GPS 1 + 3 + 2 (= 6). The example
sets the L1 row's 10 as a per-row override until the rule behind it is known.

The listed contributions (1 per L2/EXT switch, 3 AC aux, 2 DC aux) give 7 for
cabinet 001, while the library example gives an L1 switch `hwio_points: 1`.
*Default:* per-row values come from the library (`hwio_points` per unit) and
from the commodity catalogue for aux contacts; I'll fit them to 17/17/6 once
Q1's data arrives. Note XDIN = 40 = 17 + 17 + 6, so XDIN looks like "total
project HWIO"; confirm, and confirm the WS console contributes 0.

**Q6 — Terminal quantities without a stated rule.**
X4-DC1/DC2 "rounded up to 32 in network cabinets" (from 28; rounding step
unknown), THF 12 vs 5, X-AC and X-DC 6 vs 4, XIP 40/40/12, XDIN 40.
*Default:* implement the rules that are stated; for the rest, take defaults by
panel `kind` (network/control/console) from the example values, overridable by
`terminal_overrides`. Please give the real rules if they exist.

**Q7 — Branch MCB rating.** Column P is ⌈O⌉ but the catalogue only has
1/2/6/10/16 A. *Default:* rating = smallest catalogue size ≥ max(min_branch_mcb_a, ⌈O⌉).

**Q8 — Fan throughput: per fan or per cabinet?** 716 m³/h is compared with each
cabinet's requirement and 3 × 716 is used for the line-up, but each cabinet has
2 fans. *Default:* 716 m³/h is the cabinet's total (the fan pair); the library
`fan.airflow_m3h` is per fan and the check uses the pair's figure. Please confirm.

**Q9 — Fixed print areas.** A1:L97, A1:M66, A1:N70 fit the example only.
*Default:* compute print areas from the last used row and column.

**Q10 — Revision comparison input (OUT-8).** *Default:* both a manual list in
the panel file (`revision.highlight`) and `bomgen build --compare previous.xlsx`
that highlights cells whose value changed.

**Q11 — Calculation sheet header details.** The `<scope>` in "Power Consumption
for <scope>" and the calc-sheet header font size are not defined. *Default:*
scope is a per-document field in `project.yaml` (e.g. "GIS Substation PSA
System"); project name bold at 20 pt on calculation sheets. *M5:* 20 pt is the
cap; a calculation sheet uses the largest size whose three header lines, scaled
with the sheet's print scale, fit between the header and top margins (17 pt on
Power Consumption and Heat Dissipation, 11 pt on Heat Calculations).

**Q12 — Tags that don't fit `<PANEL>-<LEVEL>-<TYPE>-<LAN><NN>`.** FOPP
(`PSA1-FOPP-CCR-A01`) and gateways (`PSA1-DHPCC-GW-1`, numbered by LAN index).
*Default:* optional `tag_pattern` per library device with fields `{prefix}`,
`{level}`, `{type}`, `{lan}`, `{lan_index}`, `{nn}`; panel `tag` override wins.

**Q13 — Single-fed external DC loads.** The annunciator is loose material but its
QCOD-1, X-ANN strip and change-over diodes sit in cabinet 003. *Default:*
`loose_material.items[].fed_from: psa3` decides which panel gets the QCOD
circuit, and the load appears in "Power Consumption for External Equipment" and
"PSA Auxiliary Equipment" (excluded from the fan check).

**Q14 — Merge examples mix sheets.** "Formatting → Merges" lists cell ranges from
different sheets (B4:B7 FOPP on 001, B6:B10 Axion on 003, B49:B50 annunciator on
sheet 4). *Default:* merges are computed from parent/child spans; the listed
ranges become golden assertions per sheet once Q1's data fixes row positions.

**Q15 — How to evaluate formulas in tests.** *Default:* `pycel` (pure Python,
dev dependency) to evaluate the workbook in pytest; optionally a LibreOffice
headless recalc job later to prove "opens without repair" (OUT-1).

**Q16 — UI platform.** *Resolved 2026-10-28:* Ali wants an installable,
shareable Windows app whose UI is designed with the impeccable skill, with
device-library updates shipped as packages (M8–M11). *Proposed stack:* ADR 0007
(pywebview + PyInstaller + Inno Setup) and ADR 0008 (`.bomlib` packages).

**Q17 — Writer library (ADR 0003).** *Resolved 2026-10-28:* Ali chose
XlsxWriter for writing and openpyxl for reading back in tests.

**Q18 — Who publishes library updates, and must they be signed?** *Default:*
you (or a named owner) build `.bomlib` packages with `bomgen library pack`;
packages carry checksums but no signature. If packages will travel by email or
shared drives, I suggest signing them with an Ed25519 key you hold, so the app
rejects tampered or unofficial libraries.

**Q19 — Installer code signing.** Unsigned installers trigger a Windows
SmartScreen warning. *Default:* ship unsigned with instructions; add signing if
you have (or buy) a code-signing certificate or use Azure Trusted Signing.

**Q20 — Install scope and Windows versions.** *Default:* per-user install, no
admin rights, Windows 10 (21H2+) and 11, 64-bit; WebView2 runtime is part of
both and the installer bootstraps it if it's missing.

**Q21 — Should projects travel with the library?** *Default:* a project file
records the library name and version; when sharing a project with someone on
an older library, the app tells them which `.bomlib` to import. Alternatively
a project can be exported as a bundle that includes its library snapshot.


**Q22 — Mistakes in the example workbook.** *Resolved 2026-10-28:* Ali: "fix it". The
generator writes the corrected values and the golden tests expect them: cabinet-1
Power Consumption AC rows reference cabinet 1's own BOM (the workbook points at
`Panel 3`); the External Equipment DC row divides by 125 V (not 230 V); `PSA2-XPS`
uses UT-2.5-MTD code 3064085 (not 3064086); `Panel 3`'s title reads 003; the
XRTAC-C1…C6 strips sit with the other group G strips before grounding; the WS QCOD
branch MCBs are 2 A, A9F74202 (the workbook text says 2A but uses the 1 A code).

**Q23 — Issued sheets differ from their masters.** Issued sheets `1`/`2` list the EXT
switch as a Ruggedcom RST-2228 and the L2 1G/100M MM SFPs as 18/6; the masters list a
SEL-2730M and 15/2. *Default:* the masters, because Power Consumption reads them and
they reproduce the spec's totals. Waiting for Ali.

**Q24 — Document register per project or per substation.** *Resolved 2026-10-28:*
per project, listing the documents per substation (ADR 0012).

**Q25 — Blank plates in the BOM.** *Resolved 2026-10-28:* Ali: not in the BOM; the
blank space only counts toward the panel's usable 32U (ADR 0013).

**Q26 — Where common devices go.** *Resolved 2026-10-28:* Ali: in the same panels as
the A/B pairs, not in their own panel (ADR 0013, rule R6).

**Q27 — Ring topology rule.** *Resolved 2026-10-28 by default:* two ports per ring,
`ring_max_switches` 6, both user-editable (ADR 0013).

**Q28 — L1 uplinks in a star.** *Resolved 2026-10-28:* Ali: one uplink from each L1
switch to its own L2 side, and the A and B switches of a pair interconnected
(ADR 0013, rule R1).

**Q32 — Cable managers against the usable 32U.** Cable managers are 1U each,
nine per network cabinet today (spec: "roughly one per rack-mounted switch/patch
panel"). *Resolved 2026-10-28:* Ali: they count against the 32U. Each rack switch,
firewall or patch panel unit carries a 1U cable manager directly under it as one
block with no blank plate inside (ADR 0013); generated panels take the
cable-manager count from the layout.

**Q33 — FOPP-96SM rack height.** The datasheet was not found; the device database
assumed 2U from Hubbell's 48-fibre 1U unit (`data/device-db/`, PR #18).
*Resolved 2026-10-28:* Ali: 1U. A3 and A2 update the device database and the example
library (done in #33: FOPP-96SM `height_u: 1`).

**Q34 — Group E–H rules the spec states only by example** (M3; ADR 0014).
*Resolved 2026-10-28:* Ali accepted all four defaults below, including no XDIN row
when the HWIO total is 0 and no override is set:
1. Strips follow the order of the example's group G rows ('Panel 1', 'Panel 3'): the
   fixed strips, then the device strips (library `terminals`) after X-ANN and before
   XIP: the per-unit strips (Axion DI slots XDIPD–XDIPG) in group B order, then
   XDIN, then the per-serial-port strips (XRTAC-C1…C6). A rule without `{n}` or
   `{slot}` gives one strip of count × units.
2. XDIN appears with the DI slot strips. *Default:* its quantity is the
   substation's HWIO total (17 + 17 + 6 = 40, the spec's "hardwired DI count");
   `terminal_overrides` wins. Its text is fixed: "Knife Disconnect Terminal Blocks
   For DI Negative". With an HWIO total of 0 and no override, no XDIN row is written.
3. The console's aux contacts carry HWIO 0 (`Aux`!H21 and H31 are blank); other
   kinds count 1 per AC aux contact and 2 for the DC mains.
4. Descriptions are written one way in every cabinet: MCBs "2A, 2P MCB For …"
   (the spec's example reads "2A,2P", the workbook mixes both), spares "SPARE",
   one text per terminal strip, the console's CINC "Main Auxiliary AC Supply"
   (`Aux` reads "Non-UPS AC Supply"), and a branch load named by its tag without the
   prefix ("SRV/OAS/EAS PS1"; `Aux` reads "OAS PS1").

**Q29 — Thermostat load and fan airflow in the library defaults.** The device
research (`docs/device-db-findings.md`, items 1 and 2) found that the SK 3110.000
thermostat's "30 W" is a contact switching rating, not a load, and that 716 m³/h is the
SK 3243.100 fan's free-blowing 60 Hz figure. *Resolved 2026-10-28:* Ali: the example
and golden values stay as the issued workbook. Future library default: SK 3110
thermostat 0 W; SK 3243.100 fan 460 m³/h with the SK 3243.200 outlet filter (60 Hz),
so the per-fan airflow changes from 358. Applied when A2 next revises the library
defaults, not to the example.

**Q30 — Where a device's loose items go in the loose-material table.** The workbook
lists the GPS clock's accessories (`Aux` rows 53–57) between the software and the
cables; nothing in the inputs says where they belong. *Default:* the project's
`loose_material.items` in order, then each device's `loose_items` as one block in
panel order (ADR 0014). If the workbook order matters, `loose_material.items` would
need a marker naming the device whose loose items go at that position (A2's schema).

**Q31 — Group A–D rules the spec states only by example** (A1 review of the M2 PR;
defaults in ADR 0014, all in force until Ali answers):
1. The loose-material title line 2, "PSA Panels Loose Material and Auxiliary
   Equipment", is a constant; the spec only says the table has a title block.
   *Done in M1b/M3:* `loose_material.title`, with that text as the default.
2. Which SFP part serves a port: matching speed and media, then the host's make,
   then library order. *Alternative:* name the SFP part on each port allocation.
   Cable managers and serial cables likewise take the first library record of
   their category.
3. Cable managers = one per switch and patch panel unit ("roughly one per
   rack-mounted switch/patch panel"). *Confirm:* firewalls, gateways and RTACs get
   none.
4. Natural ventilation takes 2 vent filters (the workbook's WS console); the spec
   says "vent filters" without a count.
